"""
Payment & Check Run System — ACH, Virtual Card, Check printing.
Matches payments to adjudicated claims, prevents duplicate payments,
handles reversals and adjustments.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentCreate(BaseModel):
    claim_id: str
    payment_method: str = "ach"  # ach, virtual_card, check
    payee_name: str = ""
    payee_npi: str = ""
    notes: str = ""


class PaymentBatch(BaseModel):
    group_id: Optional[str] = None
    funding_source: str = "aso"  # aso, level_funded
    payment_method: str = "ach"
    description: str = ""


class ReversalRequest(BaseModel):
    payment_id: str
    reason: str
    notes: str = ""


class AdjustmentRequest(BaseModel):
    claim_id: str
    adjustment_type: str  # increase, decrease, void
    amount: float
    reason: str
    notes: str = ""


@router.post("")
async def create_payment(data: PaymentCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a payment for an adjudicated claim."""
    claim = await db.claims.find_one({"id": data.claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(404, "Claim not found")
    if claim["status"] not in ("approved", "paid"):
        raise HTTPException(400, f"Claim status '{claim['status']}' is not payable")
    if claim.get("total_paid", 0) <= 0:
        raise HTTPException(400, "Claim has no payable amount")

    # Duplicate payment check
    existing = await db.payments.find_one({
        "claim_id": data.claim_id, "status": {"$in": ["pending", "processed", "cleared"]}
    })
    if existing:
        raise HTTPException(400, f"Duplicate payment — existing payment {existing['id']} for this claim")

    now = datetime.now(timezone.utc).isoformat()
    payment_id = str(uuid.uuid4())
    payment = {
        "id": payment_id,
        "claim_id": data.claim_id,
        "claim_number": claim.get("claim_number", ""),
        "member_id": claim.get("member_id", ""),
        "provider_npi": data.payee_npi or claim.get("provider_npi", ""),
        "provider_name": data.payee_name or claim.get("provider_name", ""),
        "amount": round(claim.get("total_paid", 0), 2),
        "payment_method": data.payment_method,
        "status": "pending",
        "batch_id": None,
        "check_number": None,
        "ach_trace": None,
        "virtual_card_token": None,
        "notes": data.notes,
        "created_by": user["id"],
        "created_at": now,
        "processed_at": None,
        "cleared_at": None,
    }
    await db.payments.insert_one(payment)
    await db.claims.update_one({"id": data.claim_id}, {"$set": {"status": "paid", "payment_id": payment_id}})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "action": "payment_created",
        "entity_type": "payment", "entity_id": payment_id,
        "user_id": user["id"], "timestamp": now,
        "details": {"claim_id": data.claim_id, "amount": payment["amount"], "method": data.payment_method}
    })

    payment.pop("_id", None)
    return payment


@router.get("")
async def list_payments(
    status: Optional[str] = None,
    payment_method: Optional[str] = None,
    batch_id: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    user: dict = Depends(get_current_user),
):
    """List payments with filters."""
    query = {}
    if status:
        query["status"] = status
    if payment_method:
        query["payment_method"] = payment_method
    if batch_id:
        query["batch_id"] = batch_id
    payments = await db.payments.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return payments


@router.get("/summary")
async def payment_summary(user: dict = Depends(get_current_user)):
    """Get payment summary by method and status."""
    pipe = [
        {"$group": {
            "_id": {"method": "$payment_method", "status": "$status"},
            "count": {"$sum": 1},
            "total": {"$sum": "$amount"},
        }},
    ]
    agg = await db.payments.aggregate(pipe).to_list(100)

    by_method = {}
    by_status = {}
    for a in agg:
        m = a["_id"]["method"]
        s = a["_id"]["status"]
        if m not in by_method:
            by_method[m] = {"count": 0, "total": 0}
        by_method[m]["count"] += a["count"]
        by_method[m]["total"] = round(by_method[m]["total"] + a["total"], 2)
        if s not in by_status:
            by_status[s] = {"count": 0, "total": 0}
        by_status[s]["count"] += a["count"]
        by_status[s]["total"] = round(by_status[s]["total"] + a["total"], 2)

    total_payments = sum(b["count"] for b in by_status.values())
    total_amount = round(sum(b["total"] for b in by_status.values()), 2)

    return {
        "by_method": by_method,
        "by_status": by_status,
        "total_payments": total_payments,
        "total_amount": total_amount,
    }


