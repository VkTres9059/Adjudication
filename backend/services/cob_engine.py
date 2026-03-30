"""
Coordination of Benefits (COB) Engine — Handles primary/secondary payer logic.
Determines payment responsibility when a member has multiple coverage sources.
"""
from datetime import datetime, timezone
from core.database import db


COB_ORDER_RULES = [
    "birthday_rule",        # For dependent children: parent with earlier birthday is primary
    "active_employee",      # Active employee coverage > COBRA/retiree
    "longer_coverage",      # Longer-held coverage is primary
    "subscriber_first",     # Subscriber's own plan is primary over dependent coverage
]


async def determine_payer_order(member: dict, claim: dict) -> dict:
    """Determine primary/secondary payer for a member."""
    cob_info = member.get("cob_info") or {}
    if not cob_info.get("has_other_coverage"):
        return {
            "has_cob": False,
            "our_position": "primary",
            "other_payer": None,
            "notes": "No other coverage reported",
        }

    our_plan_type = cob_info.get("our_plan_type", "active_employee")
    other_plan_type = cob_info.get("other_plan_type", "active_employee")
    relationship = member.get("relationship", "subscriber")

    position = "primary"  # Default
    reason = ""

    # Active employee vs COBRA/retiree
    if our_plan_type == "active_employee" and other_plan_type in ("cobra", "retiree"):
        position = "primary"
        reason = "Active employee coverage is primary over COBRA/retiree"
    elif our_plan_type in ("cobra", "retiree") and other_plan_type == "active_employee":
        position = "secondary"
        reason = "COBRA/retiree coverage is secondary to active employee"

    # Subscriber vs dependent
    elif relationship == "subscriber":
        position = "primary"
        reason = "Subscriber's own coverage is primary"
    elif relationship in ("spouse", "dependent"):
        # Birthday rule for dependents
        our_subscriber_bday = cob_info.get("our_subscriber_birthday", "")
        other_subscriber_bday = cob_info.get("other_subscriber_birthday", "")
        if our_subscriber_bday and other_subscriber_bday:
            try:
                our_month_day = our_subscriber_bday[5:10]
                other_month_day = other_subscriber_bday[5:10]
                if our_month_day <= other_month_day:
                    position = "primary"
                    reason = "Birthday rule: our subscriber's birthday is earlier in the year"
                else:
                    position = "secondary"
                    reason = "Birthday rule: other subscriber's birthday is earlier in the year"
            except (IndexError, TypeError):
                position = "primary"
                reason = "Birthday rule: could not determine — defaulting to primary"

    return {
        "has_cob": True,
        "our_position": position,
        "other_payer": {
            "name": cob_info.get("other_payer_name", ""),
            "policy_number": cob_info.get("other_policy_number", ""),
            "plan_type": other_plan_type,
        },
        "reason": reason,
    }


async def apply_cob_to_claim(claim: dict, cob_data: dict, primary_eob: dict = None) -> dict:
    """Apply COB logic to adjust payment on a claim."""
    if not cob_data.get("has_cob"):
        return {"cob_applied": False, "adjustment": 0}

    if cob_data["our_position"] == "primary":
        return {
            "cob_applied": True,
            "our_position": "primary",
            "adjustment": 0,
            "notes": "We are primary — pay per plan rules, no COB adjustment",
        }

    # We are secondary — reduce our payment by what primary paid
    if not primary_eob:
        return {
            "cob_applied": True,
            "our_position": "secondary",
            "adjustment": 0,
            "notes": "Awaiting primary EOB — claim pended for COB",
            "pend_for_cob": True,
        }

    primary_paid = primary_eob.get("primary_paid", 0)
    primary_allowed = primary_eob.get("primary_allowed", 0)
    primary_member_resp = primary_eob.get("primary_member_resp", 0)

    # Non-duplication of benefits: our payment = min(our_allowed - primary_paid, member_responsibility)
    our_allowed = claim.get("total_allowed", 0)
    our_calculated_payment = claim.get("total_paid", 0)

    max_secondary_payment = min(primary_member_resp, our_calculated_payment)
    cob_adjustment = our_calculated_payment - max_secondary_payment

    return {
        "cob_applied": True,
        "our_position": "secondary",
        "primary_paid": primary_paid,
        "primary_allowed": primary_allowed,
        "original_our_payment": our_calculated_payment,
        "adjusted_payment": max_secondary_payment,
        "adjustment": round(cob_adjustment, 2),
        "notes": f"Secondary payer: reduced from ${our_calculated_payment:.2f} to ${max_secondary_payment:.2f}",
    }


async def record_cob_event(claim_id: str, cob_result: dict, user_id: str):
    """Record COB determination in audit trail."""
    await db.cob_records.insert_one({
        "id": str(__import__("uuid").uuid4()),
        "claim_id": claim_id,
        "cob_result": cob_result,
        "recorded_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
