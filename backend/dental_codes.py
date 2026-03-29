"""
FletchFlow - CDT (Current Dental Terminology) Codes Database
Dental procedure codes with fee schedule and benefit class mappings.
"""

# CDT Codes Database - Organized by ADA procedure categories
CDT_CODES_DATABASE = {
    # Diagnostic
    "D0120": {"description": "Periodic oral evaluation - established patient", "category": "Diagnostic", "benefit_class": "preventive", "fee": 55.00},
    "D0140": {"description": "Limited oral evaluation - problem focused", "category": "Diagnostic", "benefit_class": "preventive", "fee": 75.00},
    "D0145": {"description": "Oral evaluation for a patient under three years of age", "category": "Diagnostic", "benefit_class": "preventive", "fee": 50.00},
    "D0150": {"description": "Comprehensive oral evaluation - new or established patient", "category": "Diagnostic", "benefit_class": "preventive", "fee": 85.00},
    "D0160": {"description": "Detailed and extensive oral evaluation - problem focused", "category": "Diagnostic", "benefit_class": "diagnostic", "fee": 120.00},
    "D0170": {"description": "Re-evaluation - limited, problem focused", "category": "Diagnostic", "benefit_class": "preventive", "fee": 60.00},
    "D0180": {"description": "Comprehensive periodontal evaluation - new or established patient", "category": "Diagnostic", "benefit_class": "preventive", "fee": 95.00},
    # Radiographs
    "D0210": {"description": "Intraoral - complete series of radiographic images", "category": "Radiograph", "benefit_class": "diagnostic", "fee": 145.00},
    "D0220": {"description": "Intraoral - periapical first radiographic image", "category": "Radiograph", "benefit_class": "diagnostic", "fee": 30.00},
    "D0230": {"description": "Intraoral - periapical each additional radiographic image", "category": "Radiograph", "benefit_class": "diagnostic", "fee": 25.00},
    "D0270": {"description": "Bitewing - single radiographic image", "category": "Radiograph", "benefit_class": "diagnostic", "fee": 30.00},
    "D0272": {"description": "Bitewings - two radiographic images", "category": "Radiograph", "benefit_class": "diagnostic", "fee": 50.00},
    "D0274": {"description": "Bitewings - four radiographic images", "category": "Radiograph", "benefit_class": "diagnostic", "fee": 65.00},
    "D0330": {"description": "Panoramic radiographic image", "category": "Radiograph", "benefit_class": "diagnostic", "fee": 120.00},
    "D0340": {"description": "2D cephalometric radiographic image", "category": "Radiograph", "benefit_class": "diagnostic", "fee": 100.00},
    # Preventive
    "D1110": {"description": "Prophylaxis - adult", "category": "Preventive", "benefit_class": "preventive", "fee": 105.00},
    "D1120": {"description": "Prophylaxis - child", "category": "Preventive", "benefit_class": "preventive", "fee": 75.00},
    "D1206": {"description": "Topical application of fluoride varnish", "category": "Preventive", "benefit_class": "preventive", "fee": 38.00},
    "D1208": {"description": "Topical application of fluoride - excluding varnish", "category": "Preventive", "benefit_class": "preventive", "fee": 35.00},
    "D1351": {"description": "Sealant - per tooth", "category": "Preventive", "benefit_class": "preventive", "fee": 48.00},
    "D1354": {"description": "Interim caries arresting medicament application - per tooth", "category": "Preventive", "benefit_class": "preventive", "fee": 25.00},
    "D1510": {"description": "Space maintainer - fixed, unilateral", "category": "Preventive", "benefit_class": "preventive", "fee": 320.00},
    "D1516": {"description": "Space maintainer - fixed, bilateral, maxillary", "category": "Preventive", "benefit_class": "preventive", "fee": 450.00},
    # Restorative
    "D2140": {"description": "Amalgam - one surface, primary or permanent", "category": "Restorative", "benefit_class": "basic", "fee": 155.00},
    "D2150": {"description": "Amalgam - two surfaces, primary or permanent", "category": "Restorative", "benefit_class": "basic", "fee": 195.00},
    "D2160": {"description": "Amalgam - three surfaces, primary or permanent", "category": "Restorative", "benefit_class": "basic", "fee": 240.00},
    "D2161": {"description": "Amalgam - four or more surfaces, primary or permanent", "category": "Restorative", "benefit_class": "basic", "fee": 290.00},
    "D2330": {"description": "Resin-based composite - one surface, anterior", "category": "Restorative", "benefit_class": "basic", "fee": 170.00},
    "D2331": {"description": "Resin-based composite - two surfaces, anterior", "category": "Restorative", "benefit_class": "basic", "fee": 215.00},
    "D2332": {"description": "Resin-based composite - three surfaces, anterior", "category": "Restorative", "benefit_class": "basic", "fee": 265.00},
    "D2335": {"description": "Resin-based composite - four or more surfaces, anterior", "category": "Restorative", "benefit_class": "basic", "fee": 310.00},
    "D2391": {"description": "Resin-based composite - one surface, posterior", "category": "Restorative", "benefit_class": "basic", "fee": 185.00},
    "D2392": {"description": "Resin-based composite - two surfaces, posterior", "category": "Restorative", "benefit_class": "basic", "fee": 240.00},
    "D2393": {"description": "Resin-based composite - three surfaces, posterior", "category": "Restorative", "benefit_class": "basic", "fee": 295.00},
    "D2394": {"description": "Resin-based composite - four or more surfaces, posterior", "category": "Restorative", "benefit_class": "basic", "fee": 345.00},
    # Crowns
    "D2740": {"description": "Crown - porcelain/ceramic substrate", "category": "Crown", "benefit_class": "major", "fee": 1200.00},
    "D2750": {"description": "Crown - porcelain fused to high noble metal", "category": "Crown", "benefit_class": "major", "fee": 1250.00},
    "D2751": {"description": "Crown - porcelain fused to predominantly base metal", "category": "Crown", "benefit_class": "major", "fee": 1100.00},
    "D2752": {"description": "Crown - porcelain fused to noble metal", "category": "Crown", "benefit_class": "major", "fee": 1175.00},
    "D2790": {"description": "Crown - full cast high noble metal", "category": "Crown", "benefit_class": "major", "fee": 1300.00},
    "D2799": {"description": "Provisional crown - further treatment required", "category": "Crown", "benefit_class": "major", "fee": 400.00},
    # Endodontics
    "D3110": {"description": "Pulp cap - direct (excluding final restoration)", "category": "Endodontics", "benefit_class": "basic", "fee": 95.00},
    "D3220": {"description": "Therapeutic pulpotomy (excluding final restoration)", "category": "Endodontics", "benefit_class": "basic", "fee": 195.00},
    "D3310": {"description": "Endodontic therapy, anterior tooth (excluding final restoration)", "category": "Endodontics", "benefit_class": "major", "fee": 780.00},
    "D3320": {"description": "Endodontic therapy, premolar tooth (excluding final restoration)", "category": "Endodontics", "benefit_class": "major", "fee": 900.00},
    "D3330": {"description": "Endodontic therapy, molar tooth (excluding final restoration)", "category": "Endodontics", "benefit_class": "major", "fee": 1100.00},
    "D3346": {"description": "Retreatment of previous root canal therapy - anterior", "category": "Endodontics", "benefit_class": "major", "fee": 950.00},
    "D3348": {"description": "Retreatment of previous root canal therapy - molar", "category": "Endodontics", "benefit_class": "major", "fee": 1250.00},
    # Periodontics
    "D4210": {"description": "Gingivectomy or gingivoplasty - four or more teeth per quadrant", "category": "Periodontics", "benefit_class": "major", "fee": 475.00},
    "D4211": {"description": "Gingivectomy or gingivoplasty - one to three teeth per quadrant", "category": "Periodontics", "benefit_class": "major", "fee": 300.00},
    "D4341": {"description": "Periodontal scaling and root planing - four or more teeth per quadrant", "category": "Periodontics", "benefit_class": "basic", "fee": 275.00},
    "D4342": {"description": "Periodontal scaling and root planing - one to three teeth per quadrant", "category": "Periodontics", "benefit_class": "basic", "fee": 195.00},
    "D4355": {"description": "Full mouth debridement to enable comprehensive evaluation", "category": "Periodontics", "benefit_class": "basic", "fee": 195.00},
    "D4910": {"description": "Periodontal maintenance", "category": "Periodontics", "benefit_class": "preventive", "fee": 165.00},
    # Prosthodontics - Removable
    "D5110": {"description": "Complete denture - maxillary", "category": "Prosthodontics", "benefit_class": "major", "fee": 1800.00},
    "D5120": {"description": "Complete denture - mandibular", "category": "Prosthodontics", "benefit_class": "major", "fee": 1800.00},
    "D5130": {"description": "Immediate denture - maxillary", "category": "Prosthodontics", "benefit_class": "major", "fee": 2000.00},
    "D5211": {"description": "Maxillary partial denture - resin base", "category": "Prosthodontics", "benefit_class": "major", "fee": 1500.00},
    "D5213": {"description": "Maxillary partial denture - cast metal framework with resin base", "category": "Prosthodontics", "benefit_class": "major", "fee": 1900.00},
    "D5214": {"description": "Mandibular partial denture - cast metal framework with resin base", "category": "Prosthodontics", "benefit_class": "major", "fee": 1900.00},
    # Oral Surgery
    "D7140": {"description": "Extraction, erupted tooth or exposed root", "category": "Oral Surgery", "benefit_class": "basic", "fee": 195.00},
    "D7210": {"description": "Extraction, erupted tooth requiring removal of bone and/or sectioning", "category": "Oral Surgery", "benefit_class": "basic", "fee": 310.00},
    "D7220": {"description": "Removal of impacted tooth - soft tissue", "category": "Oral Surgery", "benefit_class": "basic", "fee": 365.00},
    "D7230": {"description": "Removal of impacted tooth - partially bony", "category": "Oral Surgery", "benefit_class": "basic", "fee": 435.00},
    "D7240": {"description": "Removal of impacted tooth - completely bony", "category": "Oral Surgery", "benefit_class": "major", "fee": 525.00},
    "D7250": {"description": "Removal of residual tooth roots (cutting procedure)", "category": "Oral Surgery", "benefit_class": "basic", "fee": 275.00},
    "D7510": {"description": "Incision and drainage of abscess - intraoral soft tissue", "category": "Oral Surgery", "benefit_class": "basic", "fee": 265.00},
    # Orthodontics
    "D8010": {"description": "Limited orthodontic treatment of the primary dentition", "category": "Orthodontics", "benefit_class": "orthodontic", "fee": 2500.00},
    "D8020": {"description": "Limited orthodontic treatment of the transitional dentition", "category": "Orthodontics", "benefit_class": "orthodontic", "fee": 3000.00},
    "D8070": {"description": "Comprehensive orthodontic treatment of the transitional dentition", "category": "Orthodontics", "benefit_class": "orthodontic", "fee": 5500.00},
    "D8080": {"description": "Comprehensive orthodontic treatment of the adolescent dentition", "category": "Orthodontics", "benefit_class": "orthodontic", "fee": 6000.00},
    "D8090": {"description": "Comprehensive orthodontic treatment of the adult dentition", "category": "Orthodontics", "benefit_class": "orthodontic", "fee": 6500.00},
    "D8680": {"description": "Orthodontic retention (removal of appliances, construction and placement of retainer)", "category": "Orthodontics", "benefit_class": "orthodontic", "fee": 400.00},
    # Adjunctive General Services
    "D9110": {"description": "Palliative (emergency) treatment of dental pain - minor procedure", "category": "Adjunctive", "benefit_class": "basic", "fee": 120.00},
    "D9215": {"description": "Local anesthesia in conjunction with operative or surgical procedures", "category": "Adjunctive", "benefit_class": "basic", "fee": 55.00},
    "D9230": {"description": "Inhalation of nitrous oxide/analgesia, anxiolysis", "category": "Adjunctive", "benefit_class": "basic", "fee": 75.00},
    "D9310": {"description": "Consultation - diagnostic service provided by dentist other than requesting dentist", "category": "Adjunctive", "benefit_class": "diagnostic", "fee": 100.00},
    "D9440": {"description": "Office visit - after regularly scheduled hours", "category": "Adjunctive", "benefit_class": "basic", "fee": 85.00},
    "D9986": {"description": "Missed appointment", "category": "Adjunctive", "benefit_class": "not_covered", "fee": 50.00},
}

