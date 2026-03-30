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
    """Enhanced deficiency report with multi-tier balances, burn rate, months remaining, at_risk flag."""
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
        cur = float(bank.get("current_balance", 0)) if bank else 0.0
        res = float(bank.get("reserve_balance", 0)) if bank else 0.0
        total = cur + res
        cushion = total - threshold

        # Burn rate from recent deductions
        deductions = await db.hour_bank_entries.find(
            {"member_id": m["member_id"], "entry_type": "monthly_deduction"},
            {"_id": 0, "hours": 1}
        ).sort("created_at", -1).to_list(3)
        burn_rate = threshold  # default
        if deductions:
            burn_rate = abs(sum(d.get("hours", 0) for d in deductions)) / len(deductions)
        months_remaining = round(total / burn_rate, 1) if burn_rate > 0 else 999
        is_at_risk = threshold > 0 and total < (2 * threshold)

        if cushion < 20:
            group = await db.groups.find_one({"id": m.get("group_id")}, {"_id": 0, "name": 1})
            elig_source = bank.get("eligibility_source", "standard_hours") if bank else "standard_hours"
            at_risk.append({
                "member_id": m["member_id"],
                "first_name": m.get("first_name", ""),
                "last_name": m.get("last_name", ""),
                "group_id": m.get("group_id", ""),
                "group_name": group.get("name", "") if group else "",
                "plan_name": plan.get("name", ""),
                "current_balance": round(cur, 2),
                "reserve_balance": round(res, 2),
                "total_balance": round(total, 2),
                "threshold": threshold,
                "cushion": round(cushion, 2),
                "burn_rate": round(burn_rate, 2),
                "months_remaining": months_remaining,
                "at_risk": is_at_risk,
                "eligibility_source": elig_source,
                "status": m.get("status", "active"),
            })

    at_risk.sort(key=lambda x: x["cushion"])
    return at_risk


@router.get("/predictive-eligibility")
async def predictive_eligibility_dashboard(user: dict = Depends(get_current_user)):
    """Predictive eligibility dashboard: all members with hour bank plans, with burn rate and risk flags."""
    plans = await db.plans.find(
        {"eligibility_threshold": {"$gt": 0}}, {"_id": 0}
    ).to_list(1000)
    plan_map = {p["id"]: p for p in plans}

    if not plan_map:
        return {"summary": {"total": 0, "at_risk": 0, "critical": 0, "healthy": 0}, "members": []}

    plan_ids = list(plan_map.keys())
    members = await db.members.find(
        {"plan_id": {"$in": plan_ids}}, {"_id": 0}
    ).to_list(100000)

    results = []
    summary = {"total": 0, "at_risk": 0, "critical": 0, "healthy": 0}

    for m in members:
        plan = plan_map.get(m.get("plan_id"))
        if not plan:
            continue

        threshold = plan.get("eligibility_threshold", 0)
        bank = await db.hour_bank.find_one({"member_id": m["member_id"]}, {"_id": 0})
        cur = float(bank.get("current_balance", 0)) if bank else 0.0
        res = float(bank.get("reserve_balance", 0)) if bank else 0.0
        total = cur + res
        cushion = total - threshold

        deductions = await db.hour_bank_entries.find(
            {"member_id": m["member_id"], "entry_type": "monthly_deduction"},
            {"_id": 0, "hours": 1}
        ).sort("created_at", -1).to_list(3)
        burn_rate = threshold
        if deductions:
            burn_rate = abs(sum(d.get("hours", 0) for d in deductions)) / len(deductions)
        months_remaining = round(total / burn_rate, 1) if burn_rate > 0 else 999
        is_at_risk = threshold > 0 and total < (2 * threshold)
        is_critical = cushion < 10 and threshold > 0

        summary["total"] += 1
        if is_critical:
            summary["critical"] += 1
        elif is_at_risk:
            summary["at_risk"] += 1
        else:
            summary["healthy"] += 1

        group = await db.groups.find_one({"id": m.get("group_id")}, {"_id": 0, "name": 1})
        elig_source = bank.get("eligibility_source", "standard_hours") if bank else "standard_hours"

        results.append({
            "member_id": m["member_id"],
            "first_name": m.get("first_name", ""),
            "last_name": m.get("last_name", ""),
            "group_id": m.get("group_id", ""),
            "group_name": group.get("name", "") if group else "",
            "plan_name": plan.get("name", ""),
            "current_balance": round(cur, 2),
            "reserve_balance": round(res, 2),
            "total_balance": round(total, 2),
            "threshold": threshold,
            "cushion": round(cushion, 2),
            "burn_rate": round(burn_rate, 2),
            "months_remaining": months_remaining,
            "at_risk": is_at_risk,
            "critical": is_critical,
            "eligibility_source": elig_source,
            "status": m.get("status", "active"),
        })

    results.sort(key=lambda x: x["cushion"])
    return {"summary": summary, "members": results}


