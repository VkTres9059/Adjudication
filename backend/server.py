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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'javelina-claims-secret-key-2024')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Create the main app
app = FastAPI(title="Javelina Claims Adjudication System", version="1.0.0")

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

async def adjudicate_claim(claim: dict, plan: dict, member: dict, locality_code: str = "00000") -> dict:
    """Apply plan rules to adjudicate a claim using Medicare fee schedule"""
    
    adjudication_notes = []
    total_allowed = 0
    total_paid = 0
    member_responsibility = 0
    
    # Check member eligibility
    claim_date = datetime.fromisoformat(claim["service_date_from"])
    member_eff = datetime.fromisoformat(member["effective_date"])
    member_term = datetime.fromisoformat(member["termination_date"]) if member.get("termination_date") else None
    
    if claim_date < member_eff:
        return {
            "status": ClaimStatus.DENIED.value,
            "total_allowed": 0,
            "total_paid": 0,
            "member_responsibility": claim["total_billed"],
            "adjudication_notes": ["DENIED: Service date before coverage effective date"]
        }
    
    if member_term and claim_date > member_term:
        return {
            "status": ClaimStatus.DENIED.value,
            "total_allowed": 0,
            "total_paid": 0,
            "member_responsibility": claim["total_billed"],
            "adjudication_notes": ["DENIED: Service date after coverage termination"]
        }
    
    # Get member accumulators
    accumulators = await db.accumulators.find_one(
        {"member_id": claim["member_id"], "plan_year": str(claim_date.year)},
        {"_id": 0}
    ) or {
        "deductible_met": 0,
        "oop_met": 0
    }
    
    deductible = plan["deductible_individual"]
    oop_max = plan["oop_max_individual"]
    
    # Get plan reimbursement method and multiplier
    reimbursement_method = plan.get("reimbursement_method", "fee_schedule")
    # Default multipliers based on reimbursement method
    method_multipliers = {
        "fee_schedule": 1.0,
        "percent_medicare": 1.2,  # 120% of Medicare
        "percent_billed": 0.8,    # 80% of billed
        "rbp": 1.4,               # 140% of Medicare for RBP
        "contracted": 1.0         # Use contracted/Medicare rates
    }
    rate_multiplier = method_multipliers.get(reimbursement_method, 1.0)
    
    # Process each service line
    processed_lines = []
    for line in claim["service_lines"]:
        cpt_code = line["cpt_code"]
        billed = line["billed_amount"]
        units = line.get("units", 1)
        
        # Look up CPT code in Medicare fee schedule
        cpt_data = get_cpt_code(cpt_code)
        
        # Find matching benefit category
        benefit = None
        for b in plan.get("benefits", []):
            if b.get("code_range"):
                # Code range matching
                if cpt_code.startswith(b["code_range"][:3]):
                    benefit = b
                    break
            elif b.get("service_category"):
                # Category matching based on CPT data
                if cpt_data:
                    cpt_category = cpt_data.get("category", "")
                    service_cat = b.get("service_category", "").lower()
                    # Map CPT categories to service categories
                    category_map = {
                        "E/M": ["office visit", "preventive", "hospital", "emergency", "evaluation"],
                        "Surgery": ["surgery", "procedure"],
                        "Radiology": ["imaging", "radiology", "x-ray", "ct", "mri"],
                        "Pathology/Lab": ["lab", "pathology", "diagnostic"],
                        "Medicine": ["physical therapy", "immunization", "vaccine", "cardio", "pulmonary"],
                        "Anesthesia": ["anesthesia"],
                        "HCPCS": ["drug", "injection", "dme", "equipment"]
                    }
                    if cpt_category in category_map:
                        for keyword in category_map[cpt_category]:
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
                **line,
                "allowed": 0,
                "paid": 0,
                "member_resp": billed,
                "denial_reason": "Service not covered under plan",
                "medicare_rate": None
            })
            adjudication_notes.append(f"Line {line['line_number']}: {cpt_code} - NOT COVERED under benefit plan")
            member_responsibility += billed
            continue
        
        # Check exclusions
        if cpt_code in plan.get("exclusions", []):
            processed_lines.append({
                **line,
                "allowed": 0,
                "paid": 0,
                "member_resp": billed,
                "denial_reason": "Service excluded from coverage",
                "medicare_rate": None
            })
            adjudication_notes.append(f"Line {line['line_number']}: {cpt_code} - EXCLUDED from coverage")
            member_responsibility += billed
            continue
        
        # Check prior auth if required
        if benefit.get("prior_auth_required") and not claim.get("prior_auth_number"):
            processed_lines.append({
                **line,
                "allowed": 0,
                "paid": 0,
                "member_resp": billed,
                "denial_reason": "Prior authorization required",
                "medicare_rate": None
            })
            adjudication_notes.append(f"Line {line['line_number']}: {cpt_code} - Prior auth REQUIRED but not provided")
            member_responsibility += billed
            continue
        
        # Calculate allowed amount using Medicare fee schedule
        medicare_rate = None
        if cpt_data:
            # Use Medicare rate with GPCI adjustment
            medicare_rate = calculate_medicare_rate(cpt_code, locality_code, use_facility=True)
            
            if medicare_rate:
                # Apply plan's reimbursement method multiplier
                allowed = medicare_rate * rate_multiplier * units
                adjudication_notes.append(
                    f"Line {line['line_number']}: {cpt_code} ({cpt_data.get('description', 'Unknown')[:50]}...) - "
                    f"Medicare Rate: ${medicare_rate:.2f}, Method: {reimbursement_method} ({rate_multiplier*100:.0f}%)"
                )
            else:
                # Fallback: use percentage of billed
                allowed = billed * 0.8
                adjudication_notes.append(
                    f"Line {line['line_number']}: {cpt_code} - No Medicare rate, using 80% of billed"
                )
        else:
            # Unknown CPT code - use percentage of billed
            allowed = billed * 0.8
            adjudication_notes.append(
                f"Line {line['line_number']}: {cpt_code} - UNKNOWN CPT code, using 80% of billed"
            )
        
        # Cap allowed at billed amount
        allowed = min(allowed, billed)
        
        # Apply deductible
        line_deductible = 0
        if benefit.get("deductible_applies", True):
            remaining_deductible = max(0, deductible - accumulators["deductible_met"])
            line_deductible = min(allowed, remaining_deductible)
            accumulators["deductible_met"] += line_deductible
        
        # Calculate coinsurance
        after_deductible = allowed - line_deductible
        copay = benefit.get("copay", 0)
        coinsurance_pct = benefit.get("coinsurance", 0.2)
        coinsurance_amount = after_deductible * coinsurance_pct
        
        # Calculate paid amount
        paid = after_deductible - coinsurance_amount - copay
        
        # Check OOP max
        member_resp_this_line = line_deductible + coinsurance_amount + copay
        remaining_oop = max(0, oop_max - accumulators["oop_met"])
        if member_resp_this_line > remaining_oop:
            # OOP max reached - plan pays more
            paid += (member_resp_this_line - remaining_oop)
            member_resp_this_line = remaining_oop
            adjudication_notes.append(f"Line {line['line_number']}: OOP MAX reached - additional plan payment applied")
        
        accumulators["oop_met"] += member_resp_this_line
        
        total_allowed += allowed
        total_paid += max(0, paid)
        member_responsibility += member_resp_this_line
        
        processed_lines.append({
            **line,
            "allowed": round(allowed, 2),
            "paid": round(max(0, paid), 2),
            "member_resp": round(member_resp_this_line, 2),
            "deductible_applied": round(line_deductible, 2),
            "coinsurance_applied": round(coinsurance_amount, 2),
            "medicare_rate": medicare_rate,
            "cpt_description": cpt_data.get("description", "Unknown") if cpt_data else "Unknown",
            "work_rvu": cpt_data.get("work_rvu") if cpt_data else None,
            "total_rvu": cpt_data.get("total_rvu") if cpt_data else None
        })
    
    # Update accumulators
    await db.accumulators.update_one(
        {"member_id": claim["member_id"], "plan_year": str(claim_date.year)},
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
    """Process EDI 834 enrollment file"""
    content = await file.read()
    content_str = content.decode('utf-8')
    
    # Simplified 834 parsing - in production would use proper X12 parser
    members_created = 0
    errors = []
    
    # Parse simple format: MemberID|FirstName|LastName|DOB|Gender|GroupID|PlanID|EffDate
    for line in content_str.strip().split('\n'):
        if not line or line.startswith('#'):
            continue
        try:
            parts = line.split('|')
            if len(parts) >= 8:
                member_data = MemberCreate(
                    member_id=parts[0],
                    first_name=parts[1],
                    last_name=parts[2],
                    dob=parts[3],
                    gender=parts[4],
                    group_id=parts[5],
                    plan_id=parts[6],
                    effective_date=parts[7],
                    relationship="subscriber"
                )
                
                # Check if exists
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
        except Exception as e:
            errors.append(f"Line error: {str(e)}")
    
    return {"members_created": members_created, "errors": errors}

@api_router.post("/edi/upload-837")
async def upload_edi_837(file: UploadFile = File(...), user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))):
    """Process EDI 837 claims file"""
    content = await file.read()
    content_str = content.decode('utf-8')
    
    claims_created = 0
    errors = []
    
    # Simplified 837 parsing
    # Format: MemberID|ProviderNPI|ProviderName|ClaimType|DateFrom|DateTo|TotalBilled|DiagCodes|CPT1:Units1:Amount1,CPT2:Units2:Amount2
    for line in content_str.strip().split('\n'):
        if not line or line.startswith('#'):
            continue
        try:
            parts = line.split('|')
            if len(parts) >= 9:
                # Parse service lines
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
                    member_id=parts[0],
                    provider_npi=parts[1],
                    provider_name=parts[2],
                    claim_type=ClaimType(parts[3]),
                    service_date_from=parts[4],
                    service_date_to=parts[5],
                    total_billed=float(parts[6]),
                    diagnosis_codes=parts[7].split(','),
                    service_lines=service_lines,
                    source="edi_837"
                )
                
                # Create claim using existing endpoint logic
                await create_claim(claim_data, user)
                claims_created += 1
        except Exception as e:
            errors.append(f"Line error: {str(e)}")
    
    return {"claims_created": claims_created, "errors": errors}

