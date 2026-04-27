# ============================================================
# routers/analytics.py - Disease Trend Analytics Routes
# Gumagamit ng Pandas para sa data processing at aggregation
# Para sa Chart.js visualization sa frontend
# ============================================================

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List, Optional
from datetime import date, datetime
import pandas as pd

from database import get_db
from models.models import DiseaseCase, Disease, Barangay, Patient, MedicalRecord, Immunization, User
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/disease-trends")
async def get_disease_trends(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    year:        Optional[int]  = Query(None, description="Taon ng datos (default: kasalukuyang taon)"),
    barangay_id: Optional[int]  = Query(None, description="Filter sa specific na barangay"),
    disease_id:  Optional[int]  = Query(None, description="Filter sa specific na sakit")
):
    """
    Kunin ang disease trend data para sa Chart.js.
    Ibinabalik ang monthly na bilang ng kaso bawat sakit at barangay.
    Ginagamit ang Pandas para sa data manipulation.
    """
    # Default sa kasalukuyang taon kung walang naibigay
    target_year = year or datetime.now().year

    # Kuhanin ang data mula sa database gamit ang ORM
    query = db.query(
        DiseaseCase.date_recorded,
        DiseaseCase.number_of_cases,
        DiseaseCase.barangay_id,
        Disease.disease_name,
        Barangay.barangay_name
    ).join(
        Disease, DiseaseCase.disease_id == Disease.disease_id
    ).join(
        Barangay, DiseaseCase.barangay_id == Barangay.barangay_id
    ).filter(
        extract('year', DiseaseCase.date_recorded) == target_year
    )

    # I-apply ang mga optional na filters
    if current_user.role == "bhw":
        # BHW: makikita lamang ang kanilang barangay
        query = query.filter(DiseaseCase.barangay_id == current_user.barangay_id)
    elif barangay_id:
        query = query.filter(DiseaseCase.barangay_id == barangay_id)

    if disease_id:
        query = query.filter(DiseaseCase.disease_id == disease_id)

    # I-execute ang query at i-convert sa list of dicts
    results = query.all()

    if not results:
        return {
            "labels": [],
            "datasets": [],
            "message": "No data available for the selected filters."
        }

    # Gamitin ang Pandas para sa data processing
    df = pd.DataFrame(results, columns=[
        'date_recorded', 'number_of_cases', 'barangay_id', 'disease_name', 'barangay_name'
    ])

    # Dagdagan ng month column
    df['month'] = pd.to_datetime(df['date_recorded']).dt.month
    df['month_name'] = pd.to_datetime(df['date_recorded']).dt.strftime('%B')

    # Gawing buwan-buwan na aggregation
    monthly_data = df.groupby(['month', 'month_name', 'disease_name'])['number_of_cases'].sum().reset_index()
    monthly_data = monthly_data.sort_values('month')

    # I-format para sa Chart.js
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']

    diseases = monthly_data['disease_name'].unique().tolist()

    # Color palette para sa mga chart lines
    colors = [
        '#0a4f76', '#1a8a5e', '#e74c3c', '#f39c12', '#9b59b6',
        '#1abc9c', '#e67e22', '#3498db', '#2ecc71', '#e91e63',
        '#ff5722', '#607d8b'
    ]

    datasets = []
    for idx, disease in enumerate(diseases):
        disease_data = monthly_data[monthly_data['disease_name'] == disease]
        monthly_cases = []

        for month_num in range(1, 13):
            month_row = disease_data[disease_data['month'] == month_num]
            cases = int(month_row['number_of_cases'].sum()) if not month_row.empty else 0
            monthly_cases.append(cases)

        color = colors[idx % len(colors)]
        datasets.append({
            "label": disease,
            "data": monthly_cases,
            "borderColor": color,
            "backgroundColor": f"{color}20",  # 20 = 12% opacity sa hex
            "tension": 0.4,
            "fill": True,
            "pointRadius": 4,
            "pointHoverRadius": 6
        })

    return {
        "labels": months,
        "datasets": datasets,
        "year": target_year
    }


@router.get("/disease-per-barangay")
async def get_disease_per_barangay(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    year:       Optional[int] = Query(None),
    disease_id: Optional[int] = Query(None)
):
    """
    Kunin ang bilang ng kaso bawat barangay.
    Para sa bar chart na nagpapakita ng comparison ng mga barangay.
    """
    target_year = year or datetime.now().year

    # Query para sa per-barangay disease cases
    query = db.query(
        Barangay.barangay_name,
        func.sum(DiseaseCase.number_of_cases).label('total_cases')
    ).join(
        DiseaseCase, Barangay.barangay_id == DiseaseCase.barangay_id
    ).filter(
        extract('year', DiseaseCase.date_recorded) == target_year
    )

    if disease_id:
        query = query.filter(DiseaseCase.disease_id == disease_id)

    if current_user.role == "bhw":
        query = query.filter(DiseaseCase.barangay_id == current_user.barangay_id)

    results = query.group_by(Barangay.barangay_name).order_by(
        func.sum(DiseaseCase.number_of_cases).desc()
    ).all()

    return {
        "labels": [r.barangay_name for r in results],
        "data": [int(r.total_cases) for r in results],
        "backgroundColor": [
            '#0a4f76', '#1a8a5e', '#e74c3c', '#f39c12', '#9b59b6',
            '#1abc9c', '#e67e22', '#3498db', '#2ecc71', '#e91e63',
            '#ff5722', '#607d8b', '#795548', '#00bcd4', '#8bc34a'
        ][:len(results)]
    }


