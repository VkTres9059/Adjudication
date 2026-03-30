"""
Real X12 EDI Parser — 834 (Enrollment), 837 (Claims), 835 (Remittance)
Handles proper envelope parsing (ISA/GS/ST), hierarchical loops, sub-element separators,
maintenance codes, and structured error/validation reporting.
"""
from datetime import datetime, timezone
import uuid
import re
from core.database import db
from models.enums import ClaimType
from services.claims import process_new_claim


# ── X12 Envelope Utilities ──

def parse_x12_envelope(raw: str):
    """Parse ISA envelope to extract separators and segments."""
    raw = raw.strip()
    if not raw.startswith("ISA"):
        return None, "File does not begin with ISA segment"

    # ISA is fixed-length: 106 chars. Element sep is ISA[3], sub-element sep is ISA[104], segment term is ISA[105]
    element_sep = raw[3]
    # Find segment terminator from ISA (position 105)
    # ISA has exactly 16 elements; count characters
    isa_elements = raw.split(element_sep, 17)
    if len(isa_elements) < 17:
        return None, f"ISA segment malformed: expected 16 elements, got {len(isa_elements)-1}"

    # Sub-element separator is the last char of ISA16 before segment terminator
    isa16_raw = isa_elements[16]
    sub_sep = isa16_raw[0] if len(isa16_raw) >= 2 else ":"
    segment_term = isa16_raw[1] if len(isa16_raw) >= 2 else "~"

    # Split into segments
    segments = [s.strip() for s in raw.split(segment_term) if s.strip()]

    return {
        "element_sep": element_sep,
        "sub_element_sep": sub_sep,
        "segment_term": segment_term,
        "segments": segments,
    }, None


def parse_x12_date(date_str):
    """Parse X12 date CCYYMMDD or YYMMDD to ISO date."""
    if not date_str:
        return ""
    date_str = date_str.strip()
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    if len(date_str) == 6:
        yy = int(date_str[:2])
        century = "20" if yy < 50 else "19"
        return f"{century}{date_str[:2]}-{date_str[2:4]}-{date_str[4:6]}"
    return date_str


def parse_x12_time(time_str):
    """Parse X12 time HHMM to HH:MM."""
    if not time_str or len(time_str) < 4:
        return ""
    return f"{time_str[:2]}:{time_str[2:4]}"


MAINTENANCE_TYPE = {
    "001": "change", "021": "addition", "024": "cancellation",
    "025": "reinstatement", "026": "termination", "030": "audit_replace",
}

MAINTENANCE_REASON = {
    "01": "divorce", "02": "birth", "03": "adoption", "04": "marriage",
    "05": "employment_begin", "06": "death", "07": "employment_term",
    "08": "termination_benefits", "11": "disability", "14": "retirement",
    "20": "initial_enrollment", "28": "transfer", "31": "non_payment",
    "33": "open_enrollment", "41": "disability_end", "43": "rehire",
    "AI": "re_enrollment",
}

INS_RELATIONSHIP = {
    "Y": "subscriber", "N": "dependent",
}

COVERAGE_LEVEL = {
    "EMP": "employee_only", "ESP": "employee_spouse", "ECH": "employee_children",
    "FAM": "family", "IND": "individual",
}

HD_COVERAGE_TYPE = {
    "HLT": "health", "DEN": "dental", "VIS": "vision", "LIF": "life",
    "STD": "short_term_disability", "LTD": "long_term_disability",
}


# ── 834 Parser ──

