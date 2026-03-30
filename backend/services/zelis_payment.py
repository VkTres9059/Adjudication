"""
Zelis Payment Vendor Integration — Simulated.
Provides ERA 835 generation, provider payment submission (ACH, Virtual Card, Check),
payment status tracking, and reconciliation with the Zelis Payments Network.

This is a MOCKED integration ready for real Zelis API credentials.
Replace the simulation logic with actual Zelis API calls when credentials are available.
"""
import uuid
from datetime import datetime, timezone, timedelta
import random
from core.database import db


ZELIS_PAYMENT_METHODS = {
    "ach": {"label": "ACH Direct Deposit", "processing_days": 2, "fee_pct": 0.0},
    "virtual_card": {"label": "Zelis Virtual Card", "processing_days": 0, "fee_pct": 2.5},
    "check": {"label": "Paper Check", "processing_days": 5, "fee_pct": 0.0},
    "ach_plus": {"label": "Zelis ACH+", "processing_days": 1, "fee_pct": 0.0},
    "zapp": {"label": "ZAPP Digital Card", "processing_days": 0, "fee_pct": 1.8},
}


def _generate_trace_number():
    return f"ZTR{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"


def _generate_virtual_card():
    return {
        "card_number_last4": str(random.randint(1000, 9999)),
        "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%m/%y"),
        "token": f"ZVCT-{uuid.uuid4().hex[:16].upper()}",
        "max_amount": 0,  # Set per transaction
        "status": "active",
    }


async def submit_payment_to_zelis(payment_doc: dict) -> dict:
    """Submit a payment through the Zelis Payments Network (SIMULATED).
    
    In production, this would call:
    POST https://api.zelis.com/v1/payments/submit
    
    Returns Zelis transaction confirmation.
    """
    method = payment_doc.get("payment_method", "ach")
    amount = payment_doc.get("amount", 0)
    method_config = ZELIS_PAYMENT_METHODS.get(method, ZELIS_PAYMENT_METHODS["ach"])

    trace_number = _generate_trace_number()
    processing_fee = round(amount * method_config["fee_pct"] / 100, 2)
    net_amount = round(amount - processing_fee, 2)
    estimated_arrival = (
        datetime.now(timezone.utc) + timedelta(days=method_config["processing_days"])
    ).isoformat()

    zelis_result = {
        "zelis_transaction_id": f"ZEL-{uuid.uuid4().hex[:12].upper()}",
        "trace_number": trace_number,
        "status": "accepted",
        "payment_method": method,
        "method_label": method_config["label"],
        "submitted_amount": amount,
        "processing_fee": processing_fee,
        "net_amount": net_amount,
        "estimated_arrival": estimated_arrival,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "provider_npi": payment_doc.get("provider_npi", ""),
        "provider_name": payment_doc.get("provider_name", ""),
        "claim_number": payment_doc.get("claim_number", ""),
    }

    # Virtual card specifics
    if method in ("virtual_card", "zapp"):
        card = _generate_virtual_card()
        card["max_amount"] = amount
        zelis_result["virtual_card"] = card
        zelis_result["status"] = "card_issued"

    # Store Zelis transaction
    zelis_result["id"] = str(uuid.uuid4())
    zelis_result["payment_id"] = payment_doc.get("id", "")
    await db.zelis_transactions.insert_one({**zelis_result})
    zelis_result.pop("_id", None)

    return zelis_result


async def check_zelis_payment_status(zelis_transaction_id: str) -> dict:
    """Check payment status through Zelis Payment Status API (SIMULATED).
    
    In production: GET https://api.zelis.com/v1/payments/{transaction_id}/status
    """
    tx = await db.zelis_transactions.find_one(
        {"zelis_transaction_id": zelis_transaction_id}, {"_id": 0}
    )
    if not tx:
        return {"error": "Transaction not found", "zelis_transaction_id": zelis_transaction_id}

    # Simulate status progression based on time
    submitted_at = tx.get("submitted_at", "")
    if submitted_at:
        submitted_dt = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - submitted_dt).total_seconds()
        if elapsed > 86400 * 3:
            status = "cleared"
        elif elapsed > 86400:
            status = "in_transit"
        elif elapsed > 3600:
            status = "processing"
        else:
            status = tx.get("status", "accepted")
    else:
        status = tx.get("status", "accepted")

    return {
        "zelis_transaction_id": zelis_transaction_id,
        "status": status,
        "trace_number": tx.get("trace_number", ""),
        "payment_method": tx.get("payment_method", ""),
        "submitted_amount": tx.get("submitted_amount", 0),
        "net_amount": tx.get("net_amount", 0),
        "estimated_arrival": tx.get("estimated_arrival", ""),
        "submitted_at": tx.get("submitted_at", ""),
        "last_checked": datetime.now(timezone.utc).isoformat(),
    }


