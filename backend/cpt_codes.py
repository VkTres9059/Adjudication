# CPT Code Database and Medicare Fee Schedule
# This module contains comprehensive CPT codes and Medicare reimbursement rates

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class CPTCategory(str, Enum):
    EVALUATION_MANAGEMENT = "E/M"
    ANESTHESIA = "Anesthesia"
    SURGERY = "Surgery"
    RADIOLOGY = "Radiology"
    PATHOLOGY_LAB = "Pathology/Lab"
    MEDICINE = "Medicine"
    HCPCS_LEVEL_II = "HCPCS"

@dataclass
class CPTCode:
    code: str
    description: str
    category: CPTCategory
    work_rvu: float  # Work Relative Value Units
    pe_rvu: float    # Practice Expense RVU
    mp_rvu: float    # Malpractice RVU
    total_rvu: float
    conversion_factor: float  # 2024 CF = $33.2875
    national_rate: float  # Base Medicare rate
    facility_rate: Optional[float] = None
    non_facility_rate: Optional[float] = None
    global_period: str = "XXX"  # 000, 010, 090, XXX, MMM, YYY, ZZZ
    bilateral_surgery: str = "1"
    assistant_surgery: str = "0"
    co_surgery: str = "0"
    multiple_procedure: str = "51"
    
# 2024 Medicare Conversion Factor
CONVERSION_FACTOR_2024 = 33.2875
CONVERSION_FACTOR_2025 = 32.7442  # Projected

# Geographic Practice Cost Indices (GPCI) by MAC Locality
# Format: locality_code: (work_gpci, pe_gpci, mp_gpci)
GPCI_LOCALITIES = {
    # National Average
    "00000": {"name": "National", "work": 1.000, "pe": 1.000, "mp": 1.000},
    
    # Alabama
    "01010": {"name": "Alabama", "work": 1.000, "pe": 0.870, "mp": 0.590},
    
    # Alaska
    "02010": {"name": "Alaska", "work": 1.500, "pe": 1.316, "mp": 0.810},
    
    # Arizona
    "03010": {"name": "Arizona", "work": 1.000, "pe": 0.977, "mp": 0.760},
    
    # Arkansas
    "04010": {"name": "Arkansas", "work": 1.000, "pe": 0.858, "mp": 0.320},
    
    # California - Multiple Localities
    "05010": {"name": "CA - Anaheim/Santa Ana", "work": 1.037, "pe": 1.224, "mp": 0.870},
    "05011": {"name": "CA - Los Angeles", "work": 1.056, "pe": 1.193, "mp": 0.890},
    "05012": {"name": "CA - Marin/Napa/Solano", "work": 1.019, "pe": 1.265, "mp": 0.580},
    "05013": {"name": "CA - Oakland/Berkeley", "work": 1.062, "pe": 1.305, "mp": 0.620},
    "05014": {"name": "CA - San Francisco", "work": 1.077, "pe": 1.503, "mp": 0.570},
    "05015": {"name": "CA - San Mateo", "work": 1.062, "pe": 1.467, "mp": 0.570},
    "05016": {"name": "CA - Santa Clara", "work": 1.063, "pe": 1.394, "mp": 0.620},
    "05017": {"name": "CA - Ventura", "work": 1.028, "pe": 1.168, "mp": 0.730},
    "05018": {"name": "CA - Rest of State", "work": 1.014, "pe": 1.054, "mp": 0.610},
    
    # Colorado
    "06010": {"name": "Colorado", "work": 1.000, "pe": 1.003, "mp": 0.740},
    
    # Connecticut
    "07010": {"name": "Connecticut", "work": 1.044, "pe": 1.146, "mp": 0.860},
    
    # Delaware
    "08010": {"name": "Delaware", "work": 1.019, "pe": 1.047, "mp": 0.710},
    
    # DC + MD/VA Suburbs
    "09010": {"name": "DC + MD/VA Suburbs", "work": 1.050, "pe": 1.218, "mp": 0.880},
    
    # Florida
    "10010": {"name": "FL - Fort Lauderdale", "work": 1.000, "pe": 1.042, "mp": 1.430},
    "10011": {"name": "FL - Miami", "work": 1.000, "pe": 1.092, "mp": 1.840},
    "10012": {"name": "FL - Rest of State", "work": 1.000, "pe": 0.948, "mp": 1.050},
    
    # Georgia
    "11010": {"name": "GA - Atlanta", "work": 1.010, "pe": 1.051, "mp": 0.930},
    "11011": {"name": "GA - Rest of State", "work": 1.000, "pe": 0.895, "mp": 0.900},
    
    # Hawaii
    "12010": {"name": "Hawaii", "work": 1.000, "pe": 1.161, "mp": 0.810},
    
    # Idaho
    "13010": {"name": "Idaho", "work": 1.000, "pe": 0.899, "mp": 0.470},
    
    # Illinois
    "14010": {"name": "IL - Chicago", "work": 1.028, "pe": 1.092, "mp": 1.490},
    "14011": {"name": "IL - East St. Louis", "work": 1.000, "pe": 0.912, "mp": 1.510},
    "14012": {"name": "IL - Rest of State", "work": 1.000, "pe": 0.893, "mp": 0.900},
    
    # Indiana
    "15010": {"name": "Indiana", "work": 1.000, "pe": 0.921, "mp": 0.510},
    
    # Iowa
    "16010": {"name": "Iowa", "work": 1.000, "pe": 0.885, "mp": 0.540},
    
    # Kansas
    "17010": {"name": "Kansas", "work": 1.000, "pe": 0.904, "mp": 0.640},
    
    # Kentucky
    "18010": {"name": "Kentucky", "work": 1.000, "pe": 0.877, "mp": 0.690},
    
    # Louisiana
    "19010": {"name": "Louisiana", "work": 1.000, "pe": 0.908, "mp": 0.910},
    
    # Maine
    "20010": {"name": "Maine", "work": 1.000, "pe": 0.964, "mp": 0.560},
    
    # Maryland
    "21010": {"name": "MD - Baltimore", "work": 1.021, "pe": 1.071, "mp": 0.850},
    "21011": {"name": "MD - Rest of State", "work": 1.000, "pe": 0.980, "mp": 0.760},
    
    # Massachusetts
    "22010": {"name": "MA - Boston", "work": 1.040, "pe": 1.252, "mp": 0.680},
    "22011": {"name": "MA - Rest of State", "work": 1.000, "pe": 1.086, "mp": 0.680},
    
    # Michigan
    "23010": {"name": "MI - Detroit", "work": 1.043, "pe": 1.025, "mp": 1.350},
    "23011": {"name": "MI - Rest of State", "work": 1.000, "pe": 0.930, "mp": 1.010},
    
    # Minnesota
    "24010": {"name": "Minnesota", "work": 1.000, "pe": 0.971, "mp": 0.400},
    
    # Mississippi
    "25010": {"name": "Mississippi", "work": 1.000, "pe": 0.843, "mp": 0.600},
    
    # Missouri
    "26010": {"name": "MO - Kansas City", "work": 1.000, "pe": 0.948, "mp": 0.660},
    "26011": {"name": "MO - St. Louis", "work": 1.000, "pe": 0.941, "mp": 0.850},
    "26012": {"name": "MO - Rest of State", "work": 1.000, "pe": 0.845, "mp": 0.540},
    
    # Montana
    "27010": {"name": "Montana", "work": 1.000, "pe": 0.888, "mp": 0.540},
    
    # Nebraska
    "28010": {"name": "Nebraska", "work": 1.000, "pe": 0.888, "mp": 0.350},
    
    # Nevada
    "29010": {"name": "Nevada", "work": 1.004, "pe": 1.051, "mp": 0.930},
    
    # New Hampshire
    "30010": {"name": "New Hampshire", "work": 1.000, "pe": 1.049, "mp": 0.680},
    
    # New Jersey
    "31010": {"name": "NJ - Northern", "work": 1.058, "pe": 1.221, "mp": 0.800},
    "31011": {"name": "NJ - Rest of State", "work": 1.028, "pe": 1.121, "mp": 0.800},
    
    # New Mexico
    "32010": {"name": "New Mexico", "work": 1.000, "pe": 0.905, "mp": 0.810},
    
    # New York
    "33010": {"name": "NY - Manhattan", "work": 1.094, "pe": 1.561, "mp": 1.050},
    "33011": {"name": "NY - NYC Suburbs", "work": 1.068, "pe": 1.288, "mp": 1.200},
    "33012": {"name": "NY - Poughkeepsie", "work": 1.011, "pe": 1.090, "mp": 0.750},
    "33013": {"name": "NY - Queens", "work": 1.058, "pe": 1.270, "mp": 1.350},
    "33014": {"name": "NY - Rest of State", "work": 1.000, "pe": 0.934, "mp": 0.610},
    
    # North Carolina
    "34010": {"name": "North Carolina", "work": 1.000, "pe": 0.929, "mp": 0.590},
    
    # North Dakota
    "35010": {"name": "North Dakota", "work": 1.000, "pe": 0.887, "mp": 0.540},
    
    # Ohio
    "36010": {"name": "Ohio", "work": 1.000, "pe": 0.937, "mp": 0.880},
    
    # Oklahoma
    "37010": {"name": "Oklahoma", "work": 1.000, "pe": 0.885, "mp": 0.450},
    
    # Oregon
    "38010": {"name": "OR - Portland", "work": 1.012, "pe": 1.048, "mp": 0.410},
    "38011": {"name": "OR - Rest of State", "work": 1.000, "pe": 0.946, "mp": 0.410},
    
    # Pennsylvania
    "39010": {"name": "PA - Philadelphia", "work": 1.033, "pe": 1.110, "mp": 0.940},
    "39011": {"name": "PA - Rest of State", "work": 1.000, "pe": 0.916, "mp": 0.650},
    
    # Puerto Rico
    "40010": {"name": "Puerto Rico", "work": 0.872, "pe": 0.711, "mp": 0.263},
    
    # Rhode Island
    "41010": {"name": "Rhode Island", "work": 1.025, "pe": 1.091, "mp": 0.700},
    
    # South Carolina
    "42010": {"name": "South Carolina", "work": 1.000, "pe": 0.903, "mp": 0.370},
    
    # South Dakota
    "43010": {"name": "South Dakota", "work": 1.000, "pe": 0.873, "mp": 0.370},
    
    # Tennessee
    "44010": {"name": "Tennessee", "work": 1.000, "pe": 0.908, "mp": 0.590},
    
    # Texas
    "45010": {"name": "TX - Austin", "work": 1.000, "pe": 1.008, "mp": 0.870},
    "45011": {"name": "TX - Beaumont", "work": 1.000, "pe": 0.899, "mp": 1.150},
    "45012": {"name": "TX - Brazoria", "work": 1.000, "pe": 1.014, "mp": 1.050},
    "45013": {"name": "TX - Dallas", "work": 1.011, "pe": 1.055, "mp": 0.920},
    "45014": {"name": "TX - Fort Worth", "work": 1.000, "pe": 1.001, "mp": 0.920},
    "45015": {"name": "TX - Galveston", "work": 1.000, "pe": 0.989, "mp": 1.050},
    "45016": {"name": "TX - Houston", "work": 1.018, "pe": 1.046, "mp": 1.050},
    "45017": {"name": "TX - Rest of State", "work": 1.000, "pe": 0.880, "mp": 0.800},
    
    # Utah
    "46010": {"name": "Utah", "work": 1.000, "pe": 0.942, "mp": 0.570},
    
    # Vermont
    "47010": {"name": "Vermont", "work": 1.000, "pe": 0.992, "mp": 0.430},
    
    # Virginia
    "48010": {"name": "Virginia", "work": 1.000, "pe": 0.957, "mp": 0.490},
    
    # Virgin Islands
    "49010": {"name": "Virgin Islands", "work": 1.000, "pe": 1.016, "mp": 1.000},
    
    # Washington
    "50010": {"name": "WA - Seattle", "work": 1.025, "pe": 1.127, "mp": 0.710},
    "50011": {"name": "WA - Rest of State", "work": 1.000, "pe": 0.987, "mp": 0.710},
    
    # West Virginia
    "51010": {"name": "West Virginia", "work": 1.000, "pe": 0.853, "mp": 0.830},
    
    # Wisconsin
    "52010": {"name": "Wisconsin", "work": 1.000, "pe": 0.929, "mp": 0.580},
    
    # Wyoming
    "53010": {"name": "Wyoming", "work": 1.000, "pe": 0.912, "mp": 0.710},
}