async def parse_834_transactions(raw: str):
    """Parse X12 834 enrollment/eligibility file. Returns structured results."""
    envelope, err = parse_x12_envelope(raw)
    if err:
        return {"success": False, "error": err, "members": [], "envelope": None}

    sep = envelope["element_sep"]
    segments = envelope["segments"]

    # Extract envelope info
    isa_els = segments[0].split(sep) if segments else []
    env_info = {
        "sender_id": isa_els[6].strip() if len(isa_els) > 6 else "",
        "receiver_id": isa_els[8].strip() if len(isa_els) > 8 else "",
        "date": parse_x12_date(isa_els[9].strip()) if len(isa_els) > 9 else "",
        "control_number": isa_els[13].strip() if len(isa_els) > 13 else "",
        "version": isa_els[12].strip() if len(isa_els) > 12 else "",
    }

    members = []
    errors = []
    current = {}
    in_member = False
    seg_count = 0
    member_idx = 0

    for seg in segments:
        els = seg.split(sep)
        sid = els[0].upper()
        seg_count += 1

        if sid == "INS":
            # Save previous member
            if in_member and current.get("member_id"):
                members.append(current)
            member_idx += 1
            in_member = True
            rel_code = els[1] if len(els) > 1 else "Y"
            maint_type = els[3] if len(els) > 3 else "021"
            maint_reason = els[4] if len(els) > 4 else ""
            benefit_status = els[5] if len(els) > 5 else "A"
            coverage_level = els[9] if len(els) > 9 else ""

            current = {
                "member_id": "",
                "first_name": "",
                "last_name": "",
                "dob": "",
                "gender": "U",
                "group_id": "",
                "plan_id": "",
                "effective_date": "",
                "termination_date": None,
                "relationship": INS_RELATIONSHIP.get(rel_code, "dependent"),
                "maintenance_type": MAINTENANCE_TYPE.get(maint_type, maint_type),
                "maintenance_reason": MAINTENANCE_REASON.get(maint_reason, maint_reason),
                "benefit_status": "active" if benefit_status == "A" else "cobra" if benefit_status == "C" else benefit_status,
                "coverage_level": COVERAGE_LEVEL.get(coverage_level, coverage_level),
                "address": {},
                "coverage_type": "",
                "_segment_index": member_idx,
            }

        elif sid == "REF" and in_member:
            qual = els[1] if len(els) > 1 else ""
            val = els[2] if len(els) > 2 else ""
            if qual == "0F":
                current["member_id"] = val
            elif qual == "1L":
                current["group_id"] = val
            elif qual == "ZZ":
                current["subscriber_id"] = val
            elif qual == "17":
                current["ssn_last4"] = val[-4:] if len(val) >= 4 else val

        elif sid == "NM1" and in_member:
            entity = els[1] if len(els) > 1 else ""
            if entity == "IL":
                current["last_name"] = els[3] if len(els) > 3 else ""
                current["first_name"] = els[4] if len(els) > 4 else ""
                current["middle_name"] = els[5] if len(els) > 5 else ""
                current["suffix"] = els[7] if len(els) > 7 else ""
                id_qual = els[8] if len(els) > 8 else ""
                id_val = els[9] if len(els) > 9 else ""
                if id_qual == "34":
                    current["ssn_last4"] = id_val[-4:] if len(id_val) >= 4 else id_val
                elif id_qual == "MI" and not current["member_id"]:
                    current["member_id"] = id_val

        elif sid == "DMG" and in_member:
            if len(els) > 2:
                current["dob"] = parse_x12_date(els[2])
            if len(els) > 3:
                g = els[3].upper()
                current["gender"] = "M" if g == "M" else "F" if g == "F" else "U"

        elif sid == "N3" and in_member:
            current["address"]["line1"] = els[1] if len(els) > 1 else ""
            current["address"]["line2"] = els[2] if len(els) > 2 else ""

        elif sid == "N4" and in_member:
            current["address"]["city"] = els[1] if len(els) > 1 else ""
            current["address"]["state"] = els[2] if len(els) > 2 else ""
            current["address"]["zip"] = els[3] if len(els) > 3 else ""

        elif sid == "DTP" and in_member:
            qual = els[1] if len(els) > 1 else ""
            date_val = els[3] if len(els) > 3 else ""
            if qual == "348":
                current["effective_date"] = parse_x12_date(date_val)
            elif qual == "349":
                current["termination_date"] = parse_x12_date(date_val)
            elif qual == "303":
                current["maintenance_effective_date"] = parse_x12_date(date_val)
            elif qual == "357":
                current["eligibility_begin"] = parse_x12_date(date_val)

        elif sid == "HD" and in_member:
            ins_type = els[3] if len(els) > 3 else ""
            plan_code = els[3] if len(els) > 3 else ""
            current["plan_id"] = plan_code
            current["coverage_type"] = HD_COVERAGE_TYPE.get(ins_type, ins_type)

        elif sid == "SE":
            pass  # End of transaction set
        elif sid == "GE":
            pass
        elif sid == "IEA":
            pass

    # Save last member
    if in_member and current.get("member_id"):
        members.append(current)

    # Validate
    for i, m in enumerate(members):
        if not m.get("member_id"):
            errors.append({"index": i, "error": "Missing member_id (REF*0F)", "data": m.get("last_name", "unknown")})
        if not m.get("first_name") and not m.get("last_name"):
            errors.append({"index": i, "error": "Missing name (NM1*IL)", "member_id": m.get("member_id", "")})

    return {
        "success": True,
        "envelope": env_info,
        "member_count": len(members),
        "members": members,
        "errors": errors,
        "segment_count": seg_count,
    }