@router.get("/top-diseases")
async def get_top_diseases(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    year:        Optional[int] = Query(None),
    barangay_id: Optional[int] = Query(None),
    limit:       int           = Query(5, ge=1, le=15)
):
    """
    Kunin ang top N na pinaka-maraming kaso na sakit.
    Para sa pie/doughnut chart.
    """
    target_year = year or datetime.now().year

    query = db.query(
        Disease.disease_name,
        func.sum(DiseaseCase.number_of_cases).label('total_cases')
    ).join(
        DiseaseCase, Disease.disease_id == DiseaseCase.disease_id
    ).filter(
        extract('year', DiseaseCase.date_recorded) == target_year
    )

    if current_user.role == "bhw":
        query = query.filter(DiseaseCase.barangay_id == current_user.barangay_id)
    elif barangay_id:
        query = query.filter(DiseaseCase.barangay_id == barangay_id)

    results = query.group_by(Disease.disease_name).order_by(
        func.sum(DiseaseCase.number_of_cases).desc()
    ).limit(limit).all()

    colors = [
        '#0a4f76', '#1a8a5e', '#e74c3c', '#f39c12', '#9b59b6',
        '#1abc9c', '#e67e22', '#3498db', '#2ecc71', '#e91e63',
        '#ff5722', '#607d8b', '#795548', '#00bcd4', '#8bc34a'
    ]

    return {
        "labels": [r.disease_name for r in results],
        "data": [int(r.total_cases) for r in results],
        "backgroundColor": colors[:len(results)]
    }


@router.get("/age-distribution")
async def get_age_distribution(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    barangay_id: Optional[int] = Query(None)
):
    """
    Kunin ang distribusyon ng edad ng mga pasyente.
    Para sa bar chart na nagpapakita ng age groups.
    """
    # Kuhanin ang lahat ng birthdate
    query = db.query(Patient.birthdate, Patient.sex).filter(Patient.is_archived == False)

    if current_user.role == "bhw":
        query = query.filter(Patient.barangay_id == current_user.barangay_id)
    elif barangay_id:
        query = query.filter(Patient.barangay_id == barangay_id)

    results = query.all()

    if not results:
        return {"labels": [], "male": [], "female": []}

    # Gamitin ang Pandas para sa age group computation
    df = pd.DataFrame(results, columns=['birthdate', 'sex'])
    today = pd.Timestamp.now()
    df['age'] = (today - pd.to_datetime(df['birthdate'])).dt.days // 365

    # Gumawa ng age group bins
    bins   = [0, 5, 12, 17, 35, 59, 150]
    labels = ['0-4 yrs', '5-12 yrs', '13-17 yrs', '18-35 yrs', '36-59 yrs', '60+ yrs']
    df['age_group'] = pd.cut(df['age'], bins=bins, labels=labels, right=True)

    # Separate counts para sa Male at Female
    male_counts   = df[df['sex'] == 'Male'].groupby('age_group', observed=True).size()
    female_counts = df[df['sex'] == 'Female'].groupby('age_group', observed=True).size()

    return {
        "labels":  labels,
        "male":    [int(male_counts.get(lbl, 0)) for lbl in labels],
        "female":  [int(female_counts.get(lbl, 0)) for lbl in labels]
    }


@router.get("/dashboard-summary")
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Kunin ang lahat ng summary numbers para sa Admin/BHW Dashboard.
    Isang API call lang para sa lahat ng dashboard stats.
    """
    # I-filter depende sa role ng user
    patient_query = db.query(Patient).filter(Patient.is_archived == False)
    record_query  = db.query(MedicalRecord)
    immun_query   = db.query(Immunization)
    case_query    = db.query(DiseaseCase)

    if current_user.role == "bhw":
        bid = current_user.barangay_id
        patient_query = patient_query.filter(Patient.barangay_id == bid)

        # Para sa medical records, kailangan i-join sa patient
        patient_ids = [p.patient_id for p in patient_query.all()]
        record_query = record_query.filter(MedicalRecord.patient_id.in_(patient_ids))
        immun_query  = immun_query.filter(Immunization.patient_id.in_(patient_ids))
        case_query   = case_query.filter(DiseaseCase.barangay_id == bid)

    # Kunin ang current month data
    current_month = datetime.now().month
    current_year  = datetime.now().year

    total_patients     = patient_query.count()
    total_records      = record_query.count()
    total_immunizations = immun_query.count()
    total_cases_this_month = case_query.filter(
        extract('month', DiseaseCase.date_recorded) == current_month,
        extract('year',  DiseaseCase.date_recorded) == current_year
    ).with_entities(func.sum(DiseaseCase.number_of_cases)).scalar() or 0

    # Kunin ang pinaka-maraming kaso na sakit ngayong buwan
    top_disease_query = db.query(
        Disease.disease_name,
        func.sum(DiseaseCase.number_of_cases).label('total')
    ).join(DiseaseCase).filter(
        extract('month', DiseaseCase.date_recorded) == current_month,
        extract('year',  DiseaseCase.date_recorded) == current_year
    )

    if current_user.role == "bhw":
        top_disease_query = top_disease_query.filter(
            DiseaseCase.barangay_id == current_user.barangay_id
        )

    top_disease = top_disease_query.group_by(Disease.disease_name).order_by(
        func.sum(DiseaseCase.number_of_cases).desc()
    ).first()

    return {
        "total_patients":          total_patients,
        "total_medical_records":   total_records,
        "total_immunizations":     total_immunizations,
        "cases_this_month":        int(total_cases_this_month),
        "top_disease_this_month":  top_disease.disease_name if top_disease else "N/A",
        "current_month":           datetime.now().strftime("%B %Y")
    }
