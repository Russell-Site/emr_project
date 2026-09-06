# ============================================================
# routers/reports.py - PDF Report Generation Routes
# Gumagamit ng ReportLab para gumawa ng professional na PDF reports
# Admin only ang pwedeng mag-generate at mag-download ng reports
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional
from datetime import date, datetime
import io
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from database import get_db
from models.models import Patient, MedicalRecord, Immunization, DiseaseCase, Disease
from middleware.auth import require_admin, get_current_user

router = APIRouter(prefix="/api/reports", tags=["Reports"])

# ============================================================
# HELPER FUNCTIONS PARA SA PDF STYLING
# ============================================================

# Kulay na gagamitin sa PDF
PRIMARY_COLOR   = colors.HexColor('#0a4f76')
SECONDARY_COLOR = colors.HexColor('#1a8a5e')
ACCENT_COLOR    = colors.HexColor('#e8f4f8')
LIGHT_GREEN     = colors.HexColor('#e8f8f0')
TEXT_DARK       = colors.HexColor('#1a1a2e')
GRAY_LIGHT      = colors.HexColor('#f8f9fa')


def create_pdf_header(elements: list, title: str, subtitle: str, date_range: str = ""):
    """
    Gumawa ng consistent na header para sa lahat ng PDF reports.
    Kasama ang logo area, titulo, at petsa ng report.
    """
    styles = getSampleStyleSheet()

    # Title style
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        fontSize=18,
        fontName='Helvetica-Bold',
        textColor=PRIMARY_COLOR,
        spaceAfter=4,
        alignment=TA_CENTER
    )

    subtitle_style = ParagraphStyle(
        'ReportSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica',
        textColor=SECONDARY_COLOR,
        spaceAfter=4,
        alignment=TA_CENTER
    )

    info_style = ParagraphStyle(
        'ReportInfo',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        textColor=colors.gray,
        alignment=TA_CENTER
    )

    # Header content
    elements.append(Paragraph("🏥 District 1 Health Office", subtitle_style))
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(subtitle, subtitle_style))

    if date_range:
        elements.append(Paragraph(date_range, info_style))

    elements.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        info_style
    ))
    elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY_COLOR))
    elements.append(Spacer(1, 0.2 * inch))


def create_summary_table(data: list, style_color=PRIMARY_COLOR) -> Table:
    """
    Gumawa ng styled na table para sa mga report.
    Ang unang row ay treated bilang header.
    """
    if not data:
        return None

    table = Table(data, repeatRows=1)

    # Number of columns
    num_cols = len(data[0])
    header_bg = style_color
    alt_row_bg = ACCENT_COLOR

    style = TableStyle([
        # Header row styling
        ('BACKGROUND',    (0, 0), (-1, 0),  header_bg),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0),  9),
        ('ALIGN',         (0, 0), (-1, 0),  'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, 0),  8),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  8),

        # Data rows styling
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 1), (-1, -1), 8),
        ('TOPPADDING',    (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('ALIGN',         (0, 1), (-1, -1), 'LEFT'),

        # Alternating row colors para mas madaling basahin
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, alt_row_bg]),

        # Borders
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('LINEBELOW',     (0, 0), (-1, 0),  1, header_bg),
    ])

    table.setStyle(style)
    return table