async def save_834_member(member_data):
    """Save a member parsed from 834."""
    member_id = member_data.get("member_id", "")
    if not member_id:
        raise ValueError("Missing member_id")

    existing = await db.members.find_one({"member_id": member_id})
    now = datetime.now(timezone.utc).isoformat()

    maint_type = member_data.get("maintenance_type", "addition")

    # Determine status based on maintenance type
    if maint_type in ("cancellation", "termination"):
        status = "terminated"
    elif maint_type == "reinstatement":
        status = "active"
    elif existing:
        status = existing.get("status", "active")
    else:
        status = "active"

    doc = {
        "id": existing["id"] if existing else str(uuid.uuid4()),
        "member_id": member_id,
        "first_name": member_data.get("first_name", ""),
        "last_name": member_data.get("last_name", ""),
        "dob": member_data.get("dob", ""),
        "gender": member_data.get("gender", "U"),
        "group_id": member_data.get("group_id", ""),
        "plan_id": member_data.get("plan_id", ""),
        "effective_date": member_data.get("effective_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "termination_date": member_data.get("termination_date"),
        "relationship": member_data.get("relationship", "subscriber"),
        "status": status,
        "created_at": existing["created_at"] if existing else now,
        "updated_at": now,
    }

    action = "member_updated" if existing else "member_added"
    if maint_type == "addition" and not existing:
        action = "member_added"
    elif maint_type in ("cancellation", "termination"):
        action = "member_terminated"
        old_term = existing.get("termination_date") if existing else None
        new_term = doc.get("termination_date")
        if new_term and old_term and new_term < old_term:
            action = "member_retro_terminated"
    elif maint_type == "reinstatement":
        action = "member_reinstated"

    if existing:
        await db.members.replace_one({"member_id": member_id}, doc)
    else:
        await db.members.insert_one(doc)

    await db.tpa_834_feed.update_one(
        {"member_id": member_id},
        {"$set": {
            "member_id": member_id,
            "first_name": doc["first_name"],
            "last_name": doc["last_name"],
            "dob": doc["dob"],
            "group_id": doc["group_id"],
            "plan_id": doc["plan_id"],
            "effective_date": doc["effective_date"],
            "termination_date": doc["termination_date"],
            "feed_date": now,
        }},
        upsert=True,
    )

    await db.member_audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "member_id": member_id,
        "action": action,
        "user_id": "system_834",
        "details": {
            "source": "834_feed",
            "maintenance_type": maint_type,
            "maintenance_reason": member_data.get("maintenance_reason", ""),
            "effective_date": doc["effective_date"],
            "termination_date": doc.get("termination_date"),
        },
        "timestamp": now,
    })

    return action


# ── 837 Parser ──

HL_LEVEL = {"20": "information_source", "22": "subscriber", "23": "dependent"}

SBR_PAYER_RESP = {
    "P": "primary", "S": "secondary", "T": "tertiary", "A": "payer_a",
}


