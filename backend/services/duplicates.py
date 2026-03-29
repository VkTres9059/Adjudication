from difflib import SequenceMatcher
from typing import List, Dict
from core.database import db
from models.enums import ClaimStatus, DuplicateType


def calculate_similarity(str1: str, str2: str) -> float:
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


async def detect_duplicates(claim_data: dict) -> List[Dict]:
    duplicates = []

    query = {
        "member_id": claim_data["member_id"],
        "status": {"$nin": [ClaimStatus.DUPLICATE.value]},
    }

    existing_claims = await db.claims.find(query, {"_id": 0}).to_list(1000)

    for existing in existing_claims:
        if existing["id"] == claim_data.get("id"):
            continue

        match_reasons = []
        match_score = 0

        is_exact = (
            existing["member_id"] == claim_data["member_id"] and
            existing["provider_npi"] == claim_data["provider_npi"] and
            existing["service_date_from"] == claim_data["service_date_from"] and
            abs(existing["total_billed"] - claim_data["total_billed"]) < 0.01
        )

        if is_exact:
            existing_codes = set(line.get("cpt_code", "") for line in existing.get("service_lines", []))
            new_codes = set(line.get("cpt_code", "") for line in claim_data.get("service_lines", []))

            if existing_codes == new_codes:
                match_score = 1.0
                match_reasons.append("Exact match: same member, provider, date, amount, and services")
                duplicates.append({
                    "matched_claim_id": existing["id"],
                    "matched_claim_number": existing["claim_number"],
                    "duplicate_type": DuplicateType.EXACT.value,
                    "match_score": match_score,
                    "match_reasons": match_reasons
                })
                continue

        same_member = existing["member_id"] == claim_data["member_id"]
        same_provider = existing["provider_npi"] == claim_data["provider_npi"]

        date_overlap = False
        try:
            from datetime import datetime
            ex_start = datetime.fromisoformat(existing["service_date_from"])
            ex_end = datetime.fromisoformat(existing["service_date_to"])
            new_start = datetime.fromisoformat(claim_data["service_date_from"])
            new_end = datetime.fromisoformat(claim_data["service_date_to"])
            date_overlap = (ex_start <= new_end) and (new_start <= ex_end)
        except (ValueError, KeyError):
            pass

        amount_similar = False
        if existing["total_billed"] > 0:
            diff_pct = abs(existing["total_billed"] - claim_data["total_billed"]) / existing["total_billed"]
            amount_similar = diff_pct < 0.1

        existing_codes = set(line.get("cpt_code", "") for line in existing.get("service_lines", []))
        new_codes = set(line.get("cpt_code", "") for line in claim_data.get("service_lines", []))
        code_overlap = len(existing_codes & new_codes) / max(len(existing_codes | new_codes), 1)

        if same_member and same_provider and date_overlap:
            if amount_similar:
                match_score += 0.3
                match_reasons.append("Similar billed amounts (within 10%)")
            if code_overlap > 0.5:
                match_score += 0.3
                match_reasons.append(f"Service code overlap: {code_overlap*100:.0f}%")

            match_score += 0.2
            match_reasons.append("Same member, provider, overlapping dates")

            if match_score >= 0.5:
                duplicates.append({
                    "matched_claim_id": existing["id"],
                    "matched_claim_number": existing["claim_number"],
                    "duplicate_type": DuplicateType.NEAR.value,
                    "match_score": match_score,
                    "match_reasons": match_reasons
                })

        elif same_member and date_overlap and code_overlap > 0:
            match_reasons.append(f"Line-level overlap: {code_overlap*100:.0f}% service codes match")
            duplicates.append({
                "matched_claim_id": existing["id"],
                "matched_claim_number": existing["claim_number"],
                "duplicate_type": DuplicateType.LINE_LEVEL.value,
                "match_score": code_overlap * 0.5,
                "match_reasons": match_reasons
            })

    return sorted(duplicates, key=lambda x: x["match_score"], reverse=True)
