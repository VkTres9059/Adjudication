from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional, List
import uuid

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole
from models.schemas import NetworkContract
from services.adjudication import lookup_code_for_claim_type
from cpt_codes import calculate_medicare_rate

router = APIRouter(prefix="/network", tags=["network"])


@router.post("/contracts")
async def create_network_contract(contract: NetworkContract, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a network provider contract."""
    doc = {
        "id": str(uuid.uuid4()),
        **contract.model_dump(),
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.network_contracts.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/contracts")
async def list_network_contracts(network_name: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    if network_name:
        query["network_name"] = network_name
    contracts = await db.network_contracts.find(query, {"_id": 0}).to_list(1000)
    return contracts


@router.get("/reprice/{claim_id}")
async def reprice_claim(claim_id: str, user: dict = Depends(get_current_user)):
    """Compare Medicare rates with network contracted rates for a claim."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    contract = await db.network_contracts.find_one(
        {"provider_npi": claim.get("provider_npi"), "status": "active"},
        {"_id": 0}
    )

    repriced_lines = []
    total_medicare = 0
    total_network = 0

    for line in claim.get("service_lines", []):
        code = line.get("cpt_code", "")
        billed = line.get("billed_amount", 0)
        units = line.get("units", 1)

        medicare_rate = calculate_medicare_rate(code, "00000", use_facility=True)
        if not medicare_rate:
            code_data = lookup_code_for_claim_type(code, claim.get("claim_type", "medical"))
            medicare_rate = code_data.get("fee", billed * 0.8) if code_data else billed * 0.8

        medicare_allowed = medicare_rate * units

        if contract:
            network_rate = medicare_rate * contract.get("multiplier", 1.2) * units
        else:
            network_rate = medicare_allowed

        total_medicare += medicare_allowed
        total_network += network_rate

        repriced_lines.append({
            "cpt_code": code,
            "billed": billed,
            "medicare_rate": round(medicare_rate, 2),
            "medicare_allowed": round(medicare_allowed, 2),
            "network_rate": round(network_rate, 2),
            "savings_vs_billed": round(billed - network_rate, 2),
        })

    return {
        "claim_id": claim_id,
        "claim_number": claim.get("claim_number"),
        "provider_npi": claim.get("provider_npi"),
        "has_contract": contract is not None,
        "network_name": contract.get("network_name") if contract else None,
        "contract_multiplier": contract.get("multiplier") if contract else None,
        "total_billed": claim.get("total_billed", 0),
        "total_medicare": round(total_medicare, 2),
        "total_network": round(total_network, 2),
        "total_savings": round(claim.get("total_billed", 0) - total_network, 2),
        "lines": repriced_lines,
    }


@router.get("/summary")
async def network_summary(user: dict = Depends(get_current_user)):
    """Get network repricing summary across all claims."""
    contracts = await db.network_contracts.find({"status": "active"}, {"_id": 0}).to_list(1000)
    claims = await db.claims.find({"status": "approved"}, {"_id": 0, "total_billed": 1, "total_paid": 1, "total_allowed": 1}).to_list(10000)

    total_billed = sum(c.get("total_billed", 0) for c in claims)
    total_paid = sum(c.get("total_paid", 0) for c in claims)

    return {
        "active_contracts": len(contracts),
        "total_claims_processed": len(claims),
        "total_billed": round(total_billed, 2),
        "total_paid": round(total_paid, 2),
        "total_savings": round(total_billed - total_paid, 2),
        "savings_percentage": round((total_billed - total_paid) / total_billed * 100, 1) if total_billed > 0 else 0,
    }
