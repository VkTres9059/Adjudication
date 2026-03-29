from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
from enum import Enum
import re
from difflib import SequenceMatcher

# Import CPT codes and Medicare fee schedule
from cpt_codes import (
    CPT_CODES_DATABASE,
    GPCI_LOCALITIES,
    CONVERSION_FACTOR_2024,
    get_cpt_code,
    get_codes_by_category,
    calculate_medicare_rate,
    get_all_localities,
    search_cpt_codes,
)

# Import Dental CDT codes
from dental_codes import (
    CDT_CODES_DATABASE,
    DENTAL_BENEFIT_CLASSES,
    get_dental_code,
    search_dental_codes,
    calculate_dental_allowed,
)

# Import Vision codes
from vision_codes import (
    VISION_CODES_DATABASE,
    VISION_BENEFIT_CLASSES,
    get_vision_code,
    search_vision_codes,
    calculate_vision_allowed,
)

# Import Hearing codes
from hearing_codes import (
    HEARING_CODES_DATABASE,
    HEARING_BENEFIT_CLASSES,
    get_hearing_code,
    search_hearing_codes,
    calculate_hearing_allowed,
)
import json
import io

# Import Preventive Services
from preventive_services import (
    PREVENTIVE_SERVICES,
    PREVENTIVE_Z_CODES,
    is_preventive_code,
    is_preventive_diagnosis,
    has_modifier_33,
    get_preventive_service,
    search_preventive_services,
    get_preventive_by_category,
    evaluate_preventive_claim_line,
    check_preventive_frequency,
    record_preventive_utilization,
    calculate_member_age,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'fletchflow-claims-secret-key-2024')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Create the main app
