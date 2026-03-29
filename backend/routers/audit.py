from fastapi import APIRouter, Depends, Query
from typing import Optional
from core.database import db
from core.auth import get_current_user

router = APIRouter(tags=["audit"])


@router.get("/audit-logs")
async def get_audit_logs(
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    user: dict = Depends(get_current_user)
):
    query = {}
    if action:
        query["action"] = action
    if user_id:
        query["user_id"] = user_id

    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs
