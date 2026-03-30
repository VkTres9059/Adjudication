from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole, ClaimStatus
from models.schemas import (
    ClaimCreate, ClaimResponse, AdjudicationAction, HoldRequest,
    BatchClaimRequest, COBInfo,
)
from services.adjudication import adjudicate_claim
from services.claims import process_new_claim
from services.examiner import auto_assign_examiner

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post("", response_model=ClaimResponse)
async def create_claim(claim_data: ClaimCreate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    claim_dict = claim_data.model_dump()
    claim_dict["claim_type"] = claim_data.claim_type.value
    service_lines_dicts = [line.model_dump() for line in claim_data.service_lines]

    result = await process_new_claim(claim_dict, service_lines_dicts, user)
    if result is None:
        raise HTTPException(status_code=404, detail="Member plan not found")
    return ClaimResponse(**result)


@router.get("", response_model=List[ClaimResponse])
async def list_claims(
    claim_status: Optional[str] = None,
    claim_type: Optional[str] = None,
    member_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    has_duplicates: Optional[bool] = None,
    limit: int = Query(default=100, le=500),
    skip: int = 0,
    user: dict = Depends(get_current_user)
):
    query = {}
    if claim_status:
        query["status"] = claim_status
    if claim_type:
        query["claim_type"] = claim_type
    if member_id:
        query["member_id"] = member_id
    if date_from:
        query["service_date_from"] = {"$gte": date_from}
    if date_to:
        query["service_date_to"] = {"$lte": date_to}
    if has_duplicates is not None:
        if has_duplicates:
            query["duplicate_info"] = {"$ne": None}
        else:
            query["duplicate_info"] = None

    claims = await db.claims.find(query, {"_id": 0, "created_by": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [ClaimResponse(**c) for c in claims]


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(claim_id: str, user: dict = Depends(get_current_user)):
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return ClaimResponse(**claim)


@router.post("/{claim_id}/adjudicate", response_model=ClaimResponse)
async def adjudicate_claim_action(
    claim_id: str,
    action: AdjudicationAction,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))
):
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    now = datetime.now(timezone.utc).isoformat()
    update_doc = {"adjudicated_at": now}

    if action.action == "approve":
        member = await db.members.find_one({"member_id": claim["member_id"]}, {"_id": 0})
        plan = await db.plans.find_one({"id": member["plan_id"]}, {"_id": 0})
        result = await adjudicate_claim(claim, plan, member)
        update_doc.update(result)
        update_doc["status"] = ClaimStatus.APPROVED.value
        # Stop-loss auto-flag: route to examiner queue
        if result.get("stop_loss_flag"):
            update_doc["stop_loss_flag"] = True
            update_doc["examiner_flag"] = "stop_loss_review"

    elif action.action == "deny":
        update_doc["status"] = ClaimStatus.DENIED.value
        update_doc["total_paid"] = 0
        if action.denial_reason:
            update_doc["adjudication_notes"] = claim.get("adjudication_notes", []) + [f"DENIED: {action.denial_reason}"]

    elif action.action == "pend":
        update_doc["status"] = ClaimStatus.PENDED.value
        if action.notes:
            update_doc["adjudication_notes"] = claim.get("adjudication_notes", []) + [f"PENDED: {action.notes}"]

    elif action.action == "override_duplicate":
        member = await db.members.find_one({"member_id": claim["member_id"]}, {"_id": 0})
        plan = await db.plans.find_one({"id": member["plan_id"]}, {"_id": 0})
        result = await adjudicate_claim(claim, plan, member)
        update_doc.update(result)
        update_doc["status"] = ClaimStatus.APPROVED.value
        update_doc["adjudication_notes"] = claim.get("adjudication_notes", []) + [f"DUPLICATE OVERRIDE by {user['name']}: {action.notes or 'Approved'}"]
        await db.duplicate_alerts.update_many(
            {"claim_id": claim_id},
            {"$set": {"status": "overridden", "reviewed_by": user["id"], "reviewed_at": now}}
        )

    await db.claims.update_one({"id": claim_id}, {"$set": update_doc})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": f"claim_{action.action}",
        "user_id": user["id"],
        "details": {"claim_id": claim_id, "action": action.action, "notes": action.notes},
        "timestamp": now
    })

    updated = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
    return ClaimResponse(**updated)