app = FastAPI(title="FletchFlow Claims Adjudication System", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== ENUMS ====================

class UserRole(str, Enum):
    ADMIN = "admin"
    ADJUDICATOR = "adjudicator"
    REVIEWER = "reviewer"
    AUDITOR = "auditor"

class ClaimStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DENIED = "denied"
    DUPLICATE = "duplicate"
    PENDED = "pended"

class ClaimType(str, Enum):
    MEDICAL = "medical"
    DENTAL = "dental"
    VISION = "vision"
    HEARING = "hearing"

class DuplicateType(str, Enum):
    EXACT = "exact"
    NEAR = "near"
    LINE_LEVEL = "line_level"

class PlanStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"

# ==================== MODELS ====================

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: UserRole = UserRole.REVIEWER

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class PlanBenefit(BaseModel):
    service_category: str
    covered: bool = True
    copay: float = 0
    coinsurance: float = 0.2
    deductible_applies: bool = True
    annual_max: Optional[float] = None
    visit_limit: Optional[int] = None
    frequency_limit: Optional[str] = None
    waiting_period_days: int = 0
    prior_auth_required: bool = False
    code_range: Optional[str] = None

class PlanCreate(BaseModel):
    name: str
    plan_type: ClaimType
    group_id: str
    effective_date: str
    termination_date: Optional[str] = None
    deductible_individual: float = 500
    deductible_family: float = 1500
    oop_max_individual: float = 5000
    oop_max_family: float = 10000
    network_type: str = "PPO"
    reimbursement_method: str = "fee_schedule"
    benefits: List[PlanBenefit] = []
    tier_type: str = "employee_only"
    exclusions: List[str] = []
    preventive_design: str = "aca_strict"  # aca_strict | enhanced

class PlanResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    plan_type: str
    group_id: str
    effective_date: str
    termination_date: Optional[str]
    deductible_individual: float
    deductible_family: float
    oop_max_individual: float
    oop_max_family: float
    network_type: str
    reimbursement_method: str
    benefits: List[Dict]
    tier_type: str
    exclusions: List[str]
    status: str
    version: int
    created_at: str
    updated_at: str

class MemberCreate(BaseModel):
    member_id: str
    first_name: str
    last_name: str
    dob: str
    gender: str
    ssn_last4: Optional[str] = None
    group_id: str
    plan_id: str
    effective_date: str
    termination_date: Optional[str] = None
    relationship: str = "subscriber"
    address: Optional[Dict] = None

class MemberResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    member_id: str
    first_name: str
    last_name: str
    dob: str
    gender: str
    group_id: str
    plan_id: str
    effective_date: str
    termination_date: Optional[str]
    relationship: str
    status: str
    created_at: str

class ServiceLine(BaseModel):
    line_number: int
    cpt_code: str
    modifier: Optional[str] = None
    units: int = 1
    billed_amount: float
    service_date: str
    diagnosis_codes: List[str] = []
    revenue_code: Optional[str] = None
    place_of_service: str = "11"

class ClaimCreate(BaseModel):
    member_id: str
    provider_npi: str
    provider_name: str
    facility_npi: Optional[str] = None
    claim_type: ClaimType
    service_date_from: str
    service_date_to: str
    total_billed: float
    diagnosis_codes: List[str]
    service_lines: List[ServiceLine]
    prior_auth_number: Optional[str] = None
    source: str = "api"
    external_claim_id: Optional[str] = None

class ClaimResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    claim_number: str
    member_id: str
    provider_npi: str
    provider_name: str
    claim_type: str
    service_date_from: str
    service_date_to: str
    total_billed: float
    total_allowed: float
    total_paid: float
    member_responsibility: float
    status: str
    diagnosis_codes: List[str]
    service_lines: List[Dict]
    duplicate_info: Optional[Dict]
    adjudication_notes: List[str]
    created_at: str
    adjudicated_at: Optional[str]

class DuplicateAlert(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    claim_id: str
    claim_number: str
    duplicate_type: str
    matched_claim_id: str
    matched_claim_number: str
    match_score: float
    match_reasons: List[str]
    status: str
    reviewed_by: Optional[str]
    reviewed_at: Optional[str]
    created_at: str

class AdjudicationAction(BaseModel):
    action: str  # approve, deny, pend, override_duplicate
    notes: Optional[str] = None
    denial_reason: Optional[str] = None

class DashboardMetrics(BaseModel):
    total_claims: int
    pending_claims: int
    approved_claims: int
    denied_claims: int
    duplicate_alerts: int
    total_paid: float
    total_saved_duplicates: float
    auto_adjudication_rate: float
    avg_turnaround_hours: float

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_roles(allowed_roles: List[UserRole]):
    async def role_checker(user: dict = Depends(get_current_user)):
        if user["role"] not in [r.value for r in allowed_roles]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

# ==================== DUPLICATE DETECTION ====================

def calculate_similarity(str1: str, str2: str) -> float:
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

async def detect_duplicates(claim_data: dict) -> List[Dict]:
    duplicates = []
    
    # Search for potential duplicates
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
        
        # Exact duplicate check
        is_exact = (
            existing["member_id"] == claim_data["member_id"] and
            existing["provider_npi"] == claim_data["provider_npi"] and
            existing["service_date_from"] == claim_data["service_date_from"] and
            abs(existing["total_billed"] - claim_data["total_billed"]) < 0.01
        )
        
        if is_exact:
            # Check service lines
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
        
        # Near duplicate check
        same_member = existing["member_id"] == claim_data["member_id"]
        same_provider = existing["provider_npi"] == claim_data["provider_npi"]
        
        # Date overlap check
        date_overlap = False
        try:
            ex_start = datetime.fromisoformat(existing["service_date_from"])
            ex_end = datetime.fromisoformat(existing["service_date_to"])
            new_start = datetime.fromisoformat(claim_data["service_date_from"])
            new_end = datetime.fromisoformat(claim_data["service_date_to"])
            date_overlap = (ex_start <= new_end) and (new_start <= ex_end)
        except (ValueError, KeyError):
            pass
        
        # Amount similarity
        amount_similar = False
        if existing["total_billed"] > 0:
            diff_pct = abs(existing["total_billed"] - claim_data["total_billed"]) / existing["total_billed"]
            amount_similar = diff_pct < 0.1
        
        # Service code overlap
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
            
            match_score += 0.2  # Base score for same member/provider/date overlap
            match_reasons.append("Same member, provider, overlapping dates")
            
            if match_score >= 0.5:
                duplicates.append({
                    "matched_claim_id": existing["id"],
                    "matched_claim_number": existing["claim_number"],
                    "duplicate_type": DuplicateType.NEAR.value,
                    "match_score": match_score,
                    "match_reasons": match_reasons
                })
        
        # Line-level duplicate check
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

# ==================== ADJUDICATION ENGINE ====================

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
    # Default / medical: use CPT/Medicare codes
    data = get_cpt_code(cpt_code)
    if data:
        return {"source": "medical", **data}
    # Try all databases as fallback
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
    # Medical / Medicare fee schedule
    medicare_rate = calculate_medicare_rate(code, locality_code, use_facility=True)
    if medicare_rate:
        allowed = medicare_rate * rate_multiplier * units
        return allowed, None, None, f"Medicare Rate: ${medicare_rate:.2f}, Method: {reimbursement_method} ({rate_multiplier*100:.0f}%)"
    return None, None, None, None


async def adjudicate_claim(claim: dict, plan: dict, member: dict, locality_code: str = "00000") -> dict:
    """Apply plan rules to adjudicate a claim - supports Medical, Dental, Vision, Hearing + Preventive."""
    
    adjudication_notes = []
    total_allowed = 0
    total_paid = 0
    member_responsibility = 0
    claim_type = claim.get("claim_type", "medical")
    
    # Check member eligibility
    claim_date = datetime.fromisoformat(claim["service_date_from"])
    member_eff = datetime.fromisoformat(member["effective_date"])
    member_term = datetime.fromisoformat(member["termination_date"]) if member.get("termination_date") else None
    
    if claim_date < member_eff:
        return {
            "status": ClaimStatus.DENIED.value,
            "total_allowed": 0, "total_paid": 0,
            "member_responsibility": claim["total_billed"],
            "adjudication_notes": ["DENIED: Service date before coverage effective date"]
        }
    
    if member_term and claim_date > member_term:
        return {
            "status": ClaimStatus.DENIED.value,
            "total_allowed": 0, "total_paid": 0,
            "member_responsibility": claim["total_billed"],
            "adjudication_notes": ["DENIED: Service date after coverage termination"]
        }
    
    # Check if plan type matches claim type
    plan_type = plan.get("plan_type", "medical")
    if plan_type != claim_type:
        adjudication_notes.append(f"WARNING: Claim type '{claim_type}' does not match plan type '{plan_type}'.")
    
    # Check prior authorization if required at claim level
    if claim.get("prior_auth_number"):
        await db.prior_authorizations.find_one(
            {"auth_number": claim["prior_auth_number"], "status": "approved"},
            {"_id": 0}
        )
    
    # Get member accumulators
    accumulators = await db.accumulators.find_one(
        {"member_id": claim["member_id"], "plan_year": str(claim_date.year), "claim_type": claim_type},
        {"_id": 0}
    ) or {"deductible_met": 0, "oop_met": 0, "annual_max_used": 0}
    
    deductible = plan.get("deductible_individual", 0)
    oop_max = plan.get("oop_max_individual", 999999)
    annual_max = plan.get("annual_max", 999999)
    
    # Reimbursement method
    reimbursement_method = plan.get("reimbursement_method", "fee_schedule")
    method_multipliers = {"fee_schedule": 1.0, "percent_medicare": 1.2, "percent_billed": 0.8, "rbp": 1.4, "contracted": 1.0}
    rate_multiplier = method_multipliers.get(reimbursement_method, 1.0)
    
    # Preventive plan design: default strict ACA, allow "enhanced"
    preventive_design = plan.get("preventive_design", "aca_strict")
    
    # Calculate member age
    member_age = calculate_member_age(member.get("dob", "2000-01-01"), claim["service_date_from"])
    member_gender = member.get("gender", "U").lower()
    if member_gender in ("m", "male"):
        member_gender = "male"
    elif member_gender in ("f", "female"):
        member_gender = "female"
    
    # Claim-level diagnosis codes
    claim_diagnosis = claim.get("diagnosis_codes", [])
    
    # Process each service line
    processed_lines = []
    for line in claim["service_lines"]:
        proc_code = line["cpt_code"]
        billed = line["billed_amount"]
        units = line.get("units", 1)
        line_modifier = line.get("modifier", "")
        line_dx = line.get("diagnosis_codes", []) or claim_diagnosis
        
        # ===== PREVENTIVE SERVICE CHECK =====
        preventive_eval = evaluate_preventive_claim_line(
            proc_code, line_dx, line_modifier,
            member_age if member_age is not None else 30,
            member_gender
        )
        
        if preventive_eval["is_preventive"] is True:
            # Check frequency limits
            within_limit, freq_msg, usage_count = await check_preventive_frequency(
                db, claim["member_id"], proc_code, claim.get("service_date_from", ""),
                preventive_eval.get("service")
            )
            
            if not within_limit:
                # Frequency exceeded - reclassify as diagnostic, apply normal benefits
                adjudication_notes.append(
                    f"Line {line['line_number']}: {proc_code} - PREVENTIVE frequency exceeded ({freq_msg}). Reclassified as diagnostic."
                )
                # Fall through to normal adjudication below
            else:
                # PREVENTIVE: $0 member cost, outside deductible
                svc = preventive_eval.get("service", {})
                allowed = svc.get("fee", billed) * units
                allowed = min(allowed, billed)
                paid = allowed  # Plan pays 100%
                member_resp = 0.0
                
                total_allowed += allowed
                total_paid += paid
                
                # Record utilization
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
                    "allowed": round(allowed, 2),
                    "paid": round(paid, 2),
                    "member_resp": 0.0,
                    "deductible_applied": 0.0,
                    "medicare_rate": None,
                    "cpt_description": svc.get("description", "Preventive Service"),
                    "coverage_type": "preventive",
                    "is_preventive": True,
                    "preventive_category": svc.get("category", ""),
                    "preventive_source": svc.get("source", ""),
                    "eob_message": "Preventive Service - $0 Member Responsibility",
                })
                continue
        
        elif preventive_eval.get("is_preventive") == "split":
            # Split claim scenario: preventive part + diagnostic part
            adjudication_notes.append(
                f"Line {line['line_number']}: {proc_code} - Split claim: preventive diagnosis with illness secondary dx. "
                "Processing as diagnostic with normal cost sharing."
            )
            # Fall through to normal adjudication
        
        elif preventive_eval.get("reclassify_as") == "diagnostic":
            adjudication_notes.append(
                f"Line {line['line_number']}: {proc_code} - Preventive code but billed as diagnostic (no Z-code/modifier 33). "
                "Normal plan benefits apply."
            )
            # Fall through to normal adjudication
        
        # ===== NORMAL (NON-PREVENTIVE) ADJUDICATION =====
        code_data = lookup_code_for_claim_type(proc_code, claim_type)
        
        # Find matching benefit category from plan
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
        
        # Check if service is covered
        if not benefit.get("covered", True):
            processed_lines.append({
                **line, "allowed": 0, "paid": 0, "member_resp": billed,
                "denial_reason": "Service not covered under plan", "medicare_rate": None
            })
            adjudication_notes.append(f"Line {line['line_number']}: {proc_code} - NOT COVERED")
            member_responsibility += billed
            continue
        
        # Check exclusions
        if proc_code in plan.get("exclusions", []):
            processed_lines.append({
                **line, "allowed": 0, "paid": 0, "member_resp": billed,
                "denial_reason": "Service excluded from coverage", "medicare_rate": None
            })
            adjudication_notes.append(f"Line {line['line_number']}: {proc_code} - EXCLUDED")
            member_responsibility += billed
            continue
        
        # Check prior auth if required
        if benefit.get("prior_auth_required") and not claim.get("prior_auth_number"):
            processed_lines.append({
                **line, "allowed": 0, "paid": 0, "member_resp": billed,
                "denial_reason": "Prior authorization required", "medicare_rate": None
            })
            adjudication_notes.append(f"Line {line['line_number']}: {proc_code} - Prior auth REQUIRED")
            member_responsibility += billed
            continue
        
        # Calculate allowed amount
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
        adjudication_notes.append(f"Line {line['line_number']}: {proc_code} - {rate_note}")
        
        # Dental/vision/hearing benefit class pricing
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
            # Standard medical adjudication with deductible/coinsurance/OOP
            line_deductible = 0
            if benefit.get("deductible_applies", True):
                remaining_deductible = max(0, deductible - accumulators["deductible_met"])
                line_deductible = min(allowed, remaining_deductible)
                accumulators["deductible_met"] += line_deductible
            
            after_deductible = allowed - line_deductible
            copay = benefit.get("copay", 0)
            coinsurance_pct = benefit.get("coinsurance", 0.2)
            coinsurance_amount = after_deductible * coinsurance_pct
            
            paid = after_deductible - coinsurance_amount - copay
            member_resp_this_line = line_deductible + coinsurance_amount + copay
            
            remaining_oop = max(0, oop_max - accumulators["oop_met"])
            if member_resp_this_line > remaining_oop:
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
            "deductible_applied": round(accumulators.get("deductible_met", 0), 2),
            "medicare_rate": medicare_rate,
            "cpt_description": code_data.get("description", "Unknown") if code_data else "Unknown",
            "work_rvu": code_data.get("work_rvu") if code_data else None,
            "total_rvu": code_data.get("total_rvu") if code_data else None,
            "coverage_type": code_data.get("source", claim_type) if code_data else claim_type,
            "is_preventive": False,
        })
    
    # Update accumulators
    await db.accumulators.update_one(
        {"member_id": claim["member_id"], "plan_year": str(claim_date.year), "claim_type": claim_type},
        {"$set": accumulators},
        upsert=True
    )
    
    return {
        "status": ClaimStatus.APPROVED.value if total_paid > 0 else ClaimStatus.DENIED.value,
        "total_allowed": round(total_allowed, 2),
        "total_paid": round(total_paid, 2),
        "member_responsibility": round(member_responsibility, 2),
        "service_lines": processed_lines,
        "adjudication_notes": adjudication_notes
    }

# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role.value,
        "created_at": now,
        "updated_at": now
    }
    
    await db.users.insert_one(user_doc)
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "user_registered",
        "user_id": user_id,
        "details": {"email": user_data.email, "role": user_data.role.value},
        "timestamp": now
    })
    
    token = create_access_token({"sub": user_id, "email": user_data.email, "role": user_data.role.value})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=user_data.email,
            name=user_data.name,
            role=user_data.role.value,
            created_at=now
        )
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]})
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "user_login",
        "user_id": user["id"],
        "details": {"email": user["email"]},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            created_at=user["created_at"]
        )
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        created_at=user["created_at"]
    )

# ==================== PLAN ENDPOINTS ====================

@api_router.post("/plans", response_model=PlanResponse)
async def create_plan(plan_data: PlanCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    plan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    plan_doc = {
        "id": plan_id,
        **plan_data.model_dump(),
        "plan_type": plan_data.plan_type.value,
        "status": PlanStatus.ACTIVE.value,
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "created_by": user["id"]
    }
    
    await db.plans.insert_one(plan_doc)
    
    # Audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "plan_created",
        "user_id": user["id"],
        "details": {"plan_id": plan_id, "plan_name": plan_data.name},
        "timestamp": now
    })
    
    return PlanResponse(**{k: v for k, v in plan_doc.items() if k != "_id"})

@api_router.get("/plans", response_model=List[PlanResponse])
async def list_plans(
    plan_status: Optional[str] = None,
    plan_type: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if plan_status:
        query["status"] = plan_status
    if plan_type:
        query["plan_type"] = plan_type
    
    plans = await db.plans.find(query, {"_id": 0}).to_list(1000)
    return [PlanResponse(**p) for p in plans]

@api_router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str, user: dict = Depends(get_current_user)):
    plan = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return PlanResponse(**plan)

@api_router.put("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(plan_id: str, plan_data: PlanCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    existing = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_doc = {
        **plan_data.model_dump(),
        "plan_type": plan_data.plan_type.value,
        "version": existing["version"] + 1,
        "updated_at": now
    }
    
    await db.plans.update_one({"id": plan_id}, {"$set": update_doc})
    
    # Audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "plan_updated",
        "user_id": user["id"],
        "details": {"plan_id": plan_id, "new_version": existing["version"] + 1},
        "timestamp": now
    })
    
    updated = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    return PlanResponse(**updated)

# ==================== MEMBER ENDPOINTS ====================

@api_router.post("/members", response_model=MemberResponse)
async def create_member(member_data: MemberCreate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    # Check if member exists
    existing = await db.members.find_one({"member_id": member_data.member_id})
    if existing:
        raise HTTPException(status_code=400, detail="Member ID already exists")
    
    member_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    member_doc = {
        "id": member_id,
        **member_data.model_dump(),
        "status": "active",
        "created_at": now,
        "updated_at": now
    }
    
    await db.members.insert_one(member_doc)
    
    return MemberResponse(**{k: v for k, v in member_doc.items() if k not in ["_id", "address", "ssn_last4", "updated_at"]})

@api_router.get("/members", response_model=List[MemberResponse])
async def list_members(
    group_id: Optional[str] = None,
    plan_id: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if group_id:
        query["group_id"] = group_id
    if plan_id:
        query["plan_id"] = plan_id
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"member_id": {"$regex": search, "$options": "i"}}
        ]
    
    members = await db.members.find(query, {"_id": 0, "address": 0, "ssn_last4": 0}).to_list(1000)
    return [MemberResponse(**m) for m in members]

@api_router.get("/members/{member_id}", response_model=MemberResponse)
async def get_member(member_id: str, user: dict = Depends(get_current_user)):
    member = await db.members.find_one({"member_id": member_id}, {"_id": 0, "ssn_last4": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return MemberResponse(**{k: v for k, v in member.items() if k not in ["address", "updated_at"]})

# ==================== CLAIMS ENDPOINTS ====================

@api_router.post("/claims", response_model=ClaimResponse)
async def create_claim(claim_data: ClaimCreate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    # Verify member exists
    member = await db.members.find_one({"member_id": claim_data.member_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Get member's plan
    plan = await db.plans.find_one({"id": member["plan_id"]}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Member plan not found")
    
    claim_id = str(uuid.uuid4())
    claim_number = f"CLM{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    
    claim_doc = {
        "id": claim_id,
        "claim_number": claim_number,
        **claim_data.model_dump(),
        "claim_type": claim_data.claim_type.value,
        "service_lines": [line.model_dump() for line in claim_data.service_lines],
        "total_allowed": 0,
        "total_paid": 0,
        "member_responsibility": claim_data.total_billed,
        "status": ClaimStatus.PENDING.value,
        "duplicate_info": None,
        "adjudication_notes": [],
        "created_at": now,
        "created_by": user["id"],
        "adjudicated_at": None
    }
    
    # Check for duplicates BEFORE inserting
    duplicates = await detect_duplicates(claim_doc)
    
    if duplicates:
        # Flag highest confidence duplicate
        top_dup = duplicates[0]
        claim_doc["duplicate_info"] = top_dup
        
        if top_dup["match_score"] >= 0.95:
            # Auto-deny exact duplicates
            claim_doc["status"] = ClaimStatus.DUPLICATE.value
            claim_doc["adjudication_notes"].append(f"AUTO-DENIED: Exact duplicate of {top_dup['matched_claim_number']}")
        else:
            # Pend for review
            claim_doc["status"] = ClaimStatus.PENDED.value
            claim_doc["adjudication_notes"].append(f"PENDED: Potential duplicate of {top_dup['matched_claim_number']} (Score: {top_dup['match_score']:.0%})")
        
        # Create duplicate alert
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
        # No duplicates - auto-adjudicate
        adjudication_result = await adjudicate_claim(claim_doc, plan, member)
        claim_doc.update(adjudication_result)
        claim_doc["adjudicated_at"] = now
    
    await db.claims.insert_one(claim_doc)
    
    # Audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "claim_created",
        "user_id": user["id"],
        "details": {"claim_id": claim_id, "claim_number": claim_number, "status": claim_doc["status"]},
        "timestamp": now
    })
    
    return ClaimResponse(**{k: v for k, v in claim_doc.items() if k not in ["_id", "created_by"]})

@api_router.get("/claims", response_model=List[ClaimResponse])
async def list_claims(
    claim_status: Optional[str] = None,
    claim_type: Optional[str] = None,
    member_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    has_duplicates: Optional[bool] = None,
    limit: int = Query(default=100, le=500),
    skip: int = 0,
    user: dict = Depends(get_current_user)
):
    query = {}
    if claim_status:
        query["status"] = claim_status
    if claim_type:
        query["claim_type"] = claim_type
    if member_id:
        query["member_id"] = member_id
    if date_from:
        query["service_date_from"] = {"$gte": date_from}
    if date_to:
        query["service_date_to"] = {"$lte": date_to}
    if has_duplicates is not None:
        if has_duplicates:
            query["duplicate_info"] = {"$ne": None}
        else:
            query["duplicate_info"] = None
    
    claims = await db.claims.find(query, {"_id": 0, "created_by": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [ClaimResponse(**c) for c in claims]

@api_router.get("/claims/{claim_id}", response_model=ClaimResponse)
async def get_claim(claim_id: str, user: dict = Depends(get_current_user)):
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return ClaimResponse(**claim)

@api_router.post("/claims/{claim_id}/adjudicate", response_model=ClaimResponse)
async def adjudicate_claim_action(
    claim_id: str,
    action: AdjudicationAction,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))
):
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_doc = {"adjudicated_at": now}
    
    if action.action == "approve":
        # Get member and plan for adjudication
        member = await db.members.find_one({"member_id": claim["member_id"]}, {"_id": 0})
        plan = await db.plans.find_one({"id": member["plan_id"]}, {"_id": 0})
        
        result = await adjudicate_claim(claim, plan, member)
        update_doc.update(result)
        update_doc["status"] = ClaimStatus.APPROVED.value
        
    elif action.action == "deny":
        update_doc["status"] = ClaimStatus.DENIED.value
        update_doc["total_paid"] = 0
        if action.denial_reason:
            update_doc["adjudication_notes"] = claim.get("adjudication_notes", []) + [f"DENIED: {action.denial_reason}"]
            
    elif action.action == "pend":
        update_doc["status"] = ClaimStatus.PENDED.value
        if action.notes:
            update_doc["adjudication_notes"] = claim.get("adjudication_notes", []) + [f"PENDED: {action.notes}"]
            
    elif action.action == "override_duplicate":
        # Override duplicate flag and process
        member = await db.members.find_one({"member_id": claim["member_id"]}, {"_id": 0})
        plan = await db.plans.find_one({"id": member["plan_id"]}, {"_id": 0})
        
        result = await adjudicate_claim(claim, plan, member)
        update_doc.update(result)
        update_doc["status"] = ClaimStatus.APPROVED.value
        update_doc["adjudication_notes"] = claim.get("adjudication_notes", []) + [f"DUPLICATE OVERRIDE by {user['name']}: {action.notes or 'Approved'}"]
        
        # Update duplicate alert
        await db.duplicate_alerts.update_many(
            {"claim_id": claim_id},
            {"$set": {"status": "overridden", "reviewed_by": user["id"], "reviewed_at": now}}
        )
    
    await db.claims.update_one({"id": claim_id}, {"$set": update_doc})
    
    # Audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": f"claim_{action.action}",
        "user_id": user["id"],
        "details": {"claim_id": claim_id, "action": action.action, "notes": action.notes},
        "timestamp": now
    })
    
    updated = await db.claims.find_one({"id": claim_id}, {"_id": 0, "created_by": 0})
    return ClaimResponse(**updated)

# ==================== DUPLICATE ALERTS ====================

@api_router.get("/duplicates", response_model=List[DuplicateAlert])
async def list_duplicate_alerts(
    alert_status: Optional[str] = None,
    duplicate_type: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if alert_status:
        query["status"] = alert_status
    if duplicate_type:
        query["duplicate_type"] = duplicate_type
    
    alerts = await db.duplicate_alerts.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [DuplicateAlert(**a) for a in alerts]

@api_router.post("/duplicates/{alert_id}/resolve")
async def resolve_duplicate_alert(
    alert_id: str,
    resolution: str,  # "confirm_duplicate" or "not_duplicate"
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR, UserRole.REVIEWER]))
):
    alert = await db.duplicate_alerts.find_one({"id": alert_id}, {"_id": 0})
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.duplicate_alerts.update_one(
        {"id": alert_id},
        {"$set": {
            "status": resolution,
            "reviewed_by": user["id"],
            "reviewed_at": now
        }}
    )
    
    # If confirmed as not duplicate, update claim status
    if resolution == "not_duplicate":
        claim = await db.claims.find_one({"id": alert["claim_id"]}, {"_id": 0})
        if claim and claim["status"] in [ClaimStatus.PENDED.value, ClaimStatus.DUPLICATE.value]:
            member = await db.members.find_one({"member_id": claim["member_id"]}, {"_id": 0})
            plan = await db.plans.find_one({"id": member["plan_id"]}, {"_id": 0})
            
            result = await adjudicate_claim(claim, plan, member)
            result["adjudication_notes"] = claim.get("adjudication_notes", []) + [f"DUPLICATE CLEARED by {user['name']}"]
            result["adjudicated_at"] = now
            
            await db.claims.update_one({"id": alert["claim_id"]}, {"$set": result})
    
    return {"status": "success", "resolution": resolution}

