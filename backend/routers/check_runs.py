"""ASO Check Run Manager — Provider batching, WF integration, vendor payables, PDF generation."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import io

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole, ClaimStatus
from services.wells_fargo import (
    initiate_funding_pull, initiate_disbursement,
    process_webhook, simulate_all_complete, get_transactions,
)

router = APIRouter(prefix="/check-runs", tags=["check-runs"])


# ── Schemas ──

class VendorPayableCreate(BaseModel):
    group_id: str
    vendor_name: str
    fee_type: str  # pbm_access, telehealth_pepm, network_access, admin_fee, other
    description: str = ""
    amount: float
    frequency: str = "monthly"  # monthly, weekly, per_claim, one_time
    is_active: bool = True


class WebhookPayload(BaseModel):
    transaction_id: str
    status: str = "completed"
    timestamp: Optional[str] = None


# ═══════════════════════════════════════
# ASO Groups
# ═══════════════════════════════════════

@router.get("/groups")
async def list_aso_groups(user: dict = Depends(get_current_user)):
    """List all ASO groups eligible for check runs."""
    groups = await db.groups.find(
        {"funding_type": "aso", "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "tax_id": 1, "employee_count": 1, "funding_type": 1}
    ).sort("name", 1).to_list(500)
    return groups


# ═══════════════════════════════════════
# Pending Claims — Provider-Level Batching
# ═══════════════════════════════════════

@router.get("/pending")
async def get_pending_check_run(
    group_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Aggregate approved claims by ASO group AND provider for consolidated payments."""
    match = {"status": ClaimStatus.APPROVED.value, "check_run_id": {"$exists": False}}
    if group_id:
        members = await db.members.find({"group_id": group_id}, {"member_id": 1, "_id": 0}).to_list(100000)
        mids = [m["member_id"] for m in members]
        match["member_id"] = {"$in": mids}

    # Aggregate by member
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {"member_id": "$member_id", "provider_npi": {"$ifNull": ["$provider_npi", "UNKNOWN"]}},
            "claim_count": {"$sum": 1},
            "total_billed": {"$sum": "$total_billed"},
            "total_paid": {"$sum": "$total_paid"},
            "member_resp": {"$sum": "$member_responsibility"},
            "claim_ids": {"$push": "$id"},
            "provider_name": {"$first": {"$ifNull": ["$provider_name", ""]}},
        }},
    ]
    results = await db.claims.aggregate(pipeline).to_list(100000)

    # Map members → groups
    all_mids = list(set(r["_id"]["member_id"] for r in results))
    members = await db.members.find(
        {"member_id": {"$in": all_mids}},
        {"_id": 0, "member_id": 1, "group_id": 1, "first_name": 1, "last_name": 1}
    ).to_list(100000)
    member_map = {m["member_id"]: m for m in members}

    group_ids = list(set(m.get("group_id", "") for m in members))
    groups = await db.groups.find(
        {"id": {"$in": group_ids}, "funding_type": "aso"},
        {"_id": 0, "id": 1, "name": 1}
    ).to_list(500)
    group_map = {g["id"]: g["name"] for g in groups}

    # Build response grouped by group with provider breakdown
    by_group = {}
    for r in results:
        mid = r["_id"]["member_id"]
        pnpi = r["_id"]["provider_npi"]
        mem = member_map.get(mid, {})
        gid = mem.get("group_id", "unknown")
        if gid not in group_map:
            continue

        if gid not in by_group:
            by_group[gid] = {
                "group_id": gid,
                "group_name": group_map.get(gid, "Unknown"),
                "claim_count": 0, "total_billed": 0, "total_paid": 0,
                "member_resp": 0, "provider_payable": 0,
                "claim_ids": [], "members": [], "providers": {},
            }

        g = by_group[gid]
        g["claim_count"] += r["claim_count"]
        g["total_billed"] += r["total_billed"]
        g["total_paid"] += r["total_paid"]
        g["member_resp"] += r["member_resp"]
        g["provider_payable"] += r["total_paid"]
        g["claim_ids"].extend(r["claim_ids"])
        g["members"].append({
            "member_id": mid,
            "name": f"{mem.get('first_name', '')} {mem.get('last_name', '')}".strip(),
            "claim_count": r["claim_count"],
            "total_paid": round(r["total_paid"], 2),
        })

        # Provider consolidation
        if pnpi not in g["providers"]:
            g["providers"][pnpi] = {
                "provider_npi": pnpi,
                "provider_name": r.get("provider_name") or pnpi,
                "claim_count": 0, "total_payable": 0, "claim_ids": [],
            }
        g["providers"][pnpi]["claim_count"] += r["claim_count"]
        g["providers"][pnpi]["total_payable"] += r["total_paid"]
        g["providers"][pnpi]["claim_ids"].extend(r["claim_ids"])

    summary = []
    for gid, g in by_group.items():
        g["total_billed"] = round(g["total_billed"], 2)
        g["total_paid"] = round(g["total_paid"], 2)
        g["member_resp"] = round(g["member_resp"], 2)
        g["provider_payable"] = round(g["provider_payable"], 2)
        providers = list(g["providers"].values())
        for p in providers:
            p["total_payable"] = round(p["total_payable"], 2)
        g["providers"] = providers

        # Attach vendor fees for this group
        vp = await db.vendor_payables.find({"group_id": gid, "is_active": True}, {"_id": 0}).to_list(100)
        g["vendor_fees"] = vp
        g["vendor_fees_total"] = round(sum(v.get("amount", 0) for v in vp), 2)
        g["total_funding_required"] = round(g["provider_payable"] + g["vendor_fees_total"], 2)
        summary.append(g)

    return summary


