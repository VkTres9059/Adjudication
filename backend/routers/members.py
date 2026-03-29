from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import uuid

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole, ClaimStatus
from models.schemas import MemberCreate, MemberResponse
from services.adjudication import adjudicate_claim

router = APIRouter(prefix="/members", tags=["members"])


# --- Eligibility endpoints (static paths FIRST to avoid {member_id} capture) ---

@router.get("/eligibility/reconciliation")
async def eligibility_reconciliation(user: dict = Depends(get_current_user)):
    """Compare MGU Census vs latest TPA 834 feed snapshot."""
    census_members = await db.members.find({"status": "active"}, {"_id": 0, "member_id": 1, "first_name": 1, "last_name": 1, "group_id": 1, "plan_id": 1, "effective_date": 1}).to_list(100000)
    census_ids = {m["member_id"] for m in census_members}

    tpa_feed = await db.tpa_834_feed.find({}, {"_id": 0}).to_list(100000)
    tpa_ids = {m["member_id"] for m in tpa_feed}

    ghost_ids = census_ids - tpa_ids
    unmatched_ids = tpa_ids - census_ids
    matched_ids = census_ids & tpa_ids

    ghost_members = [m for m in census_members if m["member_id"] in ghost_ids]
    unmatched_members = [m for m in tpa_feed if m["member_id"] in unmatched_ids]

    return {
        "census_count": len(census_ids),
        "tpa_feed_count": len(tpa_ids),
        "matched_count": len(matched_ids),
        "ghost_members": ghost_members,
        "unmatched_members": unmatched_members,
        "last_feed_date": (await db.tpa_834_feed.find_one({}, {"_id": 0, "feed_date": 1}, sort=[("feed_date", -1)])) or {},
    }


@router.post("/eligibility/upload-tpa-feed")
async def upload_tpa_feed(file: UploadFile = File(...), user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Upload a TPA 834 feed snapshot for reconciliation comparison."""
    content = await file.read()
    content_str = content.decode('utf-8')
    now = datetime.now(timezone.utc).isoformat()

    await db.tpa_834_feed.delete_many({})

    feed_members = []
    for line in content_str.strip().split('\n'):
        if not line or line.startswith('#'):
            continue
        parts = line.split('|')
        if len(parts) >= 6:
            feed_members.append({
                "member_id": parts[0],
                "first_name": parts[1],
                "last_name": parts[2],
                "dob": parts[3] if len(parts) > 3 else "",
                "group_id": parts[4] if len(parts) > 4 else "",
                "plan_id": parts[5] if len(parts) > 5 else "",
                "effective_date": parts[6] if len(parts) > 6 else "",
                "termination_date": parts[7] if len(parts) > 7 else None,
                "feed_date": now,
            })

    if feed_members:
        await db.tpa_834_feed.insert_many(feed_members)

    await db.member_audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "action": "tpa_feed_uploaded",
        "user_id": user["id"],
        "details": {"member_count": len(feed_members)},
        "timestamp": now,
    })

    return {"members_loaded": len(feed_members), "feed_date": now}


@router.get("/eligibility/retro-terms")
async def retro_term_monitor(user: dict = Depends(get_current_user)):
    """Scan for retro-terminated members and identify claims paid after term date."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    retro_members = await db.members.find(
        {"termination_date": {"$ne": None, "$lt": now_str}, "status": {"$in": ["active", "terminated"]}},
        {"_id": 0}
    ).to_list(10000)

    results = []
    for m in retro_members:
        term_date = m.get("termination_date", "")
        if not term_date:
            continue

        claims_after_term = await db.claims.find(
            {"member_id": m["member_id"], "service_date_from": {"$gt": term_date}, "status": "approved"},
            {"_id": 0, "id": 1, "claim_number": 1, "total_paid": 1, "service_date_from": 1, "provider_name": 1}
        ).to_list(1000)

        if claims_after_term:
            clawback_total = sum(c.get("total_paid", 0) for c in claims_after_term)
            existing_refund = await db.clawback_ledger.find_one(
                {"member_id": m["member_id"]}, {"_id": 0, "status": 1}
            )
            results.append({
                "member_id": m["member_id"],
                "first_name": m.get("first_name", ""),
                "last_name": m.get("last_name", ""),
                "group_id": m.get("group_id", ""),
                "termination_date": term_date,
                "claims_after_term": claims_after_term,
                "clawback_total": round(clawback_total, 2),
                "refund_status": existing_refund.get("status") if existing_refund else None,
            })

    return results


