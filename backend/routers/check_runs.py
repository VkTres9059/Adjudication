"""ASO Check Run Manager — Aggregate approved claims, generate funding requests, execute check runs."""

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole, ClaimStatus

router = APIRouter(prefix="/check-runs", tags=["check-runs"])


@router.get("/groups")
async def list_aso_groups(user: dict = Depends(get_current_user)):
    """List all ASO groups eligible for check runs."""
    groups = await db.groups.find(
        {"funding_type": "aso", "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "tax_id": 1, "employee_count": 1, "funding_type": 1}
    ).sort("name", 1).to_list(500)
    return groups


@router.get("/pending")
async def get_pending_check_run(
    group_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Aggregate all approved claims not yet in a check run, grouped by ASO group."""
    match = {"status": ClaimStatus.APPROVED.value, "check_run_id": {"$exists": False}}
    if group_id:
        # Get member_ids for this group
        members = await db.members.find({"group_id": group_id}, {"member_id": 1, "_id": 0}).to_list(100000)
        mids = [m["member_id"] for m in members]
        match["member_id"] = {"$in": mids}

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$member_id",
            "claim_count": {"$sum": 1},
            "total_billed": {"$sum": "$total_billed"},
            "total_allowed": {"$sum": {"$ifNull": ["$total_allowed", 0]}},
            "total_paid": {"$sum": "$total_paid"},
            "member_resp": {"$sum": "$member_responsibility"},
            "claim_ids": {"$push": "$id"},
        }},
    ]
    results = await db.claims.aggregate(pipeline).to_list(100000)

    # Map member → group
    all_mids = [r["_id"] for r in results]
    members = await db.members.find(
        {"member_id": {"$in": all_mids}},
        {"_id": 0, "member_id": 1, "group_id": 1, "first_name": 1, "last_name": 1}
    ).to_list(100000)
    member_map = {m["member_id"]: m for m in members}

    # Get group names
    group_ids = list(set(m.get("group_id", "") for m in members))
    groups = await db.groups.find(
        {"id": {"$in": group_ids}, "funding_type": "aso"},
        {"_id": 0, "id": 1, "name": 1}
    ).to_list(500)
    group_map = {g["id"]: g["name"] for g in groups}

    # Build response grouped by group
    by_group = {}
    for r in results:
        mem = member_map.get(r["_id"], {})
        gid = mem.get("group_id", "unknown")
        if gid not in group_map:
            continue  # Skip non-ASO groups
        if gid not in by_group:
            by_group[gid] = {
                "group_id": gid,
                "group_name": group_map.get(gid, "Unknown"),
                "claim_count": 0,
                "total_billed": 0,
                "total_paid": 0,
                "member_resp": 0,
                "provider_payable": 0,
                "claim_ids": [],
                "members": [],
            }
        by_group[gid]["claim_count"] += r["claim_count"]
        by_group[gid]["total_billed"] += r["total_billed"]
        by_group[gid]["total_paid"] += r["total_paid"]
        by_group[gid]["member_resp"] += r["member_resp"]
        by_group[gid]["provider_payable"] += r["total_paid"]
        by_group[gid]["claim_ids"].extend(r["claim_ids"])
        by_group[gid]["members"].append({
            "member_id": r["_id"],
            "name": f"{mem.get('first_name', '')} {mem.get('last_name', '')}".strip(),
            "claim_count": r["claim_count"],
            "total_paid": round(r["total_paid"], 2),
        })

    summary = list(by_group.values())
    for s in summary:
        s["total_billed"] = round(s["total_billed"], 2)
        s["total_paid"] = round(s["total_paid"], 2)
        s["member_resp"] = round(s["member_resp"], 2)
        s["provider_payable"] = round(s["provider_payable"], 2)

    return summary


@router.post("/generate-funding-request")
async def generate_funding_request(
    group_id: str = Query(...),
    user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """Generate a funding request for an ASO group (aggregates approved, un-run claims)."""
    group = await db.groups.find_one({"id": group_id, "funding_type": "aso"}, {"_id": 0})
    if not group:
        raise HTTPException(404, "ASO group not found")

    members = await db.members.find({"group_id": group_id}, {"member_id": 1, "_id": 0}).to_list(100000)
    mids = [m["member_id"] for m in members]

    claims = await db.claims.find(
        {"status": ClaimStatus.APPROVED.value, "check_run_id": {"$exists": False}, "member_id": {"$in": mids}},
        {"_id": 0}
    ).to_list(100000)

    if not claims:
        raise HTTPException(400, "No approved claims pending for this group")

    now = datetime.now(timezone.utc)
    request_id = str(uuid.uuid4())

    total_payable = sum(c.get("total_paid", 0) for c in claims)

    doc = {
        "id": request_id,
        "group_id": group_id,
        "group_name": group.get("name", ""),
        "status": "pending_funding",  # pending_funding → funded → executed
        "claim_count": len(claims),
        "total_billed": round(sum(c.get("total_billed", 0) for c in claims), 2),
        "total_payable": round(total_payable, 2),
        "member_responsibility": round(sum(c.get("member_responsibility", 0) for c in claims), 2),
        "claim_ids": [c["id"] for c in claims],
        "period_from": min(c.get("adjudicated_at", c.get("created_at", "")) for c in claims)[:10],
        "period_to": max(c.get("adjudicated_at", c.get("created_at", "")) for c in claims)[:10],
        "created_by": user["id"],
        "created_at": now.isoformat(),
        "funded_at": None,
        "executed_at": None,
    }
    await db.check_runs.insert_one(doc)

    # Mark claims as part of this check run
    await db.claims.update_many(
        {"id": {"$in": doc["claim_ids"]}},
        {"$set": {"check_run_id": request_id, "check_run_status": "pending_funding"}}
    )

    doc.pop("_id", None)
    return doc


@router.post("/{run_id}/confirm-funding")
async def confirm_funding(run_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Employer confirms funding is available. Moves check run to 'funded' status."""
    run = await db.check_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Check run not found")
    if run["status"] != "pending_funding":
        raise HTTPException(400, f"Check run is '{run['status']}', expected 'pending_funding'")

    now = datetime.now(timezone.utc).isoformat()
    await db.check_runs.update_one({"id": run_id}, {"$set": {"status": "funded", "funded_at": now}})
    await db.claims.update_many(
        {"check_run_id": run_id},
        {"$set": {"check_run_status": "funded"}}
    )
    return {"status": "funded", "run_id": run_id, "funded_at": now}


@router.post("/{run_id}/execute")
async def execute_check_run(run_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Execute the check run: generate digital check file (ACH batch) and move claims to Paid."""
    run = await db.check_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Check run not found")
    if run["status"] != "funded":
        raise HTTPException(400, f"Check run must be 'funded' to execute, currently '{run['status']}'")

    now = datetime.now(timezone.utc)
    batch_number = f"ACH-{now.strftime('%Y%m%d')}-{run_id[:8].upper()}"

    # Move all claims to 'paid'
    await db.claims.update_many(
        {"check_run_id": run_id},
        {"$set": {
            "status": "paid",
            "check_run_status": "executed",
            "paid_at": now.isoformat(),
            "ach_batch": batch_number,
        }}
    )

    await db.check_runs.update_one({"id": run_id}, {"$set": {
        "status": "executed",
        "executed_at": now.isoformat(),
        "ach_batch": batch_number,
    }})

    # Generate ACH content (simplified Nacha-like format)
    claims = await db.claims.find({"check_run_id": run_id}, {"_id": 0}).to_list(100000)
    ach_lines = [
        f"1{' ' * 2}01{' ' * 10}FLETCHFLOW{' ' * 13}{now.strftime('%y%m%d%H%M')}{batch_number}",
        f"5220{run.get('group_name', '')[:16]:<16s}{run.get('group_id', '')[:10]:<10s}PPD CLMPAY  {now.strftime('%y%m%d')}{now.strftime('%y%m%d')}   1",
    ]
    for c in claims:
        ach_lines.append(
            f"6{c.get('provider_npi', '000000000'):<17s}{int(c.get('total_paid', 0) * 100):010d}{c.get('member_id', ''):<15s}{c.get('claim_number', '')}"
        )
    ach_lines.append(f"8{len(claims):06d}{int(run.get('total_payable', 0) * 100):012d}")
    ach_lines.append(f"9{' ' * 80}")
    ach_content = "\n".join(ach_lines)

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "check_run_executed",
        "user_id": user["id"],
        "timestamp": now.isoformat(),
        "details": {
            "run_id": run_id,
            "group_id": run["group_id"],
            "claim_count": run["claim_count"],
            "total_payable": run["total_payable"],
            "ach_batch": batch_number,
        }
    })

    return {
        "status": "executed",
        "run_id": run_id,
        "ach_batch": batch_number,
        "claim_count": len(claims),
        "total_payable": run["total_payable"],
        "ach_content": ach_content,
    }


@router.get("")
async def list_check_runs(
    group_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    """List check run history."""
    query = {}
    if group_id:
        query["group_id"] = group_id
    if status:
        query["status"] = status
    runs = await db.check_runs.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return runs


@router.get("/{run_id}")
async def get_check_run(run_id: str, user: dict = Depends(get_current_user)):
    """Get a single check run with its claims."""
    run = await db.check_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Check run not found")
    claims = await db.claims.find(
        {"check_run_id": run_id},
        {"_id": 0, "id": 1, "claim_number": 1, "member_id": 1, "provider_npi": 1, "total_billed": 1, "total_paid": 1, "status": 1}
    ).to_list(100000)
    run["claims"] = claims
    return run
