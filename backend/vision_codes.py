"""
FletchFlow - Vision Service Codes Database
Vision procedure codes with fee schedule for exam and materials benefits.
"""

# Vision Codes Database - Exam and Materials
VISION_CODES_DATABASE = {
    # Eye Exams
    "92002": {"description": "Ophthalmological services: medical examination - intermediate, new patient", "category": "Eye Exam", "benefit_class": "exam", "fee": 125.00},
    "92004": {"description": "Ophthalmological services: medical examination - comprehensive, new patient", "category": "Eye Exam", "benefit_class": "exam", "fee": 200.00},
    "92012": {"description": "Ophthalmological services: medical examination - intermediate, established patient", "category": "Eye Exam", "benefit_class": "exam", "fee": 100.00},
    "92014": {"description": "Ophthalmological services: medical examination - comprehensive, established patient", "category": "Eye Exam", "benefit_class": "exam", "fee": 175.00},
    "99213V": {"description": "Office visit - established patient, vision-related", "category": "Eye Exam", "benefit_class": "exam", "fee": 115.00},
    "99214V": {"description": "Office visit - established patient, moderate complexity, vision-related", "category": "Eye Exam", "benefit_class": "exam", "fee": 155.00},
    # Refraction
    "92015": {"description": "Determination of refractive state", "category": "Refraction", "benefit_class": "exam", "fee": 50.00},
    # Contact Lens Services
    "92310": {"description": "Prescription of optical and physical characteristics of contact lens - corneal lens, both eyes", "category": "Contact Lens", "benefit_class": "contact_lens", "fee": 85.00},
    "92311": {"description": "Prescription of optical and physical characteristics of contact lens - corneal lens, one eye", "category": "Contact Lens", "benefit_class": "contact_lens", "fee": 55.00},
    "92312": {"description": "Prescription of contact lens - corneal, both eyes, modified", "category": "Contact Lens", "benefit_class": "contact_lens", "fee": 95.00},
    "92313": {"description": "Prescription of optical and physical characteristics of contact lens - corneoscleral lens", "category": "Contact Lens", "benefit_class": "contact_lens", "fee": 110.00},
    "92314": {"description": "Prescription of optical and physical characteristics of contact lens - includes fitting", "category": "Contact Lens", "benefit_class": "contact_lens", "fee": 75.00},
    # Contact Lens Materials
    "V2500": {"description": "Contact lens, PMMA, spherical, per lens", "category": "Contact Lens Materials", "benefit_class": "contact_lens", "fee": 60.00},
    "V2501": {"description": "Contact lens, PMMA, toric or prism ballast, per lens", "category": "Contact Lens Materials", "benefit_class": "contact_lens", "fee": 85.00},
    "V2510": {"description": "Contact lens, gas permeable, spherical, per lens", "category": "Contact Lens Materials", "benefit_class": "contact_lens", "fee": 95.00},
    "V2511": {"description": "Contact lens, gas permeable, toric, prism ballast, per lens", "category": "Contact Lens Materials", "benefit_class": "contact_lens", "fee": 120.00},
    "V2520": {"description": "Contact lens, hydrophilic, spherical, per lens", "category": "Contact Lens Materials", "benefit_class": "contact_lens", "fee": 45.00},
    "V2521": {"description": "Contact lens, hydrophilic, toric, or prism ballast, per lens", "category": "Contact Lens Materials", "benefit_class": "contact_lens", "fee": 65.00},
    "V2599": {"description": "Contact lens, other type", "category": "Contact Lens Materials", "benefit_class": "contact_lens", "fee": 75.00},
    # Spectacle Lenses
    "V2100": {"description": "Sphere, single vision, plano to plus or minus 4.00", "category": "Lenses", "benefit_class": "materials", "fee": 55.00},
    "V2101": {"description": "Sphere, single vision, plus or minus 4.12 to plus or minus 7.00", "category": "Lenses", "benefit_class": "materials", "fee": 70.00},
    "V2102": {"description": "Sphere, single vision, plus or minus 7.12 to plus or minus 20.00", "category": "Lenses", "benefit_class": "materials", "fee": 85.00},
    "V2200": {"description": "Sphere, bifocal, plano to plus or minus 4.00", "category": "Lenses", "benefit_class": "materials", "fee": 80.00},
    "V2201": {"description": "Sphere, bifocal, plus or minus 4.12 to plus or minus 7.00", "category": "Lenses", "benefit_class": "materials", "fee": 100.00},
    "V2300": {"description": "Sphere, trifocal, plano to plus or minus 4.00", "category": "Lenses", "benefit_class": "materials", "fee": 110.00},
    "V2301": {"description": "Sphere, trifocal, plus or minus 4.12 to plus or minus 7.00", "category": "Lenses", "benefit_class": "materials", "fee": 130.00},
    "V2781": {"description": "Progressive lens, per lens", "category": "Lenses", "benefit_class": "materials", "fee": 95.00},
    # Lens Options/Add-ons
    "V2744": {"description": "Tint, photochromatic lens", "category": "Lens Options", "benefit_class": "materials", "fee": 30.00},
    "V2750": {"description": "Anti-reflective coating, per lens", "category": "Lens Options", "benefit_class": "materials", "fee": 45.00},
    "V2755": {"description": "UV lens, per lens", "category": "Lens Options", "benefit_class": "materials", "fee": 15.00},
    "V2760": {"description": "Scratch resistant coating, per lens", "category": "Lens Options", "benefit_class": "materials", "fee": 20.00},
    "V2761": {"description": "Mirror coating, per lens", "category": "Lens Options", "benefit_class": "materials", "fee": 25.00},
    "V2762": {"description": "Polarization, per lens", "category": "Lens Options", "benefit_class": "materials", "fee": 40.00},
    # Frames
    "V2020": {"description": "Frames, purchases new", "category": "Frames", "benefit_class": "materials", "fee": 175.00},
    "V2025": {"description": "Deluxe frame", "category": "Frames", "benefit_class": "materials", "fee": 225.00},
    # Special Procedures
    "92081": {"description": "Visual field examination, unilateral or bilateral, with interpretation and report", "category": "Special Procedures", "benefit_class": "medical_eye", "fee": 75.00},
    "92082": {"description": "Visual field examination, unilateral or bilateral, with interpretation and report, intermediate", "category": "Special Procedures", "benefit_class": "medical_eye", "fee": 95.00},
    "92083": {"description": "Visual field examination, unilateral or bilateral, with interpretation and report, extended", "category": "Special Procedures", "benefit_class": "medical_eye", "fee": 120.00},
    "92132": {"description": "Scanning computerized ophthalmic diagnostic imaging, anterior segment", "category": "Special Procedures", "benefit_class": "medical_eye", "fee": 65.00},
    "92133": {"description": "Scanning computerized ophthalmic diagnostic imaging, posterior segment - optic nerve", "category": "Special Procedures", "benefit_class": "medical_eye", "fee": 75.00},
    "92134": {"description": "Scanning computerized ophthalmic diagnostic imaging, posterior segment - retina", "category": "Special Procedures", "benefit_class": "medical_eye", "fee": 75.00},
    "92250": {"description": "Fundus photography with interpretation and report", "category": "Special Procedures", "benefit_class": "medical_eye", "fee": 85.00},
    # Low Vision
    "92354": {"description": "Special spectacle mounted low vision aids, telescopes, per lens", "category": "Low Vision", "benefit_class": "low_vision", "fee": 350.00},
    "92358": {"description": "Prosthetic device for aphakia, temporary or permanent", "category": "Low Vision", "benefit_class": "low_vision", "fee": 450.00},
}

# Vision benefit class configuration
VISION_BENEFIT_CLASSES = {
    "exam": {"description": "Routine Eye Exam", "typical_copay": 15.00, "frequency": "once per 12 months"},
    "materials": {"description": "Lenses & Frames", "typical_allowance": 175.00, "frequency": "once per 24 months"},
    "contact_lens": {"description": "Contact Lenses (in lieu of glasses)", "typical_allowance": 150.00, "frequency": "once per 12 months"},
    "medical_eye": {"description": "Medical Eye Services", "typical_coinsurance": 0.2, "frequency": "as needed"},
    "low_vision": {"description": "Low Vision Services", "typical_coinsurance": 0.25, "frequency": "as needed"},
}


def get_vision_code(code):
    return VISION_CODES_DATABASE.get(code)


def search_vision_codes(query, limit=50):
    results = []
    query_lower = query.lower()
    for code, data in VISION_CODES_DATABASE.items():
        if query_lower in code.lower() or query_lower in data["description"].lower():
            results.append({"code": code, **data})
        if len(results) >= limit:
            break
    return results


def get_vision_codes_by_category(category):
    return [
        {"code": code, **data}
        for code, data in VISION_CODES_DATABASE.items()
        if data["category"] == category
    ]


def calculate_vision_allowed(code, plan_config=None):
    vision = VISION_CODES_DATABASE.get(code)
    if not vision:
        return None

    benefit_class = vision["benefit_class"]
    fee = vision["fee"]

    if benefit_class == "exam":
        copay = (plan_config or {}).get("exam_copay", 15.00)
        plan_pays = max(0, fee - copay)
        member_pays = copay
    elif benefit_class in ("materials", "contact_lens"):
        allowance = (plan_config or {}).get(f"{benefit_class}_allowance", VISION_BENEFIT_CLASSES[benefit_class].get("typical_allowance", 150.00))
        plan_pays = min(fee, allowance)
        member_pays = max(0, fee - allowance)
    elif benefit_class == "medical_eye":
        coinsurance = (plan_config or {}).get("medical_coinsurance", 0.2)
        plan_pays = fee * (1 - coinsurance)
        member_pays = fee * coinsurance
    else:
        coinsurance = 0.25
        plan_pays = fee * (1 - coinsurance)
        member_pays = fee * coinsurance

    return {
        "fee": fee,
        "benefit_class": benefit_class,
        "plan_pays": round(plan_pays, 2),
        "member_pays": round(member_pays, 2),
    }
