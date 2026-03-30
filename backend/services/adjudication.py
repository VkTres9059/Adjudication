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
    """Apply plan rules to adjudicate a claim - supports Medical, Dental, Vision, Hearing + Preventive.
    
    Enhanced with:
    - COB (Coordination of Benefits) integration
    - Rx Rules (formulary tier pricing for drug claims)
    - Visit-based copay (one copay per visit, not per service line)
    - Plan version stamping
    - Network tier repricing with RBP
    - Auto data-tier classification
    - Pre-cert penalty enforcement
    """

    adjudication_notes = []
    total_allowed = 0
    total_paid = 0
    member_responsibility = 0
    claim_type = claim.get("claim_type", "medical")
    is_mec_plan = plan.get("plan_template") == "mec_1"

    # ── Plan Version Stamping ──
    plan_version = plan.get("version", 1)

    claim_date = datetime.fromisoformat(claim["service_date_from"])
    member_eff = datetime.fromisoformat(member["effective_date"])
    member_term = datetime.fromisoformat(member["termination_date"]) if member.get("termination_date") else None

    if claim_date < member_eff:
        return {
            "status": ClaimStatus.DENIED.value,
            "total_allowed": 0, "total_paid": 0,
            "member_responsibility": claim["total_billed"],
            "adjudication_notes": ["DENIED: Service date before coverage effective date"],
            "plan_version": plan_version,
        }

    if member_term and claim_date > member_term:
        return {
            "status": ClaimStatus.DENIED.value,
            "total_allowed": 0, "total_paid": 0,
            "member_responsibility": claim["total_billed"],
            "adjudication_notes": ["DENIED: Service date after coverage termination"],
            "plan_version": plan_version,
        }

    # Hour bank deficit check
    if member.get("status") == "termed_insufficient_hours":
        return {
            "status": ClaimStatus.DENIED.value,
            "total_allowed": 0, "total_paid": 0,
            "member_responsibility": claim["total_billed"],
            "adjudication_notes": ["DENIED: Coverage suspended due to hour bank deficit."],
            "plan_version": plan_version,
            "service_lines": [{
                **line,
                "allowed": 0, "paid": 0,
                "member_resp": line.get("billed_amount", 0),
                "denial_reason": "Coverage suspended due to hour bank deficit.",
                "eob_message": "Coverage suspended due to hour bank deficit.",
            } for line in claim.get("service_lines", [])],
        }

    plan_type = plan.get("plan_type", "medical")
    if plan_type != claim_type:
        adjudication_notes.append(f"WARNING: Claim type '{claim_type}' does not match plan type '{plan_type}'.")

    # ── Pre-Cert Check with Penalty ──
    precert_penalty_applied = False
    preauth_penalty_pct = plan.get("preauth_penalty_pct", 50.0) / 100.0
    if claim.get("prior_auth_number"):
        auth = await db.prior_authorizations.find_one(
            {"auth_number": claim["prior_auth_number"], "status": "approved"},
            {"_id": 0}
        )
        if auth:
            adjudication_notes.append(f"Prior Auth {claim['prior_auth_number']} verified — approved.")
        else:
            adjudication_notes.append(f"WARNING: Prior Auth {claim['prior_auth_number']} not found or not approved.")

    # ── COB (Coordination of Benefits) ──
    cob_result = None
    cob_adjustment = 0
    cob_info = member.get("cob_info") or {}
    if cob_info.get("has_other_coverage"):
        from services.cob_engine import determine_payer_order, apply_cob_to_claim
        cob_result = await determine_payer_order(member, claim)
        adjudication_notes.append(f"COB: {cob_result['our_position'].upper()} payer — {cob_result.get('reason', '')}")

        if cob_result["our_position"] == "secondary":
            primary_eob = claim.get("primary_payer_eob")
            if not primary_eob:
                return {
                    "status": "pended_cob",
                    "total_allowed": 0, "total_paid": 0,
                    "member_responsibility": claim["total_billed"],
                    "adjudication_notes": adjudication_notes + ["PENDED: Awaiting primary payer EOB for COB processing."],
                    "plan_version": plan_version,
                    "cob_status": "awaiting_primary_eob",
                }

    # ── Accumulators (individual + family-level) ──
    accumulators = await db.accumulators.find_one(
        {"member_id": claim["member_id"], "plan_year": str(claim_date.year), "claim_type": claim_type},
        {"_id": 0}
    ) or {"deductible_met": 0, "oop_met": 0, "annual_max_used": 0}

    # Family-level accumulator check
    family_accum = None
    enrollment_tier = member.get("enrollment_tier", "employee_only")
    if enrollment_tier in ("employee_spouse", "employee_child", "family"):
        sub_id = member.get("subscriber_id", member["member_id"])
        family_members = await db.members.find(
            {"$or": [{"member_id": sub_id}, {"subscriber_id": sub_id}], "status": "active"},
            {"member_id": 1, "_id": 0}
        ).to_list(20)
        fam_ids = [m["member_id"] for m in family_members]
        fam_pipe = [
            {"$match": {"member_id": {"$in": fam_ids}, "plan_year": str(claim_date.year), "claim_type": claim_type}},
            {"$group": {"_id": None, "deductible_met": {"$sum": "$deductible_met"}, "oop_met": {"$sum": "$oop_met"}}},
        ]
        fam_agg = await db.accumulators.aggregate(fam_pipe).to_list(1)
        if fam_agg:
            family_accum = fam_agg[0]

    deductible = plan.get("deductible_individual", 0)
    deductible_family = plan.get("deductible_family", deductible * 3)
    oop_max = plan.get("oop_max_individual", 999999)
    oop_max_family = plan.get("oop_max_family", oop_max * 2)
    annual_max = plan.get("annual_max", 999999)

    # Check if family deductible already met
    family_ded_met = (family_accum or {}).get("deductible_met", 0) if family_accum else 0
    family_oop_met = (family_accum or {}).get("oop_met", 0) if family_accum else 0
    family_ded_remaining = max(0, deductible_family - family_ded_met)
    if family_ded_remaining <= 0:
        adjudication_notes.append("Family deductible fully met — individual deductible waived.")

    # ── Network Tier Determination ──
    network_tiers = plan.get("network_tiers") or []
    network_status = claim.get("network_status", "in_network")
    active_tier = None
    for tier in network_tiers:
        if tier.get("tier_name", "").lower().replace(" ", "_") == network_status.lower().replace(" ", "_"):
            active_tier = tier
            break
    if not active_tier and network_tiers:
        active_tier = network_tiers[0]  # Default to first tier

    reimbursement_method = plan.get("reimbursement_method", "fee_schedule")
    method_multipliers = {"fee_schedule": 1.0, "percent_medicare": 1.2, "percent_billed": 0.8, "rbp": 1.4, "contracted": 1.0}
    rate_multiplier = method_multipliers.get(reimbursement_method, 1.0)

    # Override with network tier RBP if available
    if active_tier:
        tier_rbp = active_tier.get("rbp_pct")
        if tier_rbp and tier_rbp > 0:
            rate_multiplier = tier_rbp / 100.0
            reimbursement_method = "rbp"
            adjudication_notes.append(f"Network Tier: {active_tier.get('tier_name', 'Default')} — RBP at {tier_rbp}% of Medicare.")

    member_age = calculate_member_age(member.get("dob", "2000-01-01"), claim["service_date_from"])
    member_gender = member.get("gender", "U").lower()
    if member_gender in ("m", "male"):
        member_gender = "male"
    elif member_gender in ("f", "female"):
        member_gender = "female"

    claim_diagnosis = claim.get("diagnosis_codes", [])

    # ── Visit-Based Copay Tracking ──
    visit_limits = plan.get("visit_limits") or {}
    visit_copay_applied = {}  # Track copay per visit category to avoid double-charging

    # ── Rx Rules Integration ──
    rx_rules = plan.get("rx_rules") or {}
    rx_enabled = rx_rules.get("enabled", False)

    processed_lines = []
    for line in claim["service_lines"]:
        proc_code = line["cpt_code"]
        billed = line["billed_amount"]
        units = line.get("units", 1)
        line_modifier = line.get("modifier", "")
        line_dx = line.get("diagnosis_codes", []) or claim_diagnosis

        # ── Rx Rules: Drug claim handling ──
        if rx_enabled and (proc_code.startswith("J") or proc_code.startswith("S0") or line.get("ndc_code")):
            from services.rx_engine import classify_drug, apply_rx_rules
            drug_class = classify_drug(
                hcpcs_code=proc_code,
                drug_name=line.get("drug_name", ""),
                ndc_code=line.get("ndc_code", ""),
            )
            drug_result = apply_rx_rules(plan, drug_class)

            if drug_result.get("covered") is False:
                processed_lines.append({
                    **line, "allowed": 0, "paid": 0, "member_resp": billed,
                    "denial_reason": f"Rx excluded: {drug_result.get('notes', 'Not on formulary')}",
                    "rx_tier": drug_result.get("tier_label"), "is_preventive": False,
                })
                adjudication_notes.append(f"Line {line['line_number']}: {proc_code} — Rx DENIED: {drug_result.get('notes')}")
                member_responsibility += billed
                continue

            if drug_result.get("requires_prior_auth") and not claim.get("prior_auth_number"):
                processed_lines.append({
                    **line, "allowed": 0, "paid": 0, "member_resp": billed,
                    "denial_reason": f"Rx prior auth required — {drug_result.get('tier_label')}",
                    "rx_tier": drug_result.get("tier_label"), "is_preventive": False,
                })
                adjudication_notes.append(f"Line {line['line_number']}: {proc_code} — Rx PRIOR AUTH required ({drug_result.get('tier_label')})")
                member_responsibility += billed
                continue

            # Apply Rx cost sharing
            rx_copay = drug_result.get("copay", 0)
            rx_coinsurance = drug_result.get("coinsurance", 0) / 100.0 if drug_result.get("coinsurance", 0) > 1 else drug_result.get("coinsurance", 0)
            allowed = min(billed, billed)  # Rx uses billed as allowed
            deductible_for_rx = 0
            if drug_result.get("deductible_applies", False):
                remaining_ded = max(0, deductible - accumulators["deductible_met"])
                deductible_for_rx = min(allowed, remaining_ded)
                accumulators["deductible_met"] += deductible_for_rx

            after_ded = allowed - deductible_for_rx
            coinsurance_amt = after_ded * rx_coinsurance
            member_resp_rx = deductible_for_rx + rx_copay + coinsurance_amt
            paid_rx = allowed - member_resp_rx

            total_allowed += allowed
            total_paid += max(0, paid_rx)
            member_responsibility += member_resp_rx

            processed_lines.append({
                **line,
                "allowed": round(allowed, 2), "paid": round(max(0, paid_rx), 2),
                "member_resp": round(member_resp_rx, 2),
                "deductible_applied": round(deductible_for_rx, 2),
                "rx_tier": drug_result.get("tier_label"),
                "rx_copay": rx_copay, "is_glp1": drug_result.get("is_glp1", False),
                "is_preventive": False, "coverage_type": "rx",
            })
            adjudication_notes.append(
                f"Line {line['line_number']}: {proc_code} — Rx {drug_result.get('tier_label')}: "
                f"Copay ${rx_copay}, CoIns {rx_coinsurance*100:.0f}%, Paid ${max(0, paid_rx):.2f}"
            )
            continue

        # ── Preventive service evaluation ──
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
                _ = 0.0  # member_resp consumed by total tracker

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
                    "allowed": round(allowed, 2), "paid": round(paid, 2),
                    "member_resp": 0.0, "deductible_applied": 0.0,
                    "medicare_rate": None,
                    "cpt_description": svc.get("description", "Preventive Service"),
                    "coverage_type": "preventive", "is_preventive": True,
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
                f"Line {line['line_number']}: {proc_code} - Preventive code but billed as diagnostic. Normal plan benefits apply."
            )

        if is_mec_plan:
            adjudication_notes.append(
                f"Line {line['line_number']}: {proc_code} - DENIED: Not a Covered Benefit (MEC 1 Plan - Preventive Only)"
            )
            processed_lines.append({
                **line,
                "allowed": 0, "paid": 0, "member_resp": billed,
                "deductible_applied": 0, "medicare_rate": None,
                "cpt_description": f"{proc_code} - Not Covered (MEC 1)",
                "coverage_type": claim_type, "is_preventive": False,
                "denial_reason": "Not a Covered Benefit - MEC 1 Plan (Preventive Services Only)",
                "eob_message": "Service denied - Not a covered benefit under MEC 1.",
            })
            member_responsibility += billed
            continue

        code_data = lookup_code_for_claim_type(proc_code, claim_type)

        # ── Benefit Matching ──
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
                "denial_reason": "Service not covered under plan", "medicare_rate": None, "is_preventive": False,
            })
            adjudication_notes.append(f"Line {line['line_number']}: {proc_code} - NOT COVERED")
            member_responsibility += billed
            continue

        if proc_code in plan.get("exclusions", []):
            processed_lines.append({
                **line, "allowed": 0, "paid": 0, "member_resp": billed,
                "denial_reason": "Service excluded from coverage", "medicare_rate": None, "is_preventive": False,
            })
            adjudication_notes.append(f"Line {line['line_number']}: {proc_code} - EXCLUDED")
            member_responsibility += billed
            continue

        # ── Pre-cert Penalty: Required but missing → apply penalty reduction ──
        if benefit.get("prior_auth_required") and not claim.get("prior_auth_number"):
            if preauth_penalty_pct < 1.0 and preauth_penalty_pct > 0:
                precert_penalty_applied = True
                adjudication_notes.append(
                    f"Line {line['line_number']}: {proc_code} — Pre-cert required but not obtained. "
                    f"Penalty: {plan.get('preauth_penalty_pct', 50)}% reduction applied."
                )
            else:
                processed_lines.append({
                    **line, "allowed": 0, "paid": 0, "member_resp": billed,
                    "denial_reason": "Prior authorization required", "medicare_rate": None, "is_preventive": False,
                })
                adjudication_notes.append(f"Line {line['line_number']}: {proc_code} - Prior auth REQUIRED — DENIED")
                member_responsibility += billed
                continue

        # ── Visit Limit Check ──
        visit_category = benefit.get("service_category", "general").lower().replace(" ", "_")
        if visit_limits and visit_category in visit_limits:
            limit_count = visit_limits[visit_category]
            year_key = str(claim_date.year)
            visit_count_doc = await db.visit_counts.find_one(
                {"member_id": claim["member_id"], "category": visit_category, "plan_year": year_key},
                {"_id": 0}
            )
            current_visits = (visit_count_doc or {}).get("count", 0)
            if current_visits >= limit_count:
                processed_lines.append({
                    **line, "allowed": 0, "paid": 0, "member_resp": billed,
                    "denial_reason": f"Visit limit exceeded ({current_visits}/{limit_count} for {visit_category})",
                    "medicare_rate": None, "is_preventive": False,
                })
                adjudication_notes.append(
                    f"Line {line['line_number']}: {proc_code} — Visit limit EXCEEDED ({current_visits}/{limit_count} {visit_category})"
                )
                member_responsibility += billed
                continue

        # ── Rate Calculation ──
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

        # Apply pre-cert penalty to allowed amount
        if precert_penalty_applied:
            allowed = allowed * (1 - preauth_penalty_pct)
            rate_note = (rate_note or "") + f" [Pre-cert penalty: {plan.get('preauth_penalty_pct', 50)}% reduction]"

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
            # ── Visit-Based Copay: Apply copay once per visit category ──
            copay = benefit.get("copay", 0)
            if active_tier and active_tier.get("copay") is not None:
                copay = active_tier["copay"]

            if visit_category in visit_copay_applied:
                copay = 0  # Already charged copay for this visit category
            else:
                visit_copay_applied[visit_category] = True

            coinsurance_pct = benefit.get("coinsurance", 0.2)
            if active_tier and active_tier.get("coinsurance") is not None:
                coinsurance_pct = active_tier["coinsurance"] / 100.0 if active_tier["coinsurance"] > 1 else active_tier["coinsurance"]

            line_deductible = 0
            if benefit.get("deductible_applies", True):
                remaining_ded = max(0, deductible - accumulators["deductible_met"])
                if family_ded_remaining <= 0:
                    remaining_ded = 0
                line_deductible = min(allowed, remaining_ded)
                accumulators["deductible_met"] += line_deductible

            after_deductible = allowed - line_deductible
            coinsurance_amount = after_deductible * coinsurance_pct

            paid = after_deductible - coinsurance_amount - copay
            member_resp_this_line = line_deductible + coinsurance_amount + copay

            remaining_oop = max(0, oop_max - accumulators["oop_met"])
            # Also check family OOP
            if family_oop_met >= oop_max_family:
                remaining_oop = 0
                adjudication_notes.append(f"Line {line['line_number']}: Family OOP MAX reached")

            if member_resp_this_line > remaining_oop and remaining_oop >= 0:
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
            "deductible_applied": round(line_deductible if 'line_deductible' in dir() else 0, 2),
            "copay": round(copay if 'copay' in dir() else 0, 2),
            "coinsurance_amount": round(coinsurance_amount if 'coinsurance_amount' in dir() else 0, 2),
            "medicare_rate": medicare_rate,
            "cpt_description": code_data.get("description", "Unknown") if code_data else "Unknown",
            "work_rvu": code_data.get("work_rvu") if code_data else None,
            "total_rvu": code_data.get("total_rvu") if code_data else None,
            "coverage_type": code_data.get("source", claim_type) if code_data else claim_type,
            "is_preventive": False,
            "network_tier": active_tier.get("tier_name") if active_tier else None,
        })

    # ── Update Accumulators ──
    await db.accumulators.update_one(
        {"member_id": claim["member_id"], "plan_year": str(claim_date.year), "claim_type": claim_type},
        {"$set": accumulators},
        upsert=True
    )

    # ── Update Visit Counts ──
    for cat in visit_copay_applied:
        await db.visit_counts.update_one(
            {"member_id": claim["member_id"], "category": cat, "plan_year": str(claim_date.year)},
            {"$inc": {"count": 1}},
            upsert=True
        )

    # ── COB Secondary Adjustment ──
    if cob_result and cob_result["our_position"] == "secondary" and claim.get("primary_payer_eob"):
        from services.cob_engine import apply_cob_to_claim
        cob_calc = await apply_cob_to_claim(
            {"total_allowed": total_allowed, "total_paid": total_paid},
            cob_result, claim["primary_payer_eob"]
        )
        if cob_calc.get("cob_applied"):
            cob_adjustment = cob_calc.get("adjustment", 0)
            total_paid = cob_calc.get("adjusted_payment", total_paid)
            adjudication_notes.append(cob_calc.get("notes", "COB adjustment applied."))

    result = {
        "status": ClaimStatus.APPROVED.value if total_paid > 0 else ClaimStatus.DENIED.value,
        "total_allowed": round(total_allowed, 2),
        "total_paid": round(total_paid, 2),
        "member_responsibility": round(member_responsibility, 2),
        "service_lines": processed_lines,
        "adjudication_notes": adjudication_notes,
        "plan_version": plan_version,
        "network_status": network_status,
        "cob_applied": bool(cob_result and cob_result.get("has_cob")),
        "cob_position": cob_result["our_position"] if cob_result else None,
        "cob_adjustment": round(cob_adjustment, 2),
        "precert_penalty_applied": precert_penalty_applied,
    }

    # ── Auto Data-Tier Classification ──
    from services.tiering_engine import TIER_1_THRESHOLD, TRIGGER_CPT_CODES
    cpt_codes = [sl.get("cpt_code", "") for sl in claim.get("service_lines", [])]
    has_trigger = any(c in TRIGGER_CPT_CODES for c in cpt_codes)
    has_prior_auth = bool(claim.get("prior_auth_number"))

    if has_trigger or has_prior_auth or total_paid >= TIER_1_THRESHOLD:
        result["data_tier"] = 2
        result["tier_label"] = "Clinical Review"
    else:
        result["data_tier"] = 1
        result["tier_label"] = "Auto-Pilot"

    # ── Stop-Loss auto-flagging ──
    risk = plan.get("risk_management")
    if risk and total_paid > 0:
        specific_limit = risk.get("specific_attachment_point", 0)
        threshold_pct = risk.get("auto_flag_threshold_pct", 50)
        if specific_limit > 0 and total_paid > (specific_limit * threshold_pct / 100):
            result["stop_loss_flag"] = True
            result["data_tier"] = 3
            result["tier_label"] = "Stop-Loss Trigger"
            result["adjudication_notes"].append(
                f"STOP-LOSS FLAG: Claim paid ${total_paid:,.2f} exceeds "
                f"{threshold_pct}% of Specific Attachment Point (${specific_limit:,.2f}). "
                f"Auto-routed to Examiner Queue for review."
            )

    return result