# ═══════════════════════════════════════
# Generate Funding Request (with WF Pull)
# ═══════════════════════════════════════

@router.post("/generate-funding-request")
async def generate_funding_request(
    group_id: str = Query(...),
    user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """Generate a funding request and initiate Wells Fargo funding pull."""
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

    # Provider batching
    provider_map = {}
    for c in claims:
        npi = c.get("provider_npi", "UNKNOWN")
        if npi not in provider_map:
            provider_map[npi] = {"provider_npi": npi, "provider_name": c.get("provider_name", npi),
                                  "claim_count": 0, "amount": 0, "claim_ids": []}
        provider_map[npi]["claim_count"] += 1
        provider_map[npi]["amount"] += c.get("total_paid", 0)
        provider_map[npi]["claim_ids"].append(c["id"])
    provider_batches = [{**v, "amount": round(v["amount"], 2)} for v in provider_map.values()]

    # Vendor fees
    vendor_fees = await db.vendor_payables.find(
        {"group_id": group_id, "is_active": True}, {"_id": 0}
    ).to_list(100)
    vendor_total = round(sum(v.get("amount", 0) for v in vendor_fees), 2)

    claims_payable = round(sum(c.get("total_paid", 0) for c in claims), 2)
    total_funding = round(claims_payable + vendor_total, 2)

    doc = {
        "id": request_id,
        "group_id": group_id,
        "group_name": group.get("name", ""),
        "status": "pending_funding",
        "claim_count": len(claims),
        "total_billed": round(sum(c.get("total_billed", 0) for c in claims), 2),
        "total_payable": claims_payable,
        "vendor_fees_total": vendor_total,
        "total_funding_required": total_funding,
        "member_responsibility": round(sum(c.get("member_responsibility", 0) for c in claims), 2),
        "claim_ids": [c["id"] for c in claims],
        "provider_batches": provider_batches,
        "vendor_fees": [{k: v for k, v in vf.items() if k != "id"} for vf in vendor_fees],
        "period_from": min(c.get("adjudicated_at", c.get("created_at", "")) for c in claims)[:10],
        "period_to": max(c.get("adjudicated_at", c.get("created_at", "")) for c in claims)[:10],
        "created_by": user["id"],
        "created_at": now.isoformat(),
        "funded_at": None,
        "executed_at": None,
        "wf_funding_txn": None,
        "wf_disbursement_id": None,
    }
    await db.check_runs.insert_one(doc)

    # Mark claims as part of this check run
    await db.claims.update_many(
        {"id": {"$in": doc["claim_ids"]}},
        {"$set": {"check_run_id": request_id, "check_run_status": "pending_funding"}}
    )

    # Initiate WF funding pull
    wf_result = await initiate_funding_pull(
        run_id=request_id,
        group_id=group_id,
        group_name=group.get("name", ""),
        employer_account=group.get("employer_account", "EMPLOYER_ACCT_" + group_id[:8]),
        amount=total_funding,
        memo=f"FletchFlow Check Run {request_id[:8]} — {group.get('name', '')}",
    )

    await db.check_runs.update_one({"id": request_id}, {"$set": {
        "wf_funding_txn": wf_result.get("transaction_id"),
    }})

    doc.pop("_id", None)
    doc["wf_funding_txn"] = wf_result.get("transaction_id")
    doc["wf_result"] = wf_result
    return doc


# ═══════════════════════════════════════
# Confirm Funding (WF Webhook or Manual)
# ═══════════════════════════════════════

@router.post("/{run_id}/confirm-funding")
async def confirm_funding(run_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Confirm funding via webhook or manually. Simulates WF webhook in sim mode."""
    run = await db.check_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Check run not found")
    if run["status"] != "pending_funding":
        raise HTTPException(400, f"Check run is '{run['status']}', expected 'pending_funding'")

    now = datetime.now(timezone.utc).isoformat()

    # Simulate WF webhook completing the funding pull
    if run.get("wf_funding_txn"):
        await process_webhook({"transaction_id": run["wf_funding_txn"], "status": "completed"})
    else:
        await db.check_runs.update_one({"id": run_id}, {"$set": {"status": "funded", "funded_at": now}})
        await db.claims.update_many(
            {"check_run_id": run_id},
            {"$set": {"check_run_status": "funded"}}
        )

    return {"status": "funded", "run_id": run_id, "funded_at": now}


# ═══════════════════════════════════════
# Execute Check Run (WF Disbursement)
# ═══════════════════════════════════════

@router.post("/{run_id}/execute")
async def execute_check_run(run_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Execute: disburse to providers via WF, move claims to paid."""
    run = await db.check_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Check run not found")
    if run["status"] != "funded":
        raise HTTPException(400, f"Check run must be 'funded' to execute, currently '{run['status']}'")

    now = datetime.now(timezone.utc)
    batch_number = f"ACH-{now.strftime('%Y%m%d')}-{run_id[:8].upper()}"

    # Initiate WF disbursement to providers
    provider_batches = run.get("provider_batches", [])
    vendor_fees = run.get("vendor_fees", [])

    wf_disb = await initiate_disbursement(
        run_id=run_id,
        group_id=run["group_id"],
        provider_payments=provider_batches,
        vendor_fees=vendor_fees,
    )

    # Simulate immediate completion for now
    await simulate_all_complete(run_id)

    # Move all claims to 'paid' with WF transaction IDs
    wf_payments = {p["provider_npi"]: p["transaction_id"] for p in wf_disb.get("payments", []) if p.get("provider_npi")}

    claims = await db.claims.find({"check_run_id": run_id}, {"_id": 0}).to_list(100000)
    for c in claims:
        npi = c.get("provider_npi", "UNKNOWN")
        wf_txn = wf_payments.get(npi, "")
        await db.claims.update_one({"id": c["id"]}, {"$set": {
            "status": "paid",
            "check_run_status": "executed",
            "paid_at": now.isoformat(),
            "ach_batch": batch_number,
            "wf_transaction_id": wf_txn,
        }})

    await db.check_runs.update_one({"id": run_id}, {"$set": {
        "status": "executed",
        "executed_at": now.isoformat(),
        "ach_batch": batch_number,
        "wf_disbursement_id": wf_disb.get("disbursement_id"),
    }})

    # Generate ACH content
    ach_lines = [
        f"1  01          FLETCHFLOW             {now.strftime('%y%m%d%H%M')}{batch_number}",
        f"5220{run.get('group_name', '')[:16]:<16s}{run.get('group_id', '')[:10]:<10s}PPD CLMPAY  {now.strftime('%y%m%d')}{now.strftime('%y%m%d')}   1",
    ]
    for pb in provider_batches:
        ach_lines.append(
            f"6{pb.get('provider_npi', '000000000'):<17s}{int(pb.get('amount', 0) * 100):010d}{pb.get('provider_name', '')[:15]:<15s}CLAIMS"
        )
    for vf in vendor_fees:
        ach_lines.append(
            f"6{'VENDOR':<17s}{int(vf.get('amount', 0) * 100):010d}{vf.get('vendor_name', '')[:15]:<15s}{vf.get('fee_type', '')}"
        )
    ach_lines.append(f"8{len(provider_batches) + len(vendor_fees):06d}{int(run.get('total_funding_required', 0) * 100):012d}")
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
            "total_payable": run.get("total_payable"),
            "vendor_fees_total": run.get("vendor_fees_total", 0),
            "total_funding": run.get("total_funding_required"),
            "ach_batch": batch_number,
            "wf_disbursement_id": wf_disb.get("disbursement_id"),
        },
    })

    return {
        "status": "executed",
        "run_id": run_id,
        "ach_batch": batch_number,
        "claim_count": len(claims),
        "total_payable": run.get("total_payable"),
        "vendor_fees_total": run.get("vendor_fees_total", 0),
        "total_funding_required": run.get("total_funding_required"),
        "wf_disbursement": wf_disb,
        "ach_content": ach_content,
    }


