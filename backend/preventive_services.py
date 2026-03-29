"""
FletchFlow - Preventive Services Database
ACA-compliant preventive service codes with age/gender/frequency rules,
ICD-10 Z-code mappings, and source references (USPSTF, HRSA, CDC).
"""

from datetime import datetime


# ==================== PREVENTIVE SERVICES DATABASE ====================

PREVENTIVE_SERVICES = {
    # ====== A. WELLNESS VISITS ======
    # New Patient Preventive Visits
    "99381": {
        "description": "Preventive visit, new patient, infant (age under 1)",
        "category": "Wellness Visit",
        "subcategory": "New Patient",
        "age_min": 0, "age_max": 1, "gender": "all",
        "frequency": "per_schedule", "frequency_limit": 6, "frequency_period": "year",
        "icd10_codes": ["Z00.110", "Z00.111", "Z00.121", "Z00.129"],
        "source": "USPSTF", "fee": 195.00,
    },
    "99382": {
        "description": "Preventive visit, new patient, early childhood (age 1-4)",
        "category": "Wellness Visit",
        "subcategory": "New Patient",
        "age_min": 1, "age_max": 4, "gender": "all",
        "frequency": "per_schedule", "frequency_limit": 4, "frequency_period": "year",
        "icd10_codes": ["Z00.121", "Z00.129"],
        "source": "USPSTF", "fee": 185.00,
    },
    "99383": {
        "description": "Preventive visit, new patient, late childhood (age 5-11)",
        "category": "Wellness Visit",
        "subcategory": "New Patient",
        "age_min": 5, "age_max": 11, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z00.121", "Z00.129"],
        "source": "USPSTF", "fee": 185.00,
    },
    "99384": {
        "description": "Preventive visit, new patient, adolescent (age 12-17)",
        "category": "Wellness Visit",
        "subcategory": "New Patient",
        "age_min": 12, "age_max": 17, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z00.121", "Z00.129"],
        "source": "USPSTF", "fee": 200.00,
    },
    "99385": {
        "description": "Preventive visit, new patient, age 18-39",
        "category": "Wellness Visit",
        "subcategory": "New Patient",
        "age_min": 18, "age_max": 39, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z00.00", "Z00.01"],
        "source": "USPSTF", "fee": 210.00,
    },
    "99386": {
        "description": "Preventive visit, new patient, age 40-64",
        "category": "Wellness Visit",
        "subcategory": "New Patient",
        "age_min": 40, "age_max": 64, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z00.00", "Z00.01"],
        "source": "USPSTF", "fee": 230.00,
    },
    "99387": {
        "description": "Preventive visit, new patient, age 65+",
        "category": "Wellness Visit",
        "subcategory": "New Patient",
        "age_min": 65, "age_max": 999, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z00.00", "Z00.01"],
        "source": "USPSTF", "fee": 250.00,
    },
    # Established Patient Preventive Visits
    "99391": {
        "description": "Preventive visit, established patient, infant (age under 1)",
        "category": "Wellness Visit",
        "subcategory": "Established Patient",
        "age_min": 0, "age_max": 1, "gender": "all",
        "frequency": "per_schedule", "frequency_limit": 6, "frequency_period": "year",
        "icd10_codes": ["Z00.110", "Z00.111", "Z00.121", "Z00.129"],
        "source": "USPSTF", "fee": 170.00,
    },
    "99392": {
        "description": "Preventive visit, established patient, early childhood (age 1-4)",
        "category": "Wellness Visit",
        "subcategory": "Established Patient",
        "age_min": 1, "age_max": 4, "gender": "all",
        "frequency": "per_schedule", "frequency_limit": 4, "frequency_period": "year",
        "icd10_codes": ["Z00.121", "Z00.129"],
        "source": "USPSTF", "fee": 165.00,
    },
    "99393": {
        "description": "Preventive visit, established patient, late childhood (age 5-11)",
        "category": "Wellness Visit",
        "subcategory": "Established Patient",
        "age_min": 5, "age_max": 11, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z00.121", "Z00.129"],
        "source": "USPSTF", "fee": 165.00,
    },
    "99394": {
        "description": "Preventive visit, established patient, adolescent (age 12-17)",
        "category": "Wellness Visit",
        "subcategory": "Established Patient",
        "age_min": 12, "age_max": 17, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z00.121", "Z00.129"],
        "source": "USPSTF", "fee": 175.00,
    },
    "99395": {
        "description": "Preventive visit, established patient, age 18-39",
        "category": "Wellness Visit",
        "subcategory": "Established Patient",
        "age_min": 18, "age_max": 39, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z00.00", "Z00.01"],
        "source": "USPSTF", "fee": 185.00,
    },
    "99396": {
        "description": "Preventive visit, established patient, age 40-64",
        "category": "Wellness Visit",
        "subcategory": "Established Patient",
        "age_min": 40, "age_max": 64, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z00.00", "Z00.01"],
        "source": "USPSTF", "fee": 205.00,
    },
    "99397": {
        "description": "Preventive visit, established patient, age 65+",
        "category": "Wellness Visit",
        "subcategory": "Established Patient",
        "age_min": 65, "age_max": 999, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z00.00", "Z00.01"],
        "source": "USPSTF", "fee": 225.00,
    },
    # ====== B. IMMUNIZATIONS (CDC Schedule) ======
    "90460": {
        "description": "Immunization administration through 18 years, first or only component",
        "category": "Immunization",
        "subcategory": "Administration",
        "age_min": 0, "age_max": 18, "gender": "all",
        "frequency": "per_schedule", "frequency_limit": 20, "frequency_period": "year",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 25.00,
    },
    "90461": {
        "description": "Immunization administration through 18 years, each additional component",
        "category": "Immunization",
        "subcategory": "Administration",
        "age_min": 0, "age_max": 18, "gender": "all",
        "frequency": "per_schedule", "frequency_limit": 20, "frequency_period": "year",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 15.00,
    },
    "90471": {
        "description": "Immunization administration (first vaccine/toxoid)",
        "category": "Immunization",
        "subcategory": "Administration",
        "age_min": 0, "age_max": 999, "gender": "all",
        "frequency": "per_schedule", "frequency_limit": 10, "frequency_period": "year",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 25.00,
    },
    "90472": {
        "description": "Immunization administration (each additional vaccine/toxoid)",
        "category": "Immunization",
        "subcategory": "Administration",
        "age_min": 0, "age_max": 999, "gender": "all",
        "frequency": "per_schedule", "frequency_limit": 10, "frequency_period": "year",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 15.00,
    },
    "90473": {
        "description": "Immunization administration by intranasal or oral route, first vaccine",
        "category": "Immunization",
        "subcategory": "Administration",
        "age_min": 0, "age_max": 999, "gender": "all",
        "frequency": "per_schedule", "frequency_limit": 5, "frequency_period": "year",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 25.00,
    },
    "90474": {
        "description": "Immunization administration by intranasal or oral route, each additional",
        "category": "Immunization",
        "subcategory": "Administration",
        "age_min": 0, "age_max": 999, "gender": "all",
        "frequency": "per_schedule", "frequency_limit": 5, "frequency_period": "year",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 15.00,
    },
    # Vaccine products (common)
    "90630": {
        "description": "Influenza virus vaccine, quadrivalent (IIV4), split virus",
        "category": "Immunization",
        "subcategory": "Influenza",
        "age_min": 6, "age_max": 999, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 45.00,
    },
    "90651": {
        "description": "HPV vaccine, 9-valent (Gardasil 9), 3-dose schedule",
        "category": "Immunization",
        "subcategory": "HPV",
        "age_min": 9, "age_max": 45, "gender": "all",
        "frequency": "lifetime_series", "frequency_limit": 3, "frequency_period": "lifetime",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 285.00,
    },
    "90707": {
        "description": "MMR vaccine (measles, mumps, rubella), live",
        "category": "Immunization",
        "subcategory": "MMR",
        "age_min": 0, "age_max": 999, "gender": "all",
        "frequency": "lifetime_series", "frequency_limit": 2, "frequency_period": "lifetime",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 75.00,
    },
    "90715": {
        "description": "Tdap vaccine (tetanus, diphtheria, pertussis)",
        "category": "Immunization",
        "subcategory": "Tdap",
        "age_min": 7, "age_max": 999, "gender": "all",
        "frequency": "once_10_years", "frequency_limit": 1, "frequency_period": "10_years",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 55.00,
    },
    "90716": {
        "description": "Varicella virus vaccine, live",
        "category": "Immunization",
        "subcategory": "Varicella",
        "age_min": 0, "age_max": 999, "gender": "all",
        "frequency": "lifetime_series", "frequency_limit": 2, "frequency_period": "lifetime",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 150.00,
    },
    "90732": {
        "description": "Pneumococcal polysaccharide vaccine (PPSV23), adult",
        "category": "Immunization",
        "subcategory": "Pneumococcal",
        "age_min": 2, "age_max": 999, "gender": "all",
        "frequency": "per_schedule", "frequency_limit": 2, "frequency_period": "lifetime",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 120.00,
    },
    "90746": {
        "description": "Hepatitis B vaccine, adult dosage (3-dose series)",
        "category": "Immunization",
        "subcategory": "Hepatitis B",
        "age_min": 18, "age_max": 999, "gender": "all",
        "frequency": "lifetime_series", "frequency_limit": 3, "frequency_period": "lifetime",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 75.00,
    },
    "90633": {
        "description": "Hepatitis A vaccine, pediatric/adolescent, 2-dose series",
        "category": "Immunization",
        "subcategory": "Hepatitis A",
        "age_min": 0, "age_max": 18, "gender": "all",
        "frequency": "lifetime_series", "frequency_limit": 2, "frequency_period": "lifetime",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 55.00,
    },
    "91322": {
        "description": "COVID-19 vaccine, updated formulation",
        "category": "Immunization",
        "subcategory": "COVID-19",
        "age_min": 6, "age_max": 999, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z23"],
        "source": "CDC", "fee": 0.00,
    },
    # ====== C. CANCER SCREENINGS ======
    "77067": {
        "description": "Screening mammography, bilateral (2-view), including CAD",
        "category": "Cancer Screening",
        "subcategory": "Mammogram",
        "age_min": 40, "age_max": 999, "gender": "female",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z12.31"],
        "source": "USPSTF", "fee": 240.00,
    },
    "77063": {
        "description": "Screening digital breast tomosynthesis, bilateral",
        "category": "Cancer Screening",
        "subcategory": "Mammogram",
        "age_min": 40, "age_max": 999, "gender": "female",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z12.31"],
        "source": "USPSTF", "fee": 75.00,
    },
    "45378": {
        "description": "Colonoscopy, flexible, diagnostic",
        "category": "Cancer Screening",
        "subcategory": "Colonoscopy",
        "age_min": 45, "age_max": 999, "gender": "all",
        "frequency": "every_10_years", "frequency_limit": 1, "frequency_period": "10_years",
        "icd10_codes": ["Z12.11", "Z12.12"],
        "source": "USPSTF", "fee": 1200.00,
        "risk_factor_override": {"high_risk": {"frequency_period": "5_years"}},
    },
    "45380": {
        "description": "Colonoscopy with biopsy, single or multiple",
        "category": "Cancer Screening",
        "subcategory": "Colonoscopy",
        "age_min": 45, "age_max": 999, "gender": "all",
        "frequency": "every_10_years", "frequency_limit": 1, "frequency_period": "10_years",
        "icd10_codes": ["Z12.11", "Z12.12"],
        "source": "USPSTF", "fee": 1450.00,
    },
    "45381": {
        "description": "Colonoscopy with submucosal injection",
        "category": "Cancer Screening",
        "subcategory": "Colonoscopy",
        "age_min": 45, "age_max": 999, "gender": "all",
        "frequency": "every_10_years", "frequency_limit": 1, "frequency_period": "10_years",
        "icd10_codes": ["Z12.11", "Z12.12"],
        "source": "USPSTF", "fee": 1500.00,
    },
    "45384": {
        "description": "Colonoscopy with removal of tumor(s), polyp(s) by snare technique",
        "category": "Cancer Screening",
        "subcategory": "Colonoscopy",
        "age_min": 45, "age_max": 999, "gender": "all",
        "frequency": "every_10_years", "frequency_limit": 1, "frequency_period": "10_years",
        "icd10_codes": ["Z12.11", "Z12.12"],
        "source": "USPSTF", "fee": 1600.00,
    },
    "45385": {
        "description": "Colonoscopy with removal of tumor(s), polyp(s) by snare technique with ablation",
        "category": "Cancer Screening",
        "subcategory": "Colonoscopy",
        "age_min": 45, "age_max": 999, "gender": "all",
        "frequency": "every_10_years", "frequency_limit": 1, "frequency_period": "10_years",
        "icd10_codes": ["Z12.11", "Z12.12"],
        "source": "USPSTF", "fee": 1700.00,
    },
    "88141": {
        "description": "Cytopathology, cervical or vaginal (Pap smear), interpretation by physician",
        "category": "Cancer Screening",
        "subcategory": "Pap Smear",
        "age_min": 21, "age_max": 65, "gender": "female",
        "frequency": "every_3_years", "frequency_limit": 1, "frequency_period": "3_years",
        "icd10_codes": ["Z12.4"],
        "source": "USPSTF", "fee": 35.00,
    },
    "88142": {
        "description": "Cytopathology, cervical or vaginal, thin-layer preparation",
        "category": "Cancer Screening",
        "subcategory": "Pap Smear",
        "age_min": 21, "age_max": 65, "gender": "female",
        "frequency": "every_3_years", "frequency_limit": 1, "frequency_period": "3_years",
        "icd10_codes": ["Z12.4"],
        "source": "USPSTF", "fee": 40.00,
    },
    "88175": {
        "description": "Cytopathology, cervical or vaginal, thin-layer preparation, automated screening",
        "category": "Cancer Screening",
        "subcategory": "Pap Smear",
        "age_min": 21, "age_max": 65, "gender": "female",
        "frequency": "every_3_years", "frequency_limit": 1, "frequency_period": "3_years",
        "icd10_codes": ["Z12.4"],
        "source": "USPSTF", "fee": 45.00,
    },
    "84153": {
        "description": "PSA (prostate-specific antigen), total",
        "category": "Cancer Screening",
        "subcategory": "PSA",
        "age_min": 55, "age_max": 69, "gender": "male",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z12.5"],
        "source": "USPSTF", "fee": 35.00,
    },
    # ====== D. PREVENTIVE SCREENINGS ======
    "80061": {
        "description": "Lipid panel (cholesterol, HDL, LDL, triglycerides)",
        "category": "Preventive Screening",
        "subcategory": "Cholesterol",
        "age_min": 20, "age_max": 999, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z13.220"],
        "source": "USPSTF", "fee": 40.00,
    },
    "83036": {
        "description": "Hemoglobin A1c (HbA1c) - diabetes screening",
        "category": "Preventive Screening",
        "subcategory": "Diabetes",
        "age_min": 35, "age_max": 70, "gender": "all",
        "frequency": "every_3_years", "frequency_limit": 1, "frequency_period": "3_years",
        "icd10_codes": ["Z13.1"],
        "source": "USPSTF", "fee": 20.00,
        "risk_factor_override": {"overweight_obese": {"frequency_period": "year"}},
    },
    "82947": {
        "description": "Glucose; quantitative, blood",
        "category": "Preventive Screening",
        "subcategory": "Diabetes",
        "age_min": 35, "age_max": 70, "gender": "all",
        "frequency": "every_3_years", "frequency_limit": 1, "frequency_period": "3_years",
        "icd10_codes": ["Z13.1"],
        "source": "USPSTF", "fee": 12.00,
    },
    "86803": {
        "description": "Hepatitis C antibody screening",
        "category": "Preventive Screening",
        "subcategory": "Hepatitis C",
        "age_min": 18, "age_max": 79, "gender": "all",
        "frequency": "once_lifetime", "frequency_limit": 1, "frequency_period": "lifetime",
        "icd10_codes": ["Z11.59"],
        "source": "USPSTF", "fee": 25.00,
        "risk_factor_override": {"high_risk": {"frequency_period": "year"}},
    },
    "87389": {
        "description": "HIV-1 antigen/antibody, immunoassay combination",
        "category": "Preventive Screening",
        "subcategory": "HIV",
        "age_min": 15, "age_max": 65, "gender": "all",
        "frequency": "once_lifetime", "frequency_limit": 1, "frequency_period": "lifetime",
        "icd10_codes": ["Z11.4"],
        "source": "USPSTF", "fee": 30.00,
        "risk_factor_override": {"high_risk": {"frequency_period": "year"}},
    },
    # ====== E. WOMEN'S PREVENTIVE SERVICES (HRSA) ======
    "59400": {
        "description": "Routine obstetric care including antepartum care, vaginal delivery, and postpartum care",
        "category": "Women's Preventive",
        "subcategory": "Maternity",
        "age_min": 12, "age_max": 55, "gender": "female",
        "frequency": "per_pregnancy", "frequency_limit": 1, "frequency_period": "pregnancy",
        "icd10_codes": ["Z34.00", "Z34.80", "Z34.90"],
        "source": "HRSA", "fee": 3500.00,
    },
    "59510": {
        "description": "Routine obstetric care including antepartum care, cesarean delivery, and postpartum care",
        "category": "Women's Preventive",
        "subcategory": "Maternity",
        "age_min": 12, "age_max": 55, "gender": "female",
        "frequency": "per_pregnancy", "frequency_limit": 1, "frequency_period": "pregnancy",
        "icd10_codes": ["Z34.00", "Z34.80", "Z34.90"],
        "source": "HRSA", "fee": 4500.00,
    },
    "81025": {
        "description": "Gestational diabetes screening (glucose tolerance test)",
        "category": "Women's Preventive",
        "subcategory": "Gestational Diabetes",
        "age_min": 12, "age_max": 55, "gender": "female",
        "frequency": "per_pregnancy", "frequency_limit": 1, "frequency_period": "pregnancy",
        "icd10_codes": ["Z13.1", "Z34.00"],
        "source": "HRSA", "fee": 15.00,
    },
    "S9443": {
        "description": "Lactation counseling / breastfeeding support",
        "category": "Women's Preventive",
        "subcategory": "Breastfeeding",
        "age_min": 12, "age_max": 55, "gender": "female",
        "frequency": "per_pregnancy", "frequency_limit": 6, "frequency_period": "pregnancy",
        "icd10_codes": ["Z39.1"],
        "source": "HRSA", "fee": 85.00,
    },
    "E0603": {
        "description": "Breast pump, electric (any type)",
        "category": "Women's Preventive",
        "subcategory": "Breastfeeding",
        "age_min": 12, "age_max": 55, "gender": "female",
        "frequency": "per_pregnancy", "frequency_limit": 1, "frequency_period": "pregnancy",
        "icd10_codes": ["Z39.1"],
        "source": "HRSA", "fee": 300.00,
    },
    "J7300": {
        "description": "Intrauterine copper contraceptive (IUD)",
        "category": "Women's Preventive",
        "subcategory": "Contraception",
        "age_min": 12, "age_max": 55, "gender": "female",
        "frequency": "per_device", "frequency_limit": 1, "frequency_period": "10_years",
        "icd10_codes": ["Z30.430"],
        "source": "HRSA", "fee": 750.00,
    },
    "J7301": {
        "description": "Levonorgestrel-releasing intrauterine contraceptive system",
        "category": "Women's Preventive",
        "subcategory": "Contraception",
        "age_min": 12, "age_max": 55, "gender": "female",
        "frequency": "per_device", "frequency_limit": 1, "frequency_period": "5_years",
        "icd10_codes": ["Z30.430"],
        "source": "HRSA", "fee": 900.00,
    },
    "J7307": {
        "description": "Etonogestrel contraceptive implant (Nexplanon)",
        "category": "Women's Preventive",
        "subcategory": "Contraception",
        "age_min": 12, "age_max": 55, "gender": "female",
        "frequency": "per_device", "frequency_limit": 1, "frequency_period": "3_years",
        "icd10_codes": ["Z30.017"],
        "source": "HRSA", "fee": 850.00,
    },
    # ====== F. PEDIATRIC PREVENTIVE SERVICES ======
    "96110": {
        "description": "Developmental screening with scoring and documentation, per standardized instrument",
        "category": "Pediatric Preventive",
        "subcategory": "Developmental Screening",
        "age_min": 0, "age_max": 5, "gender": "all",
        "frequency": "per_schedule", "frequency_limit": 3, "frequency_period": "year",
        "icd10_codes": ["Z13.40", "Z13.41", "Z13.42"],
        "source": "USPSTF", "fee": 20.00,
    },
    "96127": {
        "description": "Brief emotional/behavioral assessment with scoring and documentation",
        "category": "Pediatric Preventive",
        "subcategory": "Autism Screening",
        "age_min": 0, "age_max": 18, "gender": "all",
        "frequency": "per_schedule", "frequency_limit": 2, "frequency_period": "year",
        "icd10_codes": ["Z13.40", "Z13.41"],
        "source": "USPSTF", "fee": 10.00,
    },
    "99173": {
        "description": "Visual acuity screening, automated or semi-automated",
        "category": "Pediatric Preventive",
        "subcategory": "Vision Screening",
        "age_min": 3, "age_max": 18, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z13.5"],
        "source": "USPSTF", "fee": 10.00,
    },
    "92551": {
        "description": "Hearing screening, pure tone, air only",
        "category": "Pediatric Preventive",
        "subcategory": "Hearing Screening",
        "age_min": 0, "age_max": 18, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z13.5"],
        "source": "USPSTF", "fee": 15.00,
    },
    # ====== G. BEHAVIORAL / COUNSELING ======
    "G0447": {
        "description": "Face-to-face behavioral counseling for obesity, 15 minutes",
        "category": "Behavioral Counseling",
        "subcategory": "Obesity",
        "age_min": 18, "age_max": 999, "gender": "all",
        "frequency": "annual", "frequency_limit": 22, "frequency_period": "year",
        "icd10_codes": ["Z71.3"],
        "source": "USPSTF", "fee": 30.00,
    },
    "99406": {
        "description": "Smoking and tobacco use cessation counseling, intermediate (3-10 minutes)",
        "category": "Behavioral Counseling",
        "subcategory": "Tobacco Cessation",
        "age_min": 18, "age_max": 999, "gender": "all",
        "frequency": "annual", "frequency_limit": 8, "frequency_period": "year",
        "icd10_codes": ["Z71.6", "Z87.891"],
        "source": "USPSTF", "fee": 20.00,
    },
    "99407": {
        "description": "Smoking and tobacco use cessation counseling, intensive (>10 minutes)",
        "category": "Behavioral Counseling",
        "subcategory": "Tobacco Cessation",
        "age_min": 18, "age_max": 999, "gender": "all",
        "frequency": "annual", "frequency_limit": 8, "frequency_period": "year",
        "icd10_codes": ["Z71.6", "Z87.891"],
        "source": "USPSTF", "fee": 35.00,
    },
    "G0442": {
        "description": "Annual alcohol misuse screening, 15 minutes",
        "category": "Behavioral Counseling",
        "subcategory": "Alcohol Misuse",
        "age_min": 18, "age_max": 999, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z13.31", "Z13.39"],
        "source": "USPSTF", "fee": 20.00,
    },
    "G0443": {
        "description": "Brief face-to-face behavioral counseling for alcohol misuse, 15 minutes",
        "category": "Behavioral Counseling",
        "subcategory": "Alcohol Misuse",
        "age_min": 18, "age_max": 999, "gender": "all",
        "frequency": "annual", "frequency_limit": 4, "frequency_period": "year",
        "icd10_codes": ["Z13.31", "Z13.39"],
        "source": "USPSTF", "fee": 30.00,
    },
    "G0444": {
        "description": "Annual depression screening, 15 minutes",
        "category": "Behavioral Counseling",
        "subcategory": "Depression Screening",
        "age_min": 12, "age_max": 999, "gender": "all",
        "frequency": "annual", "frequency_limit": 1, "frequency_period": "year",
        "icd10_codes": ["Z13.31", "Z13.32"],
        "source": "USPSTF", "fee": 20.00,
    },
}

