from fastapi import APIRouter, Depends
from core.database import db
from core.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/fixed-cost-vs-claims")
async def fixed_cost_vs_claims(user: dict = Depends(get_current_user)):
    """Fixed Cost vs. Claims Spend report for all groups."""
    groups = await db.groups.find({"status": "active"}, {"_id": 0}).to_list(1000)
    report_data = []

    for group in groups:
        member_ids_cursor = await db.members.find({"group_id": group["id"]}, {"member_id": 1, "_id": 0}).to_list(100000)
        member_ids = [m["member_id"] for m in member_ids_cursor]

        pipeline = [
            {"$match": {"member_id": {"$in": member_ids}, "status": {"$nin": ["managerial_hold"]}}},
            {"$group": {"_id": None, "total_paid": {"$sum": "$total_paid"}, "total_billed": {"$sum": "$total_billed"}, "claim_count": {"$sum": 1}}}
        ]
        fin = await db.claims.aggregate(pipeline).to_list(1)
        claims_paid = fin[0]["total_paid"] if fin else 0
        claim_count = fin[0]["claim_count"] if fin else 0

        total_premium = group.get("total_premium", 0)
        mgu_fees = group.get("mgu_fees", 0)
        fixed_costs = mgu_fees
        surplus = max(0, total_premium - (mgu_fees + claims_paid))

        is_mec = False
        for pid in group.get("plan_ids", []):
            p = await db.plans.find_one({"id": pid, "plan_template": "mec_1"}, {"_id": 0, "id": 1})
            if p:
                is_mec = True
                break

        report_data.append({
            "group_id": group["id"],
            "group_name": group.get("name", ""),
            "is_mec": is_mec,
            "employee_count": group.get("employee_count", 0),
            "total_premium": round(total_premium, 2),
            "mgu_fees": round(fixed_costs, 2),
            "claims_paid": round(claims_paid, 2),
            "surplus": round(surplus, 2),
            "claim_count": claim_count,
            "margin_pct": round((surplus / total_premium * 100), 1) if total_premium > 0 else 0,
        })

    return report_data


@router.get("/hour-bank-deficiency")
async def hour_bank_deficiency_report(user: dict = Depends(get_current_user)):
    """List all members within 20 hours of losing coverage due to hour bank deficit."""
    plans = await db.plans.find(
        {"eligibility_threshold": {"$gt": 0}}, {"_id": 0}
    ).to_list(1000)
    plan_map = {p["id"]: p for p in plans}

    if not plan_map:
        return []

    plan_ids = list(plan_map.keys())
    members = await db.members.find(
        {"plan_id": {"$in": plan_ids}}, {"_id": 0}
    ).to_list(100000)

    at_risk = []
    for m in members:
        plan = plan_map.get(m.get("plan_id"))
        if not plan:
            continue

        threshold = plan.get("eligibility_threshold", 0)
        bank = await db.hour_bank.find_one({"member_id": m["member_id"]}, {"_id": 0})
        balance = bank["current_balance"] if bank else 0.0
        cushion = balance - threshold

        if cushion < 20:
            group = await db.groups.find_one({"id": m.get("group_id")}, {"_id": 0, "name": 1})
            at_risk.append({
                "member_id": m["member_id"],
                "first_name": m.get("first_name", ""),
                "last_name": m.get("last_name", ""),
                "group_id": m.get("group_id", ""),
                "group_name": group.get("name", "") if group else "",
                "plan_name": plan.get("name", ""),
                "current_balance": round(balance, 2),
                "threshold": threshold,
                "cushion": round(cushion, 2),
                "status": m.get("status", "active"),
            })

    at_risk.sort(key=lambda x: x["cushion"])
    return at_risk