# ==================== DASHBOARD & ANALYTICS ====================

@api_router.get("/dashboard/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(user: dict = Depends(get_current_user)):
    # Get claim counts
    total_claims = await db.claims.count_documents({})
    pending_claims = await db.claims.count_documents({"status": {"$in": [ClaimStatus.PENDING.value, ClaimStatus.PENDED.value, ClaimStatus.IN_REVIEW.value]}})
    approved_claims = await db.claims.count_documents({"status": ClaimStatus.APPROVED.value})
    denied_claims = await db.claims.count_documents({"status": {"$in": [ClaimStatus.DENIED.value, ClaimStatus.DUPLICATE.value]}})
    
    # Get duplicate alerts
    duplicate_alerts = await db.duplicate_alerts.count_documents({"status": "pending"})
    
    # Get payment totals
    pipeline = [
        {"$match": {"status": ClaimStatus.APPROVED.value}},
        {"$group": {"_id": None, "total": {"$sum": "$total_paid"}}}
    ]
    paid_result = await db.claims.aggregate(pipeline).to_list(1)
    total_paid = paid_result[0]["total"] if paid_result else 0
    
    # Get duplicate savings
    dup_pipeline = [
        {"$match": {"status": ClaimStatus.DUPLICATE.value}},
        {"$group": {"_id": None, "total": {"$sum": "$total_billed"}}}
    ]
    dup_result = await db.claims.aggregate(dup_pipeline).to_list(1)
    total_saved = dup_result[0]["total"] if dup_result else 0
    
    # Calculate auto-adjudication rate
    auto_adj = await db.claims.count_documents({"status": {"$in": [ClaimStatus.APPROVED.value, ClaimStatus.DENIED.value]}, "duplicate_info": None})
    auto_rate = (auto_adj / total_claims * 100) if total_claims > 0 else 0
    
    return DashboardMetrics(
        total_claims=total_claims,
        pending_claims=pending_claims,
        approved_claims=approved_claims,
        denied_claims=denied_claims,
        duplicate_alerts=duplicate_alerts,
        total_paid=total_paid,
        total_saved_duplicates=total_saved,
        auto_adjudication_rate=round(auto_rate, 1),
        avg_turnaround_hours=4.2  # Simplified - would calculate from actual data
    )

@api_router.get("/dashboard/claims-by-status")
async def get_claims_by_status(user: dict = Depends(get_current_user)):
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    results = await db.claims.aggregate(pipeline).to_list(10)
    return [{"status": r["_id"], "count": r["count"]} for r in results]

@api_router.get("/dashboard/claims-by-type")
async def get_claims_by_type(user: dict = Depends(get_current_user)):
    pipeline = [
        {"$group": {"_id": "$claim_type", "count": {"$sum": 1}, "total_billed": {"$sum": "$total_billed"}, "total_paid": {"$sum": "$total_paid"}}}
    ]
    results = await db.claims.aggregate(pipeline).to_list(10)
    return [{"type": r["_id"], "count": r["count"], "total_billed": r["total_billed"], "total_paid": r["total_paid"]} for r in results]

@api_router.get("/dashboard/recent-activity")
async def get_recent_activity(limit: int = 10, user: dict = Depends(get_current_user)):
    logs = await db.audit_logs.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs

# ==================== EDI ENDPOINTS ====================

@api_router.post("/edi/upload-834")
async def upload_edi_834(file: UploadFile = File(...), user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Process EDI 834 enrollment file - supports real X12 and pipe-delimited format."""
    content = await file.read()
    content_str = content.decode('utf-8')
    
    members_created = 0
    members_updated = 0
    errors = []
    
    is_x12 = content_str.strip().startswith('ISA')
    
    if is_x12:
        # Real X12 834 Parsing
        segment_terminator = '~'
        element_separator = '*'
        segments = [s.strip() for s in content_str.split(segment_terminator) if s.strip()]
        
        current_member = {}
        in_member_loop = False
        
        for seg in segments:
            elements = seg.split(element_separator)
            seg_id = elements[0]
            
            if seg_id == 'INS':
                # Insurance segment - start of new member
                if current_member.get("member_id"):
                    try:
                        await _save_834_member(current_member)
                        members_created += 1
                    except Exception as e:
                        errors.append(f"Member {current_member.get('member_id', '?')}: {str(e)}")
                current_member = {"relationship": "subscriber" if len(elements) > 1 and elements[1] == 'Y' else "dependent"}
                in_member_loop = True
            elif seg_id == 'REF' and in_member_loop:
                # Reference - member ID
                if len(elements) > 2 and elements[1] == '0F':
                    current_member["member_id"] = elements[2]
                elif len(elements) > 2 and elements[1] == '1L':
                    current_member["group_id"] = elements[2]
            elif seg_id == 'NM1' and in_member_loop:
                # Name segment
                if len(elements) > 3 and elements[1] == 'IL':
                    current_member["last_name"] = elements[3] if len(elements) > 3 else ""
                    current_member["first_name"] = elements[4] if len(elements) > 4 else ""
            elif seg_id == 'DMG' and in_member_loop:
                # Demographic segment
                if len(elements) > 2:
                    current_member["dob"] = _parse_x12_date(elements[2]) if len(elements) > 2 else ""
                    current_member["gender"] = elements[3] if len(elements) > 3 else "U"
            elif seg_id == 'DTP' and in_member_loop:
                # Date segment
                if len(elements) > 3:
                    if elements[1] == '348':
                        current_member["effective_date"] = _parse_x12_date(elements[3])
                    elif elements[1] == '349':
                        current_member["termination_date"] = _parse_x12_date(elements[3])
            elif seg_id == 'HD' and in_member_loop:
                # Health coverage segment
                if len(elements) > 3:
                    plan_code = elements[3] if len(elements) > 3 else ""
                    current_member["plan_id"] = plan_code
        
        # Save last member
        if current_member.get("member_id"):
            try:
                await _save_834_member(current_member)
                members_created += 1
            except Exception as e:
                errors.append(f"Member {current_member.get('member_id', '?')}: {str(e)}")
    else:
        # Pipe-delimited format: MemberID|FirstName|LastName|DOB|Gender|GroupID|PlanID|EffDate
        for line in content_str.strip().split('\n'):
            if not line or line.startswith('#'):
                continue
            try:
                parts = line.split('|')
                if len(parts) >= 8:
                    member_data = MemberCreate(
                        member_id=parts[0], first_name=parts[1], last_name=parts[2],
                        dob=parts[3], gender=parts[4], group_id=parts[5],
                        plan_id=parts[6], effective_date=parts[7], relationship="subscriber"
                    )
                    existing = await db.members.find_one({"member_id": member_data.member_id})
                    if not existing:
                        member_doc = {
                            "id": str(uuid.uuid4()),
                            **member_data.model_dump(),
                            "status": "active",
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                        await db.members.insert_one(member_doc)
                        members_created += 1
                    else:
                        members_updated += 1
            except Exception as e:
                errors.append(f"Line error: {str(e)}")
    
    return {"members_created": members_created, "members_updated": members_updated, "errors": errors}


def _parse_x12_date(date_str):
    """Parse X12 date format CCYYMMDD to ISO date string."""
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


async def _save_834_member(member_data):
    """Save a member parsed from 834."""
    member_id = member_data.get("member_id", "")
    if not member_id:
        raise ValueError("Missing member_id")
    existing = await db.members.find_one({"member_id": member_id})
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
        "created_at": existing["created_at"] if existing else datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    if existing:
        await db.members.replace_one({"member_id": member_id}, doc)
    else:
        await db.members.insert_one(doc)


@api_router.post("/edi/upload-837")
async def upload_edi_837(file: UploadFile = File(...), user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Process EDI 837 claims file - supports real X12 and pipe-delimited format."""
    content = await file.read()
    content_str = content.decode('utf-8')
    
    claims_created = 0
    errors = []
    
    is_x12 = content_str.strip().startswith('ISA')
    
    if is_x12:
        # Real X12 837 Parsing
        segment_terminator = '~'
        element_separator = '*'
        segments = [s.strip() for s in content_str.split(segment_terminator) if s.strip()]
        
        current_claim = {}
        current_service_lines = []
        current_diag_codes = []
        in_claim = False
        line_counter = 0
        
        for seg in segments:
            elements = seg.split(element_separator)
            seg_id = elements[0]
            
            if seg_id == 'CLM':
                # Claim segment - save previous claim if exists
                if in_claim and current_claim.get("member_id"):
                    try:
                        await _save_837_claim(current_claim, current_service_lines, current_diag_codes, user)
                        claims_created += 1
                    except Exception as e:
                        errors.append(f"Claim error: {str(e)}")
                
                current_claim = {}
                current_service_lines = []
                current_diag_codes = []
                line_counter = 0
                in_claim = True
                
                if len(elements) > 2:
                    current_claim["patient_control"] = elements[1]
                    current_claim["total_billed"] = float(elements[2]) if len(elements) > 2 else 0
                if len(elements) > 5:
                    pos = elements[5].split(':') if ':' in elements[5] else [elements[5]]
                    current_claim["place_of_service"] = pos[0]
            elif seg_id == 'NM1' and in_claim:
                if len(elements) > 3:
                    if elements[1] == 'IL':
                        current_claim["member_last_name"] = elements[3] if len(elements) > 3 else ""
                        current_claim["member_first_name"] = elements[4] if len(elements) > 4 else ""
                        if len(elements) > 9:
                            current_claim["member_id"] = elements[9]
                    elif elements[1] == '82':
                        current_claim["provider_name"] = f"{elements[4]} {elements[3]}" if len(elements) > 4 else elements[3]
                        if len(elements) > 9:
                            current_claim["provider_npi"] = elements[9]
            elif seg_id == 'HI' and in_claim:
                # Health info - diagnosis codes
                for i in range(1, len(elements)):
                    parts = elements[i].split(':')
                    if len(parts) >= 2:
                        current_diag_codes.append(parts[1])
            elif seg_id == 'SV1' and in_claim:
                # Service line
                line_counter += 1
                proc_parts = elements[1].split(':') if len(elements) > 1 else ["", ""]
                proc_code = proc_parts[1] if len(proc_parts) > 1 else proc_parts[0]
                modifier = proc_parts[2] if len(proc_parts) > 2 else ""
                
                svc_line = {
                    "line_number": line_counter,
                    "cpt_code": proc_code,
                    "modifier": modifier,
                    "billed_amount": float(elements[2]) if len(elements) > 2 else 0,
                    "units": int(float(elements[4])) if len(elements) > 4 else 1,
                    "service_date": current_claim.get("service_date_from", ""),
                    "place_of_service": elements[5] if len(elements) > 5 else "11",
                }
                current_service_lines.append(svc_line)
            elif seg_id == 'DTP' and in_claim:
                if len(elements) > 3:
                    if elements[1] == '472':
                        date_val = _parse_x12_date(elements[3].split('-')[0] if '-' in elements[3] else elements[3])
                        current_claim["service_date_from"] = date_val
                        current_claim["service_date_to"] = date_val
        
        # Save last claim
        if in_claim and current_claim.get("member_id"):
            try:
                await _save_837_claim(current_claim, current_service_lines, current_diag_codes, user)
                claims_created += 1
            except Exception as e:
                errors.append(f"Claim error: {str(e)}")
    else:
        # Pipe-delimited format
        for line in content_str.strip().split('\n'):
            if not line or line.startswith('#'):
                continue
            try:
                parts = line.split('|')
                if len(parts) >= 9:
                    service_lines = []
                    for i, svc in enumerate(parts[8].split(',')):
                        svc_parts = svc.split(':')
                        if len(svc_parts) >= 3:
                            service_lines.append(ServiceLine(
                                line_number=i + 1,
                                cpt_code=svc_parts[0],
                                units=int(svc_parts[1]),
                                billed_amount=float(svc_parts[2]),
                                service_date=parts[4]
                            ))
                    
                    claim_data = ClaimCreate(
                        member_id=parts[0], provider_npi=parts[1], provider_name=parts[2],
                        claim_type=ClaimType(parts[3]), service_date_from=parts[4],
                        service_date_to=parts[5], total_billed=float(parts[6]),
                        diagnosis_codes=parts[7].split(','), service_lines=service_lines,
                        source="edi_837"
                    )
                    await create_claim(claim_data, user)
                    claims_created += 1
            except Exception as e:
                errors.append(f"Line error: {str(e)}")
    
    return {"claims_created": claims_created, "errors": errors}


async def _save_837_claim(claim_data, service_lines, diag_codes, user):
    """Save a claim parsed from X12 837."""
    svc_lines = []
    for sl in service_lines:
        svc_lines.append(ServiceLine(
            line_number=sl["line_number"],
            cpt_code=sl["cpt_code"],
            modifier=sl.get("modifier", ""),
            units=sl.get("units", 1),
            billed_amount=sl.get("billed_amount", 0),
            service_date=claim_data.get("service_date_from", ""),
            place_of_service=sl.get("place_of_service", "11")
        ))
    
    total_billed = claim_data.get("total_billed", sum(sl.get("billed_amount", 0) for sl in service_lines))
    
    cd = ClaimCreate(
        member_id=claim_data.get("member_id", ""),
        provider_npi=claim_data.get("provider_npi", ""),
        provider_name=claim_data.get("provider_name", "Unknown Provider"),
        claim_type=ClaimType.MEDICAL,
        service_date_from=claim_data.get("service_date_from", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        service_date_to=claim_data.get("service_date_to", claim_data.get("service_date_from", datetime.now(timezone.utc).strftime("%Y-%m-%d"))),
        total_billed=total_billed,
        diagnosis_codes=diag_codes or ["Z00.00"],
        service_lines=svc_lines,
        source="edi_837"
    )
    await create_claim(cd, user)


@api_router.get("/edi/generate-835")
async def generate_edi_835(
    date_from: str,
    date_to: str,
    format: str = Query(default="x12", description="Output format: x12 or pipe"),
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))
):
    """Generate EDI 835 payment/remittance file in X12 or pipe-delimited format."""
    claims = await db.claims.find({
        "status": ClaimStatus.APPROVED.value,
        "adjudicated_at": {"$gte": date_from, "$lte": date_to}
    }, {"_id": 0}).to_list(10000)
    
    if format == "x12":
        # Generate real X12 835 format
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%y%m%d")
        time_str = now.strftime("%H%M")
        isa_date = now.strftime("%y%m%d")
        gs_date = now.strftime("%Y%m%d")
        control_number = str(uuid.uuid4().int)[:9].zfill(9)
        
        lines = []
        lines.append(f"ISA*00*          *00*          *ZZ*FLETCHFLOW     *ZZ*RECEIVER       *{isa_date}*{time_str}*^*00501*{control_number}*0*P*:~")
        lines.append(f"GS*HP*FLETCHFLOW*RECEIVER*{gs_date}*{time_str}*1*X*005010X221A1~")
        lines.append(f"ST*835*0001~")
        lines.append(f"BPR*I*{sum(c.get('total_paid', 0) for c in claims):.2f}*C*ACH*CTX*01*999999999*DA*123456789*1234567890**01*999999999*DA*987654321*{gs_date}~")
        lines.append(f"TRN*1*{control_number}*1234567890~")
        lines.append(f"DTM*405*{gs_date}~")
        lines.append(f"N1*PR*FletchFlow Claims System~")
        lines.append(f"N1*PE*Provider Name*XX*1234567890~")
        
        for i, claim in enumerate(claims):
            clp_status = "1" if claim.get("status") == "approved" else "2"
            lines.append(f"CLP*{claim.get('claim_number', '')}*{clp_status}*{claim.get('total_billed', 0):.2f}*{claim.get('total_paid', 0):.2f}**MC*{claim.get('id', '')}~")
            lines.append(f"NM1*QC*1*{claim.get('member_id', '')}~")
            
            for sl in claim.get("service_lines", []):
                lines.append(f"SVC*HC:{sl.get('cpt_code', '')}*{sl.get('billed_amount', 0):.2f}*{sl.get('paid', 0):.2f}**{sl.get('units', 1)}~")
                lines.append(f"DTM*472*{claim.get('service_date_from', '').replace('-', '')}~")
                cas_adj = sl.get('billed_amount', 0) - sl.get('paid', 0)
                if cas_adj > 0:
                    lines.append(f"CAS*CO*45*{cas_adj:.2f}~")
        
        lines.append(f"SE*{len(lines) - 2}*0001~")
        lines.append(f"GE*1*1~")
        lines.append(f"IEA*1*{control_number}~")
        
        content = "\n".join(lines)
    else:
        # Pipe-delimited format (legacy)
        output = ["# EDI 835 Payment File", f"# Generated: {datetime.now(timezone.utc).isoformat()}", "# ClaimNumber|MemberID|ProviderNPI|TotalBilled|TotalAllowed|TotalPaid|MemberResp"]
        for claim in claims:
            output.append(f"{claim['claim_number']}|{claim['member_id']}|{claim['provider_npi']}|{claim['total_billed']}|{claim['total_allowed']}|{claim['total_paid']}|{claim['member_responsibility']}")
        content = "\n".join(output)
    
    return {"content": content, "claim_count": len(claims), "format": format}

# ==================== AUDIT LOGS ====================

@api_router.get("/audit-logs")
async def get_audit_logs(
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.AUDITOR]))
):
    query = {}
    if action:
        query["action"] = action
    if user_id:
        query["user_id"] = user_id
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs

