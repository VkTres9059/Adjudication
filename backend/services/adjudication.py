from datetime import datetime, timezone
from core.database import db
from models.enums import ClaimStatus
from cpt_codes import get_cpt_code, calculate_medicare_rate
from dental_codes import get_dental_code, calculate_dental_allowed
from vision_codes import get_vision_code, calculate_vision_allowed
from hearing_codes import get_hearing_code, calculate_hearing_allowed
from preventive_services import (
    evaluate_preventive_claim_line,
    check_preventive_frequency,
    record_preventive_utilization,
    calculate_member_age,
    get_preventive_service,
)


def lookup_code_for_claim_type(cpt_code, claim_type):
    """Look up a procedure code across all coverage databases based on claim type."""
    if claim_type == "dental":
        data = get_dental_code(cpt_code)
        if data:
            return {"source": "dental", **data}
    elif claim_type == "vision":
        data = get_vision_code(cpt_code)
        if data:
            return {"source": "vision", **data}
    elif claim_type == "hearing":
        data = get_hearing_code(cpt_code)
        if data:
            return {"source": "hearing", **data}
    data = get_cpt_code(cpt_code)
    if data:
        return {"source": "medical", **data}
    for fn, src in [(get_dental_code, "dental"), (get_vision_code, "vision"), (get_hearing_code, "hearing")]:
        data = fn(cpt_code)
        if data:
            return {"source": src, **data}
    return None


def calculate_line_allowed_for_type(code, code_data, claim_type, locality_code, reimbursement_method, rate_multiplier, units):
    """Calculate allowed amount for a service line based on claim type."""
    if code_data["source"] == "dental":
        result = calculate_dental_allowed(code)
        if result:
            return result["fee"] * units, result["plan_pays"] * units, result["member_pays"] * units, f"Dental CDT fee: ${result['fee']:.2f} ({result['benefit_class']})"
    elif code_data["source"] == "vision":
        result = calculate_vision_allowed(code)
        if result:
            return result["fee"] * units, result["plan_pays"] * units, result["member_pays"] * units, f"Vision fee: ${result['fee']:.2f} ({result['benefit_class']})"
    elif code_data["source"] == "hearing":
        result = calculate_hearing_allowed(code)
        if result:
            return result["fee"] * units, result["plan_pays"] * units, result["member_pays"] * units, f"Hearing fee: ${result['fee']:.2f} ({result['benefit_class']})"
    medicare_rate = calculate_medicare_rate(code, locality_code, use_facility=True)
    if medicare_rate:
        allowed = medicare_rate * rate_multiplier * units
        return allowed, None, None, f"Medicare Rate: ${medicare_rate:.2f}, Method: {reimbursement_method} ({rate_multiplier*100:.0f}%)"
    return None, None, None, None


async def adjudicate_claim(claim: dict, plan: dict, member: dict, locality_code: str = "00000") -> dict:
    """Apply plan rules to adjudicate a claim - supports Medical, Dental, Vision, Hearing + Preventive."""

    adjudication_notes = []
    total_allowed = 0
    total_paid = 0
    member_responsibility = 0
    claim_type = claim.get("claim_type", "medical")
    is_mec_plan = plan.get("plan_template") == "mec_1"

    claim_date = datetime.fromisoformat(claim["service_date_from"])
    member_eff = datetime.fromisoformat(member["effective_date"])
    member_term = datetime.fromisoformat(member["termination_date"]) if member.get("termination_date") else None

    if claim_date < member_eff:
        return {
            "status": ClaimStatus.DENIED.value,
            "total_allowed": 0, "total_paid": 0,
            "member_responsibility": claim["total_billed"],
            "adjudication_notes": ["DENIED: Service date before coverage effective date"]
        }

    if member_term and claim_date > member_term:
        return {
            "status": ClaimStatus.DENIED.value,
            "total_allowed": 0, "total_paid": 0,
            "member_responsibility": claim["total_billed"],
            "adjudication_notes": ["DENIED: Service date after coverage termination"]
        }

    # Hour bank deficit check
    if member.get("status") == "termed_insufficient_hours":
        return {
            "status": ClaimStatus.DENIED.value,
            "total_allowed": 0, "total_paid": 0,
            "member_responsibility": claim["total_billed"],
            "adjudication_notes": ["DENIED: Coverage suspended due to hour bank deficit."],
            "service_lines": [{
                **line,
                "allowed": 0,
                "paid": 0,
                "member_resp": line.get("billed_amount", 0),
                "denial_reason": "Coverage suspended due to hour bank deficit.",
                "eob_message": "Coverage suspended due to hour bank deficit.",
            } for line in claim.get("service_lines", [])],
        }

    plan_type = plan.get("plan_type", "medical")
    if plan_type != claim_type:
        adjudication_notes.append(f"WARNING: Claim type '{claim_type}' does not match plan type '{plan_type}'.")

    if claim.get("prior_auth_number"):
        await db.prior_authorizations.find_one(
            {"auth_number": claim["prior_auth_number"], "status": "approved"},
            {"_id": 0}
        )

    accumulators = await db.accumulators.find_one(
        {"member_id": claim["member_id"], "plan_year": str(claim_date.year), "claim_type": claim_type},
        {"_id": 0}
    ) or {"deductible_met": 0, "oop_met": 0, "annual_max_used": 0}

    deductible = plan.get("deductible_individual", 0)
    oop_max = plan.get("oop_max_individual", 999999)
    annual_max = plan.get("annual_max", 999999)

    reimbursement_method = plan.get("reimbursement_method", "fee_schedule")
    method_multipliers = {"fee_schedule": 1.0, "percent_medicare": 1.2, "percent_billed": 0.8, "rbp": 1.4, "contracted": 1.0}
    rate_multiplier = method_multipliers.get(reimbursement_method, 1.0)

    preventive_design = plan.get("preventive_design", "aca_strict")

    member_age = calculate_member_age(member.get("dob", "2000-01-01"), claim["service_date_from"])
    member_gender = member.get("gender", "U").lower()
    if member_gender in ("m", "male"):
        member_gender = "male"
    elif member_gender in ("f", "female"):
        member_gender = "female"

    claim_diagnosis = claim.get("diagnosis_codes", [])

    processed_lines = []
    for line in claim["service_lines"]:
        proc_code = line["cpt_code"]
        billed = line["billed_amount"]
        units = line.get("units", 1)
        line_modifier = line.get("modifier", "")
        line_dx = line.get("diagnosis_codes", []) or claim_diagnosis

        preventive_eval = evaluate_preventive_claim_line(
            proc_code, line_dx, line_modifier,
            member_age if member_age is not None else 30,
            member_gender
        )

        if preventive_eval["is_preventive"] is True:
            within_limit, freq_msg, usage_count = await check_preventive_frequency(
                db, claim["member_id"], proc_code, claim.get("service_date_from", ""),
                preventive_eval.get("service")
            )

            if not within_limit:
                adjudication_notes.append(
                    f"Line {line['line_number']}: {proc_code} - PREVENTIVE frequency exceeded ({freq_msg}). Reclassified as diagnostic."
                )
            else:
                svc = preventive_eval.get("service", {})
                allowed = svc.get("fee", billed) * units
                allowed = min(allowed, billed)
                paid = allowed
                member_resp = 0.0

                total_allowed += allowed
                total_paid += paid

                await record_preventive_utilization(
                    db, claim["member_id"], proc_code,
                    claim.get("service_date_from", ""), claim.get("id", "")
                )

                adjudication_notes.append(
                    f"Line {line['line_number']}: {proc_code} - PREVENTIVE SERVICE ($0 member cost). "
                    f"Source: {svc.get('source', 'ACA')}. {freq_msg}"
                )

                processed_lines.append({
                    **line,
                    "allowed": round(allowed, 2),
                    "paid": round(paid, 2),
                    "member_resp": 0.0,
                    "deductible_applied": 0.0,
                    "medicare_rate": None,
                    "cpt_description": svc.get("description", "Preventive Service"),
                    "coverage_type": "preventive",
                    "is_preventive": True,
                    "preventive_category": svc.get("category", ""),
                    "preventive_source": svc.get("source", ""),
                    "eob_message": "Preventive Service - $0 Member Responsibility",
                })
                continue

        elif preventive_eval.get("is_preventive") == "split":
            adjudication_notes.append(
                f"Line {line['line_number']}: {proc_code} - Split claim: preventive diagnosis with illness secondary dx. "
                "Processing as diagnostic with normal cost sharing."
            )

        elif preventive_eval.get("reclassify_as") == "diagnostic":
            adjudication_notes.append(
                f"Line {line['line_number']}: {proc_code} - Preventive code but billed as diagnostic (no Z-code/modifier 33). "
                "Normal plan benefits apply."
            )

        if is_mec_plan:
            adjudication_notes.append(
                f"Line {line['line_number']}: {proc_code} - DENIED: Not a Covered Benefit (MEC 1 Plan - Preventive Only)"
            )
            processed_lines.append({
                **line,
                "allowed": 0,
                "paid": 0,
                "member_resp": billed,
                "deductible_applied": 0,
                "medicare_rate": None,
                "cpt_description": f"{proc_code} - Not Covered (MEC 1)",
                "coverage_type": claim_type,
                "is_preventive": False,
                "denial_reason": "Not a Covered Benefit - MEC 1 Plan (Preventive Services Only)",
                "eob_message": "Service denied - Not a covered benefit under MEC 1. Only ACA-compliant preventive services are covered.",
            })
            member_responsibility += billed
            continue

        code_data = lookup_code_for_claim_type(proc_code, claim_type)

        benefit = None
        for b in plan.get("benefits", []):
            if b.get("code_range"):
                if proc_code.startswith(b["code_range"][:3]):
                    benefit = b
                    break
            elif b.get("service_category"):
                if code_data:
                    code_category = code_data.get("category", "")
                    service_cat = b.get("service_category", "").lower()
                    category_map = {
                        "E/M": ["office visit", "preventive", "hospital", "emergency", "evaluation"],
                        "Surgery": ["surgery", "procedure"],
                        "Radiology": ["imaging", "radiology", "x-ray", "ct", "mri"],
                        "Pathology/Lab": ["lab", "pathology", "diagnostic"],
                        "Medicine": ["physical therapy", "immunization", "vaccine", "cardio", "pulmonary"],
                        "Anesthesia": ["anesthesia"],
                        "HCPCS": ["drug", "injection", "dme", "equipment"],
                        "Diagnostic": ["diagnostic", "preventive"],
                        "Radiograph": ["diagnostic", "imaging", "x-ray"],
                        "Preventive": ["preventive"],
                        "Restorative": ["basic", "restorative"],
                        "Crown": ["major", "crown"],
                        "Endodontics": ["major", "endodontic"],
                        "Periodontics": ["basic", "periodontic"],
                        "Prosthodontics": ["major", "prosthodontic"],
                        "Oral Surgery": ["basic", "surgery"],
                        "Orthodontics": ["orthodontic"],
                        "Eye Exam": ["exam", "office visit", "evaluation"],
                        "Lenses": ["materials", "lens"],
                        "Frames": ["materials", "frame"],
                        "Contact Lens": ["contact lens", "materials"],
                        "Audiometric Testing": ["diagnostic", "testing"],
                        "Hearing Aid Service": ["hearing aid", "service"],
                        "Hearing Aid Device": ["hearing aid", "device"],
                        "Cochlear Implant": ["cochlear", "implant"],
                    }
                    if code_category in category_map:
                        for keyword in category_map[code_category]:
                            if keyword in service_cat:
                                benefit = b
                                break
                if benefit:
                    break

        if not benefit:
            benefit = {"covered": True, "copay": 0, "coinsurance": 0.2, "deductible_applies": True}

        if not benefit.get("covered", True):
            processed_lines.append({
                **line, "allowed": 0, "paid": 0, "member_resp": billed,
                "denial_reason": "Service not covered under plan", "medicare_rate": None
            })
            adjudication_notes.append(f"Line {line['line_number']}: {proc_code} - NOT COVERED")
            member_responsibility += billed
            continue

        if proc_code in plan.get("exclusions", []):
            processed_lines.append({
                **line, "allowed": 0, "paid": 0, "member_resp": billed,
                "denial_reason": "Service excluded from coverage", "medicare_rate": None
            })
            adjudication_notes.append(f"Line {line['line_number']}: {proc_code} - EXCLUDED")
            member_responsibility += billed
            continue

        if benefit.get("prior_auth_required") and not claim.get("prior_auth_number"):
            processed_lines.append({
                **line, "allowed": 0, "paid": 0, "member_resp": billed,
                "denial_reason": "Prior authorization required", "medicare_rate": None
            })
            adjudication_notes.append(f"Line {line['line_number']}: {proc_code} - Prior auth REQUIRED")
            member_responsibility += billed
            continue

        allowed = None
        type_plan_pays = None
        type_member_pays = None
        rate_note = None
        medicare_rate = None

        if code_data:
            allowed, type_plan_pays, type_member_pays, rate_note = calculate_line_allowed_for_type(
                proc_code, code_data, claim_type, locality_code, reimbursement_method, rate_multiplier, units
            )
            if code_data["source"] == "medical":
                medicare_rate = calculate_medicare_rate(proc_code, locality_code, use_facility=True)

        if allowed is None:
            allowed = billed * 0.8
            rate_note = "UNKNOWN code, using 80% of billed"

        allowed = min(allowed, billed)
        adjudication_notes.append(f"Line {line['line_number']}: {proc_code} - {rate_note}")

        if type_plan_pays is not None and type_member_pays is not None:
            paid = type_plan_pays
            member_resp_this_line = type_member_pays
            if claim_type == "dental" and annual_max < 999999:
                remaining_annual = max(0, annual_max - accumulators.get("annual_max_used", 0))
                if paid > remaining_annual:
                    excess = paid - remaining_annual
                    paid = remaining_annual
                    member_resp_this_line += excess
                    adjudication_notes.append(f"Line {line['line_number']}: Annual max reached - excess ${excess:.2f}")
                accumulators["annual_max_used"] = accumulators.get("annual_max_used", 0) + min(type_plan_pays, remaining_annual)
        else:
            line_deductible = 0
            if benefit.get("deductible_applies", True):
                remaining_deductible = max(0, deductible - accumulators["deductible_met"])
                line_deductible = min(allowed, remaining_deductible)
                accumulators["deductible_met"] += line_deductible

            after_deductible = allowed - line_deductible
            copay = benefit.get("copay", 0)
            coinsurance_pct = benefit.get("coinsurance", 0.2)
            coinsurance_amount = after_deductible * coinsurance_pct

            paid = after_deductible - coinsurance_amount - copay
            member_resp_this_line = line_deductible + coinsurance_amount + copay

            remaining_oop = max(0, oop_max - accumulators["oop_met"])
            if member_resp_this_line > remaining_oop:
                paid += (member_resp_this_line - remaining_oop)
                member_resp_this_line = remaining_oop
                adjudication_notes.append(f"Line {line['line_number']}: OOP MAX reached")

            accumulators["oop_met"] += member_resp_this_line

        total_allowed += allowed
        total_paid += max(0, paid)
        member_responsibility += member_resp_this_line

        processed_lines.append({
            **line,
            "allowed": round(allowed, 2),
            "paid": round(max(0, paid), 2),
            "member_resp": round(member_resp_this_line, 2),
            "deductible_applied": round(accumulators.get("deductible_met", 0), 2),
            "medicare_rate": medicare_rate,
            "cpt_description": code_data.get("description", "Unknown") if code_data else "Unknown",
            "work_rvu": code_data.get("work_rvu") if code_data else None,
            "total_rvu": code_data.get("total_rvu") if code_data else None,
            "coverage_type": code_data.get("source", claim_type) if code_data else claim_type,
            "is_preventive": False,
        })

    await db.accumulators.update_one(
        {"member_id": claim["member_id"], "plan_year": str(claim_date.year), "claim_type": claim_type},
        {"$set": accumulators},
        upsert=True
    )

    result = {
        "status": ClaimStatus.APPROVED.value if total_paid > 0 else ClaimStatus.DENIED.value,
        "total_allowed": round(total_allowed, 2),
        "total_paid": round(total_paid, 2),
        "member_responsibility": round(member_responsibility, 2),
        "service_lines": processed_lines,
        "adjudication_notes": adjudication_notes
    }

    # Stop-Loss auto-flagging: if claim exceeds threshold % of Specific Attachment Point
    risk = plan.get("risk_management")
    if risk and total_paid > 0:
        specific_limit = risk.get("specific_attachment_point", 0)
        threshold_pct = risk.get("auto_flag_threshold_pct", 50)
        if specific_limit > 0 and total_paid > (specific_limit * threshold_pct / 100):
            result["stop_loss_flag"] = True
            result["adjudication_notes"].append(
                f"STOP-LOSS FLAG: Claim paid ${total_paid:,.2f} exceeds "
                f"{threshold_pct}% of Specific Attachment Point (${specific_limit:,.2f}). "
                f"Auto-routed to Examiner Queue for review."
            )

    return result