@router.post("/batch")
async def create_payment_batch(data: PaymentBatch, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a payment batch — gather all approved unpaid claims by group/funding."""
    query = {"status": "approved", "payment_id": {"$exists": False}}
    if data.group_id:
        members = await db.members.find({"group_id": data.group_id}, {"member_id": 1, "_id": 0}).to_list(100000)
        mids = [m["member_id"] for m in members]
        query["member_id"] = {"$in": mids}

    claims = await db.claims.find(query, {"_id": 0}).to_list(5000)
    if not claims:
        raise HTTPException(400, "No approved claims awaiting payment")

    now = datetime.now(timezone.utc).isoformat()
    batch_id = str(uuid.uuid4())
    payments_created = []

    for claim in claims:
        if claim.get("total_paid", 0) <= 0:
            continue

        # Duplicate check
        existing = await db.payments.find_one({"claim_id": claim["id"], "status": {"$nin": ["reversed", "voided"]}})
        if existing:
            continue

        payment_id = str(uuid.uuid4())
        payment = {
            "id": payment_id,
            "claim_id": claim["id"],
            "claim_number": claim.get("claim_number", ""),
            "member_id": claim.get("member_id", ""),
            "provider_npi": claim.get("provider_npi", ""),
            "provider_name": claim.get("provider_name", ""),
            "amount": round(claim.get("total_paid", 0), 2),
            "payment_method": data.payment_method,
            "status": "pending",
            "batch_id": batch_id,
            "notes": data.description,
            "created_by": user["id"],
            "created_at": now,
        }
        await db.payments.insert_one(payment)
        await db.claims.update_one({"id": claim["id"]}, {"$set": {"status": "paid", "payment_id": payment_id}})
        payments_created.append(payment_id)

    # Calculate total amount from created payments
    total_amount = 0.0
    for pid in payments_created:
        payment_doc = await db.payments.find_one({"id": pid}, {"amount": 1, "_id": 0})
        if payment_doc:
            total_amount += payment_doc.get("amount", 0)

    # Create batch record
    batch = {
        "id": batch_id,
        "type": "payment_batch",
        "group_id": data.group_id,
        "funding_source": data.funding_source,
        "payment_method": data.payment_method,
        "payment_count": len(payments_created),
        "total_amount": round(total_amount, 2),
        "status": "pending",
        "created_by": user["id"],
        "created_at": now,
    }
    await db.payment_batches.insert_one(batch)

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "action": "payment_batch_created",
        "entity_type": "payment_batch", "entity_id": batch_id,
        "user_id": user["id"], "timestamp": now,
        "details": {"count": len(payments_created), "method": data.payment_method}
    })

    batch.pop("_id", None)
    return batch


@router.get("/batches")
async def list_batches(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    user: dict = Depends(get_current_user),
):
    """List payment batches."""
    query = {"type": "payment_batch"}
    if status:
        query["status"] = status
    batches = await db.payment_batches.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return batches


@router.post("/reverse")
async def reverse_payment(data: ReversalRequest, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Reverse a payment — creates an offsetting entry."""
    payment = await db.payments.find_one({"id": data.payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(404, "Payment not found")
    if payment["status"] in ("reversed", "voided"):
        raise HTTPException(400, "Payment already reversed/voided")

    now = datetime.now(timezone.utc).isoformat()
    reversal_id = str(uuid.uuid4())

    # Create reversal record
    reversal = {
        "id": reversal_id,
        "original_payment_id": data.payment_id,
        "claim_id": payment["claim_id"],
        "claim_number": payment.get("claim_number", ""),
        "member_id": payment.get("member_id", ""),
        "provider_npi": payment.get("provider_npi", ""),
        "provider_name": payment.get("provider_name", ""),
        "amount": -payment["amount"],
        "payment_method": payment["payment_method"],
        "status": "reversed",
        "reversal_reason": data.reason,
        "notes": data.notes,
        "created_by": user["id"],
        "created_at": now,
    }
    await db.payments.insert_one(reversal)

    # Update original payment
    await db.payments.update_one({"id": data.payment_id}, {"$set": {
        "status": "reversed", "reversed_at": now, "reversal_id": reversal_id
    }})

    # Revert claim status
    await db.claims.update_one({"id": payment["claim_id"]}, {
        "$set": {"status": "approved"},
        "$unset": {"payment_id": ""},
    })

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "action": "payment_reversed",
        "entity_type": "payment", "entity_id": data.payment_id,
        "user_id": user["id"], "timestamp": now,
        "details": {"reason": data.reason, "amount": payment["amount"]}
    })

    reversal.pop("_id", None)
    return reversal


@router.post("/adjust")
async def adjust_claim_payment(data: AdjustmentRequest, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a payment adjustment on a claim."""
    claim = await db.claims.find_one({"id": data.claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(404, "Claim not found")

    now = datetime.now(timezone.utc).isoformat()
    adj_id = str(uuid.uuid4())

    if data.adjustment_type == "void":
        effective_amount = -(claim.get("total_paid", 0))
    elif data.adjustment_type == "decrease":
        effective_amount = -abs(data.amount)
    else:
        effective_amount = abs(data.amount)

    new_total_paid = round(claim.get("total_paid", 0) + effective_amount, 2)
    if new_total_paid < 0:
        new_total_paid = 0

    adjustment = {
        "id": adj_id,
        "claim_id": data.claim_id,
        "claim_number": claim.get("claim_number", ""),
        "adjustment_type": data.adjustment_type,
        "original_amount": claim.get("total_paid", 0),
        "adjustment_amount": effective_amount,
        "new_amount": new_total_paid,
        "reason": data.reason,
        "notes": data.notes,
        "created_by": user["id"],
        "created_at": now,
    }
    await db.payment_adjustments.insert_one(adjustment)

    # Update claim
    update_fields = {"total_paid": new_total_paid}
    if data.adjustment_type == "void":
        update_fields["status"] = "voided"
    adj_notes = claim.get("adjudication_notes", []) + [
        f"ADJUSTMENT ({data.adjustment_type}): ${effective_amount:+,.2f} by {user.get('name', user['email'])} — {data.reason}"
    ]
    update_fields["adjudication_notes"] = adj_notes
    await db.claims.update_one({"id": data.claim_id}, {"$set": update_fields})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "action": "payment_adjustment",
        "entity_type": "claim", "entity_id": data.claim_id,
        "user_id": user["id"], "timestamp": now,
        "details": {"type": data.adjustment_type, "amount": effective_amount, "reason": data.reason}
    })

    adjustment.pop("_id", None)
    return adjustment


@router.get("/adjustments")
async def list_adjustments(
    claim_id: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    user: dict = Depends(get_current_user),
):
    """List payment adjustments."""
    query = {}
    if claim_id:
        query["claim_id"] = claim_id
    adjs = await db.payment_adjustments.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return adjs


@router.get("/reconciliation")
async def payment_reconciliation(
    group_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Full reconciliation — claims paid vs stop-loss thresholds, funding balances."""
    query = {"status": {"$in": ["approved", "paid"]}}
    if group_id:
        members = await db.members.find({"group_id": group_id}, {"member_id": 1, "_id": 0}).to_list(100000)
        mids = [m["member_id"] for m in members]
        query["member_id"] = {"$in": mids}

    pipe = [
        {"$match": query},
        {"$group": {
            "_id": None,
            "total_billed": {"$sum": "$total_billed"},
            "total_allowed": {"$sum": "$total_allowed"},
            "total_paid": {"$sum": "$total_paid"},
            "claim_count": {"$sum": 1},
        }},
    ]
    claims_agg = await db.claims.aggregate(pipe).to_list(1)
    claims_data = claims_agg[0] if claims_agg else {"total_billed": 0, "total_allowed": 0, "total_paid": 0, "claim_count": 0}

    pay_pipe = [
        {"$match": {"status": {"$nin": ["reversed", "voided"]}}},
        {"$group": {
            "_id": None,
            "total_paid": {"$sum": "$amount"},
            "payment_count": {"$sum": 1},
        }},
    ]
    pay_agg = await db.payments.aggregate(pay_pipe).to_list(1)
    pay_data = pay_agg[0] if pay_agg else {"total_paid": 0, "payment_count": 0}

    discrepancy = round(claims_data["total_paid"] - pay_data["total_paid"], 2)

    # Stop-loss check
    stop_loss_status = []
    if group_id:
        group = await db.groups.find_one({"id": group_id}, {"_id": 0})
        if group:
            sl = group.get("stop_loss") or {}
            spec = sl.get("specific_deductible", 0)
            agg_att = sl.get("aggregate_attachment_point", 0)
            stop_loss_status.append({
                "group": group.get("name", ""),
                "specific_deductible": spec,
                "aggregate_attachment": agg_att,
                "total_claims_paid": round(claims_data["total_paid"], 2),
                "aggregate_utilization_pct": round(claims_data["total_paid"] / agg_att * 100, 1) if agg_att > 0 else 0,
            })

    return {
        "claims": {
            "total_billed": round(claims_data["total_billed"], 2),
            "total_allowed": round(claims_data["total_allowed"], 2),
            "total_paid": round(claims_data["total_paid"], 2),
            "claim_count": claims_data["claim_count"],
        },
        "payments": {
            "total_disbursed": round(pay_data["total_paid"], 2),
            "payment_count": pay_data["payment_count"],
        },
        "discrepancy": discrepancy,
        "stop_loss": stop_loss_status,
    }
