from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from datetime import datetime, timezone
from typing import Optional
import uuid
import csv
import io

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole, ClaimStatus

router = APIRouter(prefix="/hour-bank", tags=["hour_bank"])


# ── helpers ──

def _safe_float(doc, key, default=0.0):
    return float(doc.get(key, default)) if doc else default


async def _get_bridge_config():
    doc = await db.settings.find_one({"key": "bridge_payment"}, {"_id": 0})
    if not doc:
        return {"enabled": False, "rate_per_hour": 20.0}
    return doc.get("value", {"enabled": False, "rate_per_hour": 20.0})


# ── Upload Work Report ──

@router.post("/upload-work-report")
async def upload_work_report(
    file: UploadFile = File(...),
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Ingest Work Report CSV (member_id, week_ending, hours_worked).
    Multi-tier: hours fill 'current' bucket. Overflow above threshold
    goes to 'reserve' (capped at max_bank)."""
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    errors = []

    for i, row in enumerate(reader):
        try:
            member_id = row.get("member_id", "").strip()
            week_ending = row.get("week_ending", "").strip()
            hours = float(row.get("hours_worked", "0").strip())
            if not member_id or not week_ending:
                errors.append(f"Row {i+1}: missing member_id or week_ending")
                continue

            member = await db.members.find_one({"member_id": member_id}, {"_id": 0, "member_id": 1, "plan_id": 1})
            if not member:
                errors.append(f"Row {i+1}: member {member_id} not found")
                continue

            plan = await db.plans.find_one({"id": member.get("plan_id")}, {"_id": 0, "eligibility_threshold": 1, "hour_bank_max": 1})
            threshold = plan.get("eligibility_threshold", 0) if plan else 0
            max_bank = plan.get("hour_bank_max", 0) if plan else 0

            bank = await db.hour_bank.find_one({"member_id": member_id}, {"_id": 0})
            cur = _safe_float(bank, "current_balance")
            res = _safe_float(bank, "reserve_balance")

            # Hours go into current bucket
            cur += hours
            # If threshold is set and current exceeds it, spill to reserve
            if threshold > 0 and cur > threshold:
                overflow = cur - threshold
                cur = threshold
                res += overflow
                if max_bank > 0:
                    res = min(res, max_bank)

            total = round(cur + res, 2)

            await db.hour_bank_entries.insert_one({
                "id": str(uuid.uuid4()),
                "member_id": member_id,
                "entry_type": "work_hours",
                "hours": hours,
                "bucket": "current",
                "running_balance": total,
                "current_after": round(cur, 2),
                "reserve_after": round(res, 2),
                "description": f"Work hours — week ending {week_ending}",
                "week_ending": week_ending,
                "period": None,
                "source": file.filename or "csv_upload",
                "created_at": now,
                "created_by": user["id"],
            })

            await db.hour_bank.update_one(
                {"member_id": member_id},
                {"$set": {
                    "member_id": member_id,
                    "plan_id": member.get("plan_id", ""),
                    "current_balance": round(cur, 2),
                    "reserve_balance": round(res, 2),
                    "updated_at": now,
                }},
                upsert=True,
            )
            inserted += 1
        except Exception as e:
            errors.append(f"Row {i+1}: {str(e)}")

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "action": "hour_bank_work_report_uploaded",
        "user_id": user["id"],
        "details": {"filename": file.filename, "rows_inserted": inserted, "errors": len(errors)},
        "timestamp": now,
    })
    return {"rows_inserted": inserted, "errors": errors}


# ── Member Ledger (with burn rate + multi-tier) ──

@router.get("/{member_id}")
async def get_member_hour_bank(member_id: str, user: dict = Depends(get_current_user)):
    """Hour bank ledger with multi-tier balances, burn rate, and bridge info."""
    member = await db.members.find_one({"member_id": member_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    bank = await db.hour_bank.find_one({"member_id": member_id}, {"_id": 0})
    plan = await db.plans.find_one(
        {"id": member.get("plan_id")},
        {"_id": 0, "eligibility_threshold": 1, "hour_bank_max": 1, "name": 1}
    )

    entries = await db.hour_bank_entries.find(
        {"member_id": member_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)

    threshold = plan.get("eligibility_threshold", 0) if plan else 0
    max_bank = plan.get("hour_bank_max", 0) if plan else 0
    cur = _safe_float(bank, "current_balance")
    res = _safe_float(bank, "reserve_balance")
    total = round(cur + res, 2)
    cushion = total - threshold if threshold > 0 else total
    eligibility_source = bank.get("eligibility_source", "standard_hours") if bank else "standard_hours"

    # Burn rate: average hours consumed per month over last 3 entries of type monthly_deduction
    deductions = [e for e in entries if e.get("entry_type") == "monthly_deduction"][:3]
    burn_rate = threshold  # default to threshold if no history
    if deductions:
        burn_rate = abs(sum(d.get("hours", 0) for d in deductions)) / len(deductions)

    months_remaining = (total / burn_rate) if burn_rate > 0 else 999
    at_risk = threshold > 0 and total < (2 * threshold)

    # Bridge info
    bridge_cfg = await _get_bridge_config()
    hours_short = max(0, threshold - cur)
    bridge_eligible = bridge_cfg.get("enabled", False) and hours_short > 0 and member.get("status") == "termed_insufficient_hours"
    bridge_cost = round(hours_short * bridge_cfg.get("rate_per_hour", 20), 2) if bridge_eligible else 0

    return {
        "member_id": member_id,
        "plan_name": plan.get("name", "—") if plan else "—",
        "current_balance": round(cur, 2),
        "reserve_balance": round(res, 2),
        "total_balance": total,
        "threshold": threshold,
        "max_bank": max_bank,
        "hours_until_deficit": round(cushion, 2),
        "burn_rate": round(burn_rate, 2),
        "months_remaining": round(months_remaining, 1),
        "at_risk": at_risk,
        "eligibility_source": eligibility_source,
        "status": member.get("status", "active"),
        "bridge": {
            "enabled": bridge_cfg.get("enabled", False),
            "eligible": bridge_eligible,
            "hours_short": round(hours_short, 2),
            "cost": bridge_cost,
            "rate_per_hour": bridge_cfg.get("rate_per_hour", 20),
        },
        "entries": entries,
    }


# ── Monthly Calculation (multi-tier) ──

@router.post("/run-monthly")
async def run_monthly_hour_bank(
    period: Optional[str] = None,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """End-of-month calculation with multi-tier banking.
    Current is consumed first, reserve covers deficits."""
    now = datetime.now(timezone.utc)
    if not period:
        period = now.strftime("%Y-%m")
    now_iso = now.isoformat()

    plans = await db.plans.find({"eligibility_threshold": {"$gt": 0}}, {"_id": 0}).to_list(1000)
    plan_map = {p["id"]: p for p in plans}
    if not plan_map:
        return {"message": "No plans with eligibility threshold configured", "processed": 0}

    members = await db.members.find(
        {"plan_id": {"$in": list(plan_map.keys())}}, {"_id": 0}
    ).to_list(100000)

    activated = 0
    termed = 0
    unchanged = 0
    reserve_draws = 0
    notifications = []

    for m in members:
        plan = plan_map.get(m.get("plan_id"))
        if not plan:
            continue

        threshold = plan.get("eligibility_threshold", 0)
        max_bank = plan.get("hour_bank_max", 0)

        existing = await db.hour_bank_entries.find_one({
            "member_id": m["member_id"], "entry_type": "monthly_deduction", "period": period,
        })
        if existing:
            unchanged += 1
            continue

        bank = await db.hour_bank.find_one({"member_id": m["member_id"]}, {"_id": 0})
        cur = _safe_float(bank, "current_balance")
        res = _safe_float(bank, "reserve_balance")
        total_before = cur + res

        # Multi-tier deduction
        if cur >= threshold:
            # Current covers it — overflow to reserve
            overflow = cur - threshold
            if max_bank > 0:
                overflow = min(overflow, max_bank - res)
                overflow = max(0, overflow)
            new_cur = 0.0
            new_res = res + overflow
            if max_bank > 0:
                new_res = min(new_res, max_bank)
            new_status = "active"
            elig_source = "standard_hours"
            activated += 1
        elif cur + res >= threshold:
            # Reserve draw covers the deficit
            deficit = threshold - cur
            new_cur = 0.0
            new_res = res - deficit
            new_status = "active"
            elig_source = "reserve_draw"
            activated += 1
            reserve_draws += 1
        else:
            # Insufficient hours
            new_cur = 0.0
            new_res = max(0, res - max(0, threshold - cur))
            new_status = "termed_insufficient_hours"
            elig_source = "insufficient"
            termed += 1

        new_total = new_cur + new_res

        await db.hour_bank_entries.insert_one({
            "id": str(uuid.uuid4()),
            "member_id": m["member_id"],
            "entry_type": "monthly_deduction",
            "hours": -threshold,
            "bucket": "current" if cur >= threshold else "reserve_draw",
            "running_balance": round(new_total, 2),
            "current_after": round(new_cur, 2),
            "reserve_after": round(new_res, 2),
            "description": f"Monthly deduction for {period} ({threshold} hrs)" +
                           (f" — Reserve draw: {round(threshold - cur, 1)} hrs" if elig_source == "reserve_draw" else ""),
            "week_ending": None,
            "period": period,
            "source": "system",
            "created_at": now_iso,
            "created_by": user["id"],
        })

        await db.hour_bank.update_one(
            {"member_id": m["member_id"]},
            {"$set": {
                "member_id": m["member_id"],
                "plan_id": m.get("plan_id", ""),
                "current_balance": round(new_cur, 2),
                "reserve_balance": round(new_res, 2),
                "last_calculated": period,
                "eligibility_source": elig_source,
                "updated_at": now_iso,
            }},
            upsert=True,
        )

        old_status = m.get("status", "active")
        if old_status != new_status:
            await db.members.update_one(
                {"member_id": m["member_id"]},
                {"$set": {"status": new_status, "updated_at": now_iso}}
            )
            await db.member_audit_trail.insert_one({
                "id": str(uuid.uuid4()),
                "member_id": m["member_id"],
                "action": "hour_bank_status_change",
                "user_id": "system",
                "details": {
                    "period": period,
                    "balance_before": round(total_before, 2),
                    "balance_after": round(new_total, 2),
                    "threshold": threshold,
                    "eligibility_source": elig_source,
                    "old_status": old_status,
                    "new_status": new_status,
                },
                "timestamp": now_iso,
            })

        # Low-balance notification if within 10 hours of threshold
        cushion = new_total - threshold
        if 0 <= cushion < 10 and new_status == "active":
            group = await db.groups.find_one({"id": m.get("group_id")}, {"_id": 0, "name": 1, "contact_email": 1})
            notifications.append({
                "id": str(uuid.uuid4()),
                "type": "low_hour_bank_balance",
                "member_id": m["member_id"],
                "member_name": f"{m.get('first_name', '')} {m.get('last_name', '')}",
                "group_id": m.get("group_id", ""),
                "group_name": group.get("name", "") if group else "",
                "admin_email": group.get("contact_email", "") if group else "",
                "current_balance": round(new_total, 2),
                "threshold": threshold,
                "cushion": round(cushion, 2),
                "created_at": now_iso,
                "read": False,
            })

    if notifications:
        await db.hour_bank_notifications.insert_many(notifications)

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "action": "hour_bank_monthly_run",
        "user_id": user["id"],
        "details": {"period": period, "activated": activated, "termed": termed, "unchanged": unchanged, "reserve_draws": reserve_draws, "notifications": len(notifications)},
        "timestamp": now_iso,
    })

    return {
        "period": period,
        "total_members": len(members),
        "activated": activated,
        "termed": termed,
        "unchanged": unchanged,
        "reserve_draws": reserve_draws,
        "notifications_sent": len(notifications),
    }


# ── Bridge Payment ──

@router.post("/{member_id}/bridge-payment")
async def log_bridge_payment(
    member_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Log a bridge payment for a member short on hours.
    Calculates cost, adds hours, flips status to Active, releases held claims."""
    member = await db.members.find_one({"member_id": member_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    bridge_cfg = await _get_bridge_config()
    if not bridge_cfg.get("enabled"):
        raise HTTPException(status_code=400, detail="Bridge payments are not enabled")

    plan = await db.plans.find_one(
        {"id": member.get("plan_id")},
        {"_id": 0, "eligibility_threshold": 1, "hour_bank_max": 1}
    )
    threshold = plan.get("eligibility_threshold", 0) if plan else 0
    if threshold <= 0:
        raise HTTPException(status_code=400, detail="Plan has no eligibility threshold")

    bank = await db.hour_bank.find_one({"member_id": member_id}, {"_id": 0})
    cur = _safe_float(bank, "current_balance")
    res = _safe_float(bank, "reserve_balance")
    total = cur + res

    hours_short = max(0, threshold - total)
    if hours_short <= 0:
        raise HTTPException(status_code=400, detail="Member is not short on hours")

    rate = bridge_cfg.get("rate_per_hour", 20)
    cost = round(hours_short * rate, 2)
    now = datetime.now(timezone.utc).isoformat()

    # Add bridge hours to current
    new_cur = cur + hours_short
    new_total = new_cur + res

    await db.hour_bank_entries.insert_one({
        "id": str(uuid.uuid4()),
        "member_id": member_id,
        "entry_type": "bridge_payment",
        "hours": hours_short,
        "bucket": "current",
        "running_balance": round(new_total, 2),
        "current_after": round(new_cur, 2),
        "reserve_after": round(res, 2),
        "description": f"Bridge Payment — {hours_short:.1f} hrs @ ${rate}/hr = ${cost:.2f}",
        "week_ending": None,
        "period": None,
        "source": "bridge_payment",
        "created_at": now,
        "created_by": user["id"],
    })

    await db.hour_bank.update_one(
        {"member_id": member_id},
        {"$set": {
            "current_balance": round(new_cur, 2),
            "eligibility_source": "bridge_payment",
            "updated_at": now,
        }},
        upsert=True,
    )

    # Flip status to active
    await db.members.update_one(
        {"member_id": member_id},
        {"$set": {"status": "active", "updated_at": now}}
    )

    # Release any held/pending claims for this member
    released_claims = await db.claims.find(
        {"member_id": member_id, "status": {"$in": [
            ClaimStatus.PENDING_REVIEW.value,
            ClaimStatus.MANAGERIAL_HOLD.value,
        ]}},
        {"_id": 0, "id": 1, "claim_number": 1}
    ).to_list(1000)

    released_ids = []
    for c in released_claims:
        await db.claims.update_one(
            {"id": c["id"]},
            {"$set": {
                "status": ClaimStatus.PENDING.value,
                "adjudication_notes": [f"BRIDGE PAYMENT: Coverage restored for {member_id}. Claim released for processing."],
                "eligibility_source": "bridge_payment",
            }}
        )
        released_ids.append(c["claim_number"])

    await db.member_audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "member_id": member_id,
        "action": "bridge_payment_logged",
        "user_id": user["id"],
        "details": {
            "hours_added": round(hours_short, 2),
            "cost": cost, "rate": rate,
            "claims_released": len(released_ids),
        },
        "timestamp": now,
    })

    return {
        "member_id": member_id,
        "hours_added": round(hours_short, 2),
        "cost": cost,
        "new_balance": round(new_total, 2),
        "status": "active",
        "claims_released": released_ids,
    }


# ── Notifications ──

@router.get("/notifications/list")
async def list_notifications(
    unread_only: bool = True,
    user: dict = Depends(get_current_user)
):
    """Get low-balance notifications for group admins."""
    query = {}
    if unread_only:
        query["read"] = False
    notifs = await db.hour_bank_notifications.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return notifs
