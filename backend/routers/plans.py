from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import List, Optional
import uuid
import io

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



MODULE_LABELS = {
    "preventive": "Preventive Care (ACA)",
    "physician": "Physician / Office Visit",
    "inpatient": "Inpatient / Hospital",
    "emergency": "Emergency / Urgent Care",
    "pharmacy": "Pharmacy (Rx)",
}


@router.get("/{plan_id}/sbc-pdf")
async def generate_sbc_pdf(plan_id: str, token: Optional[str] = Query(None)):
    """Generate a Summary of Benefits and Coverage (SBC) PDF."""
    if token:
        import jwt as pyjwt
        from core.config import JWT_SECRET, JWT_ALGORITHM
        try:
            pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except Exception:
            raise HTTPException(401, "Invalid or expired token")
    else:
        raise HTTPException(401, "Token required")

    plan = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(404, "Plan not found")

    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table as RLTable, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("SBCTitle", parent=styles["Title"], fontSize=20, spaceAfter=4)
    sub_style = ParagraphStyle("SBCSub", parent=styles["Normal"], fontSize=10, textColor=colors.grey)
    h2 = ParagraphStyle("SBCH2", parent=styles["Heading2"], fontSize=13, spaceBefore=16, spaceAfter=6, textColor=colors.HexColor("#1A3636"))
    note_style = ParagraphStyle("SBCNote", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    elements = []

    # Header
    elements.append(Paragraph("Summary of Benefits and Coverage (SBC)", title_style))
    elements.append(Paragraph(
        f"<b>{plan.get('name', '')}</b> | Type: {plan.get('plan_type', '').title()} | Network: {plan.get('network_type', '')} | "
        f"Effective: {plan.get('effective_date', '')}",
        sub_style,
    ))
    elements.append(Spacer(1, 16))

    # Cost Sharing Summary
    elements.append(Paragraph("Cost Sharing", h2))
    cs_data = [
        ["", "Individual", "Family"],
        ["Annual Deductible", f"${plan.get('deductible_individual', 0):,.0f}", f"${plan.get('deductible_family', 0):,.0f}"],
        ["Out-of-Pocket Maximum", f"${plan.get('oop_max_individual', 0):,.0f}", f"${plan.get('oop_max_family', 0):,.0f}"],
    ]
    t = RLTable(cs_data, colWidths=[2.5 * inch, 2 * inch, 2 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A3636")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F4")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E2DF")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 8))

    # Reimbursement
    reimb = plan.get("reimbursement_method", "fee_schedule")
    reimb_label = {"fee_schedule": "Fee Schedule", "percent_medicare": "% of Medicare", "rbp": f"Reference Based Pricing ({plan.get('rbp_medicare_pct', 150)}% of Medicare)", "contracted": "Contracted Network", "percent_billed": "% of Billed"}.get(reimb, reimb)
    elements.append(Paragraph(f"<b>Reimbursement Method:</b> {reimb_label}", sub_style))
    elements.append(Spacer(1, 12))

    # Benefit Modules
    modules = plan.get("benefit_modules", [])
    if modules:
        elements.append(Paragraph("Covered Benefits", h2))
        mod_data = [["Benefit Module", "Copay", "Deductible", "Coinsurance", "Prior Auth"]]
        for m in modules:
            if m.get("enabled", True):
                label = MODULE_LABELS.get(m.get("module_id", ""), m.get("module_id", ""))
                mod_data.append([
                    label,
                    f"${m.get('copay', 0):,.0f}",
                    f"${m.get('deductible', 0):,.0f}",
                    f"{m.get('coinsurance', 20):.0f}%",
                    "Yes" if m.get("prior_auth_required") else "No",
                ])
        mt = RLTable(mod_data, colWidths=[2.5 * inch, 1 * inch, 1 * inch, 1 * inch, 1 * inch])
        mt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A6FA5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EFF4FB")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E2DF")),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(mt)
        elements.append(Spacer(1, 12))

    # Network Tiers
    tiers = plan.get("network_tiers", [])
    if tiers:
        elements.append(Paragraph("Network Tiers", h2))
        tier_data = [["Tier", "Coinsurance", "Deductible", "OOP Max", "Description"]]
        for tr in tiers:
            tier_data.append([
                tr.get("name", tr.get("tier_id", "")),
                f"{tr.get('coinsurance', 20):.0f}%",
                f"${tr.get('deductible', 0):,.0f}",
                f"${tr.get('oop_max', 0):,.0f}",
                tr.get("description", "")[:40],
            ])
        tt = RLTable(tier_data, colWidths=[1.2 * inch, 1 * inch, 1 * inch, 1 * inch, 2.3 * inch])
        tt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5C2D91")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F5FF")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E2DF")),
            ("ALIGN", (1, 0), (3, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(tt)
        elements.append(Spacer(1, 12))

    # Risk Management
    risk = plan.get("risk_management")
    if risk and (risk.get("specific_attachment_point", 0) > 0 or risk.get("aggregate_attachment_point", 0) > 0):
        elements.append(Paragraph("Risk Management / Stop-Loss", h2))
        risk_data = [
            ["Parameter", "Value"],
            ["Specific Attachment Point", f"${risk.get('specific_attachment_point', 0):,.0f}"],
            ["Aggregate Attachment Point", f"${risk.get('aggregate_attachment_point', 0):,.0f}"],
            ["Auto-Flag Threshold", f"{risk.get('auto_flag_threshold_pct', 50):.0f}% of Specific"],
            ["Stop-Loss Carrier", risk.get("stop_loss_carrier", "N/A")],
            ["Contract Period", risk.get("contract_period", "12 months")],
        ]
        rt = RLTable(risk_data, colWidths=[3 * inch, 3.5 * inch])
        rt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C24A3B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBEAE7")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E2DF")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(rt)
        elements.append(Spacer(1, 12))

    # Exclusions
    excl = plan.get("exclusions", [])
    if excl:
        elements.append(Paragraph("Excluded Services", h2))
        elements.append(Paragraph(", ".join(excl[:50]), sub_style))
        elements.append(Spacer(1, 12))

    # Footer
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(f"Plan Version: {plan.get('version', 1)} | Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", note_style))
    elements.append(Paragraph("This Summary of Benefits and Coverage is generated by FletchFlow Claims Adjudication System.", note_style))

    doc.build(elements)
    buf.seek(0)
    filename = f"SBC_{plan.get('name', 'Plan').replace(' ', '_')}_{plan_id[:8]}.pdf"
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
