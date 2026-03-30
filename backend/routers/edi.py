from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from datetime import datetime, timezone
from typing import Optional
import uuid

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole, ClaimStatus, ClaimType
from models.schemas import MemberCreate, ServiceLine, ClaimCreate
from services.edi_parser import (
    parse_834_transactions, save_834_member,
    parse_837_transactions, save_837_claim,
    generate_835_content, parse_x12_date,
)
from services.claims import process_new_claim

router = APIRouter(prefix="/edi", tags=["edi"])


async def _log_transaction(tx_type, filename, result, user_id):
    """Log an EDI transaction for audit/history."""
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "type": tx_type,
        "filename": filename,
        "status": "success" if not result.get("errors") else "partial" if result.get("success") else "failed",
        "envelope": result.get("envelope"),
        "record_count": result.get("member_count") or result.get("claim_count") or result.get("claim_count_out", 0),
        "error_count": len(result.get("errors", [])),
        "errors": result.get("errors", [])[:20],
        "segment_count": result.get("segment_count", 0),
        "processed_by": user_id,
        "created_at": now,
    }
    await db.edi_transactions.insert_one(doc)
    return doc["id"]


# ── 834 Endpoints ──

@router.post("/validate-834")
async def validate_834(file: UploadFile = File(...), user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Validate/preview an 834 file without committing. Returns parsed members and any errors."""
    content = await file.read()
    content_str = content.decode("utf-8", errors="replace")

    is_x12 = content_str.strip().startswith("ISA")
    if not is_x12:
        return {
            "format": "pipe_delimited",
            "is_x12": False,
            "preview": _preview_pipe_834(content_str),
        }

    result = await parse_834_transactions(content_str)
    # Strip internal fields for preview
    preview_members = []
    for m in result.get("members", []):
        preview_members.append({
            "member_id": m.get("member_id"),
            "first_name": m.get("first_name"),
            "last_name": m.get("last_name"),
            "dob": m.get("dob"),
            "gender": m.get("gender"),
            "group_id": m.get("group_id"),
            "plan_id": m.get("plan_id"),
            "effective_date": m.get("effective_date"),
            "termination_date": m.get("termination_date"),
            "relationship": m.get("relationship"),
            "maintenance_type": m.get("maintenance_type"),
            "maintenance_reason": m.get("maintenance_reason"),
            "coverage_type": m.get("coverage_type"),
        })

    return {
        "format": "x12_834",
        "is_x12": True,
        "envelope": result.get("envelope"),
        "member_count": result.get("member_count", 0),
        "segment_count": result.get("segment_count", 0),
        "errors": result.get("errors", []),
        "members": preview_members,
    }


def _preview_pipe_834(content_str):
    """Preview pipe-delimited 834 content."""
    rows = [ln for ln in content_str.strip().split("\n") if ln and not ln.startswith("#")]
    members = []
    for line in rows[:50]:
        parts = line.split("|")
        if len(parts) >= 8:
            members.append({
                "member_id": parts[0], "first_name": parts[1], "last_name": parts[2],
                "dob": parts[3], "gender": parts[4], "group_id": parts[5],
                "plan_id": parts[6], "effective_date": parts[7],
            })
    return {"member_count": len(members), "members": members}


@router.post("/upload-834")
async def upload_edi_834(file: UploadFile = File(...), user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Process EDI 834 enrollment file (X12 or pipe-delimited)."""
    content = await file.read()
    content_str = content.decode("utf-8", errors="replace")
    is_x12 = content_str.strip().startswith("ISA")

    members_created = 0
    members_updated = 0
    members_terminated = 0
    errors = []

    if is_x12:
        result = await parse_834_transactions(content_str)
        if not result["success"]:
            return {"members_created": 0, "members_updated": 0, "errors": [result["error"]], "format": "x12"}

        for m in result["members"]:
            try:
                action = await save_834_member(m)
                if action == "member_added":
                    members_created += 1
                elif action in ("member_terminated", "member_retro_terminated"):
                    members_terminated += 1
                else:
                    members_updated += 1
            except Exception as e:
                errors.append(f"Member {m.get('member_id', '?')}: {str(e)}")

        tx_result = {
            "success": True,
            "envelope": result.get("envelope"),
            "member_count": result.get("member_count", 0),
            "segment_count": result.get("segment_count", 0),
            "errors": errors,
        }
        await _log_transaction("834", file.filename, tx_result, user["id"])

        return {
            "format": "x12",
            "envelope": result.get("envelope"),
            "members_created": members_created,
            "members_updated": members_updated,
            "members_terminated": members_terminated,
            "segment_count": result.get("segment_count", 0),
            "errors": errors,
        }
    else:
        # Pipe-delimited fallback
        for line in content_str.strip().split("\n"):
            if not line or line.startswith("#"):
                continue
            try:
                parts = line.split("|")
                if len(parts) >= 8:
                    member_data = MemberCreate(
                        member_id=parts[0], first_name=parts[1], last_name=parts[2],
                        dob=parts[3], gender=parts[4], group_id=parts[5],
                        plan_id=parts[6], effective_date=parts[7], relationship="subscriber"
                    )
                    existing = await db.members.find_one({"member_id": member_data.member_id})
                    if not existing:
                        now = datetime.now(timezone.utc).isoformat()
                        member_doc = {
                            "id": str(uuid.uuid4()),
                            **member_data.model_dump(),
                            "status": "active",
                            "created_at": now,
                            "updated_at": now,
                        }
                        await db.members.insert_one(member_doc)
                        members_created += 1
                    else:
                        members_updated += 1
            except Exception as e:
                errors.append(f"Line error: {str(e)}")

        await _log_transaction("834", file.filename, {"success": True, "member_count": members_created + members_updated, "errors": errors}, user["id"])
        return {"format": "pipe", "members_created": members_created, "members_updated": members_updated, "errors": errors}


# ── 837 Endpoints ──

@router.post("/validate-837")
async def validate_837(file: UploadFile = File(...), user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Validate/preview an 837 claims file without committing."""
    content = await file.read()
    content_str = content.decode("utf-8", errors="replace")

    is_x12 = content_str.strip().startswith("ISA")
    if not is_x12:
        return {
            "format": "pipe_delimited",
            "is_x12": False,
            "preview": _preview_pipe_837(content_str),
        }

    result = await parse_837_transactions(content_str)
    preview_claims = []
    for c in result.get("claims", []):
        preview_claims.append({
            "member_id": c.get("member_id"),
            "provider_name": c.get("provider_name"),
            "provider_npi": c.get("provider_npi"),
            "total_billed": c.get("total_billed"),
            "service_date_from": c.get("service_date_from"),
            "service_date_to": c.get("service_date_to"),
            "diagnosis_codes": c.get("diagnosis_codes", []),
            "service_line_count": len(c.get("service_lines", [])),
            "prior_auth_number": c.get("prior_auth_number"),
        })

    return {
        "format": "x12_837",
        "is_x12": True,
        "envelope": result.get("envelope"),
        "claim_count": result.get("claim_count", 0),
        "segment_count": result.get("segment_count", 0),
        "errors": result.get("errors", []),
        "claims": preview_claims,
    }


def _preview_pipe_837(content_str):
    rows = [ln for ln in content_str.strip().split("\n") if ln and not ln.startswith("#")]
    claims = []
    for line in rows[:50]:
        parts = line.split("|")
        if len(parts) >= 9:
            claims.append({
                "member_id": parts[0], "provider_npi": parts[1], "provider_name": parts[2],
                "claim_type": parts[3], "service_date_from": parts[4], "total_billed": parts[6],
            })
    return {"claim_count": len(claims), "claims": claims}


@router.post("/upload-837")
async def upload_edi_837(file: UploadFile = File(...), user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Process EDI 837 claims file (X12 or pipe-delimited)."""
    content = await file.read()
    content_str = content.decode("utf-8", errors="replace")
    is_x12 = content_str.strip().startswith("ISA")

    claims_created = 0
    errors = []

    if is_x12:
        result = await parse_837_transactions(content_str)
        if not result["success"]:
            return {"claims_created": 0, "errors": [result["error"]], "format": "x12"}

        for c in result["claims"]:
            try:
                svc_lines = c.get("service_lines", [])
                diag_codes = c.get("diagnosis_codes", [])
                await save_837_claim(c, svc_lines, diag_codes, user)
                claims_created += 1
            except Exception as e:
                errors.append(f"Claim {c.get('patient_control', '?')}: {str(e)}")

        tx_result = {
            "success": True,
            "envelope": result.get("envelope"),
            "claim_count": result.get("claim_count", 0),
            "segment_count": result.get("segment_count", 0),
            "errors": errors,
        }
        await _log_transaction("837", file.filename, tx_result, user["id"])

        return {
            "format": "x12",
            "envelope": result.get("envelope"),
            "claims_created": claims_created,
            "segment_count": result.get("segment_count", 0),
            "errors": errors,
        }
    else:
        for line in content_str.strip().split("\n"):
            if not line or line.startswith("#"):
                continue
            try:
                parts = line.split("|")
                if len(parts) >= 9:
                    service_lines = []
                    for i, svc in enumerate(parts[8].split(",")):
                        svc_parts = svc.split(":")
                        if len(svc_parts) >= 3:
                            service_lines.append({
                                "line_number": i + 1, "cpt_code": svc_parts[0],
                                "units": int(svc_parts[1]), "billed_amount": float(svc_parts[2]),
                                "service_date": parts[4], "modifier": None,
                                "diagnosis_codes": [], "revenue_code": None, "place_of_service": "11",
                            })

                    claim_dict = {
                        "member_id": parts[0], "provider_npi": parts[1], "provider_name": parts[2],
                        "facility_npi": None, "claim_type": parts[3],
                        "service_date_from": parts[4], "service_date_to": parts[5],
                        "total_billed": float(parts[6]), "diagnosis_codes": parts[7].split(","),
                        "prior_auth_number": None, "source": "edi_837", "external_claim_id": None,
                    }
                    await process_new_claim(claim_dict, service_lines, user)
                    claims_created += 1
            except Exception as e:
                errors.append(f"Line error: {str(e)}")

        await _log_transaction("837", file.filename, {"success": True, "claim_count": claims_created, "errors": errors}, user["id"])
        return {"format": "pipe", "claims_created": claims_created, "errors": errors}


# ── 835 Endpoints ──

@router.get("/generate-835")
async def generate_edi_835(
    date_from: str,
    date_to: str,
    format: str = Query(default="x12", description="Output format: x12 or pipe"),
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))
):
    """Generate EDI 835 payment/remittance file for approved claims in date range."""
    claims = await db.claims.find({
        "status": ClaimStatus.APPROVED.value,
        "adjudicated_at": {"$gte": date_from, "$lte": date_to}
    }, {"_id": 0}).to_list(10000)

    if format == "x12":
        content = await generate_835_content(claims)
    else:
        output = [
            "# EDI 835 Payment File",
            f"# Generated: {datetime.now(timezone.utc).isoformat()}",
            "# ClaimNumber|MemberID|ProviderNPI|TotalBilled|TotalAllowed|TotalPaid|MemberResp",
        ]
        for claim in claims:
            output.append(
                f"{claim['claim_number']}|{claim['member_id']}|{claim.get('provider_npi', '')}|"
                f"{claim['total_billed']}|{claim.get('total_allowed', 0)}|{claim['total_paid']}|{claim['member_responsibility']}"
            )
        content = "\n".join(output)

    await _log_transaction("835", f"835_{date_from}_{date_to}.{format}", {
        "success": True,
        "claim_count_out": len(claims),
        "errors": [],
    }, user["id"])

    return {"content": content, "claim_count": len(claims), "format": format}


# ── Transaction History ──

@router.get("/transactions")
async def list_transactions(
    limit: int = Query(50, ge=1, le=200),
    tx_type: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List EDI transaction history."""
    query = {}
    if tx_type:
        query["type"] = tx_type
    txns = await db.edi_transactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return txns