# ==================== CPT CODES & FEE SCHEDULE ENDPOINTS ====================

@api_router.get("/cpt-codes/search")
async def search_cpt(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=50, le=100),
    user: dict = Depends(get_current_user)
):
    """Search CPT codes by code or description"""
    results = search_cpt_codes(q, limit)
    return {"results": results, "count": len(results)}

@api_router.get("/cpt-codes/{code}")
async def get_cpt_code_details(code: str, user: dict = Depends(get_current_user)):
    """Get detailed information for a specific CPT code"""
    cpt_data = get_cpt_code(code)
    if not cpt_data:
        raise HTTPException(status_code=404, detail="CPT code not found")
    return {"code": code, **cpt_data}

@api_router.get("/cpt-codes/category/{category:path}")
async def get_codes_by_cat(
    category: str,
    user: dict = Depends(get_current_user)
):
    """Get all CPT codes in a specific category"""
    # Handle URL-encoded category names
    from urllib.parse import unquote
    category = unquote(category)
    
    valid_categories = ["E/M", "Anesthesia", "Surgery", "Radiology", "Pathology/Lab", "Medicine", "HCPCS"]
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Valid: {valid_categories}")
    codes = get_codes_by_category(category)
    return {"category": category, "codes": codes, "count": len(codes)}

