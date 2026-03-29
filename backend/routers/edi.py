from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from datetime import datetime, timezone
from typing import Optional
import uuid

from core.database import db
from core.auth import require_roles
from models.enums import UserRole, ClaimStatus, ClaimType
from models.schemas import MemberCreate, ServiceLine, ClaimCreate
from services.edi_parser import _parse_x12_date, save_834_member, save_837_claim
from services.claims import process_new_claim

router = APIRouter(prefix="/edi", tags=["edi"])


@router.post("/upload-834")
async def upload_edi_834(file: UploadFile = File(...), user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Process EDI 834 enrollment file."""
    content = await file.read()
    content_str = content.decode('utf-8')

    members_created = 0
    members_updated = 0
    errors = []

    is_x12 = content_str.strip().startswith('ISA')

    if is_x12:
        segment_terminator = '~'
        element_separator = '*'
        segments = [s.strip() for s in content_str.split(segment_terminator) if s.strip()]

        current_member = {}
        in_member_loop = False

        for seg in segments:
            elements = seg.split(element_separator)
            seg_id = elements[0]

            if seg_id == 'INS':
                if current_member.get("member_id"):
                    try:
                        await save_834_member(current_member)
                        members_created += 1
                    except Exception as e:
                        errors.append(f"Member {current_member.get('member_id', '?')}: {str(e)}")
                current_member = {"relationship": "subscriber" if len(elements) > 1 and elements[1] == 'Y' else "dependent"}
                in_member_loop = True
            elif seg_id == 'REF' and in_member_loop:
                if len(elements) > 2 and elements[1] == '0F':
                    current_member["member_id"] = elements[2]
                elif len(elements) > 2 and elements[1] == '1L':
                    current_member["group_id"] = elements[2]
            elif seg_id == 'NM1' and in_member_loop:
                if len(elements) > 3 and elements[1] == 'IL':
                    current_member["last_name"] = elements[3] if len(elements) > 3 else ""
                    current_member["first_name"] = elements[4] if len(elements) > 4 else ""
            elif seg_id == 'DMG' and in_member_loop:
                if len(elements) > 2:
                    current_member["dob"] = _parse_x12_date(elements[2]) if len(elements) > 2 else ""
                    current_member["gender"] = elements[3] if len(elements) > 3 else "U"
            elif seg_id == 'DTP' and in_member_loop:
                if len(elements) > 3:
                    if elements[1] == '348':
                        current_member["effective_date"] = _parse_x12_date(elements[3])
                    elif elements[1] == '349':
                        current_member["termination_date"] = _parse_x12_date(elements[3])
            elif seg_id == 'HD' and in_member_loop:
                if len(elements) > 3:
                    plan_code = elements[3] if len(elements) > 3 else ""
                    current_member["plan_id"] = plan_code

        if current_member.get("member_id"):
            try:
                await save_834_member(current_member)
                members_created += 1
            except Exception as e:
                errors.append(f"Member {current_member.get('member_id', '?')}: {str(e)}")
    else:
        for line in content_str.strip().split('\n'):
            if not line or line.startswith('#'):
                continue
            try:
                parts = line.split('|')
                if len(parts) >= 8:
                    member_data = MemberCreate(
                        member_id=parts[0], first_name=parts[1], last_name=parts[2],
                        dob=parts[3], gender=parts[4], group_id=parts[5],
                        plan_id=parts[6], effective_date=parts[7], relationship="subscriber"
                    )
                    existing = await db.members.find_one({"member_id": member_data.member_id})
                    if not existing:
                        member_doc = {
                            "id": str(uuid.uuid4()),
                            **member_data.model_dump(),
                            "status": "active",
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                        await db.members.insert_one(member_doc)
                        members_created += 1
                    else:
                        members_updated += 1
            except Exception as e:
                errors.append(f"Line error: {str(e)}")

    return {"members_created": members_created, "members_updated": members_updated, "errors": errors}


@router.post("/upload-837")
async def upload_edi_837(file: UploadFile = File(...), user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Process EDI 837 claims file."""
    content = await file.read()
    content_str = content.decode('utf-8')

    claims_created = 0
    errors = []

    is_x12 = content_str.strip().startswith('ISA')

    if is_x12:
        segment_terminator = '~'
        element_separator = '*'
        segments = [s.strip() for s in content_str.split(segment_terminator) if s.strip()]

        current_claim = {}
        current_service_lines = []
        current_diag_codes = []
        in_claim = False
        line_counter = 0

        for seg in segments:
            elements = seg.split(element_separator)
            seg_id = elements[0]

            if seg_id == 'CLM':
                if in_claim and current_claim.get("member_id"):
                    try:
                        await save_837_claim(current_claim, current_service_lines, current_diag_codes, user)
                        claims_created += 1
                    except Exception as e:
                        errors.append(f"Claim error: {str(e)}")

                current_claim = {}
                current_service_lines = []
                current_diag_codes = []
                line_counter = 0
                in_claim = True

                if len(elements) > 2:
                    current_claim["patient_control"] = elements[1]
                    current_claim["total_billed"] = float(elements[2]) if len(elements) > 2 else 0
                if len(elements) > 5:
                    pos = elements[5].split(':') if ':' in elements[5] else [elements[5]]
                    current_claim["place_of_service"] = pos[0]
            elif seg_id == 'NM1' and in_claim:
                if len(elements) > 3:
                    if elements[1] == 'IL':
                        current_claim["member_last_name"] = elements[3] if len(elements) > 3 else ""
                        current_claim["member_first_name"] = elements[4] if len(elements) > 4 else ""
                        if len(elements) > 9:
                            current_claim["member_id"] = elements[9]
                    elif elements[1] == '82':
                        current_claim["provider_name"] = f"{elements[4]} {elements[3]}" if len(elements) > 4 else elements[3]
                        if len(elements) > 9:
                            current_claim["provider_npi"] = elements[9]
            elif seg_id == 'HI' and in_claim:
                for i in range(1, len(elements)):
                    parts = elements[i].split(':')
                    if len(parts) >= 2:
                        current_diag_codes.append(parts[1])
            elif seg_id == 'SV1' and in_claim:
                line_counter += 1
                proc_parts = elements[1].split(':') if len(elements) > 1 else ["", ""]
                proc_code = proc_parts[1] if len(proc_parts) > 1 else proc_parts[0]
                modifier = proc_parts[2] if len(proc_parts) > 2 else ""

                svc_line = {
                    "line_number": line_counter,
                    "cpt_code": proc_code,
                    "modifier": modifier,
                    "billed_amount": float(elements[2]) if len(elements) > 2 else 0,
                    "units": int(float(elements[4])) if len(elements) > 4 else 1,
                    "service_date": current_claim.get("service_date_from", ""),
                    "place_of_service": elements[5] if len(elements) > 5 else "11",
                }
                current_service_lines.append(svc_line)
            elif seg_id == 'DTP' and in_claim:
                if len(elements) > 3:
                    if elements[1] == '472':
                        date_val = _parse_x12_date(elements[3].split('-')[0] if '-' in elements[3] else elements[3])
                        current_claim["service_date_from"] = date_val
                        current_claim["service_date_to"] = date_val

        if in_claim and current_claim.get("member_id"):
            try:
                await save_837_claim(current_claim, current_service_lines, current_diag_codes, user)
                claims_created += 1
            except Exception as e:
                errors.append(f"Claim error: {str(e)}")
    else:
        for line in content_str.strip().split('\n'):
            if not line or line.startswith('#'):
                continue
            try:
                parts = line.split('|')
                if len(parts) >= 9:
                    service_lines = []
                    for i, svc in enumerate(parts[8].split(',')):
                        svc_parts = svc.split(':')
                        if len(svc_parts) >= 3:
                            service_lines.append({
                                "line_number": i + 1,
                                "cpt_code": svc_parts[0],
                                "units": int(svc_parts[1]),
                                "billed_amount": float(svc_parts[2]),
                                "service_date": parts[4],
                                "modifier": None,
                                "diagnosis_codes": [],
                                "revenue_code": None,
                                "place_of_service": "11",
                            })

                    claim_dict = {
                        "member_id": parts[0],
                        "provider_npi": parts[1],
                        "provider_name": parts[2],
                        "facility_npi": None,
                        "claim_type": parts[3],
                        "service_date_from": parts[4],
                        "service_date_to": parts[5],
                        "total_billed": float(parts[6]),
                        "diagnosis_codes": parts[7].split(','),
                        "prior_auth_number": None,
                        "source": "edi_837",
                        "external_claim_id": None,
                    }
                    await process_new_claim(claim_dict, service_lines, user)
                    claims_created += 1
            except Exception as e:
                errors.append(f"Line error: {str(e)}")

    return {"claims_created": claims_created, "errors": errors}


@router.get("/generate-835")
async def generate_edi_835(
    date_from: str,
    date_to: str,
    format: str = Query(default="x12", description="Output format: x12 or pipe"),
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))
):
    """Generate EDI 835 payment/remittance file."""
    claims = await db.claims.find({
        "status": ClaimStatus.APPROVED.value,
        "adjudicated_at": {"$gte": date_from, "$lte": date_to}
    }, {"_id": 0}).to_list(10000)

    if format == "x12":
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%y%m%d")
        time_str = now.strftime("%H%M")
        isa_date = now.strftime("%y%m%d")
        gs_date = now.strftime("%Y%m%d")
        control_number = str(uuid.uuid4().int)[:9].zfill(9)

        lines = []
        lines.append(f"ISA*00*          *00*          *ZZ*FLETCHFLOW     *ZZ*RECEIVER       *{isa_date}*{time_str}*^*00501*{control_number}*0*P*:~")
        lines.append(f"GS*HP*FLETCHFLOW*RECEIVER*{gs_date}*{time_str}*1*X*005010X221A1~")
        lines.append(f"ST*835*0001~")
        lines.append(f"BPR*I*{sum(c.get('total_paid', 0) for c in claims):.2f}*C*ACH*CTX*01*999999999*DA*123456789*1234567890**01*999999999*DA*987654321*{gs_date}~")
        lines.append(f"TRN*1*{control_number}*1234567890~")
        lines.append(f"DTM*405*{gs_date}~")
        lines.append(f"N1*PR*FletchFlow Claims System~")
        lines.append(f"N1*PE*Provider Name*XX*1234567890~")

        for i, claim in enumerate(claims):
            clp_status = "1" if claim.get("status") == "approved" else "2"
            lines.append(f"CLP*{claim.get('claim_number', '')}*{clp_status}*{claim.get('total_billed', 0):.2f}*{claim.get('total_paid', 0):.2f}**MC*{claim.get('id', '')}~")
            lines.append(f"NM1*QC*1*{claim.get('member_id', '')}~")

            for sl in claim.get("service_lines", []):
                lines.append(f"SVC*HC:{sl.get('cpt_code', '')}*{sl.get('billed_amount', 0):.2f}*{sl.get('paid', 0):.2f}**{sl.get('units', 1)}~")
                lines.append(f"DTM*472*{claim.get('service_date_from', '').replace('-', '')}~")
                cas_adj = sl.get('billed_amount', 0) - sl.get('paid', 0)
                if cas_adj > 0:
                    lines.append(f"CAS*CO*45*{cas_adj:.2f}~")

        lines.append(f"SE*{len(lines) - 2}*0001~")
        lines.append(f"GE*1*1~")
        lines.append(f"IEA*1*{control_number}~")

        content = "\n".join(lines)
    else:
        output = ["# EDI 835 Payment File", f"# Generated: {datetime.now(timezone.utc).isoformat()}", "# ClaimNumber|MemberID|ProviderNPI|TotalBilled|TotalAllowed|TotalPaid|MemberResp"]
        for claim in claims:
            output.append(f"{claim['claim_number']}|{claim['member_id']}|{claim['provider_npi']}|{claim['total_billed']}|{claim['total_allowed']}|{claim['total_paid']}|{claim['member_responsibility']}")
        content = "\n".join(output)

    return {"content": content, "claim_count": len(claims), "format": format}