@router.get("/broker-deck")
async def broker_deck_report(user: dict = Depends(get_current_user)):
    """Broker Deck — High-level Surplus vs. Paid Claims for all groups."""
    groups = await db.groups.find({"status": "active"}, {"_id": 0}).to_list(1000)
    deck = []

    for group in groups:
        member_ids_cursor = await db.members.find(
            {"group_id": group["id"]}, {"member_id": 1, "_id": 0}
        ).to_list(100000)
        member_ids = [m["member_id"] for m in member_ids_cursor]

        pipeline = [
            {"$match": {"member_id": {"$in": member_ids}, "status": {"$in": ["approved", "paid"]}}},
            {"$group": {
                "_id": None,
                "total_paid": {"$sum": "$total_paid"},
                "total_billed": {"$sum": "$total_billed"},
                "claim_count": {"$sum": 1},
            }},
        ]
        fin = await db.claims.aggregate(pipeline).to_list(1)
        claims_paid = fin[0]["total_paid"] if fin else 0
        claims_billed = fin[0]["total_billed"] if fin else 0
        claim_count = fin[0]["claim_count"] if fin else 0

        total_premium = group.get("total_premium", 0) or 0
        mgu_fees = group.get("mgu_fees", 0) or 0
        stop_loss_premium = group.get("stop_loss_premium", 0) or 0
        admin_costs = mgu_fees + stop_loss_premium
        surplus = total_premium - admin_costs - claims_paid
        loss_ratio = round((claims_paid / total_premium * 100), 1) if total_premium > 0 else 0

        deck.append({
            "group_id": group["id"],
            "group_name": group.get("name", ""),
            "funding_type": group.get("funding_type", "aso"),
            "employee_count": group.get("employee_count", 0),
            "total_premium": round(total_premium, 2),
            "admin_costs": round(admin_costs, 2),
            "claims_paid": round(claims_paid, 2),
            "claims_billed": round(claims_billed, 2),
            "surplus": round(surplus, 2),
            "loss_ratio": loss_ratio,
            "claim_count": claim_count,
            "pepm": round(claims_paid / max(group.get("employee_count", 1), 1), 2),
        })

    total_premium = sum(d["total_premium"] for d in deck)
    total_paid = sum(d["claims_paid"] for d in deck)
    total_surplus = sum(d["surplus"] for d in deck)

    return {
        "groups": deck,
        "totals": {
            "total_premium": round(total_premium, 2),
            "total_claims_paid": round(total_paid, 2),
            "total_surplus": round(total_surplus, 2),
            "overall_loss_ratio": round((total_paid / total_premium * 100), 1) if total_premium > 0 else 0,
            "group_count": len(deck),
        },
    }


@router.get("/carrier-bordereaux")
async def carrier_bordereaux_report(
    group_id: str = None,
    user: dict = Depends(get_current_user),
):
    """Carrier Bordereaux — Detailed eligibility and premium reconciliation."""
    query = {"status": "active"}
    if group_id:
        query["id"] = group_id
    groups = await db.groups.find(query, {"_id": 0}).to_list(1000)
    bordereaux = []

    for group in groups:
        members = await db.members.find(
            {"group_id": group["id"]}, {"_id": 0}
        ).to_list(100000)

        active_members = [m for m in members if m.get("status") == "active"]
        termed_members = [m for m in members if m.get("status") in ("termed", "termed_insufficient_hours")]

        member_ids = [m["member_id"] for m in members]
        claims_pipe = [
            {"$match": {"member_id": {"$in": member_ids}, "status": {"$in": ["approved", "paid"]}}},
            {"$group": {
                "_id": None,
                "total_paid": {"$sum": "$total_paid"},
                "claim_count": {"$sum": 1},
            }},
        ]
        claims_agg = await db.claims.aggregate(claims_pipe).to_list(1)
        total_claims_paid = claims_agg[0]["total_paid"] if claims_agg else 0
        claim_count = claims_agg[0]["claim_count"] if claims_agg else 0

        premium_per_member = group.get("premium_per_member", 0) or 0
        expected_premium = premium_per_member * len(active_members)
        actual_premium = group.get("total_premium", 0) or 0
        premium_variance = actual_premium - expected_premium

        bordereaux.append({
            "group_id": group["id"],
            "group_name": group.get("name", ""),
            "effective_date": group.get("effective_date", ""),
            "funding_type": group.get("funding_type", "aso"),
            "total_members": len(members),
            "active_members": len(active_members),
            "termed_members": len(termed_members),
            "premium_per_member": round(premium_per_member, 2),
            "expected_premium": round(expected_premium, 2),
            "actual_premium": round(actual_premium, 2),
            "premium_variance": round(premium_variance, 2),
            "total_claims_paid": round(total_claims_paid, 2),
            "claim_count": claim_count,
            "member_details": [{
                "member_id": m["member_id"],
                "name": f"{m.get('first_name', '')} {m.get('last_name', '')}",
                "status": m.get("status", ""),
                "effective_date": m.get("effective_date", ""),
                "termination_date": m.get("termination_date"),
            } for m in members[:100]],  # Cap at 100 per group
        })

    return {"groups": bordereaux, "total_groups": len(bordereaux)}


