"""
EOB/EOP Document Generator — Creates Explanation of Benefits (member-facing)
and Explanation of Payment (provider-facing) PDF documents using ReportLab.
"""
import io
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from core.database import db


async def generate_eob_pdf(claim_id: str) -> bytes:
    """Generate an Explanation of Benefits PDF for a claim."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise ValueError("Claim not found")

    member = await db.members.find_one({"member_id": claim["member_id"]}, {"_id": 0})
    plan = await db.plans.find_one({"id": member.get("plan_id")}, {"_id": 0}) if member else None
    group = await db.groups.find_one({"id": member.get("group_id")}, {"_id": 0}) if member else None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title2', parent=styles['Title'], fontSize=16, spaceAfter=6)
    subtitle = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=9, textColor=colors.grey)
    normal = styles['Normal']
    bold = ParagraphStyle('Bold', parent=normal, fontName='Helvetica-Bold', fontSize=9)

    elements = []
    elements.append(Paragraph("Explanation of Benefits (EOB)", title_style))
    elements.append(Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%m/%d/%Y')}", subtitle))
    elements.append(Spacer(1, 12))

    # Member & Claim Info
    info_data = [
        ["Member:", f"{member.get('first_name', '')} {member.get('last_name', '')}" if member else "N/A",
         "Claim #:", claim.get("claim_number", "")],
        ["Member ID:", claim.get("member_id", ""),
         "Service Date:", f"{claim.get('service_date_from', '')} — {claim.get('service_date_to', '')}"],
        ["Group:", group.get("name", "") if group else "N/A",
         "Provider:", claim.get("provider_name", "")],
        ["Plan:", plan.get("name", "") if plan else "N/A",
         "Status:", claim.get("status", "").upper()],
    ]
    info_table = Table(info_data, colWidths=[70, 180, 80, 180])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 16))

    # Service Lines
    elements.append(Paragraph("Service Details", bold))
    elements.append(Spacer(1, 6))

    sl_header = ["#", "CPT", "Description", "Billed", "Allowed", "Paid", "Your Resp."]
    sl_data = [sl_header]
    for sl in claim.get("service_lines", []):
        sl_data.append([
            str(sl.get("line_number", "")),
            sl.get("cpt_code", ""),
            sl.get("cpt_description", sl.get("cpt_code", ""))[:30],
            f"${sl.get('billed_amount', 0):,.2f}",
            f"${sl.get('allowed', 0):,.2f}",
            f"${sl.get('paid', 0):,.2f}",
            f"${sl.get('member_responsibility', 0):,.2f}",
        ])

    sl_table = Table(sl_data, colWidths=[25, 55, 140, 65, 65, 65, 65])
    sl_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A3636")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E2DF")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F4")]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(sl_table)
    elements.append(Spacer(1, 16))

    # Totals
    totals_data = [
        ["Total Billed:", f"${claim.get('total_billed', 0):,.2f}"],
        ["Total Allowed:", f"${claim.get('total_allowed', 0):,.2f}"],
        ["Plan Paid:", f"${claim.get('total_paid', 0):,.2f}"],
        ["Your Responsibility:", f"${claim.get('member_responsibility', 0):,.2f}"],
    ]
    tot_table = Table(totals_data, colWidths=[120, 100])
    tot_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(tot_table)
    elements.append(Spacer(1, 12))

    # Notes
    notes = claim.get("adjudication_notes", [])
    if notes:
        elements.append(Paragraph("Adjudication Notes", bold))
        for note in notes[:5]:
            elements.append(Paragraph(f"  {note}", ParagraphStyle('Note', parent=normal, fontSize=8)))
        elements.append(Spacer(1, 8))

    # Disclaimer
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        "This is not a bill. This is an explanation of how your claim was processed. "
        "If you have questions, contact your plan administrator.",
        ParagraphStyle('Disclaimer', parent=normal, fontSize=7, textColor=colors.grey)
    ))

    doc.build(elements)
    return buf.getvalue()


async def generate_eop_pdf(claim_id: str) -> bytes:
    """Generate an Explanation of Payment (provider-facing) PDF."""
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise ValueError("Claim not found")

    member = await db.members.find_one({"member_id": claim["member_id"]}, {"_id": 0})
    group = await db.groups.find_one({"id": member.get("group_id")}, {"_id": 0}) if member else None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title2', parent=styles['Title'], fontSize=16, spaceAfter=6)
    subtitle = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=9, textColor=colors.grey)
    normal = styles['Normal']
    bold = ParagraphStyle('Bold', parent=normal, fontName='Helvetica-Bold', fontSize=9)

    elements = []
    elements.append(Paragraph("Explanation of Payment (EOP)", title_style))
    elements.append(Paragraph(f"Payment Date: {datetime.now(timezone.utc).strftime('%m/%d/%Y')}", subtitle))
    elements.append(Spacer(1, 12))

    # Provider & Claim Info
    info_data = [
        ["Provider:", claim.get("provider_name", ""), "NPI:", claim.get("provider_npi", "")],
        ["Patient:", f"{member.get('first_name', '')} {member.get('last_name', '')}" if member else "N/A",
         "Claim #:", claim.get("claim_number", "")],
        ["Group:", group.get("name", "") if group else "N/A",
         "Service Date:", claim.get("service_date_from", "")],
    ]
    info_table = Table(info_data, colWidths=[70, 180, 80, 180])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 16))

    # Payment Details
    sl_header = ["CPT", "Billed", "Allowed", "Deductible", "Copay", "CoIns", "Paid"]
    sl_data = [sl_header]
    for sl in claim.get("service_lines", []):
        sl_data.append([
            sl.get("cpt_code", ""),
            f"${sl.get('billed_amount', 0):,.2f}",
            f"${sl.get('allowed', 0):,.2f}",
            f"${sl.get('deductible_applied', 0):,.2f}",
            f"${sl.get('copay', 0):,.2f}",
            f"${sl.get('coinsurance_amount', 0):,.2f}",
            f"${sl.get('paid', 0):,.2f}",
        ])

    sl_table = Table(sl_data, colWidths=[55, 65, 65, 65, 55, 55, 65])
    sl_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A3636")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E2DF")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F4")]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(sl_table)
    elements.append(Spacer(1, 16))

    totals = [
        ["Total Billed:", f"${claim.get('total_billed', 0):,.2f}"],
        ["Allowed Amount:", f"${claim.get('total_allowed', 0):,.2f}"],
        ["Provider Payment:", f"${claim.get('total_paid', 0):,.2f}"],
        ["Patient Responsibility:", f"${claim.get('member_responsibility', 0):,.2f}"],
    ]
    tot = Table(totals, colWidths=[140, 100])
    tot.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
    ]))
    elements.append(tot)

    doc.build(elements)
    return buf.getvalue()
