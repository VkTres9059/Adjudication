"""
Audit Log System — Full traceability for plan changes, claim edits,
payment approvals, and all system actions.
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from core.database import db
from core.auth import get_current_user

router = APIRouter(tags=["audit"])


@router.get("/audit-logs")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    skip: int = 0,
    user: dict = Depends(get_current_user),
):
    """Query audit logs with filters."""
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["$or"] = [
            {"entity_id": entity_id},
            {"details.claim_id": entity_id},
            {"details.plan_id": entity_id},
            {"details.group_id": entity_id},
        ]
    if action:
        query["action"] = {"$regex": action, "$options": "i"}
    if user_id:
        query["user_id"] = user_id
    if date_from:
        query.setdefault("timestamp", {})["$gte"] = date_from
    if date_to:
        query.setdefault("timestamp", {})["$lte"] = date_to

    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).to_list(limit)

    # Enrich with user names
    user_cache = {}
    for log in logs:
        uid = log.get("user_id")
        if uid and uid not in user_cache:
            u = await db.users.find_one({"id": uid}, {"name": 1, "email": 1, "_id": 0})
            user_cache[uid] = u.get("name", u.get("email", "")) if u else ""
        log["user_name"] = user_cache.get(uid, "")

    total = await db.audit_logs.count_documents(query)
    return {"logs": logs, "total": total, "limit": limit, "skip": skip}


@router.get("/audit-logs/summary")
async def audit_summary(user: dict = Depends(get_current_user)):
    """Get audit activity summary by action type."""
    pipe = [
        {"$group": {
            "_id": "$action",
            "count": {"$sum": 1},
            "last_occurrence": {"$max": "$timestamp"},
        }},
        {"$sort": {"count": -1}},
    ]
    summary = await db.audit_logs.aggregate(pipe).to_list(50)
    total = await db.audit_logs.count_documents({})

    return {
        "total_events": total,
        "by_action": [{
            "action": s["_id"],
            "count": s["count"],
            "last_occurrence": s["last_occurrence"],
        } for s in summary],
    }