async def parse_837_transactions(raw: str):
    """Parse X12 837 professional claims file with proper HL hierarchy."""
    envelope, err = parse_x12_envelope(raw)
    if err:
        return {"success": False, "error": err, "claims": [], "envelope": None}

    sep = envelope["element_sep"]
    sub_sep = envelope["sub_element_sep"]
    segments = envelope["segments"]

    isa_els = segments[0].split(sep) if segments else []
    env_info = {
        "sender_id": isa_els[6].strip() if len(isa_els) > 6 else "",
        "receiver_id": isa_els[8].strip() if len(isa_els) > 8 else "",
        "date": parse_x12_date(isa_els[9].strip()) if len(isa_els) > 9 else "",
        "control_number": isa_els[13].strip() if len(isa_els) > 13 else "",
    }

    claims = []
    errors = []
    seg_count = 0

    # State machine
    current_claim = None
    current_svc_lines = []
    current_diag_codes = []
    current_provider = {"name": "", "npi": ""}
    current_subscriber = {"member_id": "", "first_name": "", "last_name": ""}
    line_counter = 0

    for seg in segments:
        els = seg.split(sep)
        sid = els[0].upper()
        seg_count += 1

        if sid == "HL":
            pass  # HL hierarchy tracked implicitly by NM1/CLM ordering

        elif sid == "SBR":
            payer_seq = els[1] if len(els) > 1 else "P"
            current_subscriber["payer_responsibility"] = SBR_PAYER_RESP.get(payer_seq, payer_seq)

        elif sid == "NM1":
            entity = els[1] if len(els) > 1 else ""
            if entity == "IL":
                # Subscriber/Patient
                current_subscriber["last_name"] = els[3] if len(els) > 3 else ""
                current_subscriber["first_name"] = els[4] if len(els) > 4 else ""
                id_qual = els[8] if len(els) > 8 else ""
                id_val = els[9] if len(els) > 9 else ""
                if id_qual == "MI":
                    current_subscriber["member_id"] = id_val
                elif id_val:
                    current_subscriber["member_id"] = id_val
            elif entity == "QC":
                # Patient (if different from subscriber)
                if current_claim is not None:
                    current_claim["patient_last_name"] = els[3] if len(els) > 3 else ""
                    current_claim["patient_first_name"] = els[4] if len(els) > 4 else ""
                    if len(els) > 9 and els[9]:
                        current_claim["member_id"] = els[9]
            elif entity == "82":
                # Rendering provider
                last = els[3] if len(els) > 3 else ""
                first = els[4] if len(els) > 4 else ""
                current_provider["name"] = f"{first} {last}".strip() if first else last
                current_provider["npi"] = els[9] if len(els) > 9 else ""
            elif entity == "85":
                # Billing provider
                if not current_provider["name"]:
                    last = els[3] if len(els) > 3 else ""
                    first = els[4] if len(els) > 4 else ""
                    current_provider["name"] = f"{first} {last}".strip() if first else last
                if not current_provider["npi"]:
                    current_provider["npi"] = els[9] if len(els) > 9 else ""

        elif sid == "CLM":
            # Save previous claim
            if current_claim and current_claim.get("member_id"):
                current_claim["service_lines"] = current_svc_lines
                current_claim["diagnosis_codes"] = current_diag_codes
                claims.append(current_claim)

            in_svc = False  # noqa: F841
            line_counter = 0
            current_svc_lines = []
            current_diag_codes = []

            patient_ctl = els[1] if len(els) > 1 else ""
            total_billed = 0
            try:
                total_billed = float(els[2]) if len(els) > 2 else 0
            except ValueError:
                total_billed = 0

            # CLM05: Place of service / facility code
            pos = "11"
            if len(els) > 5:
                pos_parts = els[5].split(sub_sep) if sub_sep in els[5] else els[5].split(":")
                pos = pos_parts[0] if pos_parts else "11"

            # CLM06: Provider signature
            freq_code = els[7] if len(els) > 7 else "1"

            current_claim = {
                "patient_control": patient_ctl,
                "total_billed": total_billed,
                "place_of_service": pos,
                "frequency_code": freq_code,
                "member_id": current_subscriber.get("member_id", ""),
                "provider_name": current_provider.get("name", ""),
                "provider_npi": current_provider.get("npi", ""),
                "service_date_from": "",
                "service_date_to": "",
            }

        elif sid == "HI":
            for i in range(1, len(els)):
                parts = els[i].split(sub_sep) if sub_sep in els[i] else els[i].split(":")
                if len(parts) >= 2:
                    code = parts[1]
                    # Insert decimal point for ICD-10 codes >3 chars without dot
                    if len(code) > 3 and "." not in code:
                        code = code[:3] + "." + code[3:]
                    current_diag_codes.append(code)

        elif sid == "DTP":
            qual = els[1] if len(els) > 1 else ""
            fmt_code = els[2] if len(els) > 2 else ""
            date_val = els[3] if len(els) > 3 else ""
            if qual == "472":
                if "-" in date_val and fmt_code == "RD8":
                    parts = date_val.split("-")
                    if current_claim is not None:
                        current_claim["service_date_from"] = parse_x12_date(parts[0])
                        current_claim["service_date_to"] = parse_x12_date(parts[1]) if len(parts) > 1 else current_claim["service_date_from"]
                else:
                    d = parse_x12_date(date_val)
                    if current_claim is not None:
                        current_claim["service_date_from"] = d
                        current_claim["service_date_to"] = d

        elif sid == "REF":
            qual = els[1] if len(els) > 1 else ""
            val = els[2] if len(els) > 2 else ""
            if qual == "G1" and current_claim is not None:
                current_claim["prior_auth_number"] = val
            elif qual == "EA" and current_claim is not None:
                current_claim["medical_record_number"] = val

        elif sid == "SV1":
            line_counter += 1
            proc_composite = els[1] if len(els) > 1 else ""
            proc_parts = proc_composite.split(sub_sep) if sub_sep in proc_composite else proc_composite.split(":")
            proc_code = proc_parts[1] if len(proc_parts) > 1 else proc_parts[0]
            modifier = proc_parts[2] if len(proc_parts) > 2 else ""
            modifier2 = proc_parts[3] if len(proc_parts) > 3 else ""

            billed = 0
            try:
                billed = float(els[2]) if len(els) > 2 else 0
            except ValueError:
                billed = 0

            units = 1
            try:
                units = int(float(els[4])) if len(els) > 4 else 1
            except (ValueError, IndexError):
                units = 1

            svc_pos = els[5] if len(els) > 5 else current_claim.get("place_of_service", "11") if current_claim else "11"

            diag_ptr = els[7] if len(els) > 7 else "1"
            diag_ptrs = [int(p) - 1 for p in diag_ptr.split(sub_sep) if p.isdigit()]
            linked_diags = [current_diag_codes[p] for p in diag_ptrs if p < len(current_diag_codes)]

            svc_line = {
                "line_number": line_counter,
                "cpt_code": proc_code,
                "modifier": modifier,
                "modifier2": modifier2,
                "billed_amount": billed,
                "units": units,
                "service_date": current_claim.get("service_date_from", "") if current_claim else "",
                "place_of_service": svc_pos,
                "diagnosis_codes": linked_diags,
                "revenue_code": None,
            }
            current_svc_lines.append(svc_line)

        elif sid == "SV2":
            # Institutional service line (837I)
            line_counter += 1
            rev_code = els[1] if len(els) > 1 else ""
            proc_composite = els[2] if len(els) > 2 else ""
            proc_parts = proc_composite.split(sub_sep) if sub_sep and sub_sep in proc_composite else proc_composite.split(":")
            proc_code = proc_parts[1] if len(proc_parts) > 1 else proc_parts[0]
            billed = 0
            try:
                billed = float(els[3]) if len(els) > 3 else 0
            except ValueError:
                billed = 0
            units = 1
            try:
                units = int(float(els[5])) if len(els) > 5 else 1
            except (ValueError, IndexError):
                units = 1

            svc_line = {
                "line_number": line_counter,
                "cpt_code": proc_code,
                "modifier": "",
                "billed_amount": billed,
                "units": units,
                "service_date": current_claim.get("service_date_from", "") if current_claim else "",
                "place_of_service": "21",
                "diagnosis_codes": [],
                "revenue_code": rev_code,
            }
            current_svc_lines.append(svc_line)

    # Save last claim
    if current_claim and current_claim.get("member_id"):
        current_claim["service_lines"] = current_svc_lines
        current_claim["diagnosis_codes"] = current_diag_codes
        claims.append(current_claim)

    # Validate
    for i, c in enumerate(claims):
        if not c.get("member_id"):
            errors.append({"index": i, "error": "Missing member_id (NM1*IL)", "control": c.get("patient_control", "")})
        if not c.get("service_lines"):
            errors.append({"index": i, "error": "No service lines (SV1)", "control": c.get("patient_control", "")})

    return {
        "success": True,
        "envelope": env_info,
        "claim_count": len(claims),
        "claims": claims,
        "errors": errors,
        "segment_count": seg_count,
    }


