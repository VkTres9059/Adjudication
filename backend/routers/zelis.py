"""
Zelis Payment Vendor Router — Submit payments, check status, generate ERA 835.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole
from services.zelis_payment import (
    submit_payment_to_zelis, check_zelis_payment_status,
    generate_era_835, get_zelis_summary, ZELIS_PAYMENT_METHODS,
)

router = APIRouter(prefix="/zelis", tags=["zelis-payments"])


class ZelisPaymentRequest(BaseModel):
    claim_id: str
    payment_method: str = "ach"  # ach, virtual_card, check, ach_plus, zapp


class ZelisBatchRequest(BaseModel):
    payment_ids: List[str]
    payment_method: str = "ach"


class EraRequest(BaseModel):
    payment_ids: List[str]


@router.get("/methods")
async def list_payment_methods(user: dict = Depends(get_current_user)):
    """List available Zelis payment methods."""
    return {
        "methods": [
            {"id": k, **v} for k, v in ZELIS_PAYMENT_METHODS.items()
        ]
    }


@router.post("/submit")
async def submit_payment(
    req: ZelisPaymentRequest,
    user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """Submit a single claim payment through Zelis Payments Network."""
    claim = await db.claims.find_one({"id": req.claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(404, "Claim not found")
    if claim.get("total_paid", 0) <= 0:
        raise HTTPException(400, "Claim has no payable amount")

    # Check for existing Zelis transaction
    existing = await db.zelis_transactions.find_one({
        "claim_number": claim.get("claim_number"),
        "status": {"$nin": ["failed", "reversed"]},
    })
    if existing:
        raise HTTPException(400, f"Payment already submitted via Zelis: {existing.get('zelis_transaction_id')}")

    now = datetime.now(timezone.utc).isoformat()
    payment_id = str(uuid.uuid4())

    # Create internal payment record
    payment_doc = {
        "id": payment_id,
        "claim_id": req.claim_id,
        "claim_number": claim.get("claim_number", ""),
        "member_id": claim.get("member_id", ""),
        "provider_npi": claim.get("provider_npi", ""),
        "provider_name": claim.get("provider_name", ""),
        "amount": round(claim.get("total_paid", 0), 2),
        "payment_method": req.payment_method,
        "vendor": "zelis",
        "status": "submitting",
        "created_by": user["id"],
        "created_at": now,
    }
    await db.payments.insert_one(payment_doc)

    # Submit to Zelis
    zelis_result = await submit_payment_to_zelis(payment_doc)

    # Update payment with Zelis response
    await db.payments.update_one(
        {"id": payment_id},
        {"$set": {
            "status": "processed" if zelis_result.get("status") in ("accepted", "card_issued") else "failed",
            "zelis_transaction_id": zelis_result.get("zelis_transaction_id"),
            "zelis_trace": zelis_result.get("trace_number"),
            "processing_fee": zelis_result.get("processing_fee", 0),
            "processed_at": now,
        }}
    )

    # Update claim status
    await db.claims.update_one(
        {"id": req.claim_id},
        {"$set": {"status": "paid", "payment_id": payment_id}}
    )

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "action": "zelis_payment_submitted",
        "entity_type": "payment", "entity_id": payment_id,
        "user_id": user["id"], "timestamp": now,
        "details": {
            "claim_id": req.claim_id,
            "amount": payment_doc["amount"],
            "method": req.payment_method,
            "zelis_id": zelis_result.get("zelis_transaction_id"),
        }
    })

    payment_doc.pop("_id", None)
    return {
        "payment": {k: v for k, v in payment_doc.items() if k != "_id"},
        "zelis": zelis_result,
    }


@router.get("/status/{zelis_transaction_id}")
async def payment_status(
    zelis_transaction_id: str,
    user: dict = Depends(get_current_user),
):
    """Check payment status through Zelis."""
    result = await check_zelis_payment_status(zelis_transaction_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.post("/era-835")
async def generate_era(
    req: EraRequest,
    user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """Generate ERA 835 (Electronic Remittance Advice) for specified payments."""
    if not req.payment_ids:
        raise HTTPException(400, "No payment IDs provided")
    result = await generate_era_835(req.payment_ids)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/transactions")
async def list_zelis_transactions(
    status: Optional[str] = None,
    payment_method: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    user: dict = Depends(get_current_user),
):
    """List Zelis payment transactions."""
    query = {}
    if status:
        query["status"] = status
    if payment_method:
        query["payment_method"] = payment_method
    txs = await db.zelis_transactions.find(query, {"_id": 0}).sort("submitted_at", -1).to_list(limit)
    return txs


@router.get("/era-documents")
async def list_era_documents(
    limit: int = Query(default=20, le=100),
    user: dict = Depends(get_current_user),
):
    """List generated ERA 835 documents."""
    docs = await db.era_documents.find({}, {"_id": 0}).sort("generation_date", -1).to_list(limit)
    return docs


@router.get("/summary")
async def zelis_summary(user: dict = Depends(get_current_user)):
    """Get Zelis payment processing summary."""
    return await get_zelis_summary()


@router.post("/batch-submit")
async def batch_submit_payments(
    req: ZelisBatchRequest,
    user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """Submit multiple payments through Zelis in a batch."""
    results = {"submitted": 0, "failed": 0, "transactions": [], "errors": []}
    now = datetime.now(timezone.utc).isoformat()

    for pid in req.payment_ids:
        payment = await db.payments.find_one({"id": pid}, {"_id": 0})
        if not payment:
            results["errors"].append({"payment_id": pid, "error": "Payment not found"})
            results["failed"] += 1
            continue

        if payment.get("zelis_transaction_id"):
            results["errors"].append({"payment_id": pid, "error": "Already submitted to Zelis"})
            results["failed"] += 1
            continue

        payment_doc = {**payment, "payment_method": req.payment_method}
        zelis_result = await submit_payment_to_zelis(payment_doc)

        await db.payments.update_one(
            {"id": pid},
            {"$set": {
                "status": "processed",
                "vendor": "zelis",
                "zelis_transaction_id": zelis_result.get("zelis_transaction_id"),
                "zelis_trace": zelis_result.get("trace_number"),
                "processing_fee": zelis_result.get("processing_fee", 0),
                "processed_at": now,
            }}
        )
        results["submitted"] += 1
        results["transactions"].append(zelis_result)

    return results