@api_router.get("/fee-schedule/rate")
async def calculate_rate(
    cpt_code: str,
    locality: str = Query(default="00000", description="GPCI locality code"),
    facility: bool = Query(default=True, description="Use facility rate"),
    user: dict = Depends(get_current_user)
):
    """Calculate Medicare reimbursement rate for a CPT code with GPCI adjustment"""
    cpt_data = get_cpt_code(cpt_code)
    if not cpt_data:
        raise HTTPException(status_code=404, detail="CPT code not found")
    
    locality_data = GPCI_LOCALITIES.get(locality)
    if not locality_data:
        raise HTTPException(status_code=400, detail="Invalid locality code")
    
    rate = calculate_medicare_rate(cpt_code, locality, use_facility=facility)
    
    return {
        "cpt_code": cpt_code,
        "description": cpt_data.get("description"),
        "category": cpt_data.get("category"),
        "locality_code": locality,
        "locality_name": locality_data.get("name"),
        "facility_setting": facility,
        "work_rvu": cpt_data.get("work_rvu"),
        "pe_rvu": cpt_data.get("pe_rvu"),
        "mp_rvu": cpt_data.get("mp_rvu"),
        "total_rvu": cpt_data.get("total_rvu"),
        "gpci_work": locality_data.get("work"),
        "gpci_pe": locality_data.get("pe"),
        "gpci_mp": locality_data.get("mp"),
        "conversion_factor": CONVERSION_FACTOR_2024,
        "medicare_rate": rate,
        "national_facility_rate": cpt_data.get("facility_rate"),
        "national_non_facility_rate": cpt_data.get("non_facility_rate")
    }

@api_router.get("/fee-schedule/localities")
async def list_localities(user: dict = Depends(get_current_user)):
    """Get all GPCI localities with their adjustment factors"""
    localities = get_all_localities()
    return {
        "localities": [
            {
                "code": code,
                "name": data["name"],
                "work_gpci": data["work"],
                "pe_gpci": data["pe"],
                "mp_gpci": data["mp"]
            }
            for code, data in localities.items()
        ],
        "count": len(localities)
    }

@api_router.get("/fee-schedule/stats")
async def fee_schedule_stats(user: dict = Depends(get_current_user)):
    """Get statistics about the fee schedule database"""
    categories = {}
    for code, data in CPT_CODES_DATABASE.items():
        cat = data.get("category", "Unknown")
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1
    
    return {
        "total_cpt_codes": len(CPT_CODES_DATABASE),
        "total_localities": len(GPCI_LOCALITIES),
        "conversion_factor_2024": CONVERSION_FACTOR_2024,
        "categories": categories,
        "category_counts": [
            {"category": cat, "count": count}
            for cat, count in sorted(categories.items(), key=lambda x: -x[1])
        ]
    }

# ==================== DENTAL/VISION/HEARING CODE ENDPOINTS ====================

@api_router.get("/dental-codes/search")
async def search_dental(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=50, le=100),
    user: dict = Depends(get_current_user)
):
    results = search_dental_codes(q, limit)
    return {"results": results, "count": len(results)}

@api_router.get("/dental-codes/{code}")
async def get_dental(code: str, user: dict = Depends(get_current_user)):
    data = get_dental_code(code)
    if not data:
        raise HTTPException(status_code=404, detail="CDT code not found")
    return {"code": code, **data}

@api_router.get("/vision-codes/search")
async def search_vision(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=50, le=100),
    user: dict = Depends(get_current_user)
):
    results = search_vision_codes(q, limit)
    return {"results": results, "count": len(results)}

@api_router.get("/vision-codes/{code}")
async def get_vision(code: str, user: dict = Depends(get_current_user)):
    data = get_vision_code(code)
    if not data:
        raise HTTPException(status_code=404, detail="Vision code not found")
    return {"code": code, **data}

@api_router.get("/hearing-codes/search")
async def search_hearing(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=50, le=100),
    user: dict = Depends(get_current_user)
):
    results = search_hearing_codes(q, limit)
    return {"results": results, "count": len(results)}

@api_router.get("/hearing-codes/{code}")
async def get_hearing(code: str, user: dict = Depends(get_current_user)):
    data = get_hearing_code(code)
    if not data:
        raise HTTPException(status_code=404, detail="Hearing code not found")
    return {"code": code, **data}