async def save_837_claim(claim_data, service_lines, diag_codes, user):
    """Save a claim parsed from X12 837."""
    svc_lines = []
    for sl in service_lines:
        svc_lines.append({
            "line_number": sl["line_number"],
            "cpt_code": sl["cpt_code"],
            "modifier": sl.get("modifier", ""),
            "units": sl.get("units", 1),
            "billed_amount": sl.get("billed_amount", 0),
            "service_date": claim_data.get("service_date_from", ""),
            "place_of_service": sl.get("place_of_service", "11"),
            "diagnosis_codes": sl.get("diagnosis_codes", []),
            "revenue_code": sl.get("revenue_code"),
        })

    total_billed = claim_data.get("total_billed", sum(sl.get("billed_amount", 0) for sl in service_lines))

    claim_dict = {
        "member_id": claim_data.get("member_id", ""),
        "provider_npi": claim_data.get("provider_npi", ""),
        "provider_name": claim_data.get("provider_name", "Unknown Provider"),
        "facility_npi": None,
        "claim_type": ClaimType.MEDICAL.value,
        "service_date_from": claim_data.get("service_date_from", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "service_date_to": claim_data.get("service_date_to", claim_data.get("service_date_from", datetime.now(timezone.utc).strftime("%Y-%m-%d"))),
        "total_billed": total_billed,
        "diagnosis_codes": diag_codes or ["Z00.00"],
        "prior_auth_number": claim_data.get("prior_auth_number"),
        "source": "edi_837",
        "external_claim_id": claim_data.get("patient_control"),
    }

    result = await process_new_claim(claim_dict, svc_lines, user)
    return result


# ── 835 Generator ──

CAS_GROUP_CODES = {
    "contractual": "CO",
    "patient": "PR",
    "other": "OA",
    "correction": "CR",
    "payer_initiated": "PI",
}

CAS_REASON_CODES = {
    "CO": {"45": "Charge exceeds fee schedule/maximum allowable",
           "97": "The benefit for this service is included in the payment/allowance for another service",
           "253": "Sequestration - Loss of funds"},
    "PR": {"1": "Deductible amount",
           "2": "Coinsurance amount",
           "3": "Copay amount"},
}


async def generate_835_content(claims, payer_name="FletchFlow Claims System", payer_id="FLETCHFLOW"):
    """Generate compliant X12 835 remittance advice."""
    now = datetime.now(timezone.utc)
    isa_date = now.strftime("%y%m%d")
    isa_time = now.strftime("%H%M")
    gs_date = now.strftime("%Y%m%d")
    gs_time = now.strftime("%H%M")
    control_num = str(uuid.uuid4().int)[:9].zfill(9)
    total_paid = sum(c.get("total_paid", 0) for c in claims)

    lines = []

    # ISA — Interchange Control Header
    lines.append(
        f"ISA*00*          *00*          *ZZ*{payer_id:<15s}*ZZ*RECEIVER       "
        f"*{isa_date}*{isa_time}*^*00501*{control_num}*0*P*:~"
    )

    # GS — Functional Group Header
    lines.append(f"GS*HP*{payer_id}*RECEIVER*{gs_date}*{gs_time}*1*X*005010X221A1~")

    # ST — Transaction Set Header
    lines.append("ST*835*0001~")

    # BPR — Financial Information
    lines.append(
        f"BPR*I*{total_paid:.2f}*C*ACH*CTX*01*999999999*DA*123456789"
        f"*1234567890**01*999999999*DA*987654321*{gs_date}~"
    )

    # TRN — Reassociation Trace Number
    lines.append(f"TRN*1*{control_num}*1234567890~")

    # DTM — Production Date
    lines.append(f"DTM*405*{gs_date}~")

    # N1 — Payer Identification
    lines.append(f"N1*PR*{payer_name}*XV*{payer_id}~")
    lines.append("N3*100 Claims Street~")
    lines.append("N4*Atlanta*GA*30301~")
    lines.append(f"REF*2U*{control_num}~")

    # N1 — Payee Identification
    lines.append("N1*PE*Provider Name*XX*1234567890~")

    segment_count = 11  # Count segments so far (ISA through N1*PE)

    for claim in claims:
        clp_status = "1" if claim.get("status") == "approved" else "2" if claim.get("status") == "denied" else "4"
        claim_number = claim.get("claim_number", "")
        billed = claim.get("total_billed", 0)
        paid = claim.get("total_paid", 0)
        member_resp = claim.get("member_responsibility", 0)

        # CLP — Claim Payment Information
        lines.append(f"CLP*{claim_number}*{clp_status}*{billed:.2f}*{paid:.2f}*{member_resp:.2f}*MC*{claim.get('id', '')}~")
        segment_count += 1

        # CAS — Claim-level adjustments (Contractual Obligation)
        co_adj = billed - paid - member_resp
        if co_adj > 0.005:
            lines.append(f"CAS*CO*45*{co_adj:.2f}~")
            segment_count += 1
        if member_resp > 0.005:
            lines.append(f"CAS*PR*1*{member_resp:.2f}~")
            segment_count += 1

        # NM1 — Patient
        lines.append(f"NM1*QC*1*{claim.get('member_id', '')}****MI*{claim.get('member_id', '')}~")
        segment_count += 1

        # DTM — Statement date
        svc_date = claim.get("service_date_from", "").replace("-", "")
        if svc_date:
            lines.append(f"DTM*232*{svc_date}~")
            segment_count += 1

        # Service lines
        for sl in claim.get("service_lines", []):
            cpt = sl.get("cpt_code", "")
            sl_billed = sl.get("billed_amount", 0)
            sl_paid = sl.get("paid_amount", sl.get("paid", 0))
            sl_units = sl.get("units", 1)
            modifier = sl.get("modifier", "")
            proc_code = f"HC:{cpt}" + (f":{modifier}" if modifier else "")

            # SVC — Service Payment
            lines.append(f"SVC*{proc_code}*{sl_billed:.2f}*{sl_paid:.2f}**{sl_units}~")
            segment_count += 1

            # DTM — Service date
            sl_date = sl.get("service_date", svc_date).replace("-", "")
            if sl_date:
                lines.append(f"DTM*472*{sl_date}~")
                segment_count += 1

            # CAS — Service-level adjustments
            svc_adj = sl_billed - sl_paid
            if svc_adj > 0.005:
                lines.append(f"CAS*CO*45*{svc_adj:.2f}~")
                segment_count += 1

            # AMT — Allowed amount
            allowed = sl.get("allowed_amount", sl_paid)
            lines.append(f"AMT*B6*{allowed:.2f}~")
            segment_count += 1

    # PLB — Provider Level Balance (if adjustments exist)
    # lines.append(f"PLB*1234567890*{gs_date}*72*0.00~")
    # segment_count += 1

    # SE — Transaction Set Trailer
    segment_count += 1  # For SE itself
    lines.append(f"SE*{segment_count}*0001~")

    # GE — Functional Group Trailer
    lines.append("GE*1*1~")

    # IEA — Interchange Control Trailer
    lines.append(f"IEA*1*{control_num}~")

    return "\n".join(lines)
