"""
Plan Versioning Service — Snapshot-based version control for plan designs.
Every update creates a versioned snapshot. Adjudicated claims reference the
plan_version_id that was active at time of adjudication.
"""
from datetime import datetime, timezone
import uuid
import copy
from core.database import db


async def snapshot_plan_version(plan: dict, user_id: str, change_summary: str = "") -> dict:
    """Create an immutable snapshot of the current plan state before an update."""
    snapshot = copy.deepcopy(plan)
    snapshot.pop("_id", None)

    version_doc = {
        "id": str(uuid.uuid4()),
        "plan_id": plan["id"],
        "version": plan.get("version", 1),
        "snapshot": snapshot,
        "change_summary": change_summary,
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.plan_versions.insert_one(version_doc)
    version_doc.pop("_id", None)
    return version_doc


async def get_plan_version_history(plan_id: str, limit: int = 50) -> list:
    """Get version history for a plan."""
    versions = await db.plan_versions.find(
        {"plan_id": plan_id}, {"_id": 0, "snapshot": 0}
    ).sort("version", -1).to_list(limit)
    return versions


async def get_plan_version(version_id: str) -> dict:
    """Get a specific plan version snapshot."""
    v = await db.plan_versions.find_one({"id": version_id}, {"_id": 0})
    return v


async def get_plan_at_version(plan_id: str, version: int) -> dict:
    """Get plan state at a specific version number."""
    v = await db.plan_versions.find_one(
        {"plan_id": plan_id, "version": version}, {"_id": 0}
    )
    if v:
        return v.get("snapshot")
    return None


async def diff_plan_versions(plan_id: str, v1: int, v2: int) -> dict:
    """Compare two versions of a plan and return differences."""
    snap1 = await get_plan_at_version(plan_id, v1)
    snap2 = await get_plan_at_version(plan_id, v2)
    if not snap1 or not snap2:
        return {"error": "Version not found"}

    changes = []
    skip_keys = {"_id", "created_at", "updated_at", "version", "created_by"}

    all_keys = set(list(snap1.keys()) + list(snap2.keys())) - skip_keys
    for key in sorted(all_keys):
        val1 = snap1.get(key)
        val2 = snap2.get(key)
        if val1 != val2:
            changes.append({
                "field": key,
                "from_value": str(val1)[:200] if val1 is not None else None,
                "to_value": str(val2)[:200] if val2 is not None else None,
            })

    return {
        "plan_id": plan_id,
        "from_version": v1,
        "to_version": v2,
        "changes": changes,
        "total_changes": len(changes),
    }
