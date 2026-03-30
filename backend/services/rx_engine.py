"""
Rx Rules Engine — Formulary tiers, generic vs brand logic, GLP-1 handling.
Supports tiered drug classification and cost-sharing rules per plan.
"""

# Standard formulary tiers
FORMULARY_TIERS = {
    "tier1_generic": {"label": "Tier 1 — Generic", "copay": 10, "coinsurance": 0},
    "tier2_preferred_brand": {"label": "Tier 2 — Preferred Brand", "copay": 35, "coinsurance": 0},
    "tier3_non_preferred": {"label": "Tier 3 — Non-Preferred Brand", "copay": 60, "coinsurance": 0},
    "tier4_specialty": {"label": "Tier 4 — Specialty", "copay": 0, "coinsurance": 25},
    "tier5_preventive": {"label": "Tier 5 — Preventive Rx", "copay": 0, "coinsurance": 0},
}

# GLP-1 drugs — high-cost specialty requiring special authorization
GLP1_DRUGS = {
    "J3490": "Ozempic (semaglutide)",
    "J3591": "Wegovy (semaglutide)",
    "J1952": "Mounjaro (tirzepatide)",
    "J3490Z": "Zepbound (tirzepatide)",
    "S0189": "Trulicity (dulaglutide)",
    "J1951": "Saxenda (liraglutide)",
}

# NDC-to-tier mapping (simplified — in production, this maps to a formulary DB)
DRUG_CLASSIFICATIONS = {
    "generic": "tier1_generic",
    "preferred_brand": "tier2_preferred_brand",
    "non_preferred_brand": "tier3_non_preferred",
    "specialty": "tier4_specialty",
    "preventive": "tier5_preventive",
    "glp1": "tier4_specialty",
}


def classify_drug(ndc_code: str = "", drug_name: str = "", hcpcs_code: str = "") -> dict:
    """Classify a drug into formulary tier."""
    # Check GLP-1
    if hcpcs_code in GLP1_DRUGS:
        return {
            "tier": "tier4_specialty",
            "tier_label": "Tier 4 — Specialty (GLP-1)",
            "drug_name": GLP1_DRUGS[hcpcs_code],
            "is_glp1": True,
            "requires_prior_auth": True,
            "step_therapy_required": True,
            "quantity_limit": True,
            "notes": "GLP-1 medication — requires prior authorization, step therapy, and quantity limits",
        }

    name_lower = (drug_name or "").lower()

    # Simple classification by name patterns
    if any(kw in name_lower for kw in ["generic", "acetaminophen", "ibuprofen", "metformin", "lisinopril", "atorvastatin"]):
        tier = "tier1_generic"
    elif any(kw in name_lower for kw in ["humira", "enbrel", "remicade", "keytruda", "opdivo"]):
        tier = "tier4_specialty"
    elif any(kw in name_lower for kw in ["lipitor", "crestor", "nexium", "advair"]):
        tier = "tier2_preferred_brand"
    else:
        tier = "tier2_preferred_brand"  # Default to preferred brand

    tier_info = FORMULARY_TIERS.get(tier, FORMULARY_TIERS["tier2_preferred_brand"])
    return {
        "tier": tier,
        "tier_label": tier_info["label"],
        "drug_name": drug_name or "Unknown",
        "is_glp1": False,
        "requires_prior_auth": tier == "tier4_specialty",
        "step_therapy_required": False,
        "quantity_limit": tier == "tier4_specialty",
        "copay": tier_info["copay"],
        "coinsurance": tier_info["coinsurance"],
    }


def apply_rx_rules(plan: dict, drug_classification: dict) -> dict:
    """Apply plan-specific Rx rules to a drug classification."""
    rx_rules = plan.get("rx_rules") or {}
    if not rx_rules.get("enabled", True):
        return drug_classification

    result = {**drug_classification}

    # GLP-1 specific rules
    if result["is_glp1"]:
        glp1_policy = rx_rules.get("glp1_policy", "prior_auth_required")
        if glp1_policy == "not_covered":
            result["covered"] = False
            result["notes"] = "GLP-1 medications excluded from plan formulary"
            return result
        elif glp1_policy == "covered_with_conditions":
            result["requires_prior_auth"] = True
            result["step_therapy_required"] = True
            result["notes"] = "GLP-1 covered with prior auth, step therapy, and BMI > 30 requirement"

    # Override copay from plan rules
    tier = result["tier"]
    plan_tier_overrides = rx_rules.get("tier_overrides") or {}
    if tier in plan_tier_overrides:
        override = plan_tier_overrides[tier]
        result["copay"] = override.get("copay", result.get("copay", 0))
        result["coinsurance"] = override.get("coinsurance", result.get("coinsurance", 0))

    # Mandatory generic substitution
    if rx_rules.get("mandatory_generic_substitution", True):
        if result["tier"] in ("tier2_preferred_brand", "tier3_non_preferred"):
            result["generic_substitution_note"] = "Mandatory generic substitution applies — generic equivalent required unless medically necessary"

    result["covered"] = True
    result["deductible_applies"] = rx_rules.get("deductible_applies_to_rx", False)
    return result


def get_rx_rules_template() -> dict:
    """Return default Rx rules template for plan configuration."""
    return {
        "enabled": True,
        "formulary_tiers": FORMULARY_TIERS,
        "glp1_policy": "prior_auth_required",  # not_covered, prior_auth_required, covered_with_conditions
        "mandatory_generic_substitution": True,
        "deductible_applies_to_rx": False,
        "mail_order_discount_pct": 10,
        "max_days_supply": 90,
        "specialty_pharmacy_required": True,
        "tier_overrides": {},
    }
