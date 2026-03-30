"""Wells Fargo API Integration Service (SIMULATED).

This module provides the exact contract for the Wells Fargo Commercial
Electronic Office (CEO) Transfer & Payment APIs. Currently operating in
simulation mode — swap the _simulate_* methods for real HTTP calls when
production credentials are configured.

Environment variables (for production):
  WF_API_BASE_URL, WF_CLIENT_ID, WF_CLIENT_SECRET, WF_ACCOUNT_ID
"""

import os
import uuid
import random
import string
from datetime import datetime, timezone
from typing import Optional

from core.database import db
from core.config import logger

# In production these would come from .env
WF_API_BASE = os.environ.get("WF_API_BASE_URL", "https://api-sandbox.wellsfargo.com/v1")
WF_ACCOUNT_ID = os.environ.get("WF_ACCOUNT_ID", "SIMULATED_TRUST_ACCT")
SIMULATION_MODE = os.environ.get("WF_SIMULATION_MODE", "true").lower() == "true"


def _sim_txn_id() -> str:
    """Generate a realistic-looking WF transaction reference."""
    prefix = random.choice(["WFT", "WFP", "ACH"])
    seq = "".join(random.choices(string.digits, k=12))
    return f"{prefix}-{seq}"


# ═══════════════════════════════════════
# Funding Pull — Employer → FletchFlow Trust
# ═══════════════════════════════════════

async def initiate_funding_pull(
    run_id: str,
    group_id: str,
    group_name: str,
    employer_account: str,
    amount: float,
    memo: str = "",
) -> dict:
    """
    Initiate an ACH debit / wire pull from the employer's bank account
    into the FletchFlow trust account.

    Returns: {success, transaction_id, status, message}
    """
    now = datetime.now(timezone.utc).isoformat()
    txn_id = _sim_txn_id()

    if SIMULATION_MODE:
        result = {
            "success": True,
            "transaction_id": txn_id,
            "status": "processing",
            "message": f"[SIMULATED] Funding pull of ${amount:,.2f} initiated from employer account",
            "simulated": True,
        }
    else:
        # Production: POST {WF_API_BASE}/transfers
        # body = { "sourceAccount": employer_account, "destinationAccount": WF_ACCOUNT_ID,
        #          "amount": amount, "currency": "USD", "memo": memo }
        # response = httpx.post(url, json=body, headers=auth_headers)
        result = {
            "success": True,
            "transaction_id": txn_id,
            "status": "processing",
            "message": f"Funding pull of ${amount:,.2f} submitted to Wells Fargo",
            "simulated": False,
        }

    # Log the transaction
    await db.wf_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "transaction_id": txn_id,
        "type": "funding_pull",
        "run_id": run_id,
        "group_id": group_id,
        "group_name": group_name,
        "amount": amount,
        "source_account": employer_account,
        "destination_account": WF_ACCOUNT_ID,
        "status": "processing",
        "simulated": SIMULATION_MODE,
        "created_at": now,
        "completed_at": None,
    })

    logger.info(f"WF Funding Pull: {txn_id} | ${amount:,.2f} | run={run_id}")
    return result


# ═══════════════════════════════════════
# Disbursement Push — FletchFlow Trust → Providers
# ═══════════════════════════════════════