# ==================== PREVENTIVE DIAGNOSIS CODES ====================
# Z-codes that indicate a visit is preventive in nature
PREVENTIVE_Z_CODES = {
    "Z00.00": "Encounter for general adult medical examination without abnormal findings",
    "Z00.01": "Encounter for general adult medical examination with abnormal findings",
    "Z00.110": "Health examination for newborn under 8 days old",
    "Z00.111": "Health examination for newborn 8 to 28 days old",
    "Z00.121": "Encounter for routine child health examination with abnormal findings",
    "Z00.129": "Encounter for routine child health examination without abnormal findings",
    "Z01.00": "Encounter for examination of eyes and vision without abnormal findings",
    "Z01.01": "Encounter for examination of eyes and vision with abnormal findings",
    "Z01.10": "Encounter for examination of ears and hearing without abnormal findings",
    "Z01.110": "Encounter for hearing examination following failed hearing screening",
    "Z01.12": "Encounter for hearing conservation and treatment",
    "Z12.11": "Encounter for screening for malignant neoplasm of colon",
    "Z12.12": "Encounter for screening for malignant neoplasm of rectum",
    "Z12.31": "Encounter for screening mammogram for malignant neoplasm of breast",
    "Z12.39": "Encounter for other screening for malignant neoplasm of breast",
    "Z12.4": "Encounter for screening for malignant neoplasm of cervix",
    "Z12.5": "Encounter for screening for malignant neoplasm of prostate",
    "Z13.1": "Encounter for screening for diabetes mellitus",
    "Z13.220": "Encounter for screening for lipoid disorders",
    "Z13.31": "Encounter for screening for depression",
    "Z13.32": "Encounter for screening for maternal depression",
    "Z13.39": "Encounter for screening for other mental health and behavioral disorders",
    "Z13.40": "Encounter for screening for unspecified developmental delays",
    "Z13.41": "Encounter for autism screening",
    "Z13.42": "Encounter for screening for global developmental delays",
    "Z13.5": "Encounter for screening for eye and ear disorders",
    "Z11.4": "Encounter for screening for HIV",
    "Z11.59": "Encounter for screening for other viral diseases",
    "Z23": "Encounter for immunization",
    "Z30.017": "Encounter for initial prescription of implantable subdermal contraceptive",
    "Z30.430": "Encounter for insertion of intrauterine contraceptive device",
    "Z34.00": "Encounter for supervision of normal first pregnancy, unspecified trimester",
    "Z34.80": "Encounter for supervision of other normal pregnancy, unspecified trimester",
    "Z34.90": "Encounter for supervision of normal pregnancy, unspecified, unspecified trimester",
    "Z39.1": "Encounter for care and examination of lactating mother",
    "Z71.3": "Dietary counseling and surveillance",
    "Z71.6": "Tobacco abuse counseling",
    "Z87.891": "Personal history of nicotine dependence",
}


