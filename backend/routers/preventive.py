from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole
from preventive_services import (
    PREVENTIVE_SERVICES,
    get_preventive_service,
    search_preventive_services,
    get_preventive_by_category,
    evaluate_preventive_claim_line,
    check_preventive_frequency,
    calculate_member_age,
)

router = APIRouter(prefix="/preventive", tags=["preventive"])


@router.get("/services")
async def list_preventive_services(
    category: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all preventive services, optionally filtered by category."""
    if category:
        results = get_preventive_by_category(category)
    else:
        results = [{"code": code, **data} for code, data in PREVENTIVE_SERVICES.items()]
    return {"results": results, "count": len(results)}


@router.get("/search")
async def search_preventive(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=50, le=100),
    user: dict = Depends(get_current_user)
):
    results = search_preventive_services(q, limit)
    return {"results": results, "count": len(results)}


@router.get("/categories")
async def preventive_categories(user: dict = Depends(get_current_user)):
    """Get all preventive service categories with counts."""
    cats = {}
    for code, data in PREVENTIVE_SERVICES.items():
        cat = data.get("category", "Other")
        if cat not in cats:
            cats[cat] = {"count": 0, "subcategories": set()}
        cats[cat]["count"] += 1
        cats[cat]["subcategories"].add(data.get("subcategory", ""))
    for cat in cats:
        cats[cat]["subcategories"] = sorted(cats[cat]["subcategories"])
    return cats


@router.get("/check-eligibility")
async def check_preventive_eligibility(
    cpt_code: str,
    member_id: str,
    service_date: str,
    user: dict = Depends(get_current_user)
):
    """Check if a specific preventive service is eligible for a member."""
    member = await db.members.find_one({"member_id": member_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    age = calculate_member_age(member.get("dob", "2000-01-01"), service_date)
    gender = member.get("gender", "U").lower()
    if gender in ("m", "male"):
        gender = "male"
    elif gender in ("f", "female"):
        gender = "female"

    service = get_preventive_service(cpt_code)
    if not service:
        return {"eligible": False, "reason": "Code not in preventive database", "code": cpt_code}

    eval_result = evaluate_preventive_claim_line(cpt_code, ["Z00.00"], None, age, gender)

    within_limit, freq_msg, usage = await check_preventive_frequency(db, member_id, cpt_code, service_date, service)

    return {
        "code": cpt_code,
        "service": service,
        "member_age": age,
        "member_gender": gender,
        "age_eligible": eval_result.get("is_preventive") is not False or "age" not in eval_result.get("reason", ""),
        "gender_eligible": eval_result.get("is_preventive") is not False or "gender" not in eval_result.get("reason", ""),
        "within_frequency": within_limit,
        "frequency_message": freq_msg,
        "usage_count": usage,
        "evaluation": eval_result,
    }


@router.get("/utilization/{member_id}")
async def member_preventive_utilization(member_id: str, user: dict = Depends(get_current_user)):
    """Get a member's preventive service utilization history."""
    records = await db.preventive_utilization.find(
        {"member_id": member_id}, {"_id": 0}
    ).sort("service_date", -1).to_list(500)
    return {"member_id": member_id, "records": records, "count": len(records)}


@router.get("/analytics")
async def preventive_analytics(user: dict = Depends(get_current_user)):
    """Get preventive service analytics / utilization stats."""
    total_utilization = await db.preventive_utilization.count_documents({})

    pipeline_unique_members = [{"$group": {"_id": "$member_id"}}]
    unique_members = await db.preventive_utilization.aggregate(pipeline_unique_members).to_list(100000)

    total_members = await db.members.count_documents({"status": "active"})

    pipeline_cats = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cat_breakdown = await db.preventive_utilization.aggregate(pipeline_cats).to_list(50)

    pipeline_prev_claims = [
        {"$match": {"service_lines.is_preventive": True}},
        {"$count": "count"}
    ]
    prev_claims_result = await db.claims.aggregate(pipeline_prev_claims).to_list(1)
    prev_claims_count = prev_claims_result[0]["count"] if prev_claims_result else 0

    pipeline_prev_paid = [
        {"$match": {"service_lines.is_preventive": True}},
        {"$unwind": "$service_lines"},
        {"$match": {"service_lines.is_preventive": True}},
        {"$group": {"_id": None, "total_paid": {"$sum": "$service_lines.paid"}}},
    ]
    prev_paid_result = await db.claims.aggregate(pipeline_prev_paid).to_list(1)
    total_prev_paid = prev_paid_result[0]["total_paid"] if prev_paid_result else 0

    members_with_preventive = len(unique_members)
    compliance_rate = (members_with_preventive / total_members * 100) if total_members > 0 else 0
    pmpm = (total_prev_paid / max(total_members, 1)) if total_members > 0 else 0

    return {
        "total_preventive_services": total_utilization,
        "members_with_preventive": members_with_preventive,
        "total_active_members": total_members,
        "compliance_rate": round(compliance_rate, 1),
        "preventive_pmpm": round(pmpm, 2),
        "total_preventive_paid": round(total_prev_paid, 2),
        "claims_with_preventive": prev_claims_count,
        "category_breakdown": [{"category": c["_id"], "count": c["count"]} for c in cat_breakdown],
        "total_preventive_codes": len(PREVENTIVE_SERVICES),
    }


@router.get("/abuse-detection")
async def preventive_abuse_detection(user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Detect potential preventive service abuse patterns."""
    flags = []

    pipeline_dup = [
        {"$match": {"service_lines.is_preventive": True}},
        {"$group": {
            "_id": {"member_id": "$member_id", "provider_npi": "$provider_npi", "service_date_from": "$service_date_from"},
            "count": {"$sum": 1},
            "claim_ids": {"$push": "$id"},
            "claim_numbers": {"$push": "$claim_number"},
        }},
        {"$match": {"count": {"$gt": 1}}},
    ]
    dup_visits = await db.claims.aggregate(pipeline_dup).to_list(100)
    for dv in dup_visits:
        flags.append({
            "type": "duplicate_preventive_visit",
            "severity": "high",
            "member_id": dv["_id"]["member_id"],
            "provider_npi": dv["_id"]["provider_npi"],
            "service_date": dv["_id"]["service_date_from"],
            "count": dv["count"],
            "claim_numbers": dv["claim_numbers"],
            "message": f"Duplicate preventive visit: {dv['count']} claims on same date/provider",
        })

    pipeline_freq = [
        {"$group": {
            "_id": {"member_id": "$member_id", "subcategory": "$subcategory"},
            "count": {"$sum": 1},
        }},
        {"$match": {"count": {"$gt": 3}}},
    ]
    freq_excess = await db.preventive_utilization.aggregate(pipeline_freq).to_list(100)
    for fe in freq_excess:
        flags.append({
            "type": "excess_frequency",
            "severity": "medium",
            "member_id": fe["_id"]["member_id"],
            "subcategory": fe["_id"]["subcategory"],
            "count": fe["count"],
            "message": f"High frequency for {fe['_id']['subcategory']}: {fe['count']} occurrences",
        })

    return {"flags": flags, "total_flags": len(flags)}
