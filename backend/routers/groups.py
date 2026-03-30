from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone, timedelta
from typing import Optional
from dateutil.relativedelta import relativedelta
import uuid

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole
from models.schemas import GroupCreate, StopLossConfig, SFTPConfig

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("")
async def create_group(group_data: GroupCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a new employer group."""
    existing = await db.groups.find_one({"tax_id": group_data.tax_id, "status": "active"})
    if existing:
        raise HTTPException(status_code=400, detail="Active group with this Tax ID already exists")

    group_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "id": group_id,
        **group_data.model_dump(),
        "stop_loss": group_data.stop_loss.model_dump() if group_data.stop_loss else None,
        "sftp_config": group_data.sftp_config.model_dump() if group_data.sftp_config else None,
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "created_by": user["id"],
        "surplus_bucket": 0.0,
    }
    await db.groups.insert_one(doc)

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "group_created",
        "user_id": user["id"],
        "timestamp": now,
        "details": {"group_id": group_id, "group_name": group_data.name, "tax_id": group_data.tax_id}
    })

    doc.pop("_id", None)
    return doc


@router.post("/{group_id}/auto-adjust-tiers")
async def auto_adjust_enrollment_tiers(group_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Auto-adjust enrollment tiers based on dependent count.
    EE (employee_only), ES (employee_spouse), EC (employee_child), Family (>2 deps)."""
    group = await db.groups.find_one({"id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(404, "Group not found")

    members = await db.members.find({"group_id": group_id, "status": "active"}, {"_id": 0}).to_list(100000)
    subscribers = {m["member_id"]: m for m in members if m.get("relationship") == "subscriber"}
    dependents = [m for m in members if m.get("relationship") != "subscriber"]

    # Group dependents by subscriber
    dep_by_sub = {}
    for d in dependents:
        sub_id = d.get("subscriber_id", d.get("member_id", ""))
        dep_by_sub.setdefault(sub_id, []).append(d)

    adjustments = []
    for sub_id, sub in subscribers.items():
        deps = dep_by_sub.get(sub_id, [])
        dep_count = len(deps)
        has_spouse = any(d.get("relationship") == "spouse" for d in deps)
        has_child = any(d.get("relationship") in ("child", "dependent") for d in deps)

        if dep_count == 0:
            new_tier = "employee_only"
        elif dep_count >= 2 or (has_spouse and has_child):
            new_tier = "family"
        elif has_spouse:
            new_tier = "employee_spouse"
        elif has_child:
            new_tier = "employee_child"
        else:
            new_tier = "employee_only"

        current_tier = sub.get("enrollment_tier", "employee_only")
        if current_tier != new_tier:
            await db.members.update_one({"member_id": sub_id}, {"$set": {"enrollment_tier": new_tier}})
            adjustments.append({"member_id": sub_id, "from": current_tier, "to": new_tier})

    return {"group_id": group_id, "adjustments": adjustments, "total_adjusted": len(adjustments)}


@router.get("")
async def list_groups(
    status: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"tax_id": {"$regex": search, "$options": "i"}},
        ]
    groups = await db.groups.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
    return groups


@router.get("/{group_id}")
async def get_group(group_id: str, user: dict = Depends(get_current_user)):
    group = await db.groups.find_one({"id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    plans = []
    for pid in group.get("plan_ids", []):
        plan = await db.plans.find_one({"id": pid}, {"_id": 0})
        if plan:
            plans.append(plan)
    group["attached_plans"] = plans

    member_count = await db.members.count_documents({"group_id": group_id})
    group["member_count"] = member_count

    return group


@router.put("/{group_id}")
async def update_group(group_id: str, group_data: GroupCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    existing = await db.groups.find_one({"id": group_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Group not found")

    update_doc = {
        **group_data.model_dump(),
        "stop_loss": group_data.stop_loss.model_dump() if group_data.stop_loss else existing.get("stop_loss"),
        "sftp_config": group_data.sftp_config.model_dump() if group_data.sftp_config else existing.get("sftp_config"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.groups.update_one({"id": group_id}, {"$set": update_doc})
    updated = await db.groups.find_one({"id": group_id}, {"_id": 0})
    return updated


@router.post("/{group_id}/attach-plan")
async def attach_plan_to_group(group_id: str, plan_id: str = Query(...), user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Attach a plan to a group."""
    group = await db.groups.find_one({"id": group_id})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    plan = await db.plans.find_one({"id": plan_id})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan_ids = group.get("plan_ids", [])
    if plan_id in plan_ids:
        raise HTTPException(status_code=400, detail="Plan already attached to this group")

    plan_ids.append(plan_id)
    await db.groups.update_one({"id": group_id}, {"$set": {"plan_ids": plan_ids, "updated_at": datetime.now(timezone.utc).isoformat()}})
    await db.plans.update_one({"id": plan_id}, {"$set": {"group_id": group_id}})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "plan_attached_to_group",
        "user_id": user["id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {"group_id": group_id, "plan_id": plan_id, "plan_name": plan.get("name", "")}
    })

    return {"message": "Plan attached", "group_id": group_id, "plan_id": plan_id}


@router.delete("/{group_id}/detach-plan")
async def detach_plan_from_group(group_id: str, plan_id: str = Query(...), user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Detach a plan from a group."""
    group = await db.groups.find_one({"id": group_id})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    plan_ids = group.get("plan_ids", [])
    if plan_id not in plan_ids:
        raise HTTPException(status_code=400, detail="Plan not attached to this group")

    plan_ids.remove(plan_id)
    await db.groups.update_one({"id": group_id}, {"$set": {"plan_ids": plan_ids, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "Plan detached", "group_id": group_id, "plan_id": plan_id}


@router.put("/{group_id}/stop-loss")
async def update_stop_loss(group_id: str, stop_loss: StopLossConfig, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Update group stop-loss configuration."""
    group = await db.groups.find_one({"id": group_id})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    await db.groups.update_one({"id": group_id}, {"$set": {"stop_loss": stop_loss.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "Stop-loss updated", "stop_loss": stop_loss.model_dump()}


@router.put("/{group_id}/sftp")
async def update_sftp_config(group_id: str, sftp: SFTPConfig, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Update group SFTP scheduler configuration."""
    group = await db.groups.find_one({"id": group_id})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    await db.groups.update_one({"id": group_id}, {"$set": {"sftp_config": sftp.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "SFTP config updated", "sftp_config": sftp.model_dump()}


# ── Level Funded Claims Reserve ──

@router.get("/{group_id}/reserve-fund")
async def get_reserve_fund(group_id: str, user: dict = Depends(get_current_user)):
    """Get the claims reserve fund status for a level-funded group."""
    group = await db.groups.find_one({"id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.get("funding_type") != "level_funded":
        raise HTTPException(400, "Reserve fund only applies to level-funded groups")

    claims_fund_monthly = float(group.get("claims_fund_monthly", 0))
    effective = group.get("effective_date", "")

    # Calculate months since effective
    try:
        eff_date = datetime.fromisoformat(effective)
    except (ValueError, TypeError):
        eff_date = datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    months_active = max(1, (now.year - eff_date.year) * 12 + (now.month - eff_date.month) + 1)
    total_deposited = claims_fund_monthly * months_active

    # Get total claims paid for this group
    members = await db.members.find({"group_id": group_id}, {"member_id": 1, "_id": 0}).to_list(100000)
    mids = [m["member_id"] for m in members]

    pipeline = [
        {"$match": {"member_id": {"$in": mids}, "status": {"$in": ["approved", "paid"]}}},
        {"$group": {"_id": None, "total_paid": {"$sum": "$total_paid"}, "count": {"$sum": 1}}},
    ]
    agg = await db.claims.aggregate(pipeline).to_list(1)
    total_claims_paid = round(agg[0]["total_paid"], 2) if agg else 0
    claim_count = agg[0]["count"] if agg else 0

    balance = round(total_deposited - total_claims_paid, 2)
    in_deficit = balance < 0

    # Monthly breakdown (last 6 months)
    monthly = []
    for i in range(min(6, months_active)):
        month_dt = now.replace(day=1) - relativedelta(months=i)
        month_start = month_dt.strftime("%Y-%m-01")
        month_end = (month_dt.replace(day=28) + timedelta(days=4)).replace(day=1).strftime("%Y-%m-01")
        m_pipeline = [
            {"$match": {"member_id": {"$in": mids}, "status": {"$in": ["approved", "paid"]},
                         "adjudicated_at": {"$gte": month_start, "$lt": month_end}}},
            {"$group": {"_id": None, "paid": {"$sum": "$total_paid"}, "count": {"$sum": 1}}},
        ]
        m_agg = await db.claims.aggregate(m_pipeline).to_list(1)
        monthly.append({
            "month": month_dt.strftime("%Y-%m"),
            "deposited": claims_fund_monthly,
            "claims_paid": round(m_agg[0]["paid"], 2) if m_agg else 0,
            "claim_count": m_agg[0]["count"] if m_agg else 0,
        })
    monthly.reverse()

    # Flag for stop-loss review if in deficit
    stop_loss = group.get("stop_loss") or {}
    aggregate_att = stop_loss.get("aggregate_attachment_point", 0)
    needs_stop_loss_review = in_deficit or (aggregate_att > 0 and total_claims_paid > aggregate_att)

    return {
        "group_id": group_id,
        "group_name": group.get("name", ""),
        "funding_type": "level_funded",
        "claims_fund_monthly": claims_fund_monthly,
        "months_active": months_active,
        "total_deposited": round(total_deposited, 2),
        "total_claims_paid": total_claims_paid,
        "claim_count": claim_count,
        "balance": balance,
        "in_deficit": in_deficit,
        "needs_stop_loss_review": needs_stop_loss_review,
        "monthly_breakdown": monthly,
    }


@router.post("/{group_id}/reserve-deposit")
async def manual_reserve_deposit(
    group_id: str,
    amount: float = Query(..., gt=0),
    description: str = Query("Manual deposit"),
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Record a manual deposit into the claims reserve fund."""
    group = await db.groups.find_one({"id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(404, "Group not found")

    now = datetime.now(timezone.utc).isoformat()
    await db.reserve_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "group_id": group_id,
        "type": "deposit",
        "amount": amount,
        "description": description,
        "created_by": user["id"],
        "created_at": now,
    })
    return {"status": "deposited", "amount": amount}



@router.get("/{group_id}/pulse")
async def group_pulse_analytics(group_id: str, user: dict = Depends(get_current_user)):
    """Get group-level Pulse analytics."""
    group = await db.groups.find_one({"id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    member_count = await db.members.count_documents({"group_id": group_id})
    members = await db.members.find({"group_id": group_id}, {"member_id": 1, "_id": 0}).to_list(100000)
    member_ids = [m["member_id"] for m in members]

    total_claims = await db.claims.count_documents({"member_id": {"$in": member_ids}})
    approved_claims = await db.claims.count_documents({"member_id": {"$in": member_ids}, "status": "approved"})

    pipeline_financials = [
        {"$match": {"member_id": {"$in": member_ids}}},
        {"$group": {"_id": None, "total_billed": {"$sum": "$total_billed"}, "total_paid": {"$sum": "$total_paid"}, "total_allowed": {"$sum": "$total_allowed"}}}
    ]
    fin = await db.claims.aggregate(pipeline_financials).to_list(1)
    financials = fin[0] if fin else {"total_billed": 0, "total_paid": 0, "total_allowed": 0}

    pipeline_types = [
        {"$match": {"member_id": {"$in": member_ids}}},
        {"$group": {"_id": "$claim_type", "count": {"$sum": 1}, "total_paid": {"$sum": "$total_paid"}}},
    ]
    by_type = await db.claims.aggregate(pipeline_types).to_list(10)

    is_mec_group = False
    for pid in group.get("plan_ids", []):
        p = await db.plans.find_one({"id": pid, "plan_template": "mec_1"}, {"_id": 0})
        if p:
            is_mec_group = True
            break

    total_paid_val = financials.get("total_paid", 0)
    total_premium = group.get("total_premium", 0)
    mgu_fees = group.get("mgu_fees", 0)

    if is_mec_group:
        surplus = max(0, total_premium - (mgu_fees + total_paid_val))
    else:
        stop_loss = group.get("stop_loss") or {}
        aggregate_att = stop_loss.get("aggregate_attachment_point", 0)
        surplus = max(0, aggregate_att - total_paid_val) if aggregate_att > 0 else 0

    if is_mec_group:
        stop_loss_data = {
            "specific_deductible": 0,
            "aggregate_attachment_point": 0,
            "total_paid_ytd": round(total_paid_val, 2),
            "surplus_bucket": round(surplus, 2),
            "utilization_pct": 0,
            "total_premium": round(total_premium, 2),
            "mgu_fees": round(mgu_fees, 2),
        }
    else:
        stop_loss = group.get("stop_loss") or {}
        specific_ded = stop_loss.get("specific_deductible", 0)
        aggregate_att = stop_loss.get("aggregate_attachment_point", 0)
        stop_loss_data = {
            "specific_deductible": specific_ded,
            "aggregate_attachment_point": aggregate_att,
            "total_paid_ytd": round(total_paid_val, 2),
            "surplus_bucket": round(surplus, 2),
            "utilization_pct": round(total_paid_val / aggregate_att * 100, 1) if aggregate_att > 0 else 0,
        }

    return {
        "group_id": group_id,
        "group_name": group.get("name", ""),
        "is_mec": is_mec_group,
        "member_count": member_count,
        "total_claims": total_claims,
        "approved_claims": approved_claims,
        "total_billed": round(financials.get("total_billed", 0), 2),
        "total_paid": round(financials.get("total_paid", 0), 2),
        "total_savings": round(financials.get("total_billed", 0) - financials.get("total_paid", 0), 2),
        "claims_by_type": [{"type": c["_id"], "count": c["count"], "paid": round(c["total_paid"], 2)} for c in by_type],
        "stop_loss": stop_loss_data,
        "pmpm": round(total_paid_val / max(member_count, 1), 2),
    }
