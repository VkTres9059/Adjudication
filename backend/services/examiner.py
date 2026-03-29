from datetime import datetime, timezone
from core.database import db


async def auto_assign_examiner(claim_amount: float) -> dict:
    """Auto-assign claim to examiner with fewest open claims, routed by authority level."""
    if claim_amount >= 5000:
        target_role = "admin"
    else:
        target_role = "adjudicator"

    examiners = await db.users.find(
        {"role": target_role},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
    ).to_list(500)

    if not examiners:
        examiners = await db.users.find(
            {"role": "admin"},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
        ).to_list(500)

    if not examiners:
        return {}

    best = None
    best_count = float('inf')
    for ex in examiners:
        count = await db.claims.count_documents({
            "assigned_to": ex["id"],
            "status": {"$in": ["pending_review", "managerial_hold", "pended", "in_review"]}
        })
        if count < best_count:
            best_count = count
            best = ex

    if best:
        return {
            "assigned_to": best["id"],
            "assigned_to_name": best.get("name", best["email"]),
            "assigned_at": datetime.now(timezone.utc).isoformat(),
        }
    return {}
