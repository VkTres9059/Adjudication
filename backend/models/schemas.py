from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict
from models.enums import UserRole, ClaimType


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
    preventive_design: str = "aca_strict"
    plan_template: Optional[str] = None
    preauth_penalty_pct: float = 50.0
    non_network_reimbursement: str = "reference_based"
    eligibility_threshold: float = 0
    hour_bank_max: float = 0


class StopLossConfig(BaseModel):
    specific_deductible: float = 0
    aggregate_attachment_point: float = 0
    aggregate_factor: float = 125.0
    contract_period: str = "12_month"
    laser_deductibles: List[dict] = []


class SFTPConfig(BaseModel):
    host: str = ""
    port: int = 22
    username: str = ""
    directory: str = "/"
    schedule: str = "daily"
    file_types: List[str] = ["834", "835"]
    enabled: bool = False


class GroupCreate(BaseModel):
    name: str
    tax_id: str
    effective_date: str
    termination_date: Optional[str] = None
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    sic_code: str = ""
    employee_count: int = 0
    total_premium: float = 0.0
    mgu_fees: float = 0.0
    funding_type: str = "aso"  # aso, level_funded, fully_insured
    claims_fund_monthly: float = 0.0  # Monthly claims fund deposit for level_funded
    stop_loss: Optional[StopLossConfig] = None
    sftp_config: Optional[SFTPConfig] = None
    plan_ids: List[str] = []


class GroupResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    tax_id: str
    effective_date: str
    termination_date: Optional[str] = None
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    sic_code: str = ""
    employee_count: int = 0
    stop_loss: Optional[dict] = None
    sftp_config: Optional[dict] = None
    plan_ids: List[str] = []
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""


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
    preventive_design: str = "aca_strict"
    plan_template: Optional[str] = None
    preauth_penalty_pct: float = 50.0
    non_network_reimbursement: str = "reference_based"
    eligibility_threshold: float = 0
    hour_bank_max: float = 0


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
    audit_flag: Optional[str] = None
    hold_info: Optional[Dict] = None
    tier_level: Optional[int] = None
    carrier_notification: Optional[bool] = None
    eligibility_deadline: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_at: Optional[str] = None
    eligibility_source: Optional[str] = None


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
    action: str
    notes: Optional[str] = None
    denial_reason: Optional[str] = None
    deductible_adjustment: Optional[float] = None


class AdjudicationGatewayConfig(BaseModel):
    tier1_auto_pilot_limit: float = 500.0
    tier2_audit_hold_limit: float = 2500.0
    enabled: bool = True


class HoldRequest(BaseModel):
    reason_code: str
    notes: Optional[str] = None


class DashboardMetrics(BaseModel):
    total_claims: int
    pending_claims: int
    approved_claims: int
    denied_claims: int
    duplicate_alerts: int
    held_claims: int = 0
    total_paid: float
    total_saved_duplicates: float
    auto_adjudication_rate: float
    avg_turnaround_hours: float


class NetworkContract(BaseModel):
    provider_npi: str
    provider_name: str
    network_name: str
    contract_type: str = "percent_medicare"
    multiplier: float = 1.2
    effective_date: str
    termination_date: Optional[str] = None
    coverage_types: List[str] = ["medical"]


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
    decision: str
    notes: str = ""
    approved_units: Optional[int] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class BatchClaimRequest(BaseModel):
    claims: List[ClaimCreate]
    auto_adjudicate: bool = True
    locality_code: str = "00000"


class COBInfo(BaseModel):
    claim_id: str
    primary_payer: str
    primary_paid: float
    primary_allowed: float
    primary_member_resp: float
