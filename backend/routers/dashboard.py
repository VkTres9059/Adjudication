from fastapi import APIRouter, Depends, Query
from core.database import db
from core.auth import get_current_user
from models.enums import ClaimStatus
from models.schemas import DashboardMetrics

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(user: dict = Depends(get_current_user)):
    total_claims = await db.claims.count_documents({})
    pending_claims = await db.claims.count_documents({"status": {"$in": [ClaimStatus.PENDING.value, ClaimStatus.PENDED.value, ClaimStatus.IN_REVIEW.value, ClaimStatus.PENDING_REVIEW.value, ClaimStatus.PENDING_ELIGIBILITY.value]}})
    approved_claims = await db.claims.count_documents({"status": ClaimStatus.APPROVED.value})
    denied_claims = await db.claims.count_documents({"status": {"$in": [ClaimStatus.DENIED.value, ClaimStatus.DUPLICATE.value]}})
    held_claims = await db.claims.count_documents({"status": ClaimStatus.MANAGERIAL_HOLD.value})
    duplicate_alerts = await db.duplicate_alerts.count_documents({"status": "pending"})

    pipeline = [
        {"$match": {"status": ClaimStatus.APPROVED.value}},
        {"$group": {"_id": None, "total": {"$sum": "$total_paid"}}}
    ]
    paid_result = await db.claims.aggregate(pipeline).to_list(1)
    total_paid = paid_result[0]["total"] if paid_result else 0

    dup_pipeline = [
        {"$match": {"status": ClaimStatus.DUPLICATE.value}},
        {"$group": {"_id": None, "total": {"$sum": "$total_billed"}}}
    ]
    dup_result = await db.claims.aggregate(dup_pipeline).to_list(1)
    total_saved = dup_result[0]["total"] if dup_result else 0

    auto_adj = await db.claims.count_documents({"status": {"$in": [ClaimStatus.APPROVED.value, ClaimStatus.DENIED.value]}, "duplicate_info": None})
    auto_rate = (auto_adj / total_claims * 100) if total_claims > 0 else 0

    return DashboardMetrics(
        total_claims=total_claims,
        pending_claims=pending_claims,
        approved_claims=approved_claims,
        denied_claims=denied_claims,
        duplicate_alerts=duplicate_alerts,
        held_claims=held_claims,
        total_paid=total_paid,
        total_saved_duplicates=total_saved,
        auto_adjudication_rate=round(auto_rate, 1),
        avg_turnaround_hours=4.2
    )


@router.get("/claims-by-status")
async def get_claims_by_status(user: dict = Depends(get_current_user)):
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    results = await db.claims.aggregate(pipeline).to_list(10)
    return [{"status": r["_id"], "count": r["count"]} for r in results]


@router.get("/claims-by-type")
async def get_claims_by_type(user: dict = Depends(get_current_user)):
    pipeline = [
        {"$group": {"_id": "$claim_type", "count": {"$sum": 1}, "total_billed": {"$sum": "$total_billed"}, "total_paid": {"$sum": "$total_paid"}}}
    ]
    results = await db.claims.aggregate(pipeline).to_list(10)
    return [{"type": r["_id"], "count": r["count"], "total_billed": r["total_billed"], "total_paid": r["total_paid"]} for r in results]


@router.get("/recent-activity")
async def get_recent_activity(limit: int = 10, user: dict = Depends(get_current_user)):
    logs = await db.audit_logs.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs
