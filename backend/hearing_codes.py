"""
FletchFlow - Hearing Service Codes Database
Audiological and hearing aid procedure codes with fee schedule.
"""

# Hearing Codes Database
HEARING_CODES_DATABASE = {
    # Audiometric Testing
    "92552": {"description": "Pure tone audiometry (threshold); air only", "category": "Audiometric Testing", "benefit_class": "diagnostic", "fee": 45.00},
    "92553": {"description": "Pure tone audiometry (threshold); air and bone", "category": "Audiometric Testing", "benefit_class": "diagnostic", "fee": 55.00},
    "92555": {"description": "Speech audiometry threshold", "category": "Audiometric Testing", "benefit_class": "diagnostic", "fee": 40.00},
    "92556": {"description": "Speech audiometry threshold; with speech recognition", "category": "Audiometric Testing", "benefit_class": "diagnostic", "fee": 55.00},
    "92557": {"description": "Comprehensive audiometry threshold evaluation and speech recognition", "category": "Audiometric Testing", "benefit_class": "diagnostic", "fee": 80.00},
    "92567": {"description": "Tympanometry (impedance testing)", "category": "Audiometric Testing", "benefit_class": "diagnostic", "fee": 35.00},
    "92568": {"description": "Acoustic reflex testing, threshold", "category": "Audiometric Testing", "benefit_class": "diagnostic", "fee": 40.00},
    "92570": {"description": "Acoustic immittance testing, includes tympanometry, acoustic reflex threshold, and decay", "category": "Audiometric Testing", "benefit_class": "diagnostic", "fee": 55.00},
    "92579": {"description": "Visual reinforcement audiometry (VRA)", "category": "Audiometric Testing", "benefit_class": "diagnostic", "fee": 65.00},
    "92582": {"description": "Conditioning play audiometry", "category": "Audiometric Testing", "benefit_class": "diagnostic", "fee": 60.00},
    "92583": {"description": "Select picture audiometry", "category": "Audiometric Testing", "benefit_class": "diagnostic", "fee": 55.00},
    "92588": {"description": "Distortion product evoked otoacoustic emissions; comprehensive diagnostic evaluation", "category": "Audiometric Testing", "benefit_class": "diagnostic", "fee": 75.00},
    # Advanced Diagnostic
    "92585": {"description": "Auditory evoked potentials for evoked response audiometry and/or testing of central auditory function", "category": "Advanced Diagnostic", "benefit_class": "diagnostic", "fee": 200.00},
    "92586": {"description": "Auditory evoked potentials for evoked response audiometry; limited", "category": "Advanced Diagnostic", "benefit_class": "diagnostic", "fee": 150.00},
    "92587": {"description": "Distortion product evoked otoacoustic emissions; limited evaluation", "category": "Advanced Diagnostic", "benefit_class": "diagnostic", "fee": 55.00},
    "92590": {"description": "Hearing aid examination and selection; monaural", "category": "Advanced Diagnostic", "benefit_class": "hearing_aid_service", "fee": 75.00},
    "92591": {"description": "Hearing aid examination and selection; binaural", "category": "Advanced Diagnostic", "benefit_class": "hearing_aid_service", "fee": 125.00},
    # Hearing Aid Services
    "92592": {"description": "Hearing aid check; monaural", "category": "Hearing Aid Service", "benefit_class": "hearing_aid_service", "fee": 45.00},
    "92593": {"description": "Hearing aid check; binaural", "category": "Hearing Aid Service", "benefit_class": "hearing_aid_service", "fee": 65.00},
    "92594": {"description": "Electroacoustic evaluation for hearing aid; monaural", "category": "Hearing Aid Service", "benefit_class": "hearing_aid_service", "fee": 50.00},
    "92595": {"description": "Electroacoustic evaluation for hearing aid; binaural", "category": "Hearing Aid Service", "benefit_class": "hearing_aid_service", "fee": 75.00},
    "92596": {"description": "Ear protector attenuation measurements", "category": "Hearing Aid Service", "benefit_class": "hearing_aid_service", "fee": 40.00},
    # Hearing Aid Devices
    "V5008": {"description": "Hearing screening", "category": "Hearing Aid Device", "benefit_class": "diagnostic", "fee": 30.00},
    "V5010": {"description": "Assessment for hearing aid", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_service", "fee": 75.00},
    "V5011": {"description": "Fitting/orientation/checking of hearing aid", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_service", "fee": 85.00},
    "V5014": {"description": "Repair/modification of a hearing aid", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_service", "fee": 95.00},
    "V5020": {"description": "CROS hearing aid", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 1200.00},
    "V5030": {"description": "Hearing aid, monaural, body worn, air conduction", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 800.00},
    "V5040": {"description": "Hearing aid, monaural, body worn, bone conduction", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 900.00},
    "V5050": {"description": "Hearing aid, monaural, in the ear", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 1500.00},
    "V5060": {"description": "Hearing aid, monaural, behind the ear", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 1800.00},
    "V5070": {"description": "Glasses, air conduction", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 1100.00},
    "V5090": {"description": "Hearing aid, monaural, digital/programmable", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 2500.00},
    "V5095": {"description": "Semi-implantable middle ear hearing prosthesis", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 8000.00},
    "V5100": {"description": "Hearing aid, bilateral, body worn", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 1500.00},
    "V5110": {"description": "Dispensing fee, unspecified hearing aid", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_service", "fee": 200.00},
    "V5120": {"description": "Binaural, body", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 1600.00},
    "V5130": {"description": "Binaural, in the ear", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 3000.00},
    "V5140": {"description": "Binaural, behind the ear", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 3600.00},
    "V5160": {"description": "Dispensing fee, binaural", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_service", "fee": 350.00},
    "V5170": {"description": "Hearing aid, CROS, in the ear", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 1400.00},
    "V5180": {"description": "Hearing aid, CROS, behind the ear", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 1600.00},
    "V5190": {"description": "Hearing aid, CROS, glasses", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 1300.00},
    "V5200": {"description": "Dispensing fee, CROS", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_service", "fee": 250.00},
    "V5210": {"description": "Hearing aid, BiCROS, in the ear", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 3200.00},
    "V5220": {"description": "Hearing aid, BiCROS, behind the ear", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 3800.00},
    "V5241": {"description": "Dispensing fee, monaural hearing aid, any type", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_service", "fee": 200.00},
    "V5242": {"description": "Hearing aid, analog, monaural, CIC", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 1800.00},
    "V5243": {"description": "Hearing aid, analog, monaural, ITC", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 1600.00},
    "V5257": {"description": "Hearing aid, digitally programmable, monaural, CIC", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 2800.00},
    "V5261": {"description": "Hearing aid, digital, monaural, CIC", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 3200.00},
    "V5262": {"description": "Hearing aid, digital, monaural, ITC", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 2900.00},
    "V5264": {"description": "Hearing aid, digital, monaural, BTE", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_device", "fee": 3000.00},
    "V5265": {"description": "Ear mold/insert, not disposable, any type", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_service", "fee": 55.00},
    "V5266": {"description": "Battery for use in hearing device", "category": "Hearing Aid Device", "benefit_class": "hearing_aid_service", "fee": 5.00},
    # Cochlear Implant
    "69930": {"description": "Cochlear device implantation, with or without mastoidectomy", "category": "Cochlear Implant", "benefit_class": "cochlear", "fee": 35000.00},
    "L8614": {"description": "Cochlear device, includes all internal and external components", "category": "Cochlear Implant", "benefit_class": "cochlear", "fee": 25000.00},
    "L8615": {"description": "Headset/headpiece for use with cochlear implant device, replacement", "category": "Cochlear Implant", "benefit_class": "cochlear", "fee": 1500.00},
    "L8616": {"description": "Microphone for use with cochlear implant device, replacement", "category": "Cochlear Implant", "benefit_class": "cochlear", "fee": 800.00},
    "L8619": {"description": "Cochlear implant, external speech processor and controller, integrated system, replacement", "category": "Cochlear Implant", "benefit_class": "cochlear", "fee": 8000.00},
    # Vestibular Testing
    "92540": {"description": "Basic vestibular evaluation", "category": "Vestibular", "benefit_class": "diagnostic", "fee": 125.00},
    "92541": {"description": "Spontaneous nystagmus, including gaze", "category": "Vestibular", "benefit_class": "diagnostic", "fee": 75.00},
    "92542": {"description": "Positional nystagmus test", "category": "Vestibular", "benefit_class": "diagnostic", "fee": 80.00},
    "92544": {"description": "Optokinetic nystagmus test", "category": "Vestibular", "benefit_class": "diagnostic", "fee": 60.00},
    "92548": {"description": "Computerized dynamic posturography", "category": "Vestibular", "benefit_class": "diagnostic", "fee": 200.00},
}

# Hearing benefit class configuration
HEARING_BENEFIT_CLASSES = {
    "diagnostic": {"description": "Diagnostic Audiological Testing", "typical_coinsurance": 0.1, "frequency": "as needed"},
    "hearing_aid_service": {"description": "Hearing Aid Professional Services", "typical_coinsurance": 0.2, "frequency": "as needed"},
    "hearing_aid_device": {"description": "Hearing Aid Device", "typical_allowance": 2500.00, "frequency": "once per 36 months per ear"},
    "cochlear": {"description": "Cochlear Implant Services", "typical_coinsurance": 0.2, "frequency": "as needed, subject to medical necessity"},
}


def get_hearing_code(code):
    return HEARING_CODES_DATABASE.get(code)


def search_hearing_codes(query, limit=50):
    results = []
    query_lower = query.lower()
    for code, data in HEARING_CODES_DATABASE.items():
        if query_lower in code.lower() or query_lower in data["description"].lower():
            results.append({"code": code, **data})
        if len(results) >= limit:
            break
    return results


def get_hearing_codes_by_category(category):
    return [
        {"code": code, **data}
        for code, data in HEARING_CODES_DATABASE.items()
        if data["category"] == category
    ]


def calculate_hearing_allowed(code, plan_config=None):
    hearing = HEARING_CODES_DATABASE.get(code)
    if not hearing:
        return None

    benefit_class = hearing["benefit_class"]
    fee = hearing["fee"]

    if benefit_class == "hearing_aid_device":
        allowance = (plan_config or {}).get("device_allowance", 2500.00)
        plan_pays = min(fee, allowance)
        member_pays = max(0, fee - allowance)
    elif benefit_class == "cochlear":
        coinsurance = (plan_config or {}).get("cochlear_coinsurance", 0.2)
        plan_pays = fee * (1 - coinsurance)
        member_pays = fee * coinsurance
    else:
        coinsurance = HEARING_BENEFIT_CLASSES.get(benefit_class, {}).get("typical_coinsurance", 0.2)
        plan_pays = fee * (1 - coinsurance)
        member_pays = fee * coinsurance

    return {
        "fee": fee,
        "benefit_class": benefit_class,
        "plan_pays": round(plan_pays, 2),
        "member_pays": round(member_pays, 2),
    }