# ==================== HELPER FUNCTIONS ====================

def is_preventive_code(cpt_code):
    """Check if a CPT/HCPCS code is in the preventive services database."""
    return cpt_code in PREVENTIVE_SERVICES


def is_preventive_diagnosis(diagnosis_codes):
    """Check if the primary diagnosis indicates a preventive encounter."""
    if not diagnosis_codes:
        return False
    for dx in diagnosis_codes:
        dx_clean = dx.strip().upper()
        if dx_clean.startswith("Z"):
            if dx_clean in PREVENTIVE_Z_CODES:
                return True
            # Check prefix match (e.g., Z00 matches Z00.00)
            for z_code in PREVENTIVE_Z_CODES:
                if z_code.startswith(dx_clean) or dx_clean.startswith(z_code.split(".")[0]):
                    return True
    return False


def has_modifier_33(modifier):
    """Check if modifier 33 (preventive services) is present."""
    if not modifier:
        return False
    return "33" in str(modifier)


def check_age_eligibility(service, member_age):
    """Check if a member meets the age requirement for a preventive service."""
    return service.get("age_min", 0) <= member_age <= service.get("age_max", 999)


def check_gender_eligibility(service, member_gender):
    """Check if a member meets the gender requirement for a preventive service."""
    svc_gender = service.get("gender", "all")
    if svc_gender == "all":
        return True
    return svc_gender.lower() == member_gender.lower()


