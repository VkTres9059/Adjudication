from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole, ClaimType, PlanStatus
from models.schemas import PlanCreate, PlanResponse, PlanBenefit

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("", response_model=PlanResponse)
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

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "plan_created",
        "user_id": user["id"],
        "details": {"plan_id": plan_id, "plan_name": plan_data.name},
        "timestamp": now
    })

    return PlanResponse(**{k: v for k, v in plan_doc.items() if k != "_id"})


@router.get("", response_model=List[PlanResponse])
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


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str, user: dict = Depends(get_current_user)):
    plan = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return PlanResponse(**plan)


@router.put("/{plan_id}", response_model=PlanResponse)
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

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "plan_updated",
        "user_id": user["id"],
        "details": {"plan_id": plan_id, "new_version": existing["version"] + 1},
        "timestamp": now
    })

    updated = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    return PlanResponse(**updated)


@router.post("/template/mec-1")
async def create_mec1_plan(group_id: str = Query(...), plan_name: str = Query(default="MEC 1 - Standard"), user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a pre-configured MEC 1 (Minimum Essential Coverage) plan from the SOB template."""
    plan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    mec1_benefits = [
        PlanBenefit(service_category="Preventive Care", covered=True, copay=0, coinsurance=0, deductible_applies=False, prior_auth_required=False).model_dump(),
        PlanBenefit(service_category="Wellness Visit", covered=True, copay=0, coinsurance=0, deductible_applies=False, prior_auth_required=False).model_dump(),
        PlanBenefit(service_category="Immunization", covered=True, copay=0, coinsurance=0, deductible_applies=False, prior_auth_required=False).model_dump(),
        PlanBenefit(service_category="Cancer Screening", covered=True, copay=0, coinsurance=0, deductible_applies=False, prior_auth_required=False).model_dump(),
        PlanBenefit(service_category="Preventive Screening", covered=True, copay=0, coinsurance=0, deductible_applies=False, prior_auth_required=False).model_dump(),
        PlanBenefit(service_category="Women's Preventive", covered=True, copay=0, coinsurance=0, deductible_applies=False, prior_auth_required=False).model_dump(),
        PlanBenefit(service_category="Pediatric Preventive", covered=True, copay=0, coinsurance=0, deductible_applies=False, prior_auth_required=False).model_dump(),
        PlanBenefit(service_category="Behavioral Counseling", covered=True, copay=0, coinsurance=0, deductible_applies=False, prior_auth_required=False).model_dump(),
        PlanBenefit(service_category="Telemedicine - Preventive", covered=True, copay=0, coinsurance=0, deductible_applies=False, prior_auth_required=False).model_dump(),
        PlanBenefit(service_category="Preventive Rx", covered=True, copay=0, coinsurance=0, deductible_applies=False, prior_auth_required=False).model_dump(),
        PlanBenefit(service_category="Primary Care Office Visit", covered=False).model_dump(),
        PlanBenefit(service_category="Specialist Office Visit", covered=False).model_dump(),
        PlanBenefit(service_category="Emergency Room", covered=False).model_dump(),
        PlanBenefit(service_category="Urgent Care", covered=False).model_dump(),
        PlanBenefit(service_category="Inpatient Hospital", covered=False).model_dump(),
        PlanBenefit(service_category="Outpatient Surgery", covered=False).model_dump(),
        PlanBenefit(service_category="Diagnostic Testing", covered=False).model_dump(),
        PlanBenefit(service_category="Imaging Services", covered=False).model_dump(),
        PlanBenefit(service_category="DME", covered=False).model_dump(),
        PlanBenefit(service_category="Mental Health", covered=False).model_dump(),
        PlanBenefit(service_category="Physical Therapy", covered=False).model_dump(),
        PlanBenefit(service_category="Chiropractic", covered=False).model_dump(),
    ]

    mec1_exclusions = [
        "Abortion", "Acupuncture", "Applied Behavioral Analysis", "Cardiac Rehabilitation",
        "Chemotherapy", "Chiropractic Care", "Clinical Trials", "Cosmetic Surgery",
        "Custodial Care", "Dental Care", "Dialysis", "DME", "Gene and Cell Therapy",
        "Home Health Care", "Hospice Care", "Infusion Therapy", "Infertility",
        "Long Term Care", "Massage Therapy", "Mental Health (non-preventive)",
        "Occupational Therapy", "Physical Therapy", "Private Duty Nursing",
        "Radiation Services", "Skilled Nursing", "Sleep Studies", "Speech Therapy",
        "Transplant Services", "Allergy Testing", "Genetic Counseling (non-required)",
    ]

    plan_doc = {
        "id": plan_id,
        "name": plan_name,
        "plan_type": ClaimType.MEDICAL.value,
        "group_id": group_id,
        "effective_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "termination_date": None,
        "deductible_individual": 0,
        "deductible_family": 0,
        "oop_max_individual": 0,
        "oop_max_family": 0,
        "network_type": "PPO",
        "reimbursement_method": "reference_based",
        "benefits": mec1_benefits,
        "tier_type": "employee_only",
        "exclusions": mec1_exclusions,
        "preventive_design": "aca_strict",
        "plan_template": "mec_1",
        "preauth_penalty_pct": 50.0,
        "non_network_reimbursement": "reference_based",
        "status": PlanStatus.ACTIVE.value,
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "created_by": user["id"],
    }

    await db.plans.insert_one(plan_doc)

    group = await db.groups.find_one({"id": group_id})
    if group:
        plan_ids = group.get("plan_ids", [])
        if plan_id not in plan_ids:
            plan_ids.append(plan_id)
            await db.groups.update_one({"id": group_id}, {"$set": {"plan_ids": plan_ids}})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "mec1_plan_created",
        "user_id": user["id"],
        "timestamp": now,
        "details": {"plan_id": plan_id, "plan_name": plan_name, "group_id": group_id}
    })

    plan_doc.pop("_id", None)
    return plan_doc