# --- Hold / Release ---

@router.put("/{claim_id}/hold")
async def place_claim_on_hold(claim_id: str, hold: HoldRequest, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Place a claim on managerial hold."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim["status"] == ClaimStatus.MANAGERIAL_HOLD.value:
        raise HTTPException(status_code=400, detail="Claim is already on hold")

    now = datetime.now(timezone.utc).isoformat()
    hold_info = {
        "reason_code": hold.reason_code,
        "notes": hold.notes or "",
        "placed_by": user["id"],
        "placed_by_name": user.get("name", user["email"]),
        "placed_at": now,
        "previous_status": claim["status"],
    }

    notes = claim.get("adjudication_notes", []) + [
        f"MANAGERIAL HOLD placed by {user.get('name', user['email'])}: {hold.reason_code.replace('_', ' ').title()}" +
        (f" - {hold.notes}" if hold.notes else "")
    ]

    await db.claims.update_one({"id": claim_id}, {"$set": {
        "status": ClaimStatus.MANAGERIAL_HOLD.value,
        "hold_info": hold_info,
        "adjudication_notes": notes,
    }})

    if not claim.get("assigned_to"):
        assignment = await auto_assign_examiner(claim.get("total_billed", 0))
        if assignment:
            await db.claims.update_one({"id": claim_id}, {"$set": assignment})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "claim_hold_placed",
        "user_id": user["id"],
        "timestamp": now,
        "details": {"claim_id": claim_id, "reason": hold.reason_code, "claim_number": claim.get("claim_number", "")}
    })

    updated = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
    return ClaimResponse(**updated)


@router.put("/{claim_id}/release-hold")
async def release_claim_hold(claim_id: str, notes: Optional[str] = Query(default=None), user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Release a claim from managerial hold. Requires admin."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim["status"] != ClaimStatus.MANAGERIAL_HOLD.value:
        raise HTTPException(status_code=400, detail="Claim is not on hold")

    now = datetime.now(timezone.utc).isoformat()
    hold_info = claim.get("hold_info", {})
    previous_status = hold_info.get("previous_status", ClaimStatus.PENDING.value)

    release_notes = claim.get("adjudication_notes", []) + [
        f"HOLD RELEASED by {user.get('name', user['email'])} (Admin)" + (f" - {notes}" if notes else "")
    ]

    await db.claims.update_one({"id": claim_id}, {"$set": {
        "status": previous_status,
        "hold_info": None,
        "adjudication_notes": release_notes,
    }})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "claim_hold_released",
        "user_id": user["id"],
        "timestamp": now,
        "details": {"claim_id": claim_id, "restored_status": previous_status, "claim_number": claim.get("claim_number", "")}
    })

    updated = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
    return ClaimResponse(**updated)


# --- Examiner workspace actions (on claims paths) ---

