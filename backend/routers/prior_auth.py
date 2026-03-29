from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from typing import Optional
import uuid

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole
from models.schemas import PriorAuthRequest, PriorAuthDecision

router = APIRouter(prefix="/prior-auth", tags=["prior_auth"])


@router.post("")
async def create_prior_auth(request: PriorAuthRequest, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Submit a prior authorization request."""
    auth_id = str(uuid.uuid4())
    auth_number = f"PA{datetime.now().strftime('%Y%m%d')}{auth_id[:6].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "id": auth_id,
        "auth_number": auth_number,
        **request.model_dump(),
        "status": "pending",
        "created_at": now,
        "created_by": user["id"],
        "decision": None,
        "decision_date": None,
        "decision_by": None,
    }

    await db.prior_authorizations.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("")
async def list_prior_auths(
    status: Optional[str] = None,
    member_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if member_id:
        query["member_id"] = member_id
    auths = await db.prior_authorizations.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return auths


@router.get("/{auth_id}")
async def get_prior_auth(auth_id: str, user: dict = Depends(get_current_user)):
    auth = await db.prior_authorizations.find_one({"id": auth_id}, {"_id": 0})
    if not auth:
        raise HTTPException(status_code=404, detail="Prior authorization not found")
    return auth


@router.post("/{auth_id}/decide")
async def decide_prior_auth(auth_id: str, decision: PriorAuthDecision, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Approve or deny a prior authorization."""
    auth = await db.prior_authorizations.find_one({"id": auth_id})
    if not auth:
        raise HTTPException(status_code=404, detail="Prior authorization not found")

    now = datetime.now(timezone.utc).isoformat()

    await db.prior_authorizations.update_one(
        {"id": auth_id},
        {"$set": {
            "status": decision.decision,
            "decision": decision.model_dump(),
            "decision_date": now,
            "decision_by": user["id"],
        }}
    )

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": f"prior_auth_{decision.decision}",
        "user_id": user["id"],
        "timestamp": now,
        "details": {"auth_id": auth_id, "auth_number": auth.get("auth_number")}
    })

    updated = await db.prior_authorizations.find_one({"id": auth_id}, {"_id": 0})
    return updated