# ═══════════════════════════════════════
# List & Detail
# ═══════════════════════════════════════

@router.get("")
async def list_check_runs(
    group_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    query = {}
    if group_id:
        query["group_id"] = group_id
    if status:
        query["status"] = status
    runs = await db.check_runs.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return runs


# ═══════════════════════════════════════
# Wells Fargo Webhook & Transactions
# ═══════════════════════════════════════

@router.post("/wf-webhook")
async def wf_webhook_handler(payload: WebhookPayload):
    """Receive Wells Fargo transaction confirmation webhook."""
    result = await process_webhook(payload.model_dump())
    return result


@router.get("/wf-transactions/{run_id}")
async def get_wf_transactions(run_id: str, user: dict = Depends(get_current_user)):
    return await get_transactions(run_id=run_id)


# ═══════════════════════════════════════
# Vendor Payables CRUD
# ═══════════════════════════════════════

@router.get("/vendor-payables")
async def list_vendor_payables(
    group_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    query = {}
    if group_id:
        query["group_id"] = group_id
    payables = await db.vendor_payables.find(query, {"_id": 0}).sort("vendor_name", 1).to_list(500)
    return payables


@router.post("/vendor-payables")
async def create_vendor_payable(
    data: VendorPayableCreate,
    user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    now = datetime.now(timezone.utc).isoformat()
    doc = data.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = now
    doc["created_by"] = user["id"]
    await db.vendor_payables.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/vendor-payables/{payable_id}")
async def update_vendor_payable(
    payable_id: str,
    data: VendorPayableCreate,
    user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    existing = await db.vendor_payables.find_one({"id": payable_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Vendor payable not found")
    update = data.model_dump()
    await db.vendor_payables.update_one({"id": payable_id}, {"$set": update})
    return {**existing, **update}


@router.delete("/vendor-payables/{payable_id}")
async def delete_vendor_payable(
    payable_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    await db.vendor_payables.delete_one({"id": payable_id})
    return {"status": "deleted"}


# ═══════════════════════════════════════
# Dynamic ID routes — MUST be last
# ═══════════════════════════════════════

@router.get("/{run_id}")
async def get_check_run(run_id: str, user: dict = Depends(get_current_user)):
    run = await db.check_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Check run not found")
    claims = await db.claims.find(
        {"check_run_id": run_id},
        {"_id": 0, "id": 1, "claim_number": 1, "member_id": 1, "provider_npi": 1,
         "provider_name": 1, "total_billed": 1, "total_paid": 1, "status": 1, "wf_transaction_id": 1}
    ).to_list(100000)
    run["claims"] = claims
    # WF transactions for this run
    wf_txns = await get_transactions(run_id=run_id)
    run["wf_transactions"] = wf_txns
    return run


# ═══════════════════════════════════════
# Funding Request PDF
# ═══════════════════════════════════════

@router.get("/{run_id}/pdf")
async def download_funding_request_pdf(run_id: str, token: Optional[str] = Query(None)):
    """Generate and download a Funding Request PDF. Accepts token as query param for browser downloads."""
    # Validate token from query param (for browser window.open)
    if token:
        import jwt as pyjwt
        from core.config import JWT_SECRET, JWT_ALGORITHM
        try:
            payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(401, "Invalid token")
        except Exception:
            raise HTTPException(401, "Invalid or expired token")
    else:
        raise HTTPException(401, "Token required")

    run = await db.check_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Check run not found")

    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table as RLTable, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=18, spaceAfter=6)
    subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.grey)
    h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, spaceBefore=16, spaceAfter=6)
    elements = []

    # Header
    elements.append(Paragraph("FletchFlow — Funding Request", title_style))
    elements.append(Paragraph(
        f"Group: <b>{run.get('group_name', '')}</b> | Period: {run.get('period_from', '')} to {run.get('period_to', '')} | "
        f"Run ID: {run_id[:8]}... | Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        subtitle_style,
    ))
    elements.append(Spacer(1, 16))

    # Summary
    elements.append(Paragraph("Financial Summary", h2_style))
    sum_data = [
        ["Description", "Amount"],
        ["Total Claims Payable", f"${run.get('total_payable', 0):,.2f}"],
        ["Vendor Fees", f"${run.get('vendor_fees_total', 0):,.2f}"],
        ["Total Billed", f"${run.get('total_billed', 0):,.2f}"],
        ["Member Responsibility", f"${run.get('member_responsibility', 0):,.2f}"],
        ["", ""],
        ["TOTAL FUNDING REQUIRED", f"${run.get('total_funding_required', run.get('total_payable', 0)):,.2f}"],
    ]
    t = RLTable(sum_data, colWidths=[4 * inch, 2 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A3636")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F7F7F4")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EDF2EE")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E2DF")),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    # Provider Breakdown
    batches = run.get("provider_batches", [])
    if batches:
        elements.append(Paragraph("Provider Payment Schedule", h2_style))
        prov_data = [["Provider NPI", "Provider Name", "Claims", "Amount"]]
        for pb in batches:
            prov_data.append([
                pb.get("provider_npi", ""),
                pb.get("provider_name", "")[:30],
                str(pb.get("claim_count", 0)),
                f"${pb.get('amount', 0):,.2f}",
            ])
        pt = RLTable(prov_data, colWidths=[1.5 * inch, 2.5 * inch, 1 * inch, 1.5 * inch])
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A6FA5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F4")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E2DF")),
            ("ALIGN", (2, 0), (3, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(pt)
        elements.append(Spacer(1, 12))

    # Vendor Fees
    vfees = run.get("vendor_fees", [])
    if vfees:
        elements.append(Paragraph("Vendor Fee Line Items", h2_style))
        vf_data = [["Vendor", "Fee Type", "Description", "Amount"]]
        for vf in vfees:
            vf_data.append([
                vf.get("vendor_name", ""),
                vf.get("fee_type", ""),
                vf.get("description", "")[:30],
                f"${vf.get('amount', 0):,.2f}",
            ])
        vt = RLTable(vf_data, colWidths=[1.5 * inch, 1.5 * inch, 2 * inch, 1.5 * inch])
        vt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5C2D91")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F5FF")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E2DF")),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(vt)
        elements.append(Spacer(1, 12))

    # Footer
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(
        f"Wells Fargo Transaction ID: {run.get('wf_funding_txn', 'N/A')} | "
        f"Status: {run.get('status', '').replace('_', ' ').title()}",
        subtitle_style,
    ))
    elements.append(Paragraph("This document is generated by FletchFlow Claims Adjudication System.", subtitle_style))

    doc.build(elements)
    buf.seek(0)

    filename = f"FundingRequest_{run.get('group_name', 'Group').replace(' ', '_')}_{run_id[:8]}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