@router.post("/{claim_id}/force-preventive")
async def force_preventive_override(claim_id: str, notes: Optional[str] = Query(default=None), user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """MEC Examiner: Force preventive flag on a claim."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    now = datetime.now(timezone.utc).isoformat()
    service_lines = claim.get("service_lines", [])
    total_allowed = 0
    total_paid = 0
    for line in service_lines:
        allowed = line.get("billed_amount", line.get("allowed", 0))
        line["is_preventive"] = True
        line["paid"] = allowed
        line["allowed"] = allowed
        line["member_resp"] = 0.0
        line["eob_message"] = "Preventive Service - $0 Member Responsibility (Examiner Override)"
        line["coverage_type"] = "preventive"
        total_allowed += allowed
        total_paid += allowed

    adj_notes = claim.get("adjudication_notes", []) + [
        f"EXAMINER OVERRIDE: Preventive flag forced by {user.get('name', user['email'])}. All lines set to $0 member cost." +
        (f" Notes: {notes}" if notes else "")
    ]

    await db.claims.update_one({"id": claim_id}, {"$set": {
        "status": ClaimStatus.APPROVED.value,
        "total_allowed": round(total_allowed, 2),
        "total_paid": round(total_paid, 2),
        "member_responsibility": 0.0,
        "service_lines": service_lines,
        "adjudication_notes": adj_notes,
        "adjudicated_at": now,
    }})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "examiner_force_preventive",
        "user_id": user["id"],
        "timestamp": now,
        "details": {"claim_id": claim_id, "claim_number": claim.get("claim_number", "")}
    })

    updated = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
    return ClaimResponse(**updated)


@router.post("/{claim_id}/adjust-deductible")
async def adjust_deductible(claim_id: str, amount: float = Query(...), notes: Optional[str] = Query(default=None), user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Standard Plan Examiner: Manually adjust the deductible."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    now = datetime.now(timezone.utc).isoformat()
    original_member_resp = claim.get("member_responsibility", 0)
    original_paid = claim.get("total_paid", 0)

    delta = max(0, original_member_resp) - max(0, amount)
    new_member_resp = max(0, amount)
    new_paid = max(0, original_paid + delta)

    adj_notes = claim.get("adjudication_notes", []) + [
        f"EXAMINER DEDUCTIBLE ADJUSTMENT by {user.get('name', user['email'])}: Member responsibility changed from ${original_member_resp:.2f} to ${new_member_resp:.2f}." +
        (f" Notes: {notes}" if notes else "")
    ]

    await db.claims.update_one({"id": claim_id}, {"$set": {
        "member_responsibility": round(new_member_resp, 2),
        "total_paid": round(new_paid, 2),
        "adjudication_notes": adj_notes,
        "adjudicated_at": now,
    }})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "examiner_adjust_deductible",
        "user_id": user["id"],
        "timestamp": now,
        "details": {"claim_id": claim_id, "old_member_resp": original_member_resp, "new_member_resp": new_member_resp}
    })

    updated = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
    return ClaimResponse(**updated)


@router.post("/{claim_id}/carrier-notification")
async def flag_carrier_notification(claim_id: str, notes: Optional[str] = Query(default=None), user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Stop-Loss Examiner: Flag claim as Specific Notification to Carrier."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    now = datetime.now(timezone.utc).isoformat()
    adj_notes = claim.get("adjudication_notes", []) + [
        f"CARRIER NOTIFICATION flagged by {user.get('name', user['email'])}: Specific attachment point notification sent to carrier." +
        (f" Notes: {notes}" if notes else "")
    ]

    await db.claims.update_one({"id": claim_id}, {"$set": {
        "carrier_notification": True,
        "adjudication_notes": adj_notes,
    }})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "carrier_notification_flagged",
        "user_id": user["id"],
        "timestamp": now,
        "details": {"claim_id": claim_id, "claim_number": claim.get("claim_number", "")}
    })

    updated = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
    return ClaimResponse(**updated)


@router.post("/{claim_id}/reassign")
async def reassign_claim(claim_id: str, examiner_id: str = Query(...), user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Admin: Reassign a claim to a different examiner."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    examiner = await db.users.find_one({"id": examiner_id}, {"_id": 0})
    if not examiner:
        raise HTTPException(status_code=404, detail="Examiner not found")

    now = datetime.now(timezone.utc).isoformat()
    old_assignee = claim.get("assigned_to_name", "Unassigned")
    new_assignee = examiner.get("name", examiner["email"])

    adj_notes = claim.get("adjudication_notes", []) + [
        f"REASSIGNED by {user.get('name', user['email'])}: {old_assignee} -> {new_assignee}"
    ]

    await db.claims.update_one({"id": claim_id}, {"$set": {
        "assigned_to": examiner_id,
        "assigned_to_name": new_assignee,
        "assigned_at": now,
        "adjudication_notes": adj_notes,
    }})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "claim_reassigned",
        "user_id": user["id"],
        "timestamp": now,
        "details": {"claim_id": claim_id, "from": old_assignee, "to": new_assignee}
    })

    updated = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
    return ClaimResponse(**updated)


# --- Pending Eligibility Processing ---

@router.post("/process-pending-eligibility")
async def process_pending_eligibility(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Process pending eligibility queue."""
    now = datetime.now(timezone.utc).isoformat()

    pending_claims = await db.claims.find(
        {"status": ClaimStatus.PENDING_ELIGIBILITY.value},
        {"_id": 0}
    ).to_list(10000)

    released = 0
    denied = 0
    still_pending = 0

    for claim in pending_claims:
        member = await db.members.find_one({"member_id": claim["member_id"]}, {"_id": 0})
        deadline = claim.get("eligibility_deadline", "")

        if member:
            plan = await db.plans.find_one({"id": member["plan_id"]}, {"_id": 0})
            if plan:
                adj_result = await adjudicate_claim(claim, plan, member)
                notes = claim.get("adjudication_notes", []) + [
                    f"ELIGIBILITY CONFIRMED: Member found in census. Auto-released and adjudicated."
                ] + adj_result.get("adjudication_notes", [])
                await db.claims.update_one({"id": claim["id"]}, {"$set": {
                    "status": adj_result["status"],
                    "total_allowed": adj_result["total_allowed"],
                    "total_paid": adj_result["total_paid"],
                    "member_responsibility": adj_result["member_responsibility"],
                    "adjudication_notes": notes,
                    "adjudicated_at": now,
                    "eligibility_deadline": None,
                }})
                released += 1
            else:
                await db.claims.update_one({"id": claim["id"]}, {"$set": {
                    "status": ClaimStatus.DENIED.value,
                    "adjudication_notes": claim.get("adjudication_notes", []) + ["DENIED: Member found but plan not found."],
                    "adjudicated_at": now,
                    "eligibility_deadline": None,
                }})
                denied += 1
        elif deadline and now > deadline:
            await db.claims.update_one({"id": claim["id"]}, {"$set": {
                "status": ClaimStatus.DENIED.value,
                "adjudication_notes": claim.get("adjudication_notes", []) + [
                    f"AUTO-DENIED: 72-hour eligibility window expired. Member {claim['member_id']} not found in census."
                ],
                "adjudicated_at": now,
                "eligibility_deadline": None,
            }})
            denied += 1
        else:
            still_pending += 1

    return {"released": released, "denied": denied, "still_pending": still_pending, "total_processed": len(pending_claims)}


# --- Batch Processing ---

@router.post("/batch")
async def batch_process_claims(batch: BatchClaimRequest, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Process multiple claims in a batch."""
    results = {
        "total": len(batch.claims),
        "created": 0,
        "adjudicated": 0,
        "errors": [],
        "claim_ids": [],
    }

    for i, claim_data in enumerate(batch.claims):
        try:
            claim_dict = claim_data.model_dump()
            claim_dict["claim_type"] = claim_data.claim_type.value
            service_lines_dicts = [line.model_dump() for line in claim_data.service_lines]
            result = await process_new_claim(claim_dict, service_lines_dicts, user)
            results["created"] += 1
            if result:
                results["claim_ids"].append(result.get("id"))
                if result.get("status") in ["approved", "denied"]:
                    results["adjudicated"] += 1
        except Exception as e:
            results["errors"].append({"index": i, "error": str(e)})

    return results


# --- Coordination of Benefits ---

@router.post("/{claim_id}/cob")
async def process_cob(claim_id: str, cob: COBInfo, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Process Coordination of Benefits - apply secondary plan payment."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    remaining = cob.primary_member_resp
    secondary_allowed = claim.get("total_allowed", 0)
    secondary_pays = min(remaining, secondary_allowed - cob.primary_paid)
    secondary_pays = max(0, secondary_pays)
    final_member_resp = max(0, remaining - secondary_pays)

    cob_record = {
        "primary_payer": cob.primary_payer,
        "primary_paid": cob.primary_paid,
        "primary_allowed": cob.primary_allowed,
        "primary_member_resp": cob.primary_member_resp,
        "secondary_paid": round(secondary_pays, 2),
        "final_member_resp": round(final_member_resp, 2),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "processed_by": user.get("id"),
    }

    await db.claims.update_one(
        {"id": claim_id},
        {"$set": {
            "cob_info": cob_record,
            "total_paid": round(claim.get("total_paid", 0) + secondary_pays, 2) if claim.get("status") != "approved" else claim.get("total_paid", 0),
            "member_responsibility": round(final_member_resp, 2),
        }}
    )

    return {
        "claim_id": claim_id,
        "cob": cob_record,
        "total_all_payers": round(cob.primary_paid + secondary_pays, 2),
    }