async def generate_era_835(payment_ids: list) -> dict:
    """Generate ERA 835 (Electronic Remittance Advice) for a set of payments (SIMULATED).
    
    In production, Zelis delivers 835 ERA files via clearinghouse (SFTP).
    This simulates the ERA content structure.
    """
    payments = []
    for pid in payment_ids:
        pay = await db.payments.find_one({"id": pid}, {"_id": 0})
        if pay:
            claim = await db.claims.find_one({"id": pay.get("claim_id")}, {"_id": 0})
            payments.append({"payment": pay, "claim": claim})

    if not payments:
        return {"error": "No valid payments found"}

    now = datetime.now(timezone.utc)
    era_doc = {
        "id": str(uuid.uuid4()),
        "era_number": f"ERA{now.strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}",
        "generation_date": now.isoformat(),
        "transaction_count": len(payments),
        "total_payment_amount": sum(p["payment"].get("amount", 0) for p in payments),
        "payer_id": "FLETCHFLOW-TPA",
        "payer_name": "FletchFlow Claims Adjudication",
        "format": "ANSI X12 835",
        "delivery_method": "zelis_clearinghouse",
        "status": "generated",
        "transactions": [],
    }

    for entry in payments:
        pay = entry["payment"]
        claim = entry.get("claim") or {}
        era_doc["transactions"].append({
            "claim_number": pay.get("claim_number", ""),
            "patient_member_id": pay.get("member_id", ""),
            "provider_npi": pay.get("provider_npi", ""),
            "provider_name": pay.get("provider_name", ""),
            "service_date": claim.get("service_date_from", ""),
            "billed_amount": claim.get("total_billed", 0),
            "allowed_amount": claim.get("total_allowed", 0),
            "paid_amount": pay.get("amount", 0),
            "patient_responsibility": claim.get("member_responsibility", 0),
            "adjustment_reason_codes": _get_adjustment_codes(claim),
            "payment_method": pay.get("payment_method", "ach"),
        })

    await db.era_documents.insert_one({**era_doc})
    era_doc.pop("_id", None)
    return era_doc


def _get_adjustment_codes(claim: dict) -> list:
    """Generate CAS (Claim Adjustment Segment) reason codes from claim data."""
    codes = []
    if claim.get("member_responsibility", 0) > 0:
        deductible = 0
        coinsurance = 0
        for sl in claim.get("service_lines", []):
            deductible += sl.get("deductible_applied", 0)
            coinsurance += sl.get("coinsurance_amount", 0)
        if deductible > 0:
            codes.append({"group": "PR", "code": "1", "amount": deductible, "desc": "Deductible"})
        if coinsurance > 0:
            codes.append({"group": "PR", "code": "2", "amount": coinsurance, "desc": "Coinsurance"})
        copay = claim.get("member_responsibility", 0) - deductible - coinsurance
        if copay > 0:
            codes.append({"group": "PR", "code": "3", "amount": round(copay, 2), "desc": "Copay"})
    billed = claim.get("total_billed", 0)
    allowed = claim.get("total_allowed", 0)
    if billed > allowed and allowed > 0:
        codes.append({
            "group": "CO", "code": "45",
            "amount": round(billed - allowed, 2),
            "desc": "Charges exceed fee schedule/maximum allowable",
        })
    return codes


async def get_zelis_summary() -> dict:
    """Get Zelis payment processing summary."""
    pipe = [
        {"$group": {
            "_id": {"method": "$payment_method", "status": "$status"},
            "count": {"$sum": 1},
            "total": {"$sum": "$submitted_amount"},
            "fees": {"$sum": "$processing_fee"},
        }}
    ]
    agg = await db.zelis_transactions.aggregate(pipe).to_list(100)

    by_method = {}
    by_status = {}
    total_fees = 0

    for a in agg:
        m = a["_id"]["method"]
        s = a["_id"]["status"]
        if m not in by_method:
            by_method[m] = {"count": 0, "total": 0, "label": ZELIS_PAYMENT_METHODS.get(m, {}).get("label", m)}
        by_method[m]["count"] += a["count"]
        by_method[m]["total"] = round(by_method[m]["total"] + a["total"], 2)
        if s not in by_status:
            by_status[s] = {"count": 0, "total": 0}
        by_status[s]["count"] += a["count"]
        by_status[s]["total"] = round(by_status[s]["total"] + a["total"], 2)
        total_fees += a.get("fees", 0)

    return {
        "by_method": by_method,
        "by_status": by_status,
        "total_transactions": sum(b["count"] for b in by_status.values()),
        "total_amount": round(sum(b["total"] for b in by_status.values()), 2),
        "total_processing_fees": round(total_fees, 2),
        "supported_methods": {k: v["label"] for k, v in ZELIS_PAYMENT_METHODS.items()},
    }
