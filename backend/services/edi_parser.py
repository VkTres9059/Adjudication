from datetime import datetime, timezone
import uuid
from core.database import db
from models.schemas import MemberCreate, ServiceLine, ClaimCreate
from models.enums import ClaimType
from services.claims import process_new_claim


def _parse_x12_date(date_str):
    """Parse X12 date format CCYYMMDD to ISO date string."""
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


async def save_834_member(member_data):
    """Save a member parsed from 834."""
    member_id = member_data.get("member_id", "")
    if not member_id:
        raise ValueError("Missing member_id")
    existing = await db.members.find_one({"member_id": member_id})
    now = datetime.now(timezone.utc).isoformat()
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
        "status": "active",
        "created_at": existing["created_at"] if existing else now,
        "updated_at": now
    }

    action = "member_updated" if existing else "member_added"
    if existing:
        old_term = existing.get("termination_date")
        new_term = doc.get("termination_date")
        if new_term and not old_term:
            action = "member_terminated"
        elif new_term and old_term and new_term < old_term:
            action = "member_retro_terminated"
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
        upsert=True
    )

    await db.member_audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "member_id": member_id,
        "action": action,
        "user_id": "system_834",
        "details": {"source": "834_feed", "effective_date": doc["effective_date"], "termination_date": doc.get("termination_date")},
        "timestamp": now,
    })


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
            "diagnosis_codes": [],
            "revenue_code": None,
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
        "prior_auth_number": None,
        "source": "edi_837",
        "external_claim_id": None,
    }

    await process_new_claim(claim_dict, svc_lines, user)