@router.get("/eligibility/age-out-alerts")
async def age_out_alerts(user: dict = Depends(get_current_user)):
    """Find dependents turning 26 within the next 30 days."""
    today = datetime.now(timezone.utc).date()
    cutoff_date = today + timedelta(days=30)

    dependents = await db.members.find(
        {"relationship": {"$in": ["child", "dependent"]}, "status": "active"},
        {"_id": 0}
    ).to_list(100000)

    age_out_list = []
    for dep in dependents:
        dob_str = dep.get("dob", "")
        if not dob_str:
            continue
        try:
            dob = datetime.fromisoformat(dob_str).date()
            birthday_26 = dob.replace(year=dob.year + 26)
            if today <= birthday_26 <= cutoff_date:
                days_until = (birthday_26 - today).days
                age_out_list.append({
                    "member_id": dep["member_id"],
                    "first_name": dep.get("first_name", ""),
                    "last_name": dep.get("last_name", ""),
                    "dob": dob_str,
                    "group_id": dep.get("group_id", ""),
                    "age_out_date": birthday_26.isoformat(),
                    "days_until": days_until,
                })
        except (ValueError, OverflowError):
            continue

    age_out_list.sort(key=lambda x: x["days_until"])
    return age_out_list


# --- Member CRUD ---

@router.post("", response_model=MemberResponse)
async def create_member(member_data: MemberCreate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    existing = await db.members.find_one({"member_id": member_data.member_id})
    if existing:
        raise HTTPException(status_code=400, detail="Member ID already exists")

    member_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    member_doc = {
        "id": member_id,
        **member_data.model_dump(),
        "status": "active",
        "created_at": now,
        "updated_at": now
    }

    await db.members.insert_one(member_doc)

    await db.member_audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "member_id": member_data.member_id,
        "action": "member_added",
        "user_id": user["id"],
        "details": {"first_name": member_data.first_name, "last_name": member_data.last_name, "effective_date": member_data.effective_date, "group_id": member_data.group_id},
        "timestamp": now,
    })

    return MemberResponse(**{k: v for k, v in member_doc.items() if k not in ["_id", "address", "ssn_last4", "updated_at"]})


@router.get("", response_model=List[MemberResponse])
async def list_members(
    group_id: Optional[str] = None,
    plan_id: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if group_id:
        query["group_id"] = group_id
    if plan_id:
        query["plan_id"] = plan_id
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"member_id": {"$regex": search, "$options": "i"}}
        ]

    members = await db.members.find(query, {"_id": 0, "address": 0, "ssn_last4": 0}).to_list(1000)
    return [MemberResponse(**m) for m in members]