def calculate_member_age(dob_str, service_date_str):
    """Calculate member age at date of service."""
    try:
        dob = datetime.fromisoformat(dob_str) if "T" in dob_str else datetime.strptime(dob_str, "%Y-%m-%d")
        svc = datetime.fromisoformat(service_date_str) if "T" in service_date_str else datetime.strptime(service_date_str, "%Y-%m-%d")
        age = svc.year - dob.year - ((svc.month, svc.day) < (dob.month, dob.day))
        return age
    except (ValueError, TypeError):
        return None


def get_preventive_service(cpt_code):
    """Get preventive service details."""
    return PREVENTIVE_SERVICES.get(cpt_code)


def search_preventive_services(query, limit=50):
    """Search preventive services by code or description."""
    results = []
    query_lower = query.lower()
    for code, data in PREVENTIVE_SERVICES.items():
        if query_lower in code.lower() or query_lower in data["description"].lower() or query_lower in data.get("category", "").lower() or query_lower in data.get("subcategory", "").lower():
            results.append({"code": code, **data})
        if len(results) >= limit:
            break
    return results


def get_preventive_by_category(category):
    """Get all preventive services in a category."""
    return [
        {"code": code, **data}
        for code, data in PREVENTIVE_SERVICES.items()
        if data.get("category") == category
    ]


