"""SFTP Scheduler Router — Connection CRUD, schedule management, intake logs."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import asyncio

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole
from services.sftp_scheduler import (
    test_sftp_connection, rebuild_jobs, run_schedule_now,
)

router = APIRouter(prefix="/sftp", tags=["sftp"])


# ── Schemas ──

class SFTPConnectionCreate(BaseModel):
    name: str
    host: str
    port: int = 22
    username: str
    auth_type: str = "password"  # "password" or "key"
    password: Optional[str] = ""
    ssh_key: Optional[str] = ""
    base_path: str = "/"
    enabled: bool = True


class SFTPScheduleCreate(BaseModel):
    name: str
    connection_id: str
    frequency: str = "daily"  # hourly, daily, weekly
    time_of_day: str = "02:00"
    day_of_week: str = "mon"
    file_pattern: str = "*"
    route_type: str = "834"  # 834, 835, work_report
    enabled: bool = True


# ═══════════════════════════════════════
# SFTP Connections
# ═══════════════════════════════════════

@router.get("/connections")
async def list_connections(user: dict = Depends(get_current_user)):
    """List all SFTP connection configurations."""
    conns = await db.sftp_connections.find({}, {"_id": 0}).sort("name", 1).to_list(100)
    # Mask passwords in response
    for c in conns:
        if c.get("password"):
            c["password"] = "••••••••"
        if c.get("ssh_key"):
            c["ssh_key"] = "••••(key stored)••••"
    return conns


@router.post("/connections")
async def create_connection(config: SFTPConnectionCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a new SFTP connection."""
    now = datetime.now(timezone.utc).isoformat()
    doc = config.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = now
    doc["updated_at"] = now
    await db.sftp_connections.insert_one(doc)
    # Mask in response
    resp = {k: v for k, v in doc.items() if k != "_id"}
    if resp.get("password"):
        resp["password"] = "••••••••"
    if resp.get("ssh_key"):
        resp["ssh_key"] = "••••(key stored)••••"
    return resp


@router.put("/connections/{conn_id}")
async def update_connection(conn_id: str, config: SFTPConnectionCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Update an SFTP connection. If password/key is masked, keep existing."""
    existing = await db.sftp_connections.find_one({"id": conn_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Connection not found")

    doc = config.model_dump()
    # Preserve secrets if masked values sent back
    if doc.get("password", "").startswith("••"):
        doc["password"] = existing.get("password", "")
    if doc.get("ssh_key", "").startswith("••"):
        doc["ssh_key"] = existing.get("ssh_key", "")
    doc["id"] = conn_id
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.sftp_connections.update_one({"id": conn_id}, {"$set": doc})
    resp = {k: v for k, v in doc.items() if k != "_id"}
    if resp.get("password"):
        resp["password"] = "••••••••"
    if resp.get("ssh_key"):
        resp["ssh_key"] = "••••(key stored)••••"
    return resp


@router.delete("/connections/{conn_id}")
async def delete_connection(conn_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Delete an SFTP connection and its schedules."""
    await db.sftp_connections.delete_one({"id": conn_id})
    await db.sftp_schedules.delete_many({"connection_id": conn_id})
    await rebuild_jobs()
    return {"status": "deleted"}


@router.post("/connections/{conn_id}/test")
async def test_connection(conn_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Test an SFTP connection without running a full sync."""
    conn = await db.sftp_connections.find_one({"id": conn_id}, {"_id": 0})
    if not conn:
        raise HTTPException(404, "Connection not found")
    # Run the blocking paramiko call in a thread
    result = await asyncio.to_thread(test_sftp_connection, conn)
    return result


@router.post("/connections/test-inline")
async def test_inline_connection(config: SFTPConnectionCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Test SFTP credentials before saving (inline test)."""
    result = await asyncio.to_thread(test_sftp_connection, config.model_dump())
    return result


# ═══════════════════════════════════════
# SFTP Schedules
# ═══════════════════════════════════════

@router.get("/schedules")
async def list_schedules(user: dict = Depends(get_current_user)):
    """List all SFTP intake schedules."""
    schedules = await db.sftp_schedules.find({}, {"_id": 0}).sort("name", 1).to_list(200)
    return schedules


@router.post("/schedules")
async def create_schedule(config: SFTPScheduleCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a new SFTP intake schedule."""
    conn = await db.sftp_connections.find_one({"id": config.connection_id}, {"_id": 0})
    if not conn:
        raise HTTPException(400, "Connection not found")

    now = datetime.now(timezone.utc).isoformat()
    doc = config.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["connection_name"] = conn.get("name", "Unknown")
    doc["last_run"] = None
    doc["created_at"] = now
    await db.sftp_schedules.insert_one(doc)
    await rebuild_jobs()
    return {k: v for k, v in doc.items() if k != "_id"}


@router.put("/schedules/{schedule_id}")
async def update_schedule(schedule_id: str, config: SFTPScheduleCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Update an SFTP schedule."""
    existing = await db.sftp_schedules.find_one({"id": schedule_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Schedule not found")

    conn = await db.sftp_connections.find_one({"id": config.connection_id}, {"_id": 0})
    doc = config.model_dump()
    doc["id"] = schedule_id
    doc["connection_name"] = conn.get("name", "Unknown") if conn else existing.get("connection_name", "")
    doc["last_run"] = existing.get("last_run")
    await db.sftp_schedules.update_one({"id": schedule_id}, {"$set": doc})
    await rebuild_jobs()
    return {k: v for k, v in doc.items() if k != "_id"}


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    await db.sftp_schedules.delete_one({"id": schedule_id})
    await rebuild_jobs()
    return {"status": "deleted"}


@router.put("/schedules/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Enable/disable a schedule."""
    sched = await db.sftp_schedules.find_one({"id": schedule_id}, {"_id": 0})
    if not sched:
        raise HTTPException(404, "Schedule not found")
    new_val = not sched.get("enabled", True)
    await db.sftp_schedules.update_one({"id": schedule_id}, {"$set": {"enabled": new_val}})
    await rebuild_jobs()
    return {"enabled": new_val}


@router.post("/schedules/{schedule_id}/run-now")
async def trigger_run(schedule_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Manually trigger a schedule to run now."""
    sched = await db.sftp_schedules.find_one({"id": schedule_id}, {"_id": 0})
    if not sched:
        raise HTTPException(404, "Schedule not found")
    await run_schedule_now(schedule_id)
    return {"status": "triggered", "schedule_id": schedule_id}


# ═══════════════════════════════════════
# Intake Logs
# ═══════════════════════════════════════

@router.get("/intake-logs")
async def list_intake_logs(
    limit: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List SFTP intake history."""
    query = {}
    if status:
        query["status"] = status
    logs = await db.sftp_intake_logs.find(query, {"_id": 0}).sort("started_at", -1).to_list(limit)
    return logs
