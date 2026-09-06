# ============================================================
# routers/analytics.py — Disease Trend Analytics
# Single-barangay — no barangay FK or dropdown needed
# All data is from the current database instance
# ============================================================

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional
from datetime import datetime
import pandas as pd

from database import get_db, get_barangay_name
from models.models import DiseaseCase, Disease, Patient, MedicalRecord, Immunization, User
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

# Color palette for charts
COLORS = [
    '#0b1f4b','#1a6fad','#1a8a5e','#e74c3c','#f39c12',
    '#8e44ad','#1abc9c','#e67e22','#3498db','#2ecc71',
    '#e91e63','#ff5722','#607d8b','#795548','#00bcd4'
]


@router.get("/dashboard-summary")
async def dashboard_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Lahat ng summary numbers para sa dashboard.
    Isang API call lang — para sa stat cards.
    """
    now           = datetime.now()
    total_patients = db.query(Patient).filter(Patient.is_archived == False).count()
    total_records  = db.query(MedicalRecord).count()
    total_immun    = db.query(Immunization).count()
    total_female   = db.query(Patient).filter(
        Patient.is_archived == False, Patient.sex == "Female"
    ).count()

    # Cases this month
    cases_month = db.query(func.sum(DiseaseCase.number_of_cases)).filter(
        extract('month', DiseaseCase.date_recorded) == now.month,
        extract('year',  DiseaseCase.date_recorded) == now.year
    ).scalar() or 0

    # Top disease this month
    top = db.query(
        Disease.disease_name,
        func.sum(DiseaseCase.number_of_cases).label('total')
    ).join(DiseaseCase).filter(
        extract('month', DiseaseCase.date_recorded) == now.month,
        extract('year',  DiseaseCase.date_recorded) == now.year
    ).group_by(Disease.disease_name).order_by(
        func.sum(DiseaseCase.number_of_cases).desc()
    ).first()

    # BHW stats (admin only)
    total_bhw  = db.query(User).filter(User.role == "bhw").count()
    active_bhw = db.query(User).filter(User.role == "bhw", User.status == "active").count()

    return {
        "barangay_name":         get_barangay_name(),
        "total_patients":        total_patients,
        "total_medical_records": total_records,
        "total_immunizations":   total_immun,
        "total_female_patients": total_female,
        "cases_this_month":      int(cases_month),
        "top_disease_this_month":top.disease_name if top else "N/A",
        "total_bhw":             total_bhw,
        "active_bhw":            active_bhw,
        "current_month":         now.strftime("%B %Y")
    }


@router.get("/disease-trends")
async def disease_trends(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    year: Optional[int] = Query(None)
):
    """
    Monthly disease trend data para sa Chart.js line chart.
    Ibinabalik ang isang dataset per disease, 12 months.
    Ang labels ay nakasulat na sa chart mismo (datalabels plugin).
    """
    target_year = year or datetime.now().year

    rows = db.query(
        DiseaseCase.date_recorded,
        DiseaseCase.number_of_cases,
        Disease.disease_name
    ).join(Disease).filter(
        extract('year', DiseaseCase.date_recorded) == target_year
    ).all()

    if not rows:
        return {"labels": [], "datasets": [], "year": target_year}

    df = pd.DataFrame(rows, columns=['date_recorded','number_of_cases','disease_name'])
    df['month'] = pd.to_datetime(df['date_recorded']).dt.month

    months   = ['Jan','Feb','Mar','Apr','May','Jun',
                'Jul','Aug','Sep','Oct','Nov','Dec']
    diseases = df['disease_name'].unique().tolist()

    datasets = []
    for idx, disease in enumerate(diseases):
        sub    = df[df['disease_name'] == disease]
        totals = []
        for m in range(1, 13):
            row = sub[sub['month'] == m]
            totals.append(int(row['number_of_cases'].sum()) if not row.empty else 0)

        color = COLORS[idx % len(COLORS)]
        datasets.append({
            "label":            disease,
            "data":             totals,
            "borderColor":      color,
            "backgroundColor":  color + "25",
            "tension":          0.4,
            "fill":             True,
            "pointRadius":      5,
            "pointHoverRadius": 7,
            "borderWidth":      2.5
        })

    return {"labels": months, "datasets": datasets, "year": target_year}


@router.get("/top-diseases")
async def top_diseases(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    year:  Optional[int] = Query(None),
    limit: int            = Query(8, ge=1, le=15)
):
    """
    Top N diseases by case count para sa doughnut chart.
    """
    target_year = year or datetime.now().year

    rows = db.query(
        Disease.disease_name,
        func.sum(DiseaseCase.number_of_cases).label('total')
    ).join(DiseaseCase).filter(
        extract('year', DiseaseCase.date_recorded) == target_year
    ).group_by(Disease.disease_name).order_by(
        func.sum(DiseaseCase.number_of_cases).desc()
    ).limit(limit).all()

    return {
        "labels":          [r.disease_name for r in rows],
        "data":            [int(r.total)   for r in rows],
        "backgroundColor": COLORS[:len(rows)]
    }


@router.get("/monthly-cases")
async def monthly_cases(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    year: Optional[int] = Query(None)
):
    """
    Total cases per month para sa bar chart.
    """
    target_year = year or datetime.now().year

    rows = db.query(
        extract('month', DiseaseCase.date_recorded).label('month'),
        func.sum(DiseaseCase.number_of_cases).label('total')
    ).filter(
        extract('year', DiseaseCase.date_recorded) == target_year
    ).group_by('month').order_by('month').all()

    months_short = ['Jan','Feb','Mar','Apr','May','Jun',
                    'Jul','Aug','Sep','Oct','Nov','Dec']
    totals = [0] * 12
    for r in rows:
        totals[int(r.month) - 1] = int(r.total)

    return {
        "labels":          months_short,
        "data":            totals,
        "backgroundColor": [COLORS[0]] * 12
    }


@router.get("/age-distribution")
async def age_distribution(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Distribusyon ng edad ng mga pasyente para sa bar chart."""
    rows = db.query(Patient.birthdate, Patient.sex).filter(
        Patient.is_archived == False
    ).all()

    if not rows:
        return {"labels": [], "male": [], "female": []}

    df    = pd.DataFrame(rows, columns=['birthdate','sex'])
    today = pd.Timestamp.now()
    df['age'] = (today - pd.to_datetime(df['birthdate'])).dt.days // 365

    bins   = [0, 4, 12, 17, 35, 59, 150]
    labels = ['0-4','5-12','13-17','18-35','36-59','60+']
    df['age_group'] = pd.cut(df['age'], bins=bins, labels=labels, right=True)

    male   = df[df['sex']=='Male'].groupby('age_group', observed=True).size()
    female = df[df['sex']=='Female'].groupby('age_group', observed=True).size()

    return {
        "labels": labels,
        "male":   [int(male.get(l, 0))   for l in labels],
        "female": [int(female.get(l, 0)) for l in labels]
    }


@router.get("/surveillance")
async def surveillance(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    year: Optional[int] = Query(None)
):
    """
    Disease surveillance table — case counts per disease.
    Para sa Surveillance section ng dashboard.
    """
    target_year = year or datetime.now().year

    rows = db.query(
        Disease.disease_name,
        Disease.category,
        func.sum(DiseaseCase.number_of_cases).label('total')
    ).join(DiseaseCase).filter(
        extract('year', DiseaseCase.date_recorded) == target_year
    ).group_by(Disease.disease_name, Disease.category).order_by(
        func.sum(DiseaseCase.number_of_cases).desc()
    ).all()

    grand_total = sum(r.total for r in rows) if rows else 0

    return {
        "year":        target_year,
        "grand_total": int(grand_total),
        "diseases": [
            {
                "disease_name": r.disease_name,
                "category":     r.category,
                "total":        int(r.total),
                "pct":          round(r.total / grand_total * 100, 1) if grand_total else 0
            }
            for r in rows
        ]
    }