# Comprehensive CPT Code Database
# Organized by category with RVUs and Medicare rates

CPT_CODES_DATABASE: Dict[str, Dict] = {
    # ============================================
    # EVALUATION AND MANAGEMENT (99201-99499)
    # ============================================
    
    # Office/Outpatient Visits - New Patient (99202-99205)
    "99202": {
        "description": "Office/outpatient visit, new patient, straightforward MDM, 15-29 min",
        "category": "E/M",
        "work_rvu": 0.93,
        "pe_rvu": 1.12,
        "mp_rvu": 0.07,
        "total_rvu": 2.12,
        "facility_rate": 70.59,
        "non_facility_rate": 79.61,
        "global_period": "XXX"
    },
    "99203": {
        "description": "Office/outpatient visit, new patient, low MDM, 30-44 min",
        "category": "E/M",
        "work_rvu": 1.60,
        "pe_rvu": 1.57,
        "mp_rvu": 0.10,
        "total_rvu": 3.27,
        "facility_rate": 108.87,
        "non_facility_rate": 124.18,
        "global_period": "XXX"
    },
    "99204": {
        "description": "Office/outpatient visit, new patient, moderate MDM, 45-59 min",
        "category": "E/M",
        "work_rvu": 2.60,
        "pe_rvu": 2.14,
        "mp_rvu": 0.14,
        "total_rvu": 4.88,
        "facility_rate": 162.48,
        "non_facility_rate": 187.08,
        "global_period": "XXX"
    },
    "99205": {
        "description": "Office/outpatient visit, new patient, high MDM, 60-74 min",
        "category": "E/M",
        "work_rvu": 3.50,
        "pe_rvu": 2.59,
        "mp_rvu": 0.17,
        "total_rvu": 6.26,
        "facility_rate": 208.42,
        "non_facility_rate": 240.95,
        "global_period": "XXX"
    },
    
    # Office/Outpatient Visits - Established Patient (99211-99215)
    "99211": {
        "description": "Office/outpatient visit, established patient, minimal problem, 5 min",
        "category": "E/M",
        "work_rvu": 0.18,
        "pe_rvu": 0.47,
        "mp_rvu": 0.01,
        "total_rvu": 0.66,
        "facility_rate": 21.97,
        "non_facility_rate": 26.36,
        "global_period": "XXX"
    },
    "99212": {
        "description": "Office/outpatient visit, established patient, straightforward MDM, 10-19 min",
        "category": "E/M",
        "work_rvu": 0.70,
        "pe_rvu": 0.91,
        "mp_rvu": 0.05,
        "total_rvu": 1.66,
        "facility_rate": 55.26,
        "non_facility_rate": 63.85,
        "global_period": "XXX"
    },
    "99213": {
        "description": "Office/outpatient visit, established patient, low MDM, 20-29 min",
        "category": "E/M",
        "work_rvu": 1.30,
        "pe_rvu": 1.29,
        "mp_rvu": 0.08,
        "total_rvu": 2.67,
        "facility_rate": 88.90,
        "non_facility_rate": 102.35,
        "global_period": "XXX"
    },
    "99214": {
        "description": "Office/outpatient visit, established patient, moderate MDM, 30-39 min",
        "category": "E/M",
        "work_rvu": 1.92,
        "pe_rvu": 1.73,
        "mp_rvu": 0.11,
        "total_rvu": 3.76,
        "facility_rate": 125.20,
        "non_facility_rate": 145.20,
        "global_period": "XXX"
    },
    "99215": {
        "description": "Office/outpatient visit, established patient, high MDM, 40-54 min",
        "category": "E/M",
        "work_rvu": 2.80,
        "pe_rvu": 2.17,
        "mp_rvu": 0.14,
        "total_rvu": 5.11,
        "facility_rate": 170.14,
        "non_facility_rate": 195.22,
        "global_period": "XXX"
    },
    
    # Hospital Inpatient/Observation - Initial (99221-99223)
    "99221": {
        "description": "Initial hospital inpatient/observation, straightforward/low MDM",
        "category": "E/M",
        "work_rvu": 2.00,
        "pe_rvu": 0.99,
        "mp_rvu": 0.16,
        "total_rvu": 3.15,
        "facility_rate": 104.86,
        "non_facility_rate": 104.86,
        "global_period": "XXX"
    },
    "99222": {
        "description": "Initial hospital inpatient/observation, moderate MDM",
        "category": "E/M",
        "work_rvu": 2.61,
        "pe_rvu": 1.21,
        "mp_rvu": 0.21,
        "total_rvu": 4.03,
        "facility_rate": 134.17,
        "non_facility_rate": 134.17,
        "global_period": "XXX"
    },
    "99223": {
        "description": "Initial hospital inpatient/observation, high MDM",
        "category": "E/M",
        "work_rvu": 3.86,
        "pe_rvu": 1.73,
        "mp_rvu": 0.31,
        "total_rvu": 5.90,
        "facility_rate": 196.40,
        "non_facility_rate": 196.40,
        "global_period": "XXX"
    },
    
    # Hospital Inpatient/Observation - Subsequent (99231-99233)
    "99231": {
        "description": "Subsequent hospital inpatient/observation, straightforward/low MDM",
        "category": "E/M",
        "work_rvu": 0.76,
        "pe_rvu": 0.41,
        "mp_rvu": 0.06,
        "total_rvu": 1.23,
        "facility_rate": 40.96,
        "non_facility_rate": 40.96,
        "global_period": "XXX"
    },
    "99232": {
        "description": "Subsequent hospital inpatient/observation, moderate MDM",
        "category": "E/M",
        "work_rvu": 1.39,
        "pe_rvu": 0.66,
        "mp_rvu": 0.11,
        "total_rvu": 2.16,
        "facility_rate": 71.92,
        "non_facility_rate": 71.92,
        "global_period": "XXX"
    },
    "99233": {
        "description": "Subsequent hospital inpatient/observation, high MDM",
        "category": "E/M",
        "work_rvu": 2.00,
        "pe_rvu": 0.91,
        "mp_rvu": 0.16,
        "total_rvu": 3.07,
        "facility_rate": 102.19,
        "non_facility_rate": 102.19,
        "global_period": "XXX"
    },
    
    # Hospital Discharge (99238-99239)
    "99238": {
        "description": "Hospital discharge day management, 30 min or less",
        "category": "E/M",
        "work_rvu": 1.28,
        "pe_rvu": 0.64,
        "mp_rvu": 0.10,
        "total_rvu": 2.02,
        "facility_rate": 67.26,
        "non_facility_rate": 67.26,
        "global_period": "XXX"
    },
    "99239": {
        "description": "Hospital discharge day management, more than 30 min",
        "category": "E/M",
        "work_rvu": 1.90,
        "pe_rvu": 0.92,
        "mp_rvu": 0.15,
        "total_rvu": 2.97,
        "facility_rate": 98.86,
        "non_facility_rate": 98.86,
        "global_period": "XXX"
    },
    
    # Emergency Department Visits (99281-99285)
    "99281": {
        "description": "Emergency department visit, self-limited problem",
        "category": "E/M",
        "work_rvu": 0.25,
        "pe_rvu": 0.16,
        "mp_rvu": 0.02,
        "total_rvu": 0.43,
        "facility_rate": 14.31,
        "non_facility_rate": 14.31,
        "global_period": "XXX"
    },
    "99282": {
        "description": "Emergency department visit, low to moderate severity",
        "category": "E/M",
        "work_rvu": 0.65,
        "pe_rvu": 0.37,
        "mp_rvu": 0.05,
        "total_rvu": 1.07,
        "facility_rate": 35.62,
        "non_facility_rate": 35.62,
        "global_period": "XXX"
    },
    "99283": {
        "description": "Emergency department visit, moderate severity",
        "category": "E/M",
        "work_rvu": 1.34,
        "pe_rvu": 0.68,
        "mp_rvu": 0.10,
        "total_rvu": 2.12,
        "facility_rate": 70.59,
        "non_facility_rate": 70.59,
        "global_period": "XXX"
    },
    "99284": {
        "description": "Emergency department visit, high severity",
        "category": "E/M",
        "work_rvu": 2.56,
        "pe_rvu": 1.21,
        "mp_rvu": 0.21,
        "total_rvu": 3.98,
        "facility_rate": 132.50,
        "non_facility_rate": 132.50,
        "global_period": "XXX"
    },
    "99285": {
        "description": "Emergency department visit, high severity with threat to life",
        "category": "E/M",
        "work_rvu": 3.80,
        "pe_rvu": 1.77,
        "mp_rvu": 0.30,
        "total_rvu": 5.87,
        "facility_rate": 195.40,
        "non_facility_rate": 195.40,
        "global_period": "XXX"
    },
    
    # Critical Care (99291-99292)
    "99291": {
        "description": "Critical care, first 30-74 minutes",
        "category": "E/M",
        "work_rvu": 4.50,
        "pe_rvu": 1.97,
        "mp_rvu": 0.36,
        "total_rvu": 6.83,
        "facility_rate": 227.39,
        "non_facility_rate": 227.39,
        "global_period": "XXX"
    },
    "99292": {
        "description": "Critical care, each additional 30 minutes",
        "category": "E/M",
        "work_rvu": 2.25,
        "pe_rvu": 0.91,
        "mp_rvu": 0.18,
        "total_rvu": 3.34,
        "facility_rate": 111.20,
        "non_facility_rate": 111.20,
        "global_period": "ZZZ"
    },
    
    # Consultations - Office (99241-99245)
    "99242": {
        "description": "Office consultation, straightforward MDM",
        "category": "E/M",
        "work_rvu": 1.30,
        "pe_rvu": 1.29,
        "mp_rvu": 0.08,
        "total_rvu": 2.67,
        "facility_rate": 88.90,
        "non_facility_rate": 88.90,
        "global_period": "XXX"
    },
    "99243": {
        "description": "Office consultation, low MDM",
        "category": "E/M",
        "work_rvu": 1.92,
        "pe_rvu": 1.73,
        "mp_rvu": 0.11,
        "total_rvu": 3.76,
        "facility_rate": 125.20,
        "non_facility_rate": 125.20,
        "global_period": "XXX"
    },
    "99244": {
        "description": "Office consultation, moderate MDM",
        "category": "E/M",
        "work_rvu": 2.80,
        "pe_rvu": 2.17,
        "mp_rvu": 0.14,
        "total_rvu": 5.11,
        "facility_rate": 170.14,
        "non_facility_rate": 170.14,
        "global_period": "XXX"
    },
    "99245": {
        "description": "Office consultation, high MDM",
        "category": "E/M",
        "work_rvu": 3.50,
        "pe_rvu": 2.59,
        "mp_rvu": 0.17,
        "total_rvu": 6.26,
        "facility_rate": 208.42,
        "non_facility_rate": 208.42,
        "global_period": "XXX"
    },
    
    # Preventive Medicine - New Patient (99381-99387)
    "99381": {
        "description": "Preventive visit, new patient, infant (age under 1 year)",
        "category": "E/M",
        "work_rvu": 1.50,
        "pe_rvu": 1.60,
        "mp_rvu": 0.08,
        "total_rvu": 3.18,
        "facility_rate": 105.86,
        "non_facility_rate": 118.09,
        "global_period": "XXX"
    },
    "99382": {
        "description": "Preventive visit, new patient, early childhood (age 1-4)",
        "category": "E/M",
        "work_rvu": 1.50,
        "pe_rvu": 1.65,
        "mp_rvu": 0.08,
        "total_rvu": 3.23,
        "facility_rate": 107.52,
        "non_facility_rate": 120.43,
        "global_period": "XXX"
    },
    "99383": {
        "description": "Preventive visit, new patient, late childhood (age 5-11)",
        "category": "E/M",
        "work_rvu": 1.50,
        "pe_rvu": 1.57,
        "mp_rvu": 0.08,
        "total_rvu": 3.15,
        "facility_rate": 104.86,
        "non_facility_rate": 116.77,
        "global_period": "XXX"
    },
    "99384": {
        "description": "Preventive visit, new patient, adolescent (age 12-17)",
        "category": "E/M",
        "work_rvu": 1.75,
        "pe_rvu": 1.75,
        "mp_rvu": 0.09,
        "total_rvu": 3.59,
        "facility_rate": 119.52,
        "non_facility_rate": 133.39,
        "global_period": "XXX"
    },
    "99385": {
        "description": "Preventive visit, new patient, 18-39 years",
        "category": "E/M",
        "work_rvu": 1.75,
        "pe_rvu": 1.83,
        "mp_rvu": 0.09,
        "total_rvu": 3.67,
        "facility_rate": 122.19,
        "non_facility_rate": 136.71,
        "global_period": "XXX"
    },
    "99386": {
        "description": "Preventive visit, new patient, 40-64 years",
        "category": "E/M",
        "work_rvu": 2.00,
        "pe_rvu": 2.07,
        "mp_rvu": 0.10,
        "total_rvu": 4.17,
        "facility_rate": 138.83,
        "non_facility_rate": 155.37,
        "global_period": "XXX"
    },
    "99387": {
        "description": "Preventive visit, new patient, 65 years and older",
        "category": "E/M",
        "work_rvu": 2.35,
        "pe_rvu": 2.28,
        "mp_rvu": 0.12,
        "total_rvu": 4.75,
        "facility_rate": 158.12,
        "non_facility_rate": 176.30,
        "global_period": "XXX"
    },
    
    # Preventive Medicine - Established Patient (99391-99397)
    "99391": {
        "description": "Preventive visit, established patient, infant (age under 1 year)",
        "category": "E/M",
        "work_rvu": 1.20,
        "pe_rvu": 1.41,
        "mp_rvu": 0.07,
        "total_rvu": 2.68,
        "facility_rate": 89.23,
        "non_facility_rate": 99.12,
        "global_period": "XXX"
    },
    "99392": {
        "description": "Preventive visit, established patient, early childhood (age 1-4)",
        "category": "E/M",
        "work_rvu": 1.20,
        "pe_rvu": 1.44,
        "mp_rvu": 0.07,
        "total_rvu": 2.71,
        "facility_rate": 90.23,
        "non_facility_rate": 100.45,
        "global_period": "XXX"
    },
    "99393": {
        "description": "Preventive visit, established patient, late childhood (age 5-11)",
        "category": "E/M",
        "work_rvu": 1.20,
        "pe_rvu": 1.38,
        "mp_rvu": 0.07,
        "total_rvu": 2.65,
        "facility_rate": 88.23,
        "non_facility_rate": 98.00,
        "global_period": "XXX"
    },
    "99394": {
        "description": "Preventive visit, established patient, adolescent (age 12-17)",
        "category": "E/M",
        "work_rvu": 1.40,
        "pe_rvu": 1.56,
        "mp_rvu": 0.08,
        "total_rvu": 3.04,
        "facility_rate": 101.19,
        "non_facility_rate": 112.94,
        "global_period": "XXX"
    },
    "99395": {
        "description": "Preventive visit, established patient, 18-39 years",
        "category": "E/M",
        "work_rvu": 1.50,
        "pe_rvu": 1.63,
        "mp_rvu": 0.08,
        "total_rvu": 3.21,
        "facility_rate": 106.86,
        "non_facility_rate": 119.10,
        "global_period": "XXX"
    },
    "99396": {
        "description": "Preventive visit, established patient, 40-64 years",
        "category": "E/M",
        "work_rvu": 1.75,
        "pe_rvu": 1.82,
        "mp_rvu": 0.09,
        "total_rvu": 3.66,
        "facility_rate": 121.85,
        "non_facility_rate": 135.72,
        "global_period": "XXX"
    },
    "99397": {
        "description": "Preventive visit, established patient, 65 years and older",
        "category": "E/M",
        "work_rvu": 2.00,
        "pe_rvu": 2.00,
        "mp_rvu": 0.10,
        "total_rvu": 4.10,
        "facility_rate": 136.50,
        "non_facility_rate": 151.71,
        "global_period": "XXX"
    },
    
    # Telehealth/Remote Visits
    "99441": {
        "description": "Telephone E/M service, 5-10 minutes",
        "category": "E/M",
        "work_rvu": 0.25,
        "pe_rvu": 0.32,
        "mp_rvu": 0.02,
        "total_rvu": 0.59,
        "facility_rate": 19.64,
        "non_facility_rate": 22.15,
        "global_period": "XXX"
    },
    "99442": {
        "description": "Telephone E/M service, 11-20 minutes",
        "category": "E/M",
        "work_rvu": 0.50,
        "pe_rvu": 0.54,
        "mp_rvu": 0.03,
        "total_rvu": 1.07,
        "facility_rate": 35.62,
        "non_facility_rate": 40.05,
        "global_period": "XXX"
    },
    "99443": {
        "description": "Telephone E/M service, 21-30 minutes",
        "category": "E/M",
        "work_rvu": 0.75,
        "pe_rvu": 0.75,
        "mp_rvu": 0.05,
        "total_rvu": 1.55,
        "facility_rate": 51.60,
        "non_facility_rate": 58.03,
        "global_period": "XXX"
    },
    
    # Care Management Services
    "99490": {
        "description": "Chronic care management, first 20 minutes",
        "category": "E/M",
        "work_rvu": 0.61,
        "pe_rvu": 1.30,
        "mp_rvu": 0.02,
        "total_rvu": 1.93,
        "facility_rate": 64.26,
        "non_facility_rate": 64.26,
        "global_period": "XXX"
    },
    "99491": {
        "description": "Chronic care management by physician, first 30 minutes",
        "category": "E/M",
        "work_rvu": 1.00,
        "pe_rvu": 1.30,
        "mp_rvu": 0.05,
        "total_rvu": 2.35,
        "facility_rate": 78.23,
        "non_facility_rate": 78.23,
        "global_period": "XXX"
    },
    
    # Transitional Care Management
    "99495": {
        "description": "TCM, moderate complexity, contact within 2 business days",
        "category": "E/M",
        "work_rvu": 2.11,
        "pe_rvu": 2.40,
        "mp_rvu": 0.12,
        "total_rvu": 4.63,
        "facility_rate": 154.12,
        "non_facility_rate": 172.26,
        "global_period": "XXX"
    },
    "99496": {
        "description": "TCM, high complexity, contact within 2 business days",
        "category": "E/M",
        "work_rvu": 3.05,
        "pe_rvu": 3.01,
        "mp_rvu": 0.17,
        "total_rvu": 6.23,
        "facility_rate": 207.42,
        "non_facility_rate": 231.55,
        "global_period": "XXX"
    },
    
    # ============================================
    # ANESTHESIA (00100-01999)
    # ============================================
    "00100": {
        "description": "Anesthesia for salivary gland procedures",
        "category": "Anesthesia",
        "work_rvu": 3.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.10,
        "total_rvu": 3.10,
        "base_units": 5,
        "facility_rate": 103.19,
        "non_facility_rate": 103.19,
        "global_period": "XXX"
    },
    "00140": {
        "description": "Anesthesia for eye procedures",
        "category": "Anesthesia",
        "work_rvu": 3.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.10,
        "total_rvu": 3.10,
        "base_units": 4,
        "facility_rate": 103.19,
        "non_facility_rate": 103.19,
        "global_period": "XXX"
    },
    "00300": {
        "description": "Anesthesia for head and neck procedures",
        "category": "Anesthesia",
        "work_rvu": 3.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.10,
        "total_rvu": 3.10,
        "base_units": 5,
        "facility_rate": 103.19,
        "non_facility_rate": 103.19,
        "global_period": "XXX"
    },
    "00400": {
        "description": "Anesthesia for integumentary system procedures on extremities",
        "category": "Anesthesia",
        "work_rvu": 3.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.10,
        "total_rvu": 3.10,
        "base_units": 3,
        "facility_rate": 103.19,
        "non_facility_rate": 103.19,
        "global_period": "XXX"
    },
    "00500": {
        "description": "Anesthesia for esophageal procedures",
        "category": "Anesthesia",
        "work_rvu": 6.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.20,
        "total_rvu": 6.20,
        "base_units": 15,
        "facility_rate": 206.38,
        "non_facility_rate": 206.38,
        "global_period": "XXX"
    },
    "00600": {
        "description": "Anesthesia for cervical spine procedures",
        "category": "Anesthesia",
        "work_rvu": 5.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.17,
        "total_rvu": 5.17,
        "base_units": 10,
        "facility_rate": 172.10,
        "non_facility_rate": 172.10,
        "global_period": "XXX"
    },
    "00700": {
        "description": "Anesthesia for shoulder surgery",
        "category": "Anesthesia",
        "work_rvu": 3.50,
        "pe_rvu": 0.00,
        "mp_rvu": 0.12,
        "total_rvu": 3.62,
        "base_units": 5,
        "facility_rate": 120.50,
        "non_facility_rate": 120.50,
        "global_period": "XXX"
    },
    "00800": {
        "description": "Anesthesia for upper arm surgery",
        "category": "Anesthesia",
        "work_rvu": 3.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.10,
        "total_rvu": 3.10,
        "base_units": 4,
        "facility_rate": 103.19,
        "non_facility_rate": 103.19,
        "global_period": "XXX"
    },
    "00902": {
        "description": "Anesthesia for anorectal procedures",
        "category": "Anesthesia",
        "work_rvu": 3.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.10,
        "total_rvu": 3.10,
        "base_units": 5,
        "facility_rate": 103.19,
        "non_facility_rate": 103.19,
        "global_period": "XXX"
    },
    
    # ============================================
    # SURGERY - INTEGUMENTARY (10000-19999)
    # ============================================
    "10060": {
        "description": "Incision and drainage of abscess, simple",
        "category": "Surgery",
        "work_rvu": 1.22,
        "pe_rvu": 2.43,
        "mp_rvu": 0.12,
        "total_rvu": 3.77,
        "facility_rate": 125.53,
        "non_facility_rate": 159.69,
        "global_period": "010"
    },
    "10061": {
        "description": "Incision and drainage of abscess, complicated",
        "category": "Surgery",
        "work_rvu": 2.45,
        "pe_rvu": 3.50,
        "mp_rvu": 0.25,
        "total_rvu": 6.20,
        "facility_rate": 206.38,
        "non_facility_rate": 258.60,
        "global_period": "010"
    },
    "10120": {
        "description": "Incision and removal of foreign body, simple",
        "category": "Surgery",
        "work_rvu": 1.47,
        "pe_rvu": 2.62,
        "mp_rvu": 0.13,
        "total_rvu": 4.22,
        "facility_rate": 140.49,
        "non_facility_rate": 178.80,
        "global_period": "010"
    },
    "10121": {
        "description": "Incision and removal of foreign body, complicated",
        "category": "Surgery",
        "work_rvu": 2.96,
        "pe_rvu": 4.20,
        "mp_rvu": 0.28,
        "total_rvu": 7.44,
        "facility_rate": 247.66,
        "non_facility_rate": 312.94,
        "global_period": "010"
    },
    "11000": {
        "description": "Debridement of infected skin, up to 10% body surface",
        "category": "Surgery",
        "work_rvu": 0.50,
        "pe_rvu": 0.72,
        "mp_rvu": 0.04,
        "total_rvu": 1.26,
        "facility_rate": 41.94,
        "non_facility_rate": 50.53,
        "global_period": "000"
    },
    "11042": {
        "description": "Debridement, subcutaneous tissue, first 20 sq cm",
        "category": "Surgery",
        "work_rvu": 1.01,
        "pe_rvu": 2.14,
        "mp_rvu": 0.10,
        "total_rvu": 3.25,
        "facility_rate": 108.20,
        "non_facility_rate": 139.82,
        "global_period": "000"
    },
    "11102": {
        "description": "Tangential biopsy of skin, single lesion",
        "category": "Surgery",
        "work_rvu": 0.45,
        "pe_rvu": 1.51,
        "mp_rvu": 0.05,
        "total_rvu": 2.01,
        "facility_rate": 66.93,
        "non_facility_rate": 87.39,
        "global_period": "000"
    },
    "11104": {
        "description": "Punch biopsy of skin, single lesion",
        "category": "Surgery",
        "work_rvu": 0.61,
        "pe_rvu": 1.64,
        "mp_rvu": 0.06,
        "total_rvu": 2.31,
        "facility_rate": 76.89,
        "non_facility_rate": 99.36,
        "global_period": "000"
    },
    "11200": {
        "description": "Removal of skin tags, up to 15 lesions",
        "category": "Surgery",
        "work_rvu": 0.80,
        "pe_rvu": 1.85,
        "mp_rvu": 0.07,
        "total_rvu": 2.72,
        "facility_rate": 90.54,
        "non_facility_rate": 117.43,
        "global_period": "010"
    },
    "11300": {
        "description": "Shaving of epidermal lesion, trunk/arm/leg, 0.5 cm or less",
        "category": "Surgery",
        "work_rvu": 0.47,
        "pe_rvu": 1.42,
        "mp_rvu": 0.05,
        "total_rvu": 1.94,
        "facility_rate": 64.58,
        "non_facility_rate": 84.06,
        "global_period": "000"
    },
    "11400": {
        "description": "Excision, benign lesion, trunk/arm/leg, 0.5 cm or less",
        "category": "Surgery",
        "work_rvu": 0.90,
        "pe_rvu": 2.35,
        "mp_rvu": 0.08,
        "total_rvu": 3.33,
        "facility_rate": 110.87,
        "non_facility_rate": 145.53,
        "global_period": "010"
    },
    "11401": {
        "description": "Excision, benign lesion, trunk/arm/leg, 0.6-1.0 cm",
        "category": "Surgery",
        "work_rvu": 1.13,
        "pe_rvu": 2.58,
        "mp_rvu": 0.10,
        "total_rvu": 3.81,
        "facility_rate": 126.86,
        "non_facility_rate": 164.18,
        "global_period": "010"
    },
    "11402": {
        "description": "Excision, benign lesion, trunk/arm/leg, 1.1-2.0 cm",
        "category": "Surgery",
        "work_rvu": 1.42,
        "pe_rvu": 2.87,
        "mp_rvu": 0.13,
        "total_rvu": 4.42,
        "facility_rate": 147.15,
        "non_facility_rate": 188.46,
        "global_period": "010"
    },
    "11600": {
        "description": "Excision, malignant lesion, trunk/arm/leg, 0.5 cm or less",
        "category": "Surgery",
        "work_rvu": 1.33,
        "pe_rvu": 2.70,
        "mp_rvu": 0.12,
        "total_rvu": 4.15,
        "facility_rate": 138.16,
        "non_facility_rate": 176.47,
        "global_period": "010"
    },
    "11601": {
        "description": "Excision, malignant lesion, trunk/arm/leg, 0.6-1.0 cm",
        "category": "Surgery",
        "work_rvu": 1.68,
        "pe_rvu": 2.98,
        "mp_rvu": 0.15,
        "total_rvu": 4.81,
        "facility_rate": 160.12,
        "non_facility_rate": 202.08,
        "global_period": "010"
    },
    "12001": {
        "description": "Simple repair of superficial wounds, 2.5 cm or less",
        "category": "Surgery",
        "work_rvu": 1.00,
        "pe_rvu": 1.80,
        "mp_rvu": 0.10,
        "total_rvu": 2.90,
        "facility_rate": 96.53,
        "non_facility_rate": 121.03,
        "global_period": "010"
    },
    "12002": {
        "description": "Simple repair of superficial wounds, 2.6-7.5 cm",
        "category": "Surgery",
        "work_rvu": 1.35,
        "pe_rvu": 2.10,
        "mp_rvu": 0.12,
        "total_rvu": 3.57,
        "facility_rate": 118.86,
        "non_facility_rate": 147.47,
        "global_period": "010"
    },
    "12011": {
        "description": "Simple repair of superficial wounds of face, 2.5 cm or less",
        "category": "Surgery",
        "work_rvu": 1.23,
        "pe_rvu": 1.95,
        "mp_rvu": 0.11,
        "total_rvu": 3.29,
        "facility_rate": 109.53,
        "non_facility_rate": 136.42,
        "global_period": "010"
    },
    
    # ============================================
    # SURGERY - MUSCULOSKELETAL (20000-29999)
    # ============================================
    "20200": {
        "description": "Muscle biopsy, superficial",
        "category": "Surgery",
        "work_rvu": 1.15,
        "pe_rvu": 2.63,
        "mp_rvu": 0.10,
        "total_rvu": 3.88,
        "facility_rate": 129.20,
        "non_facility_rate": 169.17,
        "global_period": "000"
    },
    "20220": {
        "description": "Bone biopsy, trocar or needle, superficial",
        "category": "Surgery",
        "work_rvu": 1.53,
        "pe_rvu": 2.95,
        "mp_rvu": 0.14,
        "total_rvu": 4.62,
        "facility_rate": 153.79,
        "non_facility_rate": 197.09,
        "global_period": "000"
    },
    "20550": {
        "description": "Injection, single tendon sheath or ligament",
        "category": "Surgery",
        "work_rvu": 0.75,
        "pe_rvu": 1.28,
        "mp_rvu": 0.05,
        "total_rvu": 2.08,
        "facility_rate": 69.24,
        "non_facility_rate": 86.05,
        "global_period": "000"
    },
    "20551": {
        "description": "Injection, single tendon origin/insertion",
        "category": "Surgery",
        "work_rvu": 0.75,
        "pe_rvu": 1.25,
        "mp_rvu": 0.05,
        "total_rvu": 2.05,
        "facility_rate": 68.24,
        "non_facility_rate": 84.73,
        "global_period": "000"
    },
    "20552": {
        "description": "Injection, single or multiple trigger point(s), 1 or 2 muscles",
        "category": "Surgery",
        "work_rvu": 0.61,
        "pe_rvu": 1.08,
        "mp_rvu": 0.04,
        "total_rvu": 1.73,
        "facility_rate": 57.59,
        "non_facility_rate": 72.08,
        "global_period": "000"
    },
    "20553": {
        "description": "Injection, single or multiple trigger point(s), 3 or more muscles",
        "category": "Surgery",
        "work_rvu": 0.77,
        "pe_rvu": 1.28,
        "mp_rvu": 0.05,
        "total_rvu": 2.10,
        "facility_rate": 69.90,
        "non_facility_rate": 87.38,
        "global_period": "000"
    },
    "20600": {
        "description": "Arthrocentesis, aspiration and/or injection, small joint",
        "category": "Surgery",
        "work_rvu": 0.66,
        "pe_rvu": 1.12,
        "mp_rvu": 0.04,
        "total_rvu": 1.82,
        "facility_rate": 60.58,
        "non_facility_rate": 75.41,
        "global_period": "000"
    },
    "20605": {
        "description": "Arthrocentesis, aspiration and/or injection, intermediate joint",
        "category": "Surgery",
        "work_rvu": 0.74,
        "pe_rvu": 1.20,
        "mp_rvu": 0.05,
        "total_rvu": 1.99,
        "facility_rate": 66.26,
        "non_facility_rate": 82.40,
        "global_period": "000"
    },
    "20610": {
        "description": "Arthrocentesis, aspiration and/or injection, major joint",
        "category": "Surgery",
        "work_rvu": 0.86,
        "pe_rvu": 1.35,
        "mp_rvu": 0.06,
        "total_rvu": 2.27,
        "facility_rate": 75.56,
        "non_facility_rate": 93.69,
        "global_period": "000"
    },
    
    # Fracture Care
    "25500": {
        "description": "Closed treatment of radial shaft fracture without manipulation",
        "category": "Surgery",
        "work_rvu": 2.72,
        "pe_rvu": 2.95,
        "mp_rvu": 0.33,
        "total_rvu": 6.00,
        "facility_rate": 199.73,
        "non_facility_rate": 226.61,
        "global_period": "090"
    },
    "25505": {
        "description": "Closed treatment of radial shaft fracture with manipulation",
        "category": "Surgery",
        "work_rvu": 4.76,
        "pe_rvu": 3.82,
        "mp_rvu": 0.58,
        "total_rvu": 9.16,
        "facility_rate": 304.95,
        "non_facility_rate": 343.49,
        "global_period": "090"
    },
    "27500": {
        "description": "Closed treatment of femoral shaft fracture without manipulation",
        "category": "Surgery",
        "work_rvu": 3.87,
        "pe_rvu": 2.38,
        "mp_rvu": 0.47,
        "total_rvu": 6.72,
        "facility_rate": 223.69,
        "non_facility_rate": 250.58,
        "global_period": "090"
    },
    "27501": {
        "description": "Closed treatment of femoral shaft fracture with manipulation",
        "category": "Surgery",
        "work_rvu": 6.46,
        "pe_rvu": 3.50,
        "mp_rvu": 0.79,
        "total_rvu": 10.75,
        "facility_rate": 357.84,
        "non_facility_rate": 396.71,
        "global_period": "090"
    },
    
    # ============================================
    # RADIOLOGY (70000-79999)
    # ============================================
    "70030": {
        "description": "Radiologic examination, eye, for detection of foreign body",
        "category": "Radiology",
        "work_rvu": 0.22,
        "pe_rvu": 0.49,
        "mp_rvu": 0.01,
        "total_rvu": 0.72,
        "facility_rate": 23.97,
        "non_facility_rate": 30.38,
        "global_period": "XXX"
    },
    "70100": {
        "description": "Radiologic exam, mandible, partial, less than 4 views",
        "category": "Radiology",
        "work_rvu": 0.18,
        "pe_rvu": 0.48,
        "mp_rvu": 0.01,
        "total_rvu": 0.67,
        "facility_rate": 22.30,
        "non_facility_rate": 28.38,
        "global_period": "XXX"
    },
    "70110": {
        "description": "Radiologic exam, mandible, complete, minimum of 4 views",
        "category": "Radiology",
        "work_rvu": 0.24,
        "pe_rvu": 0.65,
        "mp_rvu": 0.01,
        "total_rvu": 0.90,
        "facility_rate": 29.96,
        "non_facility_rate": 37.70,
        "global_period": "XXX"
    },
    "70140": {
        "description": "Radiologic examination, facial bones, less than 3 views",
        "category": "Radiology",
        "work_rvu": 0.17,
        "pe_rvu": 0.45,
        "mp_rvu": 0.01,
        "total_rvu": 0.63,
        "facility_rate": 20.97,
        "non_facility_rate": 26.72,
        "global_period": "XXX"
    },
    "70150": {
        "description": "Radiologic examination, facial bones, complete, minimum of 3 views",
        "category": "Radiology",
        "work_rvu": 0.22,
        "pe_rvu": 0.60,
        "mp_rvu": 0.01,
        "total_rvu": 0.83,
        "facility_rate": 27.63,
        "non_facility_rate": 35.04,
        "global_period": "XXX"
    },
    "70200": {
        "description": "Radiologic examination, orbits, complete, minimum of 4 views",
        "category": "Radiology",
        "work_rvu": 0.23,
        "pe_rvu": 0.63,
        "mp_rvu": 0.01,
        "total_rvu": 0.87,
        "facility_rate": 28.96,
        "non_facility_rate": 36.70,
        "global_period": "XXX"
    },
    "70210": {
        "description": "Radiologic examination, sinuses, paranasal, less than 3 views",
        "category": "Radiology",
        "work_rvu": 0.17,
        "pe_rvu": 0.45,
        "mp_rvu": 0.01,
        "total_rvu": 0.63,
        "facility_rate": 20.97,
        "non_facility_rate": 26.72,
        "global_period": "XXX"
    },
    "70220": {
        "description": "Radiologic examination, sinuses, paranasal, complete, minimum of 3 views",
        "category": "Radiology",
        "work_rvu": 0.21,
        "pe_rvu": 0.58,
        "mp_rvu": 0.01,
        "total_rvu": 0.80,
        "facility_rate": 26.63,
        "non_facility_rate": 33.71,
        "global_period": "XXX"
    },
    "70250": {
        "description": "Radiologic examination, skull, less than 4 views",
        "category": "Radiology",
        "work_rvu": 0.19,
        "pe_rvu": 0.53,
        "mp_rvu": 0.01,
        "total_rvu": 0.73,
        "facility_rate": 24.30,
        "non_facility_rate": 30.71,
        "global_period": "XXX"
    },
    "70260": {
        "description": "Radiologic examination, skull, complete, minimum of 4 views",
        "category": "Radiology",
        "work_rvu": 0.24,
        "pe_rvu": 0.68,
        "mp_rvu": 0.01,
        "total_rvu": 0.93,
        "facility_rate": 30.96,
        "non_facility_rate": 39.03,
        "global_period": "XXX"
    },
    
    # CT Scans
    "70450": {
        "description": "CT head/brain without contrast",
        "category": "Radiology",
        "work_rvu": 0.85,
        "pe_rvu": 3.76,
        "mp_rvu": 0.04,
        "total_rvu": 4.65,
        "facility_rate": 154.79,
        "non_facility_rate": 197.10,
        "global_period": "XXX"
    },
    "70460": {
        "description": "CT head/brain with contrast",
        "category": "Radiology",
        "work_rvu": 1.13,
        "pe_rvu": 4.52,
        "mp_rvu": 0.05,
        "total_rvu": 5.70,
        "facility_rate": 189.74,
        "non_facility_rate": 241.62,
        "global_period": "XXX"
    },
    "70470": {
        "description": "CT head/brain without contrast, followed by contrast",
        "category": "Radiology",
        "work_rvu": 1.27,
        "pe_rvu": 5.18,
        "mp_rvu": 0.06,
        "total_rvu": 6.51,
        "facility_rate": 216.70,
        "non_facility_rate": 275.59,
        "global_period": "XXX"
    },
    "70486": {
        "description": "CT maxillofacial without contrast",
        "category": "Radiology",
        "work_rvu": 0.95,
        "pe_rvu": 4.25,
        "mp_rvu": 0.04,
        "total_rvu": 5.24,
        "facility_rate": 174.43,
        "non_facility_rate": 222.31,
        "global_period": "XXX"
    },
    "70490": {
        "description": "CT soft tissue neck without contrast",
        "category": "Radiology",
        "work_rvu": 1.28,
        "pe_rvu": 4.65,
        "mp_rvu": 0.06,
        "total_rvu": 5.99,
        "facility_rate": 199.40,
        "non_facility_rate": 253.28,
        "global_period": "XXX"
    },
    
    # MRI
    "70551": {
        "description": "MRI brain without contrast",
        "category": "Radiology",
        "work_rvu": 1.40,
        "pe_rvu": 7.89,
        "mp_rvu": 0.06,
        "total_rvu": 9.35,
        "facility_rate": 311.27,
        "non_facility_rate": 401.51,
        "global_period": "XXX"
    },
    "70552": {
        "description": "MRI brain with contrast",
        "category": "Radiology",
        "work_rvu": 1.73,
        "pe_rvu": 9.14,
        "mp_rvu": 0.08,
        "total_rvu": 10.95,
        "facility_rate": 364.50,
        "non_facility_rate": 467.40,
        "global_period": "XXX"
    },
    "70553": {
        "description": "MRI brain without contrast, followed by contrast",
        "category": "Radiology",
        "work_rvu": 2.15,
        "pe_rvu": 10.38,
        "mp_rvu": 0.10,
        "total_rvu": 12.63,
        "facility_rate": 420.41,
        "non_facility_rate": 538.98,
        "global_period": "XXX"
    },
    
    # Chest X-rays
    "71045": {
        "description": "Radiologic examination, chest, single view",
        "category": "Radiology",
        "work_rvu": 0.18,
        "pe_rvu": 0.48,
        "mp_rvu": 0.01,
        "total_rvu": 0.67,
        "facility_rate": 22.30,
        "non_facility_rate": 28.38,
        "global_period": "XXX"
    },
    "71046": {
        "description": "Radiologic examination, chest, 2 views",
        "category": "Radiology",
        "work_rvu": 0.22,
        "pe_rvu": 0.58,
        "mp_rvu": 0.01,
        "total_rvu": 0.81,
        "facility_rate": 26.96,
        "non_facility_rate": 34.04,
        "global_period": "XXX"
    },
    "71047": {
        "description": "Radiologic examination, chest, 3 views",
        "category": "Radiology",
        "work_rvu": 0.26,
        "pe_rvu": 0.68,
        "mp_rvu": 0.01,
        "total_rvu": 0.95,
        "facility_rate": 31.62,
        "non_facility_rate": 40.03,
        "global_period": "XXX"
    },
    "71048": {
        "description": "Radiologic examination, chest, 4 or more views",
        "category": "Radiology",
        "work_rvu": 0.27,
        "pe_rvu": 0.73,
        "mp_rvu": 0.01,
        "total_rvu": 1.01,
        "facility_rate": 33.62,
        "non_facility_rate": 42.36,
        "global_period": "XXX"
    },
    
    # Chest CT
    "71250": {
        "description": "CT thorax without contrast",
        "category": "Radiology",
        "work_rvu": 1.16,
        "pe_rvu": 5.12,
        "mp_rvu": 0.05,
        "total_rvu": 6.33,
        "facility_rate": 210.71,
        "non_facility_rate": 268.59,
        "global_period": "XXX"
    },
    "71260": {
        "description": "CT thorax with contrast",
        "category": "Radiology",
        "work_rvu": 1.38,
        "pe_rvu": 5.92,
        "mp_rvu": 0.06,
        "total_rvu": 7.36,
        "facility_rate": 245.00,
        "non_facility_rate": 311.54,
        "global_period": "XXX"
    },
    "71270": {
        "description": "CT thorax without contrast, followed by contrast",
        "category": "Radiology",
        "work_rvu": 1.62,
        "pe_rvu": 6.62,
        "mp_rvu": 0.07,
        "total_rvu": 8.31,
        "facility_rate": 276.63,
        "non_facility_rate": 352.18,
        "global_period": "XXX"
    },
    
    # Abdominal X-rays
    "74018": {
        "description": "Radiologic examination, abdomen, 1 view",
        "category": "Radiology",
        "work_rvu": 0.20,
        "pe_rvu": 0.50,
        "mp_rvu": 0.01,
        "total_rvu": 0.71,
        "facility_rate": 23.63,
        "non_facility_rate": 30.05,
        "global_period": "XXX"
    },
    "74019": {
        "description": "Radiologic examination, abdomen, 2 views",
        "category": "Radiology",
        "work_rvu": 0.23,
        "pe_rvu": 0.58,
        "mp_rvu": 0.01,
        "total_rvu": 0.82,
        "facility_rate": 27.30,
        "non_facility_rate": 34.37,
        "global_period": "XXX"
    },
    "74021": {
        "description": "Radiologic examination, abdomen, 3 or more views",
        "category": "Radiology",
        "work_rvu": 0.26,
        "pe_rvu": 0.67,
        "mp_rvu": 0.01,
        "total_rvu": 0.94,
        "facility_rate": 31.29,
        "non_facility_rate": 39.69,
        "global_period": "XXX"
    },
    
    # Abdominal CT
    "74150": {
        "description": "CT abdomen without contrast",
        "category": "Radiology",
        "work_rvu": 1.19,
        "pe_rvu": 5.32,
        "mp_rvu": 0.05,
        "total_rvu": 6.56,
        "facility_rate": 218.37,
        "non_facility_rate": 278.26,
        "global_period": "XXX"
    },
    "74160": {
        "description": "CT abdomen with contrast",
        "category": "Radiology",
        "work_rvu": 1.40,
        "pe_rvu": 6.08,
        "mp_rvu": 0.06,
        "total_rvu": 7.54,
        "facility_rate": 250.99,
        "non_facility_rate": 319.20,
        "global_period": "XXX"
    },
    "74170": {
        "description": "CT abdomen without contrast, followed by contrast",
        "category": "Radiology",
        "work_rvu": 1.65,
        "pe_rvu": 6.82,
        "mp_rvu": 0.07,
        "total_rvu": 8.54,
        "facility_rate": 284.29,
        "non_facility_rate": 361.84,
        "global_period": "XXX"
    },
    "74176": {
        "description": "CT abdomen and pelvis without contrast",
        "category": "Radiology",
        "work_rvu": 1.74,
        "pe_rvu": 7.85,
        "mp_rvu": 0.08,
        "total_rvu": 9.67,
        "facility_rate": 321.91,
        "non_facility_rate": 410.15,
        "global_period": "XXX"
    },
    "74177": {
        "description": "CT abdomen and pelvis with contrast",
        "category": "Radiology",
        "work_rvu": 2.01,
        "pe_rvu": 8.85,
        "mp_rvu": 0.09,
        "total_rvu": 10.95,
        "facility_rate": 364.50,
        "non_facility_rate": 464.40,
        "global_period": "XXX"
    },
    "74178": {
        "description": "CT abdomen and pelvis without contrast, followed by contrast",
        "category": "Radiology",
        "work_rvu": 2.33,
        "pe_rvu": 9.78,
        "mp_rvu": 0.10,
        "total_rvu": 12.21,
        "facility_rate": 406.44,
        "non_facility_rate": 517.34,
        "global_period": "XXX"
    },
    
    # ============================================
    # PATHOLOGY AND LABORATORY (80000-89999)
    # ============================================
    
    # Chemistry Panels
    "80048": {
        "description": "Basic metabolic panel (BMP)",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 10.56,
        "non_facility_rate": 10.56,
        "global_period": "XXX"
    },
    "80050": {
        "description": "General health panel",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 28.12,
        "non_facility_rate": 28.12,
        "global_period": "XXX"
    },
    "80053": {
        "description": "Comprehensive metabolic panel (CMP)",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 14.49,
        "non_facility_rate": 14.49,
        "global_period": "XXX"
    },
    "80061": {
        "description": "Lipid panel",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 18.37,
        "non_facility_rate": 18.37,
        "global_period": "XXX"
    },
    "80069": {
        "description": "Renal function panel",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 10.10,
        "non_facility_rate": 10.10,
        "global_period": "XXX"
    },
    "80074": {
        "description": "Acute hepatitis panel",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 63.51,
        "non_facility_rate": 63.51,
        "global_period": "XXX"
    },
    "80076": {
        "description": "Hepatic function panel",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 11.02,
        "non_facility_rate": 11.02,
        "global_period": "XXX"
    },
    
    # Individual Chemistry Tests
    "82040": {
        "description": "Albumin, serum",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 5.55,
        "non_facility_rate": 5.55,
        "global_period": "XXX"
    },
    "82150": {
        "description": "Amylase",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 8.16,
        "non_facility_rate": 8.16,
        "global_period": "XXX"
    },
    "82247": {
        "description": "Bilirubin, total",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 5.93,
        "non_facility_rate": 5.93,
        "global_period": "XXX"
    },
    "82310": {
        "description": "Calcium, total",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 5.93,
        "non_facility_rate": 5.93,
        "global_period": "XXX"
    },
    "82374": {
        "description": "Carbon dioxide (bicarbonate)",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 5.60,
        "non_facility_rate": 5.60,
        "global_period": "XXX"
    },
    "82435": {
        "description": "Chloride, serum",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 5.60,
        "non_facility_rate": 5.60,
        "global_period": "XXX"
    },
    "82550": {
        "description": "Creatine kinase (CK), total",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 9.15,
        "non_facility_rate": 9.15,
        "global_period": "XXX"
    },
    "82565": {
        "description": "Creatinine, blood",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 6.43,
        "non_facility_rate": 6.43,
        "global_period": "XXX"
    },
    "82947": {
        "description": "Glucose, quantitative, blood",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 5.14,
        "non_facility_rate": 5.14,
        "global_period": "XXX"
    },
    "83036": {
        "description": "Hemoglobin A1c",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 11.30,
        "non_facility_rate": 11.30,
        "global_period": "XXX"
    },
    "84132": {
        "description": "Potassium, serum",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 5.72,
        "non_facility_rate": 5.72,
        "global_period": "XXX"
    },
    "84295": {
        "description": "Sodium, serum",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 5.72,
        "non_facility_rate": 5.72,
        "global_period": "XXX"
    },
    "84443": {
        "description": "Thyroid stimulating hormone (TSH)",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 17.51,
        "non_facility_rate": 17.51,
        "global_period": "XXX"
    },
    "84450": {
        "description": "AST (SGOT)",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 6.68,
        "non_facility_rate": 6.68,
        "global_period": "XXX"
    },
    "84460": {
        "description": "ALT (SGPT)",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 6.68,
        "non_facility_rate": 6.68,
        "global_period": "XXX"
    },
    "84478": {
        "description": "Triglycerides",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 8.48,
        "non_facility_rate": 8.48,
        "global_period": "XXX"
    },
    "84520": {
        "description": "Urea nitrogen (BUN)",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 4.89,
        "non_facility_rate": 4.89,
        "global_period": "XXX"
    },
    "84550": {
        "description": "Uric acid, blood",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 5.76,
        "non_facility_rate": 5.76,
        "global_period": "XXX"
    },
    
    # Hematology
    "85025": {
        "description": "Complete blood count (CBC) with differential, automated",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 9.07,
        "non_facility_rate": 9.07,
        "global_period": "XXX"
    },
    "85027": {
        "description": "Complete blood count (CBC), automated",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 7.71,
        "non_facility_rate": 7.71,
        "global_period": "XXX"
    },
    "85610": {
        "description": "Prothrombin time (PT)",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 5.23,
        "non_facility_rate": 5.23,
        "global_period": "XXX"
    },
    "85730": {
        "description": "Partial thromboplastin time (PTT)",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 7.21,
        "non_facility_rate": 7.21,
        "global_period": "XXX"
    },
    
    # Urinalysis
    "81001": {
        "description": "Urinalysis, by dip stick, automated, with microscopy",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 4.25,
        "non_facility_rate": 4.25,
        "global_period": "XXX"
    },
    "81002": {
        "description": "Urinalysis, by dip stick, non-automated, without microscopy",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 3.42,
        "non_facility_rate": 3.42,
        "global_period": "XXX"
    },
    "81003": {
        "description": "Urinalysis, by dip stick, automated, without microscopy",
        "category": "Pathology/Lab",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 2.77,
        "non_facility_rate": 2.77,
        "global_period": "XXX"
    },
    
    # ============================================
    # MEDICINE (90000-99999 - Non-E/M)
    # ============================================
    
    # Immunizations
    "90471": {
        "description": "Immunization administration, first vaccine",
        "category": "Medicine",
        "work_rvu": 0.17,
        "pe_rvu": 0.65,
        "mp_rvu": 0.02,
        "total_rvu": 0.84,
        "facility_rate": 27.96,
        "non_facility_rate": 35.70,
        "global_period": "XXX"
    },
    "90472": {
        "description": "Immunization administration, each additional vaccine",
        "category": "Medicine",
        "work_rvu": 0.15,
        "pe_rvu": 0.36,
        "mp_rvu": 0.01,
        "total_rvu": 0.52,
        "facility_rate": 17.31,
        "non_facility_rate": 22.04,
        "global_period": "ZZZ"
    },
    "90473": {
        "description": "Immunization administration by intranasal/oral, first vaccine",
        "category": "Medicine",
        "work_rvu": 0.17,
        "pe_rvu": 0.66,
        "mp_rvu": 0.02,
        "total_rvu": 0.85,
        "facility_rate": 28.29,
        "non_facility_rate": 36.04,
        "global_period": "XXX"
    },
    "90474": {
        "description": "Immunization administration by intranasal/oral, each additional",
        "category": "Medicine",
        "work_rvu": 0.15,
        "pe_rvu": 0.35,
        "mp_rvu": 0.01,
        "total_rvu": 0.51,
        "facility_rate": 16.98,
        "non_facility_rate": 21.71,
        "global_period": "ZZZ"
    },
    
    # Vaccines
    "90658": {
        "description": "Influenza virus vaccine, IIV, split, preservative free",
        "category": "Medicine",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 18.27,
        "non_facility_rate": 18.27,
        "global_period": "XXX"
    },
    "90670": {
        "description": "Pneumococcal conjugate vaccine, 13 valent",
        "category": "Medicine",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 213.26,
        "non_facility_rate": 213.26,
        "global_period": "XXX"
    },
    "90732": {
        "description": "Pneumococcal vaccine, 23-valent, adult",
        "category": "Medicine",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 81.91,
        "non_facility_rate": 81.91,
        "global_period": "XXX"
    },
    "90746": {
        "description": "Hepatitis B vaccine, adult, 3 dose schedule",
        "category": "Medicine",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 48.05,
        "non_facility_rate": 48.05,
        "global_period": "XXX"
    },
    
    # Cardiovascular
    "93000": {
        "description": "Electrocardiogram (ECG), complete",
        "category": "Medicine",
        "work_rvu": 0.17,
        "pe_rvu": 0.65,
        "mp_rvu": 0.01,
        "total_rvu": 0.83,
        "facility_rate": 27.63,
        "non_facility_rate": 35.04,
        "global_period": "XXX"
    },
    "93005": {
        "description": "Electrocardiogram (ECG), tracing only",
        "category": "Medicine",
        "work_rvu": 0.00,
        "pe_rvu": 0.37,
        "mp_rvu": 0.00,
        "total_rvu": 0.37,
        "facility_rate": 12.32,
        "non_facility_rate": 16.38,
        "global_period": "XXX"
    },
    "93010": {
        "description": "Electrocardiogram (ECG), interpretation and report only",
        "category": "Medicine",
        "work_rvu": 0.17,
        "pe_rvu": 0.06,
        "mp_rvu": 0.01,
        "total_rvu": 0.24,
        "facility_rate": 7.99,
        "non_facility_rate": 10.32,
        "global_period": "XXX"
    },
    "93306": {
        "description": "Echocardiography, complete, with Doppler",
        "category": "Medicine",
        "work_rvu": 1.30,
        "pe_rvu": 4.10,
        "mp_rvu": 0.05,
        "total_rvu": 5.45,
        "facility_rate": 181.42,
        "non_facility_rate": 230.82,
        "global_period": "XXX"
    },
    "93350": {
        "description": "Echocardiography, stress test, complete",
        "category": "Medicine",
        "work_rvu": 1.50,
        "pe_rvu": 4.84,
        "mp_rvu": 0.07,
        "total_rvu": 6.41,
        "facility_rate": 213.37,
        "non_facility_rate": 271.25,
        "global_period": "XXX"
    },
    
    # Pulmonary
    "94010": {
        "description": "Spirometry, including graphic record, total and timed vital capacity",
        "category": "Medicine",
        "work_rvu": 0.17,
        "pe_rvu": 0.87,
        "mp_rvu": 0.01,
        "total_rvu": 1.05,
        "facility_rate": 34.95,
        "non_facility_rate": 44.36,
        "global_period": "XXX"
    },
    "94060": {
        "description": "Bronchodilation responsiveness, spirometry before and after",
        "category": "Medicine",
        "work_rvu": 0.31,
        "pe_rvu": 1.37,
        "mp_rvu": 0.02,
        "total_rvu": 1.70,
        "facility_rate": 56.59,
        "non_facility_rate": 71.74,
        "global_period": "XXX"
    },
    "94375": {
        "description": "Respiratory flow volume loop",
        "category": "Medicine",
        "work_rvu": 0.21,
        "pe_rvu": 0.53,
        "mp_rvu": 0.01,
        "total_rvu": 0.75,
        "facility_rate": 24.97,
        "non_facility_rate": 31.71,
        "global_period": "XXX"
    },
    "94640": {
        "description": "Nebulizer treatment, inhalation treatment",
        "category": "Medicine",
        "work_rvu": 0.00,
        "pe_rvu": 0.42,
        "mp_rvu": 0.00,
        "total_rvu": 0.42,
        "facility_rate": 13.98,
        "non_facility_rate": 17.71,
        "global_period": "XXX"
    },
    "94760": {
        "description": "Pulse oximetry, single determination",
        "category": "Medicine",
        "work_rvu": 0.00,
        "pe_rvu": 0.07,
        "mp_rvu": 0.00,
        "total_rvu": 0.07,
        "facility_rate": 2.33,
        "non_facility_rate": 3.00,
        "global_period": "XXX"
    },
    
    # Physical Medicine/Rehabilitation
    "97110": {
        "description": "Therapeutic exercises, each 15 minutes",
        "category": "Medicine",
        "work_rvu": 0.45,
        "pe_rvu": 0.52,
        "mp_rvu": 0.01,
        "total_rvu": 0.98,
        "facility_rate": 32.62,
        "non_facility_rate": 39.36,
        "global_period": "XXX"
    },
    "97112": {
        "description": "Neuromuscular reeducation, each 15 minutes",
        "category": "Medicine",
        "work_rvu": 0.45,
        "pe_rvu": 0.51,
        "mp_rvu": 0.01,
        "total_rvu": 0.97,
        "facility_rate": 32.29,
        "non_facility_rate": 38.69,
        "global_period": "XXX"
    },
    "97116": {
        "description": "Gait training, each 15 minutes",
        "category": "Medicine",
        "work_rvu": 0.40,
        "pe_rvu": 0.47,
        "mp_rvu": 0.01,
        "total_rvu": 0.88,
        "facility_rate": 29.29,
        "non_facility_rate": 35.36,
        "global_period": "XXX"
    },
    "97140": {
        "description": "Manual therapy techniques, each 15 minutes",
        "category": "Medicine",
        "work_rvu": 0.43,
        "pe_rvu": 0.49,
        "mp_rvu": 0.01,
        "total_rvu": 0.93,
        "facility_rate": 30.96,
        "non_facility_rate": 37.36,
        "global_period": "XXX"
    },
    "97530": {
        "description": "Therapeutic activities, each 15 minutes",
        "category": "Medicine",
        "work_rvu": 0.44,
        "pe_rvu": 0.50,
        "mp_rvu": 0.01,
        "total_rvu": 0.95,
        "facility_rate": 31.62,
        "non_facility_rate": 38.03,
        "global_period": "XXX"
    },
    
    # ============================================
    # HCPCS LEVEL II CODES
    # ============================================
    "J0585": {
        "description": "Injection, onabotulinumtoxinA, 1 unit",
        "category": "HCPCS",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 6.55,
        "non_facility_rate": 6.55,
        "global_period": "XXX"
    },
    "J1100": {
        "description": "Injection, dexamethasone sodium phosphate, 1 mg",
        "category": "HCPCS",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 0.09,
        "non_facility_rate": 0.09,
        "global_period": "XXX"
    },
    "J1885": {
        "description": "Injection, ketorolac tromethamine, per 15 mg",
        "category": "HCPCS",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 0.90,
        "non_facility_rate": 0.90,
        "global_period": "XXX"
    },
    "J2001": {
        "description": "Injection, lidocaine HCl, 10 mg",
        "category": "HCPCS",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 0.05,
        "non_facility_rate": 0.05,
        "global_period": "XXX"
    },
    "J3301": {
        "description": "Injection, triamcinolone acetonide, per 10 mg",
        "category": "HCPCS",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 1.25,
        "non_facility_rate": 1.25,
        "global_period": "XXX"
    },
    "J3420": {
        "description": "Injection, vitamin B12 cyanocobalamin, up to 1000 mcg",
        "category": "HCPCS",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 0.36,
        "non_facility_rate": 0.36,
        "global_period": "XXX"
    },
    
    # DME
    "E0100": {
        "description": "Cane, includes canes of all materials, adjustable or fixed",
        "category": "HCPCS",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 17.44,
        "non_facility_rate": 17.44,
        "global_period": "XXX"
    },
    "E0105": {
        "description": "Cane, quad or three prong, includes canes of all materials",
        "category": "HCPCS",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 38.57,
        "non_facility_rate": 38.57,
        "global_period": "XXX"
    },
    "E0110": {
        "description": "Crutches, forearm, includes crutches of various materials",
        "category": "HCPCS",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 61.22,
        "non_facility_rate": 61.22,
        "global_period": "XXX"
    },
    "E0130": {
        "description": "Walker, rigid, adjustable or fixed height",
        "category": "HCPCS",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 47.42,
        "non_facility_rate": 47.42,
        "global_period": "XXX"
    },
    "E0143": {
        "description": "Walker, folding, wheeled, adjustable or fixed height",
        "category": "HCPCS",
        "work_rvu": 0.00,
        "pe_rvu": 0.00,
        "mp_rvu": 0.00,
        "total_rvu": 0.00,
        "facility_rate": 70.93,
        "non_facility_rate": 70.93,
        "global_period": "XXX"
    },
}

