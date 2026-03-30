"""
Data Tiering Engine — Categorizes claims and member data into three risk tiers.

Tier 1 (Auto-Pilot): Claims < $2,500 that pass all Code Database edits.
Tier 2 (Clinical Review): Claims involving specific 'Trigger' CPT codes or Prior Auths.
Tier 3 (Stop-Loss Trigger): Any single claim > 50% of Specific Attachment Point
                            or groups hitting 80% of Aggregate Spec.
"""
from core.database import db

# Trigger CPT codes that always require clinical review
TRIGGER_CPT_CODES = {
    # High-cost surgery / procedures
    "27447", "27130", "22551", "22612", "63047",  # Joint replacements, spinal fusion
    "33533", "33405", "33361",  # CABG, valve replacement, TAVR
    "43239", "43644",  # Upper GI, bariatric
    "55840", "55845",  # Prostatectomy
    "50360", "50365",  # Kidney transplant
    "44120", "44140",  # Bowel resection
    "59510", "59610",  # C-section
    # Imaging / Specialty
    "77263", "77427",  # Radiation therapy planning
    "90839", "90837",  # Psychotherapy high-duration
    "96413", "96415",  # Chemotherapy infusion
    "J9271", "J9035",  # High-cost injectables
    "99291", "99292",  # Critical care
}

TIER_1_THRESHOLD = 2500.0
STOP_LOSS_SPECIFIC_PCT = 50
STOP_LOSS_AGGREGATE_PCT = 80


async def classify_claim(claim: dict, plan: dict = None, group: dict = None) -> dict:
    """Classify a single claim into Tier 1, 2, or 3."""
    total_paid = claim.get("total_paid", 0) or 0
    total_billed = claim.get("total_billed", 0) or 0
    has_prior_auth = bool(claim.get("prior_auth_number"))
    service_lines = claim.get("service_lines", [])

    # Check for trigger CPT codes
    cpt_codes = [sl.get("cpt_code", "") for sl in service_lines]
    has_trigger_code = any(c in TRIGGER_CPT_CODES for c in cpt_codes)

    # Default tier
    tier = 1
    tier_reason = "Auto-Pilot: Claim passed all edits and is below $2,500 threshold."

    # Tier 2: Clinical Review triggers
    if has_trigger_code or has_prior_auth:
        tier = 2
        reasons = []
        if has_trigger_code:
            triggers = [c for c in cpt_codes if c in TRIGGER_CPT_CODES]
            reasons.append(f"Trigger CPT codes: {', '.join(triggers)}")
        if has_prior_auth:
            reasons.append(f"Prior Auth: {claim.get('prior_auth_number')}")
        tier_reason = f"Clinical Review: {'; '.join(reasons)}"

    # Tier 1 threshold check
    elif total_paid >= TIER_1_THRESHOLD:
        tier = 2
        tier_reason = f"Clinical Review: Paid amount ${total_paid:,.2f} exceeds auto-pilot threshold (${TIER_1_THRESHOLD:,.0f})."

    # Tier 3: Stop-Loss checks (override Tier 2 if applicable)
    if plan:
        risk = plan.get("risk_management") or {}
        specific_limit = risk.get("specific_attachment_point", 0)
        if specific_limit > 0 and total_paid > (specific_limit * STOP_LOSS_SPECIFIC_PCT / 100):
            tier = 3
            tier_reason = (
                f"Stop-Loss Trigger: Claim paid ${total_paid:,.2f} exceeds "
                f"{STOP_LOSS_SPECIFIC_PCT}% of Specific Attachment Point (${specific_limit:,.0f})."
            )

    # Aggregate check at group level
    if group and plan:
        risk = plan.get("risk_management") or {}
        agg_limit = risk.get("aggregate_attachment_point", 0)
        if agg_limit > 0:
            members = await db.members.find(
                {"group_id": group["id"]}, {"member_id": 1, "_id": 0}
            ).to_list(100000)
            mids = [m["member_id"] for m in members]
            if mids:
                pipe = [
                    {"$match": {"member_id": {"$in": mids}, "status": {"$in": ["approved", "paid"]}}},
                    {"$group": {"_id": None, "total": {"$sum": "$total_paid"}}},
                ]
                agg = await db.claims.aggregate(pipe).to_list(1)
                group_total = (agg[0]["total"] if agg else 0) + total_paid
                if group_total > (agg_limit * STOP_LOSS_AGGREGATE_PCT / 100):
                    tier = 3
                    tier_reason = (
                        f"Stop-Loss Trigger: Group total claims ${group_total:,.2f} "
                        f"approaching {STOP_LOSS_AGGREGATE_PCT}% of Aggregate Attachment "
                        f"Point (${agg_limit:,.0f})."
                    )

    return {
        "tier": tier,
        "tier_label": {1: "Auto-Pilot", 2: "Clinical Review", 3: "Stop-Loss Trigger"}[tier],
        "tier_reason": tier_reason,
        "claim_id": claim.get("id", ""),
        "total_paid": total_paid,
        "total_billed": total_billed,
        "has_trigger_codes": has_trigger_code,
        "has_prior_auth": has_prior_auth,
    }