@router.get("/utilization-review")
async def utilization_review_report(user: dict = Depends(get_current_user)):
    """Utilization Review — Top providers, costliest CPTs, and network leakage."""
    # Top 10 providers by paid amount
    provider_pipe = [
        {"$match": {"status": {"$in": ["approved", "paid"]}}},
        {"$group": {
            "_id": "$provider_npi",
            "provider_name": {"$first": "$provider_name"},
            "total_paid": {"$sum": "$total_paid"},
            "total_billed": {"$sum": "$total_billed"},
            "claim_count": {"$sum": 1},
        }},
        {"$sort": {"total_paid": -1}},
        {"$limit": 10},
    ]
    top_providers = await db.claims.aggregate(provider_pipe).to_list(10)

    # Top 10 costliest CPT codes
    cpt_pipe = [
        {"$match": {"status": {"$in": ["approved", "paid"]}}},
        {"$unwind": "$service_lines"},
        {"$group": {
            "_id": "$service_lines.cpt_code",
            "description": {"$first": "$service_lines.cpt_description"},
            "total_paid": {"$sum": "$service_lines.paid"},
            "total_billed": {"$sum": "$service_lines.billed_amount"},
            "usage_count": {"$sum": 1},
        }},
        {"$sort": {"total_paid": -1}},
        {"$limit": 10},
    ]
    top_cpts = await db.claims.aggregate(cpt_pipe).to_list(10)

    # Network leakage (out-of-network claims)
    total_claims = await db.claims.count_documents({"status": {"$in": ["approved", "paid"]}})
    oon_claims = await db.claims.count_documents(
        {"status": {"$in": ["approved", "paid"]}, "network_status": {"$in": ["out_of_network", "oon"]}}
    )
    oon_pipe = [
        {"$match": {"status": {"$in": ["approved", "paid"]}, "network_status": {"$in": ["out_of_network", "oon"]}}},
        {"$group": {"_id": None, "total_paid": {"$sum": "$total_paid"}}},
    ]
    oon_agg = await db.claims.aggregate(oon_pipe).to_list(1)
    oon_paid = oon_agg[0]["total_paid"] if oon_agg else 0

    all_paid_pipe = [
        {"$match": {"status": {"$in": ["approved", "paid"]}}},
        {"$group": {"_id": None, "total_paid": {"$sum": "$total_paid"}}},
    ]
    all_agg = await db.claims.aggregate(all_paid_pipe).to_list(1)
    total_paid = all_agg[0]["total_paid"] if all_agg else 0

    # Claims by type breakdown
    type_pipe = [
        {"$match": {"status": {"$in": ["approved", "paid"]}}},
        {"$group": {
            "_id": "$claim_type",
            "total_paid": {"$sum": "$total_paid"},
            "claim_count": {"$sum": 1},
        }},
        {"$sort": {"total_paid": -1}},
    ]
    by_type = await db.claims.aggregate(type_pipe).to_list(10)

    return {
        "top_providers": [{
            "provider_npi": p["_id"] or "Unknown",
            "provider_name": p.get("provider_name") or "Unknown",
            "total_paid": round(p["total_paid"], 2),
            "total_billed": round(p["total_billed"], 2),
            "claim_count": p["claim_count"],
            "savings_pct": round((1 - p["total_paid"] / p["total_billed"]) * 100, 1) if p["total_billed"] > 0 else 0,
        } for p in top_providers],
        "top_cpt_codes": [{
            "cpt_code": c["_id"] or "Unknown",
            "description": c.get("description") or "",
            "total_paid": round(c["total_paid"], 2),
            "total_billed": round(c.get("total_billed", 0), 2),
            "usage_count": c["usage_count"],
        } for c in top_cpts],
        "network_leakage": {
            "total_claims": total_claims,
            "oon_claims": oon_claims,
            "oon_percentage": round((oon_claims / total_claims * 100), 1) if total_claims > 0 else 0,
            "oon_paid": round(oon_paid, 2),
            "total_paid": round(total_paid, 2),
            "oon_cost_percentage": round((oon_paid / total_paid * 100), 1) if total_paid > 0 else 0,
        },
        "claims_by_type": [{
            "type": t["_id"] or "unknown",
            "total_paid": round(t["total_paid"], 2),
            "claim_count": t["claim_count"],
        } for t in by_type],
    }