@router.get("/{member_id}", response_model=MemberResponse)
async def get_member(member_id: str, user: dict = Depends(get_current_user)):
    member = await db.members.find_one({"member_id": member_id}, {"_id": 0, "ssn_last4": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return MemberResponse(**{k: v for k, v in member.items() if k not in ["address", "updated_at"]})


@router.get("/{member_id}/audit-trail")
async def member_audit_trail(member_id: str, user: dict = Depends(get_current_user)):
    """Get the full eligibility audit trail for a member."""
    trail = await db.member_audit_trail.find(
        {"member_id": member_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(500)
    return trail


@router.get("/{member_id}/accumulators")
async def member_accumulators(member_id: str, user: dict = Depends(get_current_user)):
    """Live financial accumulators: Individual Deductible, Family Deductible, OOP Max."""
    member = await db.members.find_one({"member_id": member_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    plan = await db.plans.find_one({"id": member.get("plan_id")}, {"_id": 0})
    if not plan:
        return {
            "individual_deductible": {"used": 0, "max": 0},
            "family_deductible": {"used": 0, "max": 0, "contributions": []},
            "oop_max": {"used": 0, "max": 0},
        }

    ded_ind_max = plan.get("deductible_individual", 500)
    ded_fam_max = plan.get("deductible_family", 1500)
    oop_ind_max = plan.get("oop_max_individual", 5000)

    # Individual accumulators from paid claims
    paid_claims = await db.claims.find(
        {"member_id": member_id, "status": "approved"},
        {"_id": 0, "total_paid": 1, "total_allowed": 1, "member_responsibility": 1, "total_billed": 1}
    ).to_list(100000)

    ind_ded_used = 0.0
    ind_oop_used = 0.0
    for c in paid_claims:
        resp = c.get("member_responsibility", 0) or 0
        ind_oop_used += resp
        # Deductible contribution: up to the plan deductible cap
        ind_ded_used += min(resp, max(0, ded_ind_max - ind_ded_used))

    ind_ded_used = min(ind_ded_used, ded_ind_max)
    ind_oop_used = min(ind_oop_used, oop_ind_max)

    # Family deductible: all members in same group+plan
    group_id = member.get("group_id", "")
    plan_id = member.get("plan_id", "")
    family_members = []
    fam_ded_used = 0.0
    contributions = []

    if group_id and plan_id:
        family_members = await db.members.find(
            {"group_id": group_id, "plan_id": plan_id},
            {"_id": 0, "member_id": 1, "first_name": 1, "last_name": 1, "relationship": 1}
        ).to_list(100)

        for fm in family_members:
            fm_claims = await db.claims.find(
                {"member_id": fm["member_id"], "status": "approved"},
                {"_id": 0, "member_responsibility": 1}
            ).to_list(100000)
            fm_total = sum(c.get("member_responsibility", 0) or 0 for c in fm_claims)
            fm_contribution = min(fm_total, ded_fam_max)
            fam_ded_used += fm_contribution
            contributions.append({
                "member_id": fm["member_id"],
                "name": f"{fm.get('first_name', '')} {fm.get('last_name', '')}",
                "relationship": fm.get("relationship", "unknown"),
                "contribution": round(fm_contribution, 2),
            })

    fam_ded_used = min(fam_ded_used, ded_fam_max)

    return {
        "individual_deductible": {"used": round(ind_ded_used, 2), "max": ded_ind_max},
        "family_deductible": {"used": round(fam_ded_used, 2), "max": ded_fam_max, "contributions": contributions},
        "oop_max": {"used": round(ind_oop_used, 2), "max": oop_ind_max},
    }


@router.get("/{member_id}/claims-history")
async def member_claims_history(member_id: str, user: dict = Depends(get_current_user)):
    """All claims for a member with service date, CPT, status, amounts."""
    member = await db.members.find_one({"member_id": member_id}, {"_id": 0, "member_id": 1})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    claims = await db.claims.find(
        {"member_id": member_id},
        {"_id": 0, "created_by": 0}
    ).sort("service_date_from", -1).to_list(1000)

    result = []
    for c in claims:
        service_lines = c.get("service_lines", [])
        cpt_codes = [sl.get("cpt_code", "") for sl in service_lines if sl.get("cpt_code")]
        result.append({
            "id": c.get("id", ""),
            "claim_number": c.get("claim_number", ""),
            "service_date": c.get("service_date_from", ""),
            "provider_name": c.get("provider_name", ""),
            "cpt_codes": cpt_codes,
            "status": c.get("status", ""),
            "total_billed": c.get("total_billed", 0),
            "total_paid": c.get("total_paid", 0),
            "member_responsibility": c.get("member_responsibility", 0),
            "eligibility_source": c.get("eligibility_source", ""),
            "claim_type": c.get("claim_type", ""),
        })

    return result


@router.get("/{member_id}/dependents")
async def member_dependents(member_id: str, user: dict = Depends(get_current_user)):
    """Get household/family members linked by group_id + plan_id."""
    member = await db.members.find_one({"member_id": member_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    group_id = member.get("group_id", "")
    plan_id = member.get("plan_id", "")

    if not group_id or not plan_id:
        return {"subscriber": member, "dependents": [], "household_size": 1}

    household = await db.members.find(
        {"group_id": group_id, "plan_id": plan_id},
        {"_id": 0}
    ).to_list(100)

    def clean(m):
        return {k: v for k, v in m.items() if k not in ["address", "ssn_last4", "updated_at"]}

    # The queried member is always the "primary" in this view
    subscriber = clean(member)
    seen_ids = {member_id}
    dependents = []

    # If queried member is a dependent, find the actual subscriber
    if member.get("relationship") not in ["subscriber", None, ""]:
        for m in household:
            if m.get("relationship") == "subscriber" and m["member_id"] != member_id:
                subscriber = clean(m)
                seen_ids.add(m["member_id"])
                # Add the queried member as a dependent
                dependents.append(clean(member))
                break

    # Add remaining household members as dependents
    for m in household:
        if m["member_id"] not in seen_ids:
            seen_ids.add(m["member_id"])
            dependents.append(clean(m))

    return {
        "subscriber": subscriber,
        "dependents": dependents,
        "household_size": len(seen_ids),
    }


@router.post("/{member_id}/request-refund")
async def request_provider_refund(member_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Request provider refund for claims paid after retro-term date."""
    member = await db.members.find_one({"member_id": member_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    term_date = member.get("termination_date")
    if not term_date:
        raise HTTPException(status_code=400, detail="Member has no termination date")

    claims = await db.claims.find(
        {"member_id": member_id, "service_date_from": {"$gt": term_date}, "status": "approved"},
        {"_id": 0, "id": 1, "claim_number": 1, "total_paid": 1, "provider_name": 1, "provider_npi": 1}
    ).to_list(1000)

    if not claims:
        raise HTTPException(status_code=400, detail="No claims found after termination date")

    clawback_total = sum(c.get("total_paid", 0) for c in claims)
    now = datetime.now(timezone.utc).isoformat()

    ledger_entry = {
        "id": str(uuid.uuid4()),
        "member_id": member_id,
        "member_name": f"{member.get('first_name', '')} {member.get('last_name', '')}",
        "termination_date": term_date,
        "claims": [{"claim_id": c["id"], "claim_number": c["claim_number"], "paid": c["total_paid"], "provider": c.get("provider_name", "")} for c in claims],
        "total_recovery": round(clawback_total, 2),
        "status": "requested",
        "requested_by": user["id"],
        "requested_at": now,
    }

    await db.clawback_ledger.update_one(
        {"member_id": member_id},
        {"$set": ledger_entry},
        upsert=True
    )

    await db.member_audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "member_id": member_id,
        "action": "refund_requested",
        "user_id": user["id"],
        "details": {"total_recovery": round(clawback_total, 2), "claim_count": len(claims)},
        "timestamp": now,
    })

    return {"message": "Provider refund requested", "total_recovery": round(clawback_total, 2), "claims_affected": len(claims)}
