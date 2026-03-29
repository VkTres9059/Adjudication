from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional
import uuid

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole, ClaimStatus
from models.schemas import ClaimResponse

router = APIRouter(prefix="/examiner", tags=["examiner"])


@router.get("/queue")
async def get_examiner_queue(user: dict = Depends(get_current_user)):
    """Get claims assigned to the current user or all reviewable claims."""
    query = {
        "status": {"$in": [ClaimStatus.PENDING_REVIEW.value, ClaimStatus.MANAGERIAL_HOLD.value]}
    }
    if user["role"] != "admin":
        query["assigned_to"] = user["id"]

    claims = await db.claims.find(query, {"_id": 0, "created_by": 0}).sort("created_at", 1).to_list(1000)

    now = datetime.now(timezone.utc)
    result = []
    for c in claims:
        created = datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")) if c.get("created_at") else now
        days_in_queue = max(0, (now - created).total_seconds() / 86400)
        c["days_in_queue"] = round(days_in_queue, 1)
        result.append(c)

    result.sort(key=lambda x: (-x["days_in_queue"], -x.get("total_billed", 0)))
    return result


@router.get("/queue/all")
async def get_all_examiner_queues(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Admin view: all claims in review with assignment info."""
    claims = await db.claims.find(
        {"status": {"$in": [ClaimStatus.PENDING_REVIEW.value, ClaimStatus.MANAGERIAL_HOLD.value]}},
        {"_id": 0, "created_by": 0}
    ).sort("created_at", 1).to_list(5000)

    now = datetime.now(timezone.utc)
    for c in claims:
        created = datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")) if c.get("created_at") else now
        c["days_in_queue"] = round(max(0, (now - created).total_seconds() / 86400), 1)

    return claims


@router.post("/queue/{claim_id}/quick-action")
async def examiner_quick_action(claim_id: str, action: str = Query(...), notes: str = Query(default=""), user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """One-click adjudication from the examiner queue."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    now = datetime.now(timezone.utc).isoformat()
    adj_notes = claim.get("adjudication_notes", [])

    if action == "approve":
        adj_notes.append(f"QUICK APPROVED by {user.get('name', user['email'])} from Examiner Queue." + (f" Notes: {notes}" if notes else ""))
        await db.claims.update_one({"id": claim_id}, {"$set": {
            "status": ClaimStatus.APPROVED.value,
            "adjudication_notes": adj_notes,
            "adjudicated_at": now,
        }})
    elif action == "deny":
        adj_notes.append(f"QUICK DENIED by {user.get('name', user['email'])} from Examiner Queue." + (f" Notes: {notes}" if notes else ""))
        await db.claims.update_one({"id": claim_id}, {"$set": {
            "status": ClaimStatus.DENIED.value,
            "adjudication_notes": adj_notes,
            "adjudicated_at": now,
        }})
    elif action == "request_info":
        adj_notes.append(f"INFO REQUESTED by {user.get('name', user['email'])}." + (f" Notes: {notes}" if notes else ""))
        await db.claims.update_one({"id": claim_id}, {"$set": {
            "status": ClaimStatus.PENDED.value,
            "adjudication_notes": adj_notes,
        }})
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use: approve, deny, request_info")

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": f"examiner_quick_{action}",
        "user_id": user["id"],
        "timestamp": now,
        "details": {"claim_id": claim_id, "claim_number": claim.get("claim_number", "")}
    })

    updated = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
    return ClaimResponse(**updated)


@router.get("/performance")
async def examiner_performance(user: dict = Depends(get_current_user)):
    """Examiner performance metrics."""
    examiners = await db.users.find(
        {"role": {"$in": ["admin", "adjudicator"]}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
    ).to_list(500)

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    results = []
    for ex in examiners:
        closed_today = await db.claims.count_documents({
            "adjudicated_at": {"$gte": today_start},
            "status": {"$in": [ClaimStatus.APPROVED.value, ClaimStatus.DENIED.value]},
            "$or": [{"assigned_to": ex["id"]}, {"assigned_to": {"$exists": False}}]
        })

        open_claims = await db.claims.count_documents({
            "assigned_to": ex["id"],
            "status": {"$in": [ClaimStatus.PENDING_REVIEW.value, ClaimStatus.MANAGERIAL_HOLD.value, ClaimStatus.PENDED.value]}
        })

        pipeline = [
            {"$match": {
                "assigned_to": ex["id"],
                "adjudicated_at": {"$ne": None},
                "status": {"$in": ["approved", "denied"]}
            }},
            {"$limit": 50},
            {"$project": {
                "tat_hours": {
                    "$divide": [
                        {"$subtract": [
                            {"$dateFromString": {"dateString": "$adjudicated_at"}},
                            {"$dateFromString": {"dateString": "$created_at"}}
                        ]},
                        3600000
                    ]
                }
            }},
            {"$group": {"_id": None, "avg_tat": {"$avg": "$tat_hours"}}}
        ]
        tat_result = await db.claims.aggregate(pipeline).to_list(1)
        avg_tat = round(tat_result[0]["avg_tat"], 1) if tat_result else 0

        results.append({
            "examiner_id": ex["id"],
            "examiner_name": ex.get("name", ex["email"]),
            "role": ex["role"],
            "open_claims": open_claims,
            "closed_today": closed_today,
            "avg_tat_hours": avg_tat,
        })

    results.sort(key=lambda x: x["open_claims"])
    return results


@router.get("/list")
async def list_examiners(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """List all examiners for the reassignment dropdown."""
    examiners = await db.users.find(
        {"role": {"$in": ["admin", "adjudicator"]}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
    ).to_list(500)
    return examiners