async def get_tiering_summary() -> dict:
    """Get aggregate tiering summary across all claims."""
    all_claims = await db.claims.find(
        {"status": {"$in": ["approved", "paid", "pending", "in_review"]}},
        {"_id": 0, "id": 1, "total_paid": 1, "total_billed": 1, "service_lines": 1,
         "prior_auth_number": 1, "member_id": 1, "status": 1}
    ).to_list(100000)

    tiers = {1: [], 2: [], 3: []}
    for claim in all_claims:
        # Quick classification without plan/group lookup for summary
        total_paid = claim.get("total_paid", 0) or 0
        has_prior_auth = bool(claim.get("prior_auth_number"))
        cpt_codes = [sl.get("cpt_code", "") for sl in claim.get("service_lines", [])]
        has_trigger = any(c in TRIGGER_CPT_CODES for c in cpt_codes)

        if has_trigger or has_prior_auth or total_paid >= TIER_1_THRESHOLD:
            tier = 2
        else:
            tier = 1

        # Check if any claims have stop_loss_flag
        if claim.get("stop_loss_flag"):
            tier = 3

        tiers[tier].append(claim)

    def tier_stats(claims_list):
        total_paid = sum(c.get("total_paid", 0) or 0 for c in claims_list)
        total_billed = sum(c.get("total_billed", 0) or 0 for c in claims_list)
        return {
            "count": len(claims_list),
            "total_paid": round(total_paid, 2),
            "total_billed": round(total_billed, 2),
        }

    return {
        "tier_1": {**tier_stats(tiers[1]), "label": "Auto-Pilot", "description": "Claims < $2,500 passing all edits"},
        "tier_2": {**tier_stats(tiers[2]), "label": "Clinical Review", "description": "Trigger CPT codes or Prior Auths"},
        "tier_3": {**tier_stats(tiers[3]), "label": "Stop-Loss Trigger", "description": "Exceeds stop-loss thresholds"},
        "total_claims": len(all_claims),
    }


async def get_risk_dial_data() -> dict:
    """Calculate risk dial data for all groups with stop-loss plans."""
    groups = await db.groups.find({"status": "active"}, {"_id": 0}).to_list(1000)
    risk_groups = []

    for group in groups:
        plan_ids = group.get("plan_ids", [])
        if not plan_ids:
            continue

        plans = await db.plans.find(
            {"id": {"$in": plan_ids}}, {"_id": 0}
        ).to_list(100)

        for plan in plans:
            risk = plan.get("risk_management")
            if not risk:
                continue
            specific_limit = risk.get("specific_attachment_point", 0)
            agg_limit = risk.get("aggregate_attachment_point", 0)
            if specific_limit <= 0 and agg_limit <= 0:
                continue

            members = await db.members.find(
                {"group_id": group["id"]}, {"member_id": 1, "_id": 0}
            ).to_list(100000)
            mids = [m["member_id"] for m in members]
            if not mids:
                continue

            # Aggregate claims for this group
            pipe = [
                {"$match": {"member_id": {"$in": mids}, "status": {"$in": ["approved", "paid"]}}},
                {"$group": {"_id": None, "total": {"$sum": "$total_paid"}}},
            ]
            agg = await db.claims.aggregate(pipe).to_list(1)
            group_total = agg[0]["total"] if agg else 0

            # Per-member max
            member_pipe = [
                {"$match": {"member_id": {"$in": mids}, "status": {"$in": ["approved", "paid"]}}},
                {"$group": {"_id": "$member_id", "total": {"$sum": "$total_paid"}}},
                {"$sort": {"total": -1}},
                {"$limit": 1},
            ]
            max_member = await db.claims.aggregate(member_pipe).to_list(1)
            highest_member_total = max_member[0]["total"] if max_member else 0

            specific_pct = round((highest_member_total / specific_limit * 100), 1) if specific_limit > 0 else 0
            aggregate_pct = round((group_total / agg_limit * 100), 1) if agg_limit > 0 else 0

            alert_level = "normal"
            if aggregate_pct >= 80 or specific_pct >= 80:
                alert_level = "critical"
            elif aggregate_pct >= 60 or specific_pct >= 60:
                alert_level = "warning"

            risk_groups.append({
                "group_id": group["id"],
                "group_name": group.get("name", ""),
                "plan_name": plan.get("name", ""),
                "specific_attachment_point": specific_limit,
                "aggregate_attachment_point": agg_limit,
                "highest_member_claims": round(highest_member_total, 2),
                "specific_utilization_pct": specific_pct,
                "group_total_claims": round(group_total, 2),
                "aggregate_utilization_pct": aggregate_pct,
                "alert_level": alert_level,
                "stop_loss_carrier": risk.get("stop_loss_carrier", ""),
            })

    risk_groups.sort(key=lambda x: max(x["specific_utilization_pct"], x["aggregate_utilization_pct"]), reverse=True)

    critical_count = sum(1 for g in risk_groups if g["alert_level"] == "critical")
    warning_count = sum(1 for g in risk_groups if g["alert_level"] == "warning")

    return {
        "groups": risk_groups,
        "summary": {
            "total_monitored": len(risk_groups),
            "critical": critical_count,
            "warning": warning_count,
            "normal": len(risk_groups) - critical_count - warning_count,
        },
    }
