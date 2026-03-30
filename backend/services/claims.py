from datetime import datetime, timezone, timedelta
import uuid
from core.database import db
from models.enums import ClaimStatus
from services.adjudication import adjudicate_claim
from services.duplicates import detect_duplicates
from services.examiner import auto_assign_examiner


async def process_new_claim(claim_data_dict: dict, service_lines_dicts: list, user: dict) -> dict:
    """Core claim processing logic used by both REST endpoint and EDI parser.
    
    claim_data_dict: dict with keys matching ClaimCreate fields (claim_type already a string value)
    service_lines_dicts: list of dicts for each service line
    user: authenticated user dict
    Returns: the saved claim document (without _id, created_by)
    """
    member = await db.members.find_one({"member_id": claim_data_dict["member_id"]}, {"_id": 0})

    claim_id = str(uuid.uuid4())
    claim_number = f"CLM{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    if not member:
        eligibility_deadline = (datetime.now(timezone.utc) + timedelta(hours=72)).isoformat()
        claim_doc = {
            "id": claim_id,
            "claim_number": claim_number,
            **claim_data_dict,
            "service_lines": service_lines_dicts,
            "total_allowed": 0,
            "total_paid": 0,
            "member_responsibility": claim_data_dict["total_billed"],
            "status": ClaimStatus.PENDING_ELIGIBILITY.value,
            "duplicate_info": None,
            "adjudication_notes": [
                f"PENDING ELIGIBILITY: Member {claim_data_dict['member_id']} not found in census. Claim held for 72 hours pending 834 feed update. Deadline: {eligibility_deadline}"
            ],
            "created_at": now,
            "created_by": user["id"],
            "adjudicated_at": None,
            "eligibility_deadline": eligibility_deadline,
        }
        await db.claims.insert_one(claim_doc)

        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action": "claim_pending_eligibility",
            "user_id": user["id"],
            "details": {"claim_id": claim_id, "member_id": claim_data_dict["member_id"], "deadline": eligibility_deadline},
            "timestamp": now
        })

        result = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
        return result

    plan = await db.plans.find_one({"id": member["plan_id"]}, {"_id": 0})
    if not plan:
        return None

    # ── Hour Bank Gatekeeper ──
    # If plan has an eligibility_threshold, check hour bank before adjudicating
    eligibility_threshold = plan.get("eligibility_threshold", 0)
    eligibility_source = "standard_hours"
    if eligibility_threshold > 0:
        bank = await db.hour_bank.find_one({"member_id": member["member_id"]}, {"_id": 0})
        cur = float(bank.get("current_balance", 0)) if bank else 0.0
        res = float(bank.get("reserve_balance", 0)) if bank else 0.0
        total = cur + res
        if bank:
            eligibility_source = bank.get("eligibility_source", "standard_hours")

        if total < eligibility_threshold and member.get("status") == "termed_insufficient_hours":
            # Short on hours → route to examiner queue with Eligibility Hold
            claim_doc = {
                "id": claim_id,
                "claim_number": claim_number,
                **claim_data_dict,
                "service_lines": service_lines_dicts,
                "total_allowed": 0,
                "total_paid": 0,
                "member_responsibility": claim_data_dict["total_billed"],
                "status": ClaimStatus.PENDING_REVIEW.value,
                "duplicate_info": None,
                "adjudication_notes": [
                    f"ELIGIBILITY HOLD: Member {claim_data_dict['member_id']} has {total:.1f} hrs (threshold: {eligibility_threshold} hrs). "
                    f"Coverage suspended — routed to examiner queue. Bridge payment or additional hours required."
                ],
                "eligibility_source": "insufficient",
                "created_at": now,
                "created_by": user["id"],
                "adjudicated_at": None,
            }
            assignment = await auto_assign_examiner(claim_data_dict.get("total_billed", 0))
            if assignment:
                claim_doc.update(assignment)
                claim_doc["adjudication_notes"].append(
                    f"AUTO-ASSIGNED to {assignment.get('assigned_to_name', 'Unknown')} for eligibility review."
                )
            await db.claims.insert_one(claim_doc)
            await db.audit_logs.insert_one({
                "id": str(uuid.uuid4()),
                "action": "claim_eligibility_hold",
                "user_id": user["id"],
                "details": {"claim_id": claim_id, "member_id": claim_data_dict["member_id"], "balance": total, "threshold": eligibility_threshold},
                "timestamp": now
            })
            result = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
            return result

    claim_doc = {
        "id": claim_id,
        "claim_number": claim_number,
        **claim_data_dict,
        "service_lines": service_lines_dicts,
        "total_allowed": 0,
        "total_paid": 0,
        "member_responsibility": claim_data_dict["total_billed"],
        "status": ClaimStatus.PENDING.value,
        "duplicate_info": None,
        "adjudication_notes": [],
        "eligibility_source": eligibility_source,
        "created_at": now,
        "created_by": user["id"],
        "adjudicated_at": None
    }

    duplicates = await detect_duplicates(claim_doc)

    if duplicates:
        top_dup = duplicates[0]
        claim_doc["duplicate_info"] = top_dup

        if top_dup["match_score"] >= 0.95:
            claim_doc["status"] = ClaimStatus.DUPLICATE.value
            claim_doc["adjudication_notes"].append(f"AUTO-DENIED: Exact duplicate of {top_dup['matched_claim_number']}")
        else:
            claim_doc["status"] = ClaimStatus.PENDED.value
            claim_doc["adjudication_notes"].append(f"PENDED: Potential duplicate of {top_dup['matched_claim_number']} (Score: {top_dup['match_score']:.0%})")

        for dup in duplicates:
            alert_doc = {
                "id": str(uuid.uuid4()),
                "claim_id": claim_id,
                "claim_number": claim_number,
                "duplicate_type": dup["duplicate_type"],
                "matched_claim_id": dup["matched_claim_id"],
                "matched_claim_number": dup["matched_claim_number"],
                "match_score": dup["match_score"],
                "match_reasons": dup["match_reasons"],
                "status": "pending",
                "reviewed_by": None,
                "reviewed_at": None,
                "created_at": now
            }
            await db.duplicate_alerts.insert_one(alert_doc)
    else:
        adjudication_result = await adjudicate_claim(claim_doc, plan, member)
        claim_doc.update(adjudication_result)
        claim_doc["adjudicated_at"] = now

        # ── COB Pend: If secondary payer waiting for primary EOB ──
        if adjudication_result.get("cob_status") == "awaiting_primary_eob":
            claim_doc["status"] = "pended_cob"
            claim_doc["adjudication_notes"] = claim_doc.get("adjudication_notes", []) + [
                "PENDED COB: Claim held pending primary payer EOB."
            ]
            await db.claims.insert_one(claim_doc)
            await db.audit_logs.insert_one({
                "id": str(uuid.uuid4()), "action": "claim_pended_cob",
                "user_id": user["id"],
                "details": {"claim_id": claim_id, "claim_number": claim_number},
                "timestamp": now
            })
            result = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
            return result

        gateway_doc = await db.settings.find_one({"key": "adjudication_gateway"}, {"_id": 0})
        gateway = gateway_doc.get("value", {}) if gateway_doc else {}
        gateway_enabled = gateway.get("enabled", True)

        if gateway_enabled:
            tier1_limit = gateway.get("tier1_auto_pilot_limit", 500.0)
            tier2_limit = gateway.get("tier2_audit_hold_limit", 2500.0)
            total_paid_amount = claim_doc.get("total_paid", 0)
            total_billed_amount = claim_doc.get("total_billed", 0)
            check_amount = max(total_paid_amount, total_billed_amount)

            if check_amount <= tier1_limit:
                claim_doc["tier_level"] = 1
                claim_doc["adjudication_notes"] = claim_doc.get("adjudication_notes", []) + [
                    f"TIER 1 (Auto-Pilot): ${check_amount:.2f} within ${tier1_limit:.2f} threshold."
                ]
                # ── Auto-Queue Tier 1 to Payment ──
                claim_doc["payment_ready"] = True
                claim_doc["adjudication_notes"] = claim_doc.get("adjudication_notes", []) + [
                    "AUTO-QUEUE: Tier 1 claim queued for payment processing."
                ]
            elif check_amount <= tier2_limit:
                claim_doc["tier_level"] = 2
                claim_doc["audit_flag"] = "post_payment_audit"
                claim_doc["adjudication_notes"] = claim_doc.get("adjudication_notes", []) + [
                    f"TIER 2 (Audit Hold): ${check_amount:.2f} flagged for Post-Payment Audit (threshold: ${tier1_limit:.2f}-${tier2_limit:.2f})."
                ]
            else:
                claim_doc["tier_level"] = 3
                claim_doc["status"] = ClaimStatus.PENDING_REVIEW.value
                claim_doc["adjudication_notes"] = claim_doc.get("adjudication_notes", []) + [
                    f"TIER 3 (Hard Hold): ${check_amount:.2f} exceeds ${tier2_limit:.2f} threshold. Requires examiner review and digital signature."
                ]
                assignment = await auto_assign_examiner(check_amount)
                if assignment:
                    claim_doc.update(assignment)
                    claim_doc["adjudication_notes"] = claim_doc.get("adjudication_notes", []) + [
                        f"AUTO-ASSIGNED to {assignment.get('assigned_to_name', 'Unknown')} ({'Senior' if check_amount >= 5000 else 'Junior'} Examiner)."
                    ]

    await db.claims.insert_one(claim_doc)

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "claim_created",
        "user_id": user["id"],
        "details": {"claim_id": claim_id, "claim_number": claim_number, "status": claim_doc["status"]},
        "timestamp": now
    })

    result = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
    return result