def evaluate_preventive_claim_line(cpt_code, diagnosis_codes, modifier, member_age, member_gender, risk_factors=None):
    """
    Evaluate whether a service line qualifies as a preventive service.
    Returns a dict with determination and details.
    """
    service = PREVENTIVE_SERVICES.get(cpt_code)
    if not service:
        return {"is_preventive": False, "reason": "Code not in preventive services database"}

    # Check age
    if not check_age_eligibility(service, member_age):
        return {
            "is_preventive": False,
            "reason": f"Member age {member_age} outside range {service['age_min']}-{service['age_max']}",
            "service": service,
        }

    # Check gender
    if not check_gender_eligibility(service, member_gender):
        return {
            "is_preventive": False,
            "reason": f"Service restricted to gender: {service['gender']}",
            "service": service,
        }

    # Check diagnosis codes - must be preventive (Z-code)
    dx_preventive = is_preventive_diagnosis(diagnosis_codes)
    has_mod33 = has_modifier_33(modifier)

    if not dx_preventive and not has_mod33:
        return {
            "is_preventive": False,
            "reason": "Diagnosis codes are not preventive (no Z-code) and modifier 33 not present",
            "reclassify_as": "diagnostic",
            "service": service,
        }

    # Check for non-preventive secondary diagnosis
    has_illness_dx = False
    for dx in (diagnosis_codes or []):
        dx_clean = dx.strip().upper()
        if not dx_clean.startswith("Z") and dx_clean:
            has_illness_dx = True
            break

    if has_illness_dx and not has_mod33:
        return {
            "is_preventive": "split",
            "reason": "Secondary diagnosis indicates illness - claim should be split",
            "service": service,
        }

    return {
        "is_preventive": True,
        "reason": "Qualifies as ACA preventive service - $0 member cost share",
        "service": service,
        "fee": service["fee"],
    }


