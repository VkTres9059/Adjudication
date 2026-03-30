"""SFTP Scheduler Service — Connection testing, file fetching, intelligent routing."""

import os
import io
import re
import fnmatch
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional

import paramiko
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from core.database import db
from core.config import logger
from services.edi_parser import parse_834_transactions, save_834_member, parse_837_transactions, save_837_claim
from services.claims import process_new_claim


scheduler = AsyncIOScheduler()
_scheduler_started = False


def start_scheduler():
    """Start the APScheduler background loop (idempotent)."""
    global _scheduler_started
    if not _scheduler_started:
        scheduler.start()
        _scheduler_started = True
        logger.info("SFTP Scheduler started")


async def rebuild_jobs():
    """Rebuild all scheduler jobs from the DB (called at startup and on config change)."""
    scheduler.remove_all_jobs()
    schedules = await db.sftp_schedules.find({"enabled": True}, {"_id": 0}).to_list(500)
    for sched in schedules:
        _add_job(sched)
    logger.info(f"Rebuilt {len(schedules)} SFTP scheduler jobs")


def _add_job(sched: dict):
    """Register a single schedule as an APScheduler job."""
    job_id = f"sftp_{sched['id']}"
    freq = sched.get("frequency", "daily")
    tod = sched.get("time_of_day", "02:00")
    hour, minute = (int(x) for x in tod.split(":")) if ":" in tod else (2, 0)
    dow = sched.get("day_of_week", "mon")

    if freq == "hourly":
        trigger = IntervalTrigger(hours=1)
    elif freq == "weekly":
        trigger = CronTrigger(day_of_week=dow, hour=hour, minute=minute)
    else:
        trigger = CronTrigger(hour=hour, minute=minute)

    scheduler.add_job(
        _run_schedule,
        trigger=trigger,
        id=job_id,
        args=[sched["id"]],
        replace_existing=True,
        misfire_grace_time=300,
    )


# ── Connection Testing ──

def test_sftp_connection(conn: dict) -> dict:
    """Attempt an SFTP connection and return success/failure."""
    transport = None
    sftp = None
    try:
        host = conn.get("host", "")
        port = int(conn.get("port", 22))
        username = conn.get("username", "")
        auth_type = conn.get("auth_type", "password")

        transport = paramiko.Transport((host, port))
        transport.connect(
            username=username,
            password=conn.get("password") if auth_type == "password" else None,
            pkey=_load_key(conn.get("ssh_key", "")) if auth_type == "key" else None,
        )
        sftp = paramiko.SFTPClient.from_transport(transport)
        base = conn.get("base_path", "/")
        listing = sftp.listdir(base)
        return {"success": True, "message": f"Connected. {len(listing)} items in {base}"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        if sftp:
            sftp.close()
        if transport:
            transport.close()


def _load_key(key_str: str) -> Optional[paramiko.PKey]:
    """Parse a PEM key string into a paramiko PKey."""
    if not key_str.strip():
        return None
    key_file = io.StringIO(key_str)
    for cls in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
        try:
            key_file.seek(0)
            return cls.from_private_key(key_file)
        except Exception:
            continue
    raise ValueError("Unsupported SSH key format")


# ── Schedule Execution ──

async def _run_schedule(schedule_id: str):
    """Execute a single SFTP schedule: connect, list, match, download, route."""
    sched = await db.sftp_schedules.find_one({"id": schedule_id}, {"_id": 0})
    if not sched or not sched.get("enabled"):
        return

    conn = await db.sftp_connections.find_one({"id": sched["connection_id"]}, {"_id": 0})
    if not conn or not conn.get("enabled"):
        return

    log_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    log_entry = {
        "id": log_id,
        "schedule_id": schedule_id,
        "connection_name": conn.get("name", "Unknown"),
        "schedule_name": sched.get("name", ""),
        "route_type": sched.get("route_type", "834"),
        "filename": "",
        "records_processed": 0,
        "status": "running",
        "error_message": None,
        "started_at": now,
        "completed_at": None,
    }
    await db.sftp_intake_logs.insert_one(log_entry)

    transport = None
    sftp_client = None
    try:
        host = conn.get("host", "")
        port = int(conn.get("port", 22))
        transport = paramiko.Transport((host, port))
        auth_type = conn.get("auth_type", "password")
        transport.connect(
            username=conn.get("username", ""),
            password=conn.get("password") if auth_type == "password" else None,
            pkey=_load_key(conn.get("ssh_key", "")) if auth_type == "key" else None,
        )
        sftp_client = paramiko.SFTPClient.from_transport(transport)

        base_path = conn.get("base_path", "/")
        file_pattern = sched.get("file_pattern", "*")
        listing = sftp_client.listdir(base_path)

        matched = [f for f in listing if fnmatch.fnmatch(f, file_pattern)]
        if not matched:
            await db.sftp_intake_logs.update_one({"id": log_id}, {"$set": {
                "status": "success", "error_message": "No matching files found",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }})
            return

        total_records = 0
        errors = []
        filenames = []

        for fname in matched:
            remote_path = f"{base_path.rstrip('/')}/{fname}"
            with io.BytesIO() as buf:
                sftp_client.getfo(remote_path, buf)
                buf.seek(0)
                content = buf.read().decode("utf-8", errors="replace")

            result = await _route_file(content, fname, sched.get("route_type", "834"))
            total_records += result.get("records", 0)
            if result.get("errors"):
                errors.extend(result["errors"])
            filenames.append(fname)

        status = "success" if not errors else "partial"
        await db.sftp_intake_logs.update_one({"id": log_id}, {"$set": {
            "filename": ", ".join(filenames[:5]),
            "records_processed": total_records,
            "status": status,
            "error_message": "; ".join(errors[:5]) if errors else None,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }})

        await db.sftp_schedules.update_one({"id": schedule_id}, {"$set": {
            "last_run": datetime.now(timezone.utc).isoformat(),
        }})

    except Exception as e:
        logger.error(f"SFTP schedule {schedule_id} failed: {e}")
        await db.sftp_intake_logs.update_one({"id": log_id}, {"$set": {
            "status": "failed",
            "error_message": str(e),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }})
    finally:
        if sftp_client:
            sftp_client.close()
        if transport:
            transport.close()


async def run_schedule_now(schedule_id: str):
    """Manually trigger a schedule (runs in background)."""
    asyncio.create_task(_run_schedule(schedule_id))


# ── Intelligent File Routing ──

SYSTEM_USER = {"id": "system_sftp", "name": "SFTP Scheduler", "role": "admin", "email": "system@fletchflow.com"}


async def _route_file(content: str, filename: str, route_type: str) -> dict:
    """Route a downloaded file to the appropriate processing module."""
    if route_type == "834":
        return await _route_834(content, filename)
    elif route_type in ("835", "claims"):
        return await _route_837(content, filename)
    elif route_type == "work_report":
        return await _route_work_report(content, filename)
    return {"records": 0, "errors": [f"Unknown route type: {route_type}"]}


async def _route_834(content: str, filename: str) -> dict:
    """Route 834 file to Member Enrollment."""
    is_x12 = content.strip().startswith("ISA")
    records = 0
    errors = []

    if is_x12:
        result = await parse_834_transactions(content)
        if not result.get("success"):
            return {"records": 0, "errors": [result.get("error", "834 parse failed")]}
        for m in result.get("members", []):
            try:
                await save_834_member(m)
                records += 1
            except Exception as e:
                errors.append(f"{m.get('member_id', '?')}: {e}")
    else:
        for line in content.strip().split("\n"):
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) >= 8:
                records += 1

    await _log_edi_transaction("834", filename, records, errors)
    return {"records": records, "errors": errors}