@api_router.get("/code-database/stats")
async def code_database_stats(user: dict = Depends(get_current_user)):
    """Get stats across all code databases."""
    dental_cats = {}
    for code, data in CDT_CODES_DATABASE.items():
        cat = data.get("category", "Other")
        dental_cats[cat] = dental_cats.get(cat, 0) + 1
    
    vision_cats = {}
    for code, data in VISION_CODES_DATABASE.items():
        cat = data.get("category", "Other")
        vision_cats[cat] = vision_cats.get(cat, 0) + 1
    
    hearing_cats = {}
    for code, data in HEARING_CODES_DATABASE.items():
        cat = data.get("category", "Other")
        hearing_cats[cat] = hearing_cats.get(cat, 0) + 1
    
    return {
        "medical": {"total": len(CPT_CODES_DATABASE), "localities": len(GPCI_LOCALITIES)},
        "dental": {"total": len(CDT_CODES_DATABASE), "categories": dental_cats},
        "vision": {"total": len(VISION_CODES_DATABASE), "categories": vision_cats},
        "hearing": {"total": len(HEARING_CODES_DATABASE), "categories": hearing_cats},
        "grand_total": len(CPT_CODES_DATABASE) + len(CDT_CODES_DATABASE) + len(VISION_CODES_DATABASE) + len(HEARING_CODES_DATABASE),
    }


# ==================== NETWORK REPRICING ====================

class NetworkContract(BaseModel):
    provider_npi: str
    provider_name: str
    network_name: str
    contract_type: str = "percent_medicare"
    multiplier: float = 1.2
    effective_date: str
    termination_date: Optional[str] = None
    coverage_types: List[str] = ["medical"]

@api_router.post("/network/contracts")
async def create_network_contract(contract: NetworkContract, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a network provider contract."""
    doc = {
        "id": str(uuid.uuid4()),
        **contract.model_dump(),
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.network_contracts.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.get("/network/contracts")
async def list_network_contracts(
    network_name: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if network_name:
        query["network_name"] = network_name
    contracts = await db.network_contracts.find(query, {"_id": 0}).to_list(1000)
    return contracts

@api_router.get("/network/reprice/{claim_id}")
async def reprice_claim(claim_id: str, user: dict = Depends(get_current_user)):
    """Compare Medicare rates with network contracted rates for a claim."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    contract = await db.network_contracts.find_one(
        {"provider_npi": claim.get("provider_npi"), "status": "active"},
        {"_id": 0}
    )
    
    repriced_lines = []
    total_medicare = 0
    total_network = 0
    
    for line in claim.get("service_lines", []):
        code = line.get("cpt_code", "")
        billed = line.get("billed_amount", 0)
        units = line.get("units", 1)
        
        medicare_rate = calculate_medicare_rate(code, "00000", use_facility=True)
        if not medicare_rate:
            code_data = lookup_code_for_claim_type(code, claim.get("claim_type", "medical"))
            medicare_rate = code_data.get("fee", billed * 0.8) if code_data else billed * 0.8
        
        medicare_allowed = medicare_rate * units
        
        if contract:
            network_rate = medicare_rate * contract.get("multiplier", 1.2) * units
        else:
            network_rate = medicare_allowed
        
        total_medicare += medicare_allowed
        total_network += network_rate
        
        repriced_lines.append({
            "cpt_code": code,
            "billed": billed,
            "medicare_rate": round(medicare_rate, 2),
            "medicare_allowed": round(medicare_allowed, 2),
            "network_rate": round(network_rate, 2),
            "savings_vs_billed": round(billed - network_rate, 2),
        })
    
    return {
        "claim_id": claim_id,
        "claim_number": claim.get("claim_number"),
        "provider_npi": claim.get("provider_npi"),
        "has_contract": contract is not None,
        "network_name": contract.get("network_name") if contract else None,
        "contract_multiplier": contract.get("multiplier") if contract else None,
        "total_billed": claim.get("total_billed", 0),
        "total_medicare": round(total_medicare, 2),
        "total_network": round(total_network, 2),
        "total_savings": round(claim.get("total_billed", 0) - total_network, 2),
        "lines": repriced_lines,
    }

@api_router.get("/network/summary")
async def network_summary(user: dict = Depends(get_current_user)):
    """Get network repricing summary across all claims."""
    contracts = await db.network_contracts.find({"status": "active"}, {"_id": 0}).to_list(1000)
    claims = await db.claims.find({"status": "approved"}, {"_id": 0, "total_billed": 1, "total_paid": 1, "total_allowed": 1}).to_list(10000)
    
    total_billed = sum(c.get("total_billed", 0) for c in claims)
    total_paid = sum(c.get("total_paid", 0) for c in claims)
    
    return {
        "active_contracts": len(contracts),
        "total_claims_processed": len(claims),
        "total_billed": round(total_billed, 2),
        "total_paid": round(total_paid, 2),
        "total_savings": round(total_billed - total_paid, 2),
        "savings_percentage": round((total_billed - total_paid) / total_billed * 100, 1) if total_billed > 0 else 0,
    }


# ==================== PRIOR AUTHORIZATION ====================

class PriorAuthRequest(BaseModel):
    member_id: str
    provider_npi: str
    provider_name: str
    service_type: str
    procedure_codes: List[str]
    diagnosis_codes: List[str]
    requested_date: str
    clinical_notes: str = ""
    urgency: str = "routine"

class PriorAuthDecision(BaseModel):
    decision: str  # approved, denied, pended
    notes: str = ""
    approved_units: Optional[int] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None