# ============================================================
# PATIENT RECORDS REPORT
# ============================================================
@router.get("/patients")
async def generate_patient_report(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin),  # Admin only
    date_from:    Optional[date] = Query(None),
    date_to:      Optional[date] = Query(None)
):
    """
    Gumawa ng PDF report ng patient records.
    Admin only. May options para sa filter ng barangay at petsa.
    """
    # Kuhanin ang patient data
    from database import get_barangay_name
    barangay_name = get_barangay_name()

    query = db.query(Patient).filter(Patient.is_archived == False)

    if date_from:
        query = query.filter(Patient.created_at >= date_from)
    if date_to:
        query = query.filter(Patient.created_at <= date_to)

    results = query.order_by(Patient.last_name).all()

    if not results:
        raise HTTPException(status_code=404, detail="No patient records found.")

    # Gumawa ng PDF sa memory (walang file na ginagawa sa disk)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1 * cm
    )

    elements = []
    styles = getSampleStyleSheet()

    # Header
    subtitle = barangay_name
    date_range = ""
    if date_from or date_to:
        date_range = f"Period: {date_from or 'Start'} to {date_to or 'Present'}"

    create_pdf_header(elements, "Patient Records Report", subtitle, date_range)

    # Summary statistics
    total = len(results)
    male_count   = sum(1 for r, _ in results if r.sex == "Male")
    female_count = sum(1 for r, _ in results if r.sex == "Female")

    summary_data = [
        ['Total Patients', 'Male', 'Female'],
        [str(total), str(male_count), str(female_count)]
    ]
    summary_table = Table(summary_data, colWidths=[2 * inch, 2 * inch, 2 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND',    (0, 1), (-1, -1), LIGHT_GREEN),
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 1), (-1, -1), 14),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.gray),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Patient table
    headers = ['#', 'Last Name', 'First Name', 'Birthdate', 'Age', 'Sex', 'Contact #', 'PhilHealth', 'Address']
    table_data = [headers]

    for idx, patient in enumerate(results, 1):
        today = date.today()
        age   = today.year - patient.birthdate.year
        if (today.month, today.day) < (patient.birthdate.month, patient.birthdate.day):
            age -= 1

        table_data.append([
            str(idx),
            patient.last_name,
            patient.first_name,
            patient.birthdate.strftime("%m/%d/%Y"),
            str(age),
            patient.sex,
            patient.contact_number or "N/A",
            patient.philhealth_no  or "N/A",
            patient.address[:40] + "..." if len(patient.address) > 40 else patient.address
        ])

    col_widths = [0.4*inch, 1.3*inch, 1.3*inch, 1*inch, 0.5*inch, 0.6*inch, 1.2*inch, 1.1*inch, 3*inch]
    patient_table = create_summary_table(table_data)
    if patient_table:
        patient_table._argW = col_widths
        elements.append(patient_table)

    # I-build ang PDF
    doc.build(elements)
    buffer.seek(0)

    # I-log ang report generation")

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=patient_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        }
    )


