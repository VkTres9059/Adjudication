from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from datetime import datetime, timezone
from typing import Optional
import uuid
import csv
import io

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole

router = APIRouter(prefix="/hour-bank", tags=["hour_bank"])


@router.post("/upload-work-report")
async def upload_work_report(
    file: UploadFile = File(...),
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Ingest a Work Report CSV containing weekly worked hours per member.
    Expected columns: member_id, week_ending, hours_worked
    """
    content = await file.read()
    content_str = content.decode("utf-8")
    now = datetime.now(timezone.utc).isoformat()

    reader = csv.DictReader(io.StringIO(content_str))
    inserted = 0
    errors = []

    for i, row in enumerate(reader):
        try:
            member_id = row.get("member_id", "").strip()
            week_ending = row.get("week_ending", "").strip()
            hours_str = row.get("hours_worked", "0").strip()
            hours = float(hours_str)

            if not member_id or not week_ending:
                errors.append(f"Row {i+1}: missing member_id or week_ending")
                continue

            member = await db.members.find_one({"member_id": member_id}, {"_id": 0, "member_id": 1, "plan_id": 1})
            if not member:
                errors.append(f"Row {i+1}: member {member_id} not found")
                continue

            # Get current bank balance
            bank = await db.hour_bank.find_one({"member_id": member_id}, {"_id": 0})
            balance_before = bank["current_balance"] if bank else 0.0
            new_balance = balance_before + hours

            plan = await db.plans.find_one({"id": member.get("plan_id")}, {"_id": 0, "hour_bank_max": 1})
            max_bank = plan.get("hour_bank_max", 0) if plan else 0
            if max_bank > 0:
                new_balance = min(new_balance, max_bank)

            # Insert ledger entry
            entry = {
                "id": str(uuid.uuid4()),
                "member_id": member_id,
                "entry_type": "work_hours",
                "hours": hours,
                "running_balance": round(new_balance, 2),
                "description": f"Work hours - week ending {week_ending}",
                "week_ending": week_ending,
                "period": None,
                "source": file.filename or "csv_upload",
                "created_at": now,
                "created_by": user["id"],
            }
            await db.hour_bank_entries.insert_one(entry)

            # Update running balance
            await db.hour_bank.update_one(
                {"member_id": member_id},
                {"$set": {
                    "member_id": member_id,
                    "plan_id": member.get("plan_id", ""),
                    "current_balance": round(new_balance, 2),
                    "updated_at": now,
                }},
                upsert=True,
            )
            inserted += 1

        except Exception as e:
            errors.append(f"Row {i+1}: {str(e)}")

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "hour_bank_work_report_uploaded",
        "user_id": user["id"],
        "details": {"filename": file.filename, "rows_inserted": inserted, "errors": len(errors)},
        "timestamp": now,
    })

    return {"rows_inserted": inserted, "errors": errors}


@router.get("/{member_id}")
async def get_member_hour_bank(member_id: str, user: dict = Depends(get_current_user)):
    """Get hour bank summary and ledger for a member."""
    member = await db.members.find_one({"member_id": member_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    bank = await db.hour_bank.find_one({"member_id": member_id}, {"_id": 0})

    plan = await db.plans.find_one({"id": member.get("plan_id")}, {"_id": 0, "eligibility_threshold": 1, "hour_bank_max": 1, "name": 1})

    entries = await db.hour_bank_entries.find(
        {"member_id": member_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)

    threshold = plan.get("eligibility_threshold", 0) if plan else 0
    max_bank = plan.get("hour_bank_max", 0) if plan else 0
    current_balance = bank["current_balance"] if bank else 0.0
    hours_until_deficit = current_balance - threshold if threshold > 0 else current_balance

    return {
        "member_id": member_id,
        "plan_name": plan.get("name", "—") if plan else "—",
        "current_balance": round(current_balance, 2),
        "threshold": threshold,
        "max_bank": max_bank,
        "hours_until_deficit": round(hours_until_deficit, 2),
        "status": member.get("status", "active"),
        "entries": entries,
    }


@router.post("/run-monthly")
async def run_monthly_hour_bank(
    period: Optional[str] = None,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Run end-of-month hour bank calculation.
    Deducts threshold from each member's bank. Updates status accordingly.
    period format: YYYY-MM (defaults to current month)
    """
    now = datetime.now(timezone.utc)
    if not period:
        period = now.strftime("%Y-%m")
    now_iso = now.isoformat()

    # Find all plans with hour bank enabled
    plans = await db.plans.find(
        {"eligibility_threshold": {"$gt": 0}}, {"_id": 0}
    ).to_list(1000)
    plan_map = {p["id"]: p for p in plans}

    if not plan_map:
        return {"message": "No plans with eligibility threshold configured", "processed": 0}

    # Find all members on these plans
    plan_ids = list(plan_map.keys())
    members = await db.members.find(
        {"plan_id": {"$in": plan_ids}}, {"_id": 0}
    ).to_list(100000)

    activated = 0
    termed = 0
    unchanged = 0

    for m in members:
        plan = plan_map.get(m.get("plan_id"))
        if not plan:
            continue

        threshold = plan.get("eligibility_threshold", 0)
        max_bank = plan.get("hour_bank_max", 0)

        bank = await db.hour_bank.find_one({"member_id": m["member_id"]}, {"_id": 0})
        balance_before = bank["current_balance"] if bank else 0.0

        # Check if already deducted for this period
        existing_deduction = await db.hour_bank_entries.find_one({
            "member_id": m["member_id"],
            "entry_type": "monthly_deduction",
            "period": period,
        })
        if existing_deduction:
            unchanged += 1
            continue

        result = balance_before - threshold

        if result >= 0:
            new_balance = min(result, max_bank) if max_bank > 0 else result
            new_status = "active"
            activated += 1
        else:
            new_balance = result
            new_status = "termed_insufficient_hours"
            termed += 1

        # Insert deduction ledger entry
        await db.hour_bank_entries.insert_one({
            "id": str(uuid.uuid4()),
            "member_id": m["member_id"],
            "entry_type": "monthly_deduction",
            "hours": -threshold,
            "running_balance": round(new_balance, 2),
            "description": f"Monthly threshold deduction for {period} ({threshold} hrs)",
            "week_ending": None,
            "period": period,
            "source": "system",
            "created_at": now_iso,
            "created_by": user["id"],
        })

        # Update bank balance
        await db.hour_bank.update_one(
            {"member_id": m["member_id"]},
            {"$set": {
                "member_id": m["member_id"],
                "plan_id": m.get("plan_id", ""),
                "current_balance": round(new_balance, 2),
                "last_calculated": period,
                "updated_at": now_iso,
            }},
            upsert=True,
        )

        # Auto-status flip on the member record
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
                    "balance_before": round(balance_before, 2),
                    "balance_after": round(new_balance, 2),
                    "threshold": threshold,
                    "old_status": old_status,
                    "new_status": new_status,
                },
                "timestamp": now_iso,
            })

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "hour_bank_monthly_run",
        "user_id": user["id"],
        "details": {"period": period, "activated": activated, "termed": termed, "unchanged": unchanged},
        "timestamp": now_iso,
    })

    return {
        "period": period,
        "total_members": len(members),
        "activated": activated,
        "termed": termed,
        "unchanged": unchanged,
    }
