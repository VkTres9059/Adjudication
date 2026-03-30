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


# ── Transmission Log (outbound feeds) ──

@router.get("/transmissions")
async def list_transmissions(
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user)
):
    """List outbound feed transmission history."""
    txns = await db.edi_transmissions.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return txns


async def _log_transmission(feed_type, filename, vendor_name, vendor_id, record_count, status, user_id, details=None):
    """Log an outbound feed transmission."""
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "feed_type": feed_type,
        "filename": filename,
        "vendor_name": vendor_name,
        "vendor_id": vendor_id,
        "record_count": record_count,
        "status": status,
        "details": details or {},
        "transmitted_by": user_id,
        "created_at": now,
    }
    await db.edi_transmissions.insert_one(doc)
    return doc["id"]


# ── Export 834 Enrollment Feed ──

@router.post("/export-834")
async def export_834_feed(
    vendor_id: Optional[str] = Query(None),
    format: str = Query("hipaa_5010", description="hipaa_5010 or csv"),
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Generate outbound 834 enrollment feed. Active members = Add (021), termed = Term (024)."""

    vendor = None
    vendor_name = "Manual Export"
    if vendor_id:
        vendor = await db.feed_vendors.find_one({"id": vendor_id}, {"_id": 0})
        if vendor:
            vendor_name = vendor.get("name", "Unknown")
            format = vendor.get("format", format)

    # Get all members with hour-bank eligible plans
    plans = await db.plans.find({"eligibility_threshold": {"$gt": 0}}, {"_id": 0}).to_list(1000)
    plan_map = {p["id"]: p for p in plans}
    plan_ids = list(plan_map.keys())

    # All members on these plans
    all_members = await db.members.find(
        {"plan_id": {"$in": plan_ids}} if plan_ids else {},
        {"_id": 0}
    ).to_list(100000)

    # Also include members not on hour-bank plans (standard enrollment)
    non_hb_members = await db.members.find(
        {"plan_id": {"$nin": plan_ids}} if plan_ids else {},
        {"_id": 0}
    ).to_list(100000)

    members = all_members + non_hb_members
    now = datetime.now(timezone.utc)
    isa_date = now.strftime("%y%m%d")
    isa_time = now.strftime("%H%M")
    gs_date = now.strftime("%Y%m%d")
    control = str(uuid.uuid4().int)[:9].zfill(9)

    records = []
    adds = 0
    terms = 0

    for m in members:
        plan = plan_map.get(m.get("plan_id"))
        threshold = plan.get("eligibility_threshold", 0) if plan else 0

        # Hour bank logic: check if member should be active
        maint_code = "021"  # default: add
        maint_label = "addition"
        status = m.get("status", "active")

        if threshold > 0:
            bank = await db.hour_bank.find_one({"member_id": m["member_id"]}, {"_id": 0})
            total = 0
            if bank:
                total = float(bank.get("current_balance", 0)) + float(bank.get("reserve_balance", 0))
            if total < threshold or status == "termed_insufficient_hours":
                maint_code = "024"
                maint_label = "cancellation"
                terms += 1
            else:
                adds += 1
        elif status in ("terminated", "termed_insufficient_hours"):
            maint_code = "024"
            maint_label = "cancellation"
            terms += 1
        else:
            adds += 1

        records.append({**m, "_maint_code": maint_code, "_maint_label": maint_label})

    filename = f"834_export_{gs_date}_{isa_time}.{'edi' if format == 'hipaa_5010' else 'csv'}"

    if format == "csv":
        lines = ["MemberID,FirstName,LastName,DOB,Gender,GroupID,PlanID,EffectiveDate,TermDate,Relationship,Status,MaintenanceCode,MaintenanceType"]
        for r in records:
            lines.append(
                f"{r.get('member_id','')},{r.get('first_name','')},{r.get('last_name','')},{r.get('dob','')},"
                f"{r.get('gender','')},{r.get('group_id','')},{r.get('plan_id','')},"
                f"{r.get('effective_date','')},{r.get('termination_date','') or ''},"
                f"{r.get('relationship','')},{r.get('status','')},{r['_maint_code']},{r['_maint_label']}"
            )
        content = "\n".join(lines)
    else:
        # HIPAA 5010 X12 834
        segs = []
        segs.append(f"ISA*00*          *00*          *ZZ*FLETCHFLOW     *ZZ*{vendor_name[:15]:<15s}*{isa_date}*{isa_time}*^*00501*{control}*0*P*:~")
        segs.append(f"GS*BE*FLETCHFLOW*{vendor_name[:15]}*{gs_date}*{isa_time}*1*X*005010X220A1~")
        segs.append("ST*834*0001~")
        segs.append(f"BGN*00*{control}*{gs_date}~")
        sc = 4

        for r in records:
            rel = "Y" if r.get("relationship") == "subscriber" else "N"
            segs.append(f"INS*{rel}*18*{r['_maint_code']}*20*A****EMP~")
            sc += 1
            segs.append(f"REF*0F*{r.get('member_id', '')}~")
            sc += 1
            if r.get("group_id"):
                segs.append(f"REF*1L*{r.get('group_id', '')}~")
                sc += 1
            segs.append(f"NM1*IL*1*{r.get('last_name','')}*{r.get('first_name','')}****MI*{r.get('member_id','')}~")
            sc += 1
            dob_raw = r.get("dob", "").replace("-", "")
            gender = r.get("gender", "U")
            segs.append(f"DMG*D8*{dob_raw}*{gender}~")
            sc += 1
            eff = r.get("effective_date", "").replace("-", "")
            if eff:
                segs.append(f"DTP*348*D8*{eff}~")
                sc += 1
            term = r.get("termination_date", "")
            if term and r["_maint_code"] == "024":
                segs.append(f"DTP*349*D8*{term.replace('-', '')}~")
                sc += 1
            segs.append(f"HD*{r['_maint_code']}**HLT**EMP~")
            sc += 1

        sc += 1
        segs.append(f"SE*{sc}*0001~")
        segs.append("GE*1*1~")
        segs.append(f"IEA*1*{control}~")
        content = "\n".join(segs)

    await _log_transmission("834_export", filename, vendor_name, vendor_id or "", len(records), "success", user["id"], {
        "adds": adds, "terms": terms, "format": format,
    })

    return {
        "content": content,
        "filename": filename,
        "format": format,
        "vendor_name": vendor_name,
        "total_members": len(records),
        "adds": adds,
        "terms": terms,
    }


# ── Authorization (278) Feed ──

@router.post("/export-auth-feed")
async def export_auth_feed(
    vendor_id: Optional[str] = Query(None),
    format: str = Query("hipaa_5010", description="hipaa_5010 or csv"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))
):
    """Generate authorization feed from approved hold releases. For PBM/TPA partners."""

    vendor = None
    vendor_name = "Manual Export"
    if vendor_id:
        vendor = await db.feed_vendors.find_one({"id": vendor_id}, {"_id": 0})
        if vendor:
            vendor_name = vendor.get("name", "Unknown")
            format = vendor.get("format", format)

    # Find auth records
    query = {"type": "auth_release"}
    if date_from:
        query["created_at"] = {"$gte": date_from}
    if date_to:
        query.setdefault("created_at", {})["$lte"] = date_to + "T23:59:59"

    auth_records = await db.auth_feed_records.find(query, {"_id": 0}).sort("created_at", -1).to_list(5000)

    now = datetime.now(timezone.utc)
    gs_date = now.strftime("%Y%m%d")
    isa_date = now.strftime("%y%m%d")
    isa_time = now.strftime("%H%M")
    control = str(uuid.uuid4().int)[:9].zfill(9)
    filename = f"278_auth_{gs_date}_{isa_time}.{'edi' if format == 'hipaa_5010' else 'csv'}"

    if format == "csv":
        lines = ["AuthID,MemberID,ClaimNumber,ProviderNPI,ProviderName,CPTCodes,UnitsApproved,ServiceDateFrom,ServiceDateTo,ApprovedBy,ApprovedAt"]
        for r in auth_records:
            cpts = ";".join(r.get("cpt_codes", []))
            lines.append(
                f"{r.get('auth_id','')},{r.get('member_id','')},{r.get('claim_number','')},"
                f"{r.get('provider_npi','')},{r.get('provider_name','')},{cpts},"
                f"{r.get('units_approved',0)},{r.get('service_date_from','')},"
                f"{r.get('service_date_to','')},{r.get('approved_by','')},{r.get('created_at','')}"
            )
        content = "\n".join(lines)
    else:
        segs = []
        segs.append(f"ISA*00*          *00*          *ZZ*FLETCHFLOW     *ZZ*{vendor_name[:15]:<15s}*{isa_date}*{isa_time}*^*00501*{control}*0*P*:~")
        segs.append(f"GS*HI*FLETCHFLOW*{vendor_name[:15]}*{gs_date}*{isa_time}*1*X*005010X217~")
        segs.append("ST*278*0001~")
        sc = 3

        for r in auth_records:
            segs.append(f"HL*{sc}**1~")
            sc += 1
            segs.append(f"TRN*1*{r.get('auth_id', '')}*FLETCHFLOW~")
            sc += 1
            segs.append(f"NM1*IL*1*{r.get('member_id','')}****MI*{r.get('member_id','')}~")
            sc += 1
            segs.append(f"NM1*82*1*{r.get('provider_name','')}****XX*{r.get('provider_npi','')}~")
            sc += 1
            svc_from = r.get("service_date_from", "").replace("-", "")
            svc_to = r.get("service_date_to", "").replace("-", "")
            if svc_from:
                segs.append(f"DTP*472*RD8*{svc_from}-{svc_to or svc_from}~")
                sc += 1
            for cpt in r.get("cpt_codes", []):
                segs.append(f"SV1*HC:{cpt}*0*UN*{r.get('units_approved', 1)}~")
                sc += 1
            segs.append(f"HCR*A1*{r.get('auth_id', '')}~")
            sc += 1

        sc += 1
        segs.append(f"SE*{sc}*0001~")
        segs.append("GE*1*1~")
        segs.append(f"IEA*1*{control}~")
        content = "\n".join(segs)

    await _log_transmission("278_auth", filename, vendor_name, vendor_id or "", len(auth_records), "success", user["id"], {
        "format": format, "auth_count": len(auth_records),
    })

    return {
        "content": content,
        "filename": filename,
        "format": format,
        "vendor_name": vendor_name,
        "auth_count": len(auth_records),
    }