# Dental benefit class configuration - typical plan structure
DENTAL_BENEFIT_CLASSES = {
    "preventive": {"description": "Preventive & Diagnostic", "typical_coinsurance": 0.0, "annual_max_applies": True},
    "diagnostic": {"description": "Diagnostic Services", "typical_coinsurance": 0.0, "annual_max_applies": True},
    "basic": {"description": "Basic Restorative", "typical_coinsurance": 0.2, "annual_max_applies": True},
    "major": {"description": "Major Restorative", "typical_coinsurance": 0.5, "annual_max_applies": True},
    "orthodontic": {"description": "Orthodontic Services", "typical_coinsurance": 0.5, "annual_max_applies": False},
    "not_covered": {"description": "Not Covered", "typical_coinsurance": 1.0, "annual_max_applies": False},
}


def get_dental_code(code):
    return CDT_CODES_DATABASE.get(code)


def search_dental_codes(query, limit=50):
    results = []
    query_lower = query.lower()
    for code, data in CDT_CODES_DATABASE.items():
        if query_lower in code.lower() or query_lower in data["description"].lower():
            results.append({"code": code, **data})
        if len(results) >= limit:
            break
    return results


def get_dental_codes_by_category(category):
    return [
        {"code": code, **data}
        for code, data in CDT_CODES_DATABASE.items()
        if data["category"] == category
    ]


def calculate_dental_allowed(code, plan_benefit_classes=None):
    cdt = CDT_CODES_DATABASE.get(code)
    if not cdt:
        return None

    benefit_class = cdt["benefit_class"]
    fee = cdt["fee"]

    if plan_benefit_classes and benefit_class in plan_benefit_classes:
        coinsurance = plan_benefit_classes[benefit_class].get("coinsurance", DENTAL_BENEFIT_CLASSES[benefit_class]["typical_coinsurance"])
    else:
        coinsurance = DENTAL_BENEFIT_CLASSES.get(benefit_class, {}).get("typical_coinsurance", 0.2)

    plan_pays = fee * (1 - coinsurance)
    member_pays = fee * coinsurance

    return {
        "fee": fee,
        "benefit_class": benefit_class,
        "coinsurance": coinsurance,
        "plan_pays": round(plan_pays, 2),
        "member_pays": round(member_pays, 2),
    }