async def check_preventive_frequency(db_ref, member_id, cpt_code, service_date_str, service_data=None):
    """
    Check if a preventive service is within allowed frequency limits.
    Returns (within_limit: bool, message: str, usage_count: int).
    """
    service = service_data or PREVENTIVE_SERVICES.get(cpt_code)
    if not service:
        return True, "Not a preventive service", 0

    freq_period = service.get("frequency_period", "year")
    freq_limit = service.get("frequency_limit", 1)
    subcategory = service.get("subcategory", "")

    try:
        svc_date = datetime.fromisoformat(service_date_str) if "T" in service_date_str else datetime.strptime(service_date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return True, "Cannot parse service date", 0

    # Determine lookback window
    if freq_period == "year":
        lookback = svc_date.replace(year=svc_date.year - 1)
    elif freq_period == "3_years":
        lookback = svc_date.replace(year=svc_date.year - 3)
    elif freq_period == "5_years":
        lookback = svc_date.replace(year=svc_date.year - 5)
    elif freq_period == "10_years":
        lookback = svc_date.replace(year=svc_date.year - 10)
    elif freq_period == "lifetime":
        lookback = datetime(1900, 1, 1)
    elif freq_period in ("pregnancy", "per_device"):
        lookback = svc_date.replace(year=svc_date.year - 1)
    else:
        lookback = svc_date.replace(year=svc_date.year - 1)

    # Query utilization records
    usage = await db_ref.preventive_utilization.count_documents({
        "member_id": member_id,
        "subcategory": subcategory,
        "service_date": {"$gte": lookback.isoformat()},
    })

    if usage >= freq_limit:
        return False, f"Frequency limit exceeded: {usage}/{freq_limit} in {freq_period}", usage

    return True, f"Within frequency: {usage}/{freq_limit} in {freq_period}", usage


async def record_preventive_utilization(db_ref, member_id, cpt_code, service_date_str, claim_id):
    """Record a preventive service utilization for frequency tracking."""
    service = PREVENTIVE_SERVICES.get(cpt_code)
    if not service:
        return

    doc = {
        "member_id": member_id,
        "cpt_code": cpt_code,
        "category": service.get("category", ""),
        "subcategory": service.get("subcategory", ""),
        "service_date": service_date_str,
        "claim_id": claim_id,
        "recorded_at": datetime.now().isoformat(),
    }
    await db_ref.preventive_utilization.insert_one(doc)