def get_cpt_code(code: str) -> Optional[Dict]:
    """Get CPT code information by code"""
    return CPT_CODES_DATABASE.get(code)

def get_codes_by_category(category: str) -> List[Dict]:
    """Get all CPT codes in a category"""
    return [
        {"code": code, **data}
        for code, data in CPT_CODES_DATABASE.items()
        if data.get("category") == category
    ]

def calculate_medicare_rate(code: str, locality_code: str = "00000", use_facility: bool = True) -> Optional[float]:
    """
    Calculate Medicare reimbursement rate with GPCI adjustments
    
    Formula: [(Work RVU × Work GPCI) + (PE RVU × PE GPCI) + (MP RVU × MP GPCI)] × Conversion Factor
    """
    cpt_data = CPT_CODES_DATABASE.get(code)
    if not cpt_data:
        return None
    
    gpci = GPCI_LOCALITIES.get(locality_code, GPCI_LOCALITIES["00000"])
    
    # For lab/path codes with 0 RVUs, use the fixed rate
    if cpt_data["work_rvu"] == 0 and cpt_data["pe_rvu"] == 0:
        return cpt_data.get("facility_rate", 0) if use_facility else cpt_data.get("non_facility_rate", 0)
    
    # Calculate GPCI-adjusted rate
    adjusted_work = cpt_data["work_rvu"] * gpci["work"]
    adjusted_pe = cpt_data["pe_rvu"] * gpci["pe"]
    adjusted_mp = cpt_data["mp_rvu"] * gpci["mp"]
    
    total_adjusted_rvu = adjusted_work + adjusted_pe + adjusted_mp
    
    return round(total_adjusted_rvu * CONVERSION_FACTOR_2024, 2)

def get_all_localities() -> Dict:
    """Get all GPCI localities"""
    return GPCI_LOCALITIES

def search_cpt_codes(query: str, limit: int = 50) -> List[Dict]:
    """Search CPT codes by code or description"""
    query_lower = query.lower()
    results = []
    
    for code, data in CPT_CODES_DATABASE.items():
        if query_lower in code.lower() or query_lower in data["description"].lower():
            results.append({"code": code, **data})
            if len(results) >= limit:
                break
    
    return results

# Export all for use in server
__all__ = [
    "CPT_CODES_DATABASE",
    "GPCI_LOCALITIES", 
    "CONVERSION_FACTOR_2024",
    "CONVERSION_FACTOR_2025",
    "get_cpt_code",
    "get_codes_by_category",
    "calculate_medicare_rate",
    "get_all_localities",
    "search_cpt_codes",
]