@api_router.post("/prior-auth")
async def create_prior_auth(auth_req: PriorAuthRequest, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Create a prior authorization request."""
    auth_number = f"PA-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    
    doc = {
        "id": str(uuid.uuid4()),
        "auth_number": auth_number,
        **auth_req.model_dump(),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get("id"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "decision_history": [],
    }
    await db.prior_authorizations.insert_one(doc)
    
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "prior_auth_created",
        "user_id": user.get("id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {"auth_number": auth_number, "member_id": auth_req.member_id}
    })
    
    doc.pop("_id", None)
    return doc

@api_router.get("/prior-auth")
async def list_prior_auth(
    status: Optional[str] = None,
    member_id: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if member_id:
        query["member_id"] = member_id
    auths = await db.prior_authorizations.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return auths

@api_router.get("/prior-auth/{auth_id}")
async def get_prior_auth(auth_id: str, user: dict = Depends(get_current_user)):
    auth = await db.prior_authorizations.find_one({"id": auth_id}, {"_id": 0})
    if not auth:
        raise HTTPException(status_code=404, detail="Prior authorization not found")
    return auth

@api_router.post("/prior-auth/{auth_id}/decide")
async def decide_prior_auth(auth_id: str, decision: PriorAuthDecision, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Approve, deny, or pend a prior authorization."""
    auth = await db.prior_authorizations.find_one({"id": auth_id}, {"_id": 0})
    if not auth:
        raise HTTPException(status_code=404, detail="Prior authorization not found")
    
    update_data = {
        "status": decision.decision,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "decided_by": user.get("id"),
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }
    
    if decision.decision == "approved":
        update_data["approved_units"] = decision.approved_units
        update_data["valid_from"] = decision.valid_from or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        update_data["valid_to"] = decision.valid_to or (datetime.now(timezone.utc) + timedelta(days=90)).strftime("%Y-%m-%d")
    
    decision_record = {
        "decision": decision.decision,
        "notes": decision.notes,
        "decided_by": user.get("id"),
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.prior_authorizations.update_one(
        {"id": auth_id},
        {"$set": update_data, "$push": {"decision_history": decision_record}}
    )
    
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": f"prior_auth_{decision.decision}",
        "user_id": user.get("id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {"auth_number": auth.get("auth_number"), "auth_id": auth_id}
    })
    
    updated = await db.prior_authorizations.find_one({"id": auth_id}, {"_id": 0})
    return updated


# ==================== BATCH PROCESSING ====================

class BatchClaimRequest(BaseModel):
    claims: List[ClaimCreate]
    auto_adjudicate: bool = True
    locality_code: str = "00000"

@api_router.post("/claims/batch")
async def batch_process_claims(batch: BatchClaimRequest, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Process multiple claims in a batch."""
    results = {
        "total": len(batch.claims),
        "created": 0,
        "adjudicated": 0,
        "errors": [],
        "claim_ids": [],
    }
    
    for i, claim_data in enumerate(batch.claims):
        try:
            result = await create_claim(claim_data, user)
            results["created"] += 1
            claim_id = result.get("id") if isinstance(result, dict) else None
            if claim_id:
                results["claim_ids"].append(claim_id)
                if result.get("status") in ["approved", "denied"]:
                    results["adjudicated"] += 1
        except Exception as e:
            results["errors"].append({"index": i, "error": str(e)})
    
    return results


# ==================== COORDINATION OF BENEFITS ====================

class COBInfo(BaseModel):
    claim_id: str
    primary_payer: str
    primary_paid: float
    primary_allowed: float
    primary_member_resp: float

@api_router.post("/claims/{claim_id}/cob")
async def process_cob(claim_id: str, cob: COBInfo, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Process Coordination of Benefits - apply secondary plan payment."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Secondary plan pays remaining member responsibility up to allowed amount
    remaining = cob.primary_member_resp
    secondary_allowed = claim.get("total_allowed", 0)
    secondary_pays = min(remaining, secondary_allowed - cob.primary_paid)
    secondary_pays = max(0, secondary_pays)
    final_member_resp = max(0, remaining - secondary_pays)
    
    cob_record = {
        "primary_payer": cob.primary_payer,
        "primary_paid": cob.primary_paid,
        "primary_allowed": cob.primary_allowed,
        "primary_member_resp": cob.primary_member_resp,
        "secondary_paid": round(secondary_pays, 2),
        "final_member_resp": round(final_member_resp, 2),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "processed_by": user.get("id"),
    }
    
    await db.claims.update_one(
        {"id": claim_id},
        {"$set": {
            "cob_info": cob_record,
            "total_paid": round(claim.get("total_paid", 0) + secondary_pays, 2) if claim.get("status") != "approved" else claim.get("total_paid", 0),
            "member_responsibility": round(final_member_resp, 2),
        }}
    )
    
    return {
        "claim_id": claim_id,
        "cob": cob_record,
        "total_all_payers": round(cob.primary_paid + secondary_pays, 2),
    }


# ==================== PREVENTIVE SERVICES ENDPOINTS ====================

@api_router.get("/preventive/services")
async def list_preventive_services(
    category: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all preventive services, optionally filtered by category."""
    if category:
        results = get_preventive_by_category(category)
    else:
        results = [{"code": code, **data} for code, data in PREVENTIVE_SERVICES.items()]
    return {"results": results, "count": len(results)}

@api_router.get("/preventive/search")
async def search_preventive(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=50, le=100),
    user: dict = Depends(get_current_user)
):
    results = search_preventive_services(q, limit)
    return {"results": results, "count": len(results)}

@api_router.get("/preventive/categories")
async def preventive_categories(user: dict = Depends(get_current_user)):
    """Get all preventive service categories with counts."""
    cats = {}
    for code, data in PREVENTIVE_SERVICES.items():
        cat = data.get("category", "Other")
        if cat not in cats:
            cats[cat] = {"count": 0, "subcategories": set()}
        cats[cat]["count"] += 1
        cats[cat]["subcategories"].add(data.get("subcategory", ""))
    # Convert sets to lists for JSON
    for cat in cats:
        cats[cat]["subcategories"] = sorted(cats[cat]["subcategories"])
    return cats

@api_router.get("/preventive/check-eligibility")
async def check_preventive_eligibility(
    cpt_code: str,
    member_id: str,
    service_date: str,
    user: dict = Depends(get_current_user)
):
    """Check if a specific preventive service is eligible for a member."""
    member = await db.members.find_one({"member_id": member_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    age = calculate_member_age(member.get("dob", "2000-01-01"), service_date)
    gender = member.get("gender", "U").lower()
    if gender in ("m", "male"):
        gender = "male"
    elif gender in ("f", "female"):
        gender = "female"
    
    service = get_preventive_service(cpt_code)
    if not service:
        return {"eligible": False, "reason": "Code not in preventive database", "code": cpt_code}
    
    eval_result = evaluate_preventive_claim_line(cpt_code, ["Z00.00"], None, age, gender)
    
    within_limit, freq_msg, usage = await check_preventive_frequency(db, member_id, cpt_code, service_date, service)
    
    return {
        "code": cpt_code,
        "service": service,
        "member_age": age,
        "member_gender": gender,
        "age_eligible": eval_result.get("is_preventive") is not False or "age" not in eval_result.get("reason", ""),
        "gender_eligible": eval_result.get("is_preventive") is not False or "gender" not in eval_result.get("reason", ""),
        "within_frequency": within_limit,
        "frequency_message": freq_msg,
        "usage_count": usage,
        "evaluation": eval_result,
    }

@api_router.get("/preventive/utilization/{member_id}")
async def member_preventive_utilization(member_id: str, user: dict = Depends(get_current_user)):
    """Get a member's preventive service utilization history."""
    records = await db.preventive_utilization.find(
        {"member_id": member_id}, {"_id": 0}
    ).sort("service_date", -1).to_list(500)
    return {"member_id": member_id, "records": records, "count": len(records)}

@api_router.get("/preventive/analytics")
async def preventive_analytics(user: dict = Depends(get_current_user)):
    """Get preventive service analytics / utilization stats."""
    total_utilization = await db.preventive_utilization.count_documents({})
    
    # Members with at least one preventive service
    pipeline_unique_members = [{"$group": {"_id": "$member_id"}}]
    unique_members = await db.preventive_utilization.aggregate(pipeline_unique_members).to_list(100000)
    
    total_members = await db.members.count_documents({"status": "active"})
    
    # Category breakdown
    pipeline_cats = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cat_breakdown = await db.preventive_utilization.aggregate(pipeline_cats).to_list(50)
    
    # Claims with preventive lines
    pipeline_prev_claims = [
        {"$match": {"service_lines.is_preventive": True}},
        {"$count": "count"}
    ]
    prev_claims_result = await db.claims.aggregate(pipeline_prev_claims).to_list(1)
    prev_claims_count = prev_claims_result[0]["count"] if prev_claims_result else 0
    
    # Calculate total preventive paid
    pipeline_prev_paid = [
        {"$match": {"service_lines.is_preventive": True}},
        {"$unwind": "$service_lines"},
        {"$match": {"service_lines.is_preventive": True}},
        {"$group": {"_id": None, "total_paid": {"$sum": "$service_lines.paid"}}},
    ]
    prev_paid_result = await db.claims.aggregate(pipeline_prev_paid).to_list(1)
    total_prev_paid = prev_paid_result[0]["total_paid"] if prev_paid_result else 0
    
    members_with_preventive = len(unique_members)
    compliance_rate = (members_with_preventive / total_members * 100) if total_members > 0 else 0
    pmpm = (total_prev_paid / max(total_members, 1)) if total_members > 0 else 0
    
    return {
        "total_preventive_services": total_utilization,
        "members_with_preventive": members_with_preventive,
        "total_active_members": total_members,
        "compliance_rate": round(compliance_rate, 1),
        "preventive_pmpm": round(pmpm, 2),
        "total_preventive_paid": round(total_prev_paid, 2),
        "claims_with_preventive": prev_claims_count,
        "category_breakdown": [{"category": c["_id"], "count": c["count"]} for c in cat_breakdown],
        "total_preventive_codes": len(PREVENTIVE_SERVICES),
    }

@api_router.get("/preventive/abuse-detection")
async def preventive_abuse_detection(user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Detect potential preventive service abuse patterns."""
    flags = []
    
    # 1. Duplicate preventive visits same DOS/provider
    pipeline_dup = [
        {"$match": {"service_lines.is_preventive": True}},
        {"$group": {
            "_id": {"member_id": "$member_id", "provider_npi": "$provider_npi", "service_date_from": "$service_date_from"},
            "count": {"$sum": 1},
            "claim_ids": {"$push": "$id"},
            "claim_numbers": {"$push": "$claim_number"},
        }},
        {"$match": {"count": {"$gt": 1}}},
    ]
    dup_visits = await db.claims.aggregate(pipeline_dup).to_list(100)
    for dv in dup_visits:
        flags.append({
            "type": "duplicate_preventive_visit",
            "severity": "high",
            "member_id": dv["_id"]["member_id"],
            "provider_npi": dv["_id"]["provider_npi"],
            "service_date": dv["_id"]["service_date_from"],
            "count": dv["count"],
            "claim_numbers": dv["claim_numbers"],
            "message": f"Duplicate preventive visit: {dv['count']} claims on same date/provider",
        })
    
    # 2. Excess frequency (check utilization records)
    pipeline_freq = [
        {"$group": {
            "_id": {"member_id": "$member_id", "subcategory": "$subcategory"},
            "count": {"$sum": 1},
        }},
        {"$match": {"count": {"$gt": 3}}},
    ]
    freq_excess = await db.preventive_utilization.aggregate(pipeline_freq).to_list(100)
    for fe in freq_excess:
        flags.append({
            "type": "excess_frequency",
            "severity": "medium",
            "member_id": fe["_id"]["member_id"],
            "subcategory": fe["_id"]["subcategory"],
            "count": fe["count"],
            "message": f"High frequency for {fe['_id']['subcategory']}: {fe['count']} occurrences",
        })
    
    return {"flags": flags, "total_flags": len(flags)}


# ==================== ROOT ENDPOINT ====================

@api_router.get("/")
async def root():
    return {"message": "FletchFlow Claims Adjudication System API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
