from fastapi import APIRouter, Depends, HTTPException, Query
from core.database import db
from core.auth import get_current_user
from services.tiering_engine import classify_claim, get_tiering_summary, get_risk_dial_data

router = APIRouter(prefix="/tiering", tags=["tiering"])


@router.get("/summary")
async def tiering_summary(user: dict = Depends(get_current_user)):
    """Get aggregate tiering breakdown of all claims."""
    return await get_tiering_summary()


@router.get("/risk-dial")
async def risk_dial(user: dict = Depends(get_current_user)):
    """Real-time Risk Dial — stop-loss utilization across all groups."""
    return await get_risk_dial_data()


@router.get("/analyze/{claim_id}")
async def analyze_claim_tier(claim_id: str, user: dict = Depends(get_current_user)):
    """Classify a specific claim into its risk tier."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(404, "Claim not found")

    # Load plan and group for stop-loss checks
    plan = None
    group = None
    member = await db.members.find_one({"member_id": claim.get("member_id")}, {"_id": 0})
    if member:
        if member.get("plan_id"):
            plan = await db.plans.find_one({"id": member["plan_id"]}, {"_id": 0})
        if member.get("group_id"):
            group = await db.groups.find_one({"id": member["group_id"]}, {"_id": 0})

    result = await classify_claim(claim, plan, group)
    return result


@router.post("/batch-classify")
async def batch_classify_claims(
    limit: int = Query(default=500, le=5000),
    user: dict = Depends(get_current_user),
):
    """Batch-classify claims and store tier info."""
    claims = await db.claims.find(
        {"status": {"$in": ["approved", "paid", "pending", "in_review"]}},
        {"_id": 0}
    ).to_list(limit)

    results = {"tier_1": 0, "tier_2": 0, "tier_3": 0, "processed": 0}
    for claim in claims:
        member = await db.members.find_one({"member_id": claim.get("member_id")}, {"_id": 0})
        plan = None
        group = None
        if member:
            if member.get("plan_id"):
                plan = await db.plans.find_one({"id": member["plan_id"]}, {"_id": 0})
            if member.get("group_id"):
                group = await db.groups.find_one({"id": member["group_id"]}, {"_id": 0})

        tier_result = await classify_claim(claim, plan, group)
        tier = tier_result["tier"]
        results[f"tier_{tier}"] += 1
        results["processed"] += 1

        # Update claim with tier info
        await db.claims.update_one(
            {"id": claim["id"]},
            {"$set": {"data_tier": tier, "tier_label": tier_result["tier_label"], "tier_reason": tier_result["tier_reason"]}}
        )

    return results