async def _route_837(content: str, filename: str) -> dict:
    """Route 837/claims file to Adjudication Engine."""
    is_x12 = content.strip().startswith("ISA")
    records = 0
    errors = []

    if is_x12:
        result = await parse_837_transactions(content)
        if not result.get("success"):
            return {"records": 0, "errors": [result.get("error", "837 parse failed")]}
        for c in result.get("claims", []):
            try:
                svc_lines = c.get("service_lines", [])
                diag_codes = c.get("diagnosis_codes", [])
                await save_837_claim(c, svc_lines, diag_codes, SYSTEM_USER)
                records += 1
            except Exception as e:
                errors.append(f"Claim {c.get('patient_control', '?')}: {e}")
    else:
        for line in content.strip().split("\n"):
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) >= 9:
                records += 1

    await _log_edi_transaction("837", filename, records, errors)
    return {"records": records, "errors": errors}


async def _route_work_report(content: str, filename: str) -> dict:
    """Route work report CSV to Hour Bank Module."""
    records = 0
    errors = []
    now = datetime.now(timezone.utc).isoformat()

    for line in content.strip().split("\n"):
        if not line or line.startswith("#") or line.lower().startswith("member"):
            continue
        try:
            parts = line.split(",")
            if len(parts) >= 3:
                member_id = parts[0].strip()
                hours = float(parts[1].strip())
                period = parts[2].strip() if len(parts) > 2 else now[:7]

                member = await db.members.find_one({"member_id": member_id}, {"_id": 0})
                if not member:
                    errors.append(f"Unknown member: {member_id}")
                    await _log_duplicate_error(filename, member_id, f"Work report for unknown member {member_id}")
                    continue

                bank = await db.hour_bank.find_one({"member_id": member_id}, {"_id": 0})
                if bank:
                    new_balance = float(bank.get("current_balance", 0)) + hours
                    await db.hour_bank.update_one({"member_id": member_id}, {"$set": {
                        "current_balance": new_balance,
                        "updated_at": now,
                    }, "$push": {"ledger": {
                        "id": str(uuid.uuid4()), "type": "hours_reported",
                        "hours": hours, "period": period, "source": f"sftp:{filename}",
                        "created_at": now,
                    }}})
                else:
                    await db.hour_bank.insert_one({
                        "id": str(uuid.uuid4()), "member_id": member_id,
                        "current_balance": hours, "reserve_balance": 0,
                        "status": "active", "ledger": [{
                            "id": str(uuid.uuid4()), "type": "hours_reported",
                            "hours": hours, "period": period, "source": f"sftp:{filename}",
                            "created_at": now,
                        }],
                        "created_at": now, "updated_at": now,
                    })
                records += 1
        except Exception as e:
            errors.append(f"Line error: {e}")

    await _log_edi_transaction("work_report", filename, records, errors)
    return {"records": records, "errors": errors}


async def _log_edi_transaction(tx_type: str, filename: str, records: int, errors: list):
    """Write to the shared edi_transactions collection for cross-module visibility."""
    await db.edi_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "type": tx_type,
        "filename": filename,
        "status": "success" if not errors else "partial",
        "record_count": records,
        "error_count": len(errors),
        "errors": errors[:20],
        "envelope": None,
        "segment_count": 0,
        "processed_by": "sftp_scheduler",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


async def _log_duplicate_error(filename: str, member_id: str, message: str):
    """Push failed records to the duplicates/errors queue."""
    await db.duplicate_alerts.insert_one({
        "id": str(uuid.uuid4()),
        "type": "sftp_intake_error",
        "source_file": filename,
        "member_id": member_id,
        "message": message,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
