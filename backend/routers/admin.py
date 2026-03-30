"""
Admin Portal — Central control over user permissions, portal access,
TPA onboarding, data integrations, and system configuration.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from core.database import db
from core.auth import get_current_user, require_roles, hash_password
from models.enums import UserRole

router = APIRouter(prefix="/admin", tags=["admin"])


# Portal roles: admin, tpa_admin, mgu_admin, carrier_viewer, analytics_viewer
PORTAL_ROLES = {
    "admin": {"label": "System Admin", "permissions": ["all"]},
    "tpa_admin": {"label": "TPA Administrator", "permissions": ["claims.read", "claims.adjudicate", "members.read", "members.write", "reports.read"]},
    "mgu_admin": {"label": "MGU Administrator", "permissions": ["plans.read", "plans.write", "groups.read", "groups.write", "reports.read", "stop_loss.read"]},
    "carrier_viewer": {"label": "Carrier Viewer", "permissions": ["claims.read", "reports.read", "stop_loss.read", "payments.read"]},
    "analytics_viewer": {"label": "Analytics Viewer", "permissions": ["reports.read", "dashboard.read"]},
}


class UserCreateAdmin(BaseModel):
    email: str
    password: str
    name: str
    role: str = "reviewer"
    portal_role: str = "analytics_viewer"
    tpa_id: Optional[str] = None
    group_ids: List[str] = []


class TPAOnboard(BaseModel):
    name: str
    tax_id: str
    contact_name: str
    contact_email: str
    contact_phone: str = ""
    address: str = ""
    data_feed_type: str = "edi_834_837"  # edi_834_837, api, sftp
    group_ids: List[str] = []
    notes: str = ""


class PortalAccessUpdate(BaseModel):
    user_id: str
    portal_role: str
    group_ids: List[str] = []
    active: bool = True


@router.get("/portal-roles")
async def get_portal_roles(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """List available portal roles and permissions."""
    return PORTAL_ROLES


@router.get("/users")
async def list_all_users(
    role: Optional[str] = None,
    portal_role: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """List all users with their portal access."""
    query = {}
    if role:
        query["role"] = role
    if portal_role:
        query["portal_role"] = portal_role
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("name", 1).to_list(limit)
    return users


@router.post("/users")
async def create_user_admin(data: UserCreateAdmin, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a user with portal role assignment."""
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(400, "Email already registered")

    now = datetime.now(timezone.utc).isoformat()
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "name": data.name,
        "role": data.role,
        "portal_role": data.portal_role,
        "tpa_id": data.tpa_id,
        "group_ids": data.group_ids,
        "permissions": PORTAL_ROLES.get(data.portal_role, {}).get("permissions", []),
        "active": True,
        "created_at": now,
        "created_by": user["id"],
    }
    await db.users.insert_one(user_doc)

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "action": "user_created_admin",
        "entity_type": "user", "entity_id": user_id,
        "user_id": user["id"], "timestamp": now,
        "details": {"email": data.email, "role": data.role, "portal_role": data.portal_role}
    })

    user_doc.pop("_id", None)
    user_doc.pop("password_hash", None)
    return user_doc


@router.put("/users/{user_id}/access")
async def update_portal_access(user_id: str, data: PortalAccessUpdate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Update a user's portal access and group assignments."""
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "User not found")

    now = datetime.now(timezone.utc).isoformat()
    permissions = PORTAL_ROLES.get(data.portal_role, {}).get("permissions", [])

    await db.users.update_one({"id": user_id}, {"$set": {
        "portal_role": data.portal_role,
        "group_ids": data.group_ids,
        "permissions": permissions,
        "active": data.active,
        "updated_at": now,
    }})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "action": "portal_access_updated",
        "entity_type": "user", "entity_id": user_id,
        "user_id": user["id"], "timestamp": now,
        "details": {"portal_role": data.portal_role, "active": data.active, "groups": data.group_ids}
    })

    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return updated


# ── TPA Management ──

@router.get("/tpas")
async def list_tpas(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """List all onboarded TPAs."""
    tpas = await db.tpas.find({}, {"_id": 0}).sort("name", 1).to_list(100)
    return tpas


@router.post("/tpas")
async def onboard_tpa(data: TPAOnboard, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Onboard a new TPA with data feed configuration."""
    existing = await db.tpas.find_one({"tax_id": data.tax_id})
    if existing:
        raise HTTPException(400, "TPA with this Tax ID already exists")

    now = datetime.now(timezone.utc).isoformat()
    tpa_id = str(uuid.uuid4())
    tpa_doc = {
        "id": tpa_id,
        **data.model_dump(),
        "status": "active",
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    await db.tpas.insert_one(tpa_doc)

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "action": "tpa_onboarded",
        "entity_type": "tpa", "entity_id": tpa_id,
        "user_id": user["id"], "timestamp": now,
        "details": {"name": data.name, "tax_id": data.tax_id, "feed_type": data.data_feed_type}
    })

    tpa_doc.pop("_id", None)
    return tpa_doc


@router.put("/tpas/{tpa_id}")
async def update_tpa(tpa_id: str, data: TPAOnboard, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Update TPA configuration."""
    existing = await db.tpas.find_one({"id": tpa_id})
    if not existing:
        raise HTTPException(404, "TPA not found")

    now = datetime.now(timezone.utc).isoformat()
    await db.tpas.update_one({"id": tpa_id}, {"$set": {**data.model_dump(), "updated_at": now}})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()), "action": "tpa_updated",
        "entity_type": "tpa", "entity_id": tpa_id,
        "user_id": user["id"], "timestamp": now,
        "details": {"name": data.name}
    })

    updated = await db.tpas.find_one({"id": tpa_id}, {"_id": 0})
    return updated