# ============================================================
# DISEASE TREND REPORT
# ============================================================
@router.get("/disease-trends")
async def generate_disease_report(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin),
    year:        Optional[int]  = Query(None),
    barangay_id: Optional[int]  = Query(None)
):
    """
    Gumawa ng PDF report ng disease trends per barangay.
    Kasama ang monthly breakdown at per-barangay comparison.
    """
    target_year = year or datetime.now().year

    # Kuhanin ang disease case data
    query = db.query(
        Disease.disease_name,
        Barangay.barangay_name,
        DiseaseCase.date_recorded,
        func.sum(DiseaseCase.number_of_cases).label('total_cases')
    ).join(
        Disease,  DiseaseCase.disease_id == Disease.disease_id
    ).filter(
        extract('year', DiseaseCase.date_recorded) == target_year
    )

    if barangay_id:
        query = query.filter(DiseaseCase.barangay_id == barangay_id)

    results = query.group_by(
        Disease.disease_name, Barangay.barangay_name, DiseaseCase.date_recorded
    ).order_by(func.sum(DiseaseCase.number_of_cases).desc()).all()

    if not results:
        raise HTTPException(status_code=404, detail="No disease data found.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1 * cm
    )

    elements = []

    from database import get_barangay_name
    create_pdf_header(
        elements,
        f"Disease Trend Report - {target_year}",
        get_barangay_name(),
        f"As of {datetime.now().strftime('%B %d, %Y')}"
    )

    # Gamitin ang Pandas para sa aggregation
    df = pd.DataFrame(results, columns=['disease_name', 'date_recorded', 'total_cases'])
    df['month'] = pd.to_datetime(df['date_recorded']).dt.strftime('%B')

    # Summary per disease
    disease_summary = df.groupby('disease_name')['total_cases'].sum().reset_index()
    disease_summary = disease_summary.sort_values('total_cases', ascending=False)

    styles = getSampleStyleSheet()
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=SECONDARY_COLOR,
        spaceBefore=10,
        spaceAfter=5
    )

    elements.append(Paragraph("Summary by Disease", section_style))

    disease_headers = ['Disease Name', 'Total Cases', '% of Total']
    total_all = int(disease_summary['total_cases'].sum())
    disease_data = [disease_headers]

    for _, row in disease_summary.iterrows():
        percentage = (row['total_cases'] / total_all * 100) if total_all > 0 else 0
        disease_data.append([
            row['disease_name'],
            str(int(row['total_cases'])),
            f"{percentage:.1f}%"
        ])

    disease_data.append(['TOTAL', str(total_all), '100%'])  # Grand total row

    disease_table = Table(disease_data, colWidths=[4*inch, 2*inch, 2*inch])
    disease_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  PRIMARY_COLOR),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0),  9),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME',      (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE',      (0, 1), (-1, -2), 9),
        ('ROWBACKGROUNDS',(0, 1), (-1, -2), [colors.white, ACCENT_COLOR]),
        ('BACKGROUND',    (0, -1),(-1, -1), SECONDARY_COLOR),
        ('TEXTCOLOR',     (0, -1),(-1, -1), colors.white),
        ('FONTNAME',      (0, -1),(-1, -1), 'Helvetica-Bold'),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.gray),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(disease_table)

    # I-build ang PDF
    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=disease_trend_{target_year}_{datetime.now().strftime('%Y%m%d')}.pdf"
        }
    )


# ============================================================
# IMMUNIZATION REPORT
# ============================================================
@router.get("/immunization")
async def generate_immunization_report(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None)
):
    """
    Gumawa ng PDF report ng immunization records.
    V2: Walang barangay join — single-barangay database.
    """
    from database import get_barangay_name

    query = db.query(
        Immunization,
        Patient.first_name,
        Patient.last_name,
        Patient.sex
    ).join(
        Patient, Immunization.patient_id == Patient.patient_id
    )

    if date_from:
        query = query.filter(Immunization.date_given >= date_from)
    if date_to:
        query = query.filter(Immunization.date_given <= date_to)

    results = query.order_by(Immunization.date_given.desc()).all()

    if not results:
        raise HTTPException(status_code=404, detail="No immunization records found.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1 * cm
    )

    elements = []
    barangay_name = get_barangay_name()

    create_pdf_header(elements, "Immunization Records Report", barangay_name)

    # Immunization table — walang Barangay column (single-barangay na)
    headers = ['#', 'Patient Name', 'Sex', 'Vaccine', 'Dose #', 'Date Given', 'Next Schedule', 'Administered By']
    table_data = [headers]

    for idx, row in enumerate(results, 1):
        immun = row.Immunization
        table_data.append([
            str(idx),
            f"{row.last_name}, {row.first_name}",
            row.sex,
            immun.vaccine_name,
            str(immun.dose_number or 1),
            immun.date_given.strftime("%m/%d/%Y"),
            immun.next_schedule.strftime("%m/%d/%Y") if immun.next_schedule else "N/A",
            immun.administered_by or "N/A"
        ])

    col_widths = [0.3*inch, 2.2*inch, 0.6*inch, 1.8*inch, 0.6*inch, 1*inch, 1.1*inch, 1.8*inch]
    immun_table = create_summary_table(table_data)
    if immun_table:
        immun_table._argW = col_widths
        elements.append(immun_table)

    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=immunization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        }
    )