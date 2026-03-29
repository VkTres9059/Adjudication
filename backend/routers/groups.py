from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional
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