@router.post("/tpas/{tpa_id}/attach-groups")
async def attach_groups_to_tpa(tpa_id: str, group_ids: List[str], user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Attach groups to a TPA."""
    tpa = await db.tpas.find_one({"id": tpa_id})
    if not tpa:
        raise HTTPException(404, "TPA not found")

    current_groups = tpa.get("group_ids", [])
    new_groups = list(set(current_groups + group_ids))
    await db.tpas.update_one({"id": tpa_id}, {"$set": {"group_ids": new_groups}})

    return {"tpa_id": tpa_id, "group_ids": new_groups}


# ── System Overview ──

@router.get("/system-overview")
async def system_overview(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """System-wide overview for admin dashboard."""
    users_count = await db.users.count_documents({})
    active_users = await db.users.count_documents({"active": {"$ne": False}})
    groups_count = await db.groups.count_documents({"status": "active"})
    plans_count = await db.plans.count_documents({"status": "active"})
    members_count = await db.members.count_documents({"status": "active"})
    claims_count = await db.claims.count_documents({})
    tpas_count = await db.tpas.count_documents({"status": "active"})
    payments_count = await db.payments.count_documents({})

    # Recent audit events
    recent_audits = await db.audit_logs.find(
        {}, {"_id": 0}
    ).sort("timestamp", -1).to_list(10)

    return {
        "users": {"total": users_count, "active": active_users},
        "groups": groups_count,
        "plans": plans_count,
        "members": members_count,
        "claims": claims_count,
        "tpas": tpas_count,
        "payments": payments_count,
        "recent_activity": recent_audits,
    }


@router.get("/traceability/{claim_id}")
async def claim_traceability(claim_id: str, user: dict = Depends(get_current_user)):
    """Full lifecycle traceability: Plan → Group → Eligibility → Claim → Payment."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(404, "Claim not found")

    member = await db.members.find_one({"member_id": claim.get("member_id")}, {"_id": 0})
    plan = await db.plans.find_one({"id": member.get("plan_id")}, {"_id": 0}) if member else None
    group = await db.groups.find_one({"id": member.get("group_id")}, {"_id": 0}) if member else None

    # Payment info
    payment = await db.payments.find_one({"claim_id": claim_id, "status": {"$nin": ["reversed", "voided"]}}, {"_id": 0})

    # Audit trail
    audits = await db.audit_logs.find(
        {"$or": [
            {"details.claim_id": claim_id},
            {"entity_id": claim_id},
        ]}, {"_id": 0}
    ).sort("timestamp", 1).to_list(50)

    # Plan version at adjudication
    plan_version = None
    if plan:
        pv = await db.plan_versions.find_one(
            {"plan_id": plan["id"], "version": claim.get("plan_version", plan.get("version"))},
            {"_id": 0, "snapshot": 0}
        )
        plan_version = pv

    return {
        "claim": {
            "id": claim.get("id"),
            "claim_number": claim.get("claim_number"),
            "status": claim.get("status"),
            "total_billed": claim.get("total_billed"),
            "total_paid": claim.get("total_paid"),
            "service_date": claim.get("service_date_from"),
            "adjudicated_at": claim.get("adjudicated_at"),
            "data_tier": claim.get("data_tier"),
            "idr_case_number": claim.get("idr_case_number"),
        },
        "member": {
            "member_id": member.get("member_id") if member else None,
            "name": f"{member.get('first_name', '')} {member.get('last_name', '')}" if member else None,
            "status": member.get("status") if member else None,
            "effective_date": member.get("effective_date") if member else None,
            "enrollment_tier": member.get("enrollment_tier") if member else None,
        } if member else None,
        "plan": {
            "id": plan.get("id") if plan else None,
            "name": plan.get("name") if plan else None,
            "version": plan.get("version") if plan else None,
            "plan_type": plan.get("plan_type") if plan else None,
            "network_type": plan.get("network_type") if plan else None,
        } if plan else None,
        "plan_version_at_adjudication": plan_version,
        "group": {
            "id": group.get("id") if group else None,
            "name": group.get("name") if group else None,
            "funding_type": group.get("funding_type") if group else None,
            "block_of_business": group.get("block_of_business") if group else None,
            "carrier": group.get("carrier") if group else None,
            "mgu": group.get("mgu") if group else None,
        } if group else None,
        "payment": {
            "id": payment.get("id") if payment else None,
            "amount": payment.get("amount") if payment else None,
            "method": payment.get("payment_method") if payment else None,
            "status": payment.get("status") if payment else None,
            "processed_at": payment.get("processed_at") if payment else None,
        } if payment else None,
        "audit_trail": audits,
    }