async def initiate_disbursement(
    run_id: str,
    group_id: str,
    provider_payments: list,
    vendor_fees: list = None,
) -> dict:
    """
    Push ACH/Wire payments to providers and vendor fee recipients.

    provider_payments: [{provider_npi, provider_name, amount, claim_ids}]
    vendor_fees: [{vendor_name, fee_type, amount}]

    Returns: {success, disbursement_id, payment_count, total_disbursed, payments}
    """
    now = datetime.now(timezone.utc).isoformat()
    disbursement_id = _sim_txn_id()
    payments = []
    total = 0

    # Provider claim payments
    for p in provider_payments:
        pay_txn = _sim_txn_id()
        payments.append({
            "type": "claim_payment",
            "transaction_id": pay_txn,
            "recipient": p.get("provider_name", p.get("provider_npi", "Unknown")),
            "provider_npi": p.get("provider_npi", ""),
            "amount": p["amount"],
            "claim_count": len(p.get("claim_ids", [])),
            "method": "ACH",
            "status": "processing",
        })
        total += p["amount"]

    # Vendor fee payments
    for vf in (vendor_fees or []):
        pay_txn = _sim_txn_id()
        payments.append({
            "type": "vendor_fee",
            "transaction_id": pay_txn,
            "recipient": vf.get("vendor_name", "Unknown"),
            "fee_type": vf.get("fee_type", ""),
            "amount": vf["amount"],
            "method": "ACH",
            "status": "processing",
        })
        total += vf["amount"]

    result = {
        "success": True,
        "disbursement_id": disbursement_id,
        "payment_count": len(payments),
        "total_disbursed": round(total, 2),
        "payments": payments,
        "simulated": SIMULATION_MODE,
        "message": f"[SIMULATED] {len(payments)} payments totaling ${total:,.2f} submitted" if SIMULATION_MODE else f"{len(payments)} payments submitted to Wells Fargo",
    }

    # Log each payment
    for pay in payments:
        await db.wf_transactions.insert_one({
            "id": str(uuid.uuid4()),
            "transaction_id": pay["transaction_id"],
            "disbursement_id": disbursement_id,
            "type": pay["type"],
            "run_id": run_id,
            "group_id": group_id,
            "recipient": pay["recipient"],
            "provider_npi": pay.get("provider_npi", ""),
            "amount": pay["amount"],
            "method": pay["method"],
            "status": "processing",
            "simulated": SIMULATION_MODE,
            "created_at": now,
            "completed_at": None,
        })

    logger.info(f"WF Disbursement: {disbursement_id} | {len(payments)} payments | ${total:,.2f}")
    return result


# ═══════════════════════════════════════
# Webhook — Confirm Transfer Completion
# ═══════════════════════════════════════

async def process_webhook(payload: dict) -> dict:
    """
    Process a Wells Fargo webhook callback confirming a transfer completed.
    In simulation mode, this is called manually or via the 'simulate confirm' button.

    payload: {transaction_id, status ("completed"|"failed"), timestamp}
    """
    txn_id = payload.get("transaction_id", "")
    new_status = payload.get("status", "completed")
    now = datetime.now(timezone.utc).isoformat()

    txn = await db.wf_transactions.find_one({"transaction_id": txn_id}, {"_id": 0})
    if not txn:
        return {"success": False, "message": f"Transaction {txn_id} not found"}

    await db.wf_transactions.update_one(
        {"transaction_id": txn_id},
        {"$set": {"status": new_status, "completed_at": now}}
    )

    # If this was a funding pull that completed, auto-confirm the check run
    if txn["type"] == "funding_pull" and new_status == "completed":
        run = await db.check_runs.find_one({"id": txn["run_id"]}, {"_id": 0})
        if run and run.get("status") == "pending_funding":
            await db.check_runs.update_one(
                {"id": txn["run_id"]},
                {"$set": {"status": "funded", "funded_at": now, "wf_funding_txn": txn_id}}
            )
            await db.claims.update_many(
                {"check_run_id": txn["run_id"]},
                {"$set": {"check_run_status": "funded"}}
            )
            logger.info(f"Auto-confirmed check run {txn['run_id']} via WF webhook")

    return {"success": True, "transaction_id": txn_id, "status": new_status}


async def simulate_all_complete(run_id: str) -> dict:
    """Simulate all WF transactions for a run completing successfully."""
    txns = await db.wf_transactions.find({"run_id": run_id, "status": "processing"}, {"_id": 0}).to_list(1000)
    now = datetime.now(timezone.utc).isoformat()
    for t in txns:
        await db.wf_transactions.update_one(
            {"transaction_id": t["transaction_id"]},
            {"$set": {"status": "completed", "completed_at": now}}
        )
    return {"success": True, "completed_count": len(txns)}


async def get_transactions(run_id: str = None, limit: int = 50) -> list:
    """Get WF transaction history."""
    query = {}
    if run_id:
        query["run_id"] = run_id
    return await db.wf_transactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