@api_router.get("/edi/generate-835")
async def generate_edi_835(
    date_from: str,
    date_to: str,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR]))
):
    """Generate EDI 835 payment file"""
    claims = await db.claims.find({
        "status": ClaimStatus.APPROVED.value,
        "adjudicated_at": {"$gte": date_from, "$lte": date_to}
    }, {"_id": 0}).to_list(10000)
    
    # Simplified 835 format
    lines = ["# EDI 835 Payment File", f"# Generated: {datetime.now(timezone.utc).isoformat()}", "# ClaimNumber|MemberID|ProviderNPI|TotalBilled|TotalAllowed|TotalPaid|MemberResp"]
    
    for claim in claims:
        lines.append(f"{claim['claim_number']}|{claim['member_id']}|{claim['provider_npi']}|{claim['total_billed']}|{claim['total_allowed']}|{claim['total_paid']}|{claim['member_responsibility']}")
    
    return {"content": "\n".join(lines), "claim_count": len(claims)}

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

@api_router.get("/cpt-codes/category/{category}")
async def get_codes_by_cat(
    category: str,
    user: dict = Depends(get_current_user)
):
    """Get all CPT codes in a specific category"""
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

# ==================== ROOT ENDPOINT ====================

@api_router.get("/")
async def root():
    return {"message": "Javelina Claims Adjudication System API", "version": "1.0.0"}

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
