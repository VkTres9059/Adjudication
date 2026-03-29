from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole, ClaimStatus
from models.schemas import DuplicateAlert
from services.adjudication import adjudicate_claim

router = APIRouter(prefix="/duplicates", tags=["duplicates"])


@router.get("", response_model=List[DuplicateAlert])
async def list_duplicate_alerts(
    alert_status: Optional[str] = None,
    duplicate_type: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if alert_status:
        query["status"] = alert_status
    if duplicate_type:
        query["duplicate_type"] = duplicate_type

    alerts = await db.duplicate_alerts.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [DuplicateAlert(**a) for a in alerts]


@router.post("/{alert_id}/resolve")
async def resolve_duplicate_alert(
    alert_id: str,
    resolution: str,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR, UserRole.REVIEWER]))
):
    alert = await db.duplicate_alerts.find_one({"id": alert_id}, {"_id": 0})
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")

    now = datetime.now(timezone.utc).isoformat()

    await db.duplicate_alerts.update_one(
        {"id": alert_id},
        {"$set": {
            "status": resolution,
            "reviewed_by": user["id"],
            "reviewed_at": now
        }}
    )

    if resolution == "not_duplicate":
        claim = await db.claims.find_one({"id": alert["claim_id"]}, {"_id": 0})
        if claim and claim["status"] in [ClaimStatus.PENDED.value, ClaimStatus.DUPLICATE.value]:
            member = await db.members.find_one({"member_id": claim["member_id"]}, {"_id": 0})
            plan = await db.plans.find_one({"id": member["plan_id"]}, {"_id": 0})

            result = await adjudicate_claim(claim, plan, member)
            result["adjudication_notes"] = claim.get("adjudication_notes", []) + [f"DUPLICATE CLEARED by {user['name']}"]
            result["adjudicated_at"] = now

            await db.claims.update_one({"id": alert["claim_id"]}, {"$set": result})

    return {"status": "success", "resolution": resolution}
