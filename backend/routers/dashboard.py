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


@router.get("/funding-health")
async def get_funding_health(user: dict = Depends(get_current_user)):
    """Funding Health summary across all groups by funding type."""
    groups = await db.groups.find({"status": "active"}, {"_id": 0}).to_list(1000)

    aso_groups = [g for g in groups if g.get("funding_type") == "aso"]
    lf_groups = [g for g in groups if g.get("funding_type") == "level_funded"]
    fi_groups = [g for g in groups if g.get("funding_type") == "fully_insured"]

    # ASO: Pending Funding vs Paid
    aso_pending_funding = 0
    aso_total_paid = 0
    for g in aso_groups:
        members = await db.members.find({"group_id": g["id"]}, {"member_id": 1, "_id": 0}).to_list(100000)
        mids = [m["member_id"] for m in members]
        if not mids:
            continue
        pipe_pend = [
            {"$match": {"member_id": {"$in": mids}, "status": "approved", "check_run_id": {"$exists": False}}},
            {"$group": {"_id": None, "total": {"$sum": "$total_paid"}}},
        ]
        pipe_paid = [
            {"$match": {"member_id": {"$in": mids}, "status": "paid"}},
            {"$group": {"_id": None, "total": {"$sum": "$total_paid"}}},
        ]
        pend = await db.claims.aggregate(pipe_pend).to_list(1)
        paid = await db.claims.aggregate(pipe_paid).to_list(1)
        aso_pending_funding += pend[0]["total"] if pend else 0
        aso_total_paid += paid[0]["total"] if paid else 0

    # Level Funded: Expected Fund vs Actual Claims
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    lf_expected = 0
    lf_actual = 0
    lf_deficit_groups = []
    for g in lf_groups:
        fund_monthly = float(g.get("claims_fund_monthly", 0))
        eff = g.get("effective_date", "")
        try:
            eff_date = datetime.fromisoformat(eff)
        except (ValueError, TypeError):
            eff_date = now
        months = max(1, (now.year - eff_date.year) * 12 + (now.month - eff_date.month) + 1)
        deposited = fund_monthly * months
        lf_expected += deposited

        members = await db.members.find({"group_id": g["id"]}, {"member_id": 1, "_id": 0}).to_list(100000)
        mids = [m["member_id"] for m in members]
        if mids:
            pipe = [
                {"$match": {"member_id": {"$in": mids}, "status": {"$in": ["approved", "paid"]}}},
                {"$group": {"_id": None, "total": {"$sum": "$total_paid"}}},
            ]
            agg = await db.claims.aggregate(pipe).to_list(1)
            claims_total = agg[0]["total"] if agg else 0
            lf_actual += claims_total
            if claims_total > deposited:
                lf_deficit_groups.append({"group_id": g["id"], "group_name": g.get("name", ""), "deficit": round(claims_total - deposited, 2)})

    return {
        "aso": {
            "group_count": len(aso_groups),
            "pending_funding": round(aso_pending_funding, 2),
            "total_paid": round(aso_total_paid, 2),
        },
        "level_funded": {
            "group_count": len(lf_groups),
            "expected_fund": round(lf_expected, 2),
            "actual_claims": round(lf_actual, 2),
            "surplus": round(lf_expected - lf_actual, 2),
            "deficit_groups": lf_deficit_groups,
        },
        "fully_insured": {
            "group_count": len(fi_groups),
        },
    }
