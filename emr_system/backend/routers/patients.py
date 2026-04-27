# ============================================================
# routers/patients.py - Patient Management Routes
# CRUD operations para sa patient records
# BHW: pwede lamang sa kanilang barangay
# Admin: full access sa lahat ng barangay
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, extract
from typing import List, Optional
from datetime import date, datetime

from database import get_db
from models.models import Patient, Barangay, User
from schemas.schemas import PatientCreate, PatientUpdate, PatientResponse
from middleware.auth import get_current_user, require_admin, log_audit, get_client_info

router = APIRouter(prefix="/api/patients", tags=["Patients"])


def calculate_age(birthdate: date) -> int:
    """
    Kalkulahin ang edad batay sa kaarawan.
    Ginagamit ito para sa patient records.
    """
    today = date.today()
    age = today.year - birthdate.year
    # I-adjust kung hindi pa kaarawan ngayong taon
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        age -= 1
    return age


@router.get("/", response_model=List[PatientResponse])
async def get_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    # Search parameters
    search:      Optional[str] = Query(None, description="Maghanap ayon sa pangalan"),
    barangay_id: Optional[int] = Query(None, description="I-filter ayon sa barangay"),
    sex:         Optional[str] = Query(None, description="I-filter ayon sa kasarian"),
    age_from:    Optional[int] = Query(None, ge=0, description="Minimum na edad"),
    age_to:      Optional[int] = Query(None, le=150, description="Maximum na edad"),
    date_from:   Optional[date] = Query(None, description="Petsa ng paglikha (simula)"),
    date_to:     Optional[date] = Query(None, description="Petsa ng paglikha (hanggang)"),
    # Pagination
    skip:  int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Kunin ang listahan ng mga pasyente.
    May search at filter functionality.
    BHW: makikita lamang ang pasyente ng kanilang barangay.
    Admin: makikita ang lahat ng pasyente.
    """
    # Base query - hindi kasama ang archived na records
    query = db.query(Patient).filter(Patient.is_archived == False)

    # Kung BHW ang naka-login, limitahan sa kanilang barangay
    if current_user.role == "bhw":
        query = query.filter(Patient.barangay_id == current_user.barangay_id)
    elif barangay_id:
        # Kung Admin at may filter na barangay
        query = query.filter(Patient.barangay_id == barangay_id)

    # I-apply ang search filter (case-insensitive)
    # Gumagamit ng ORM filter para maiwasan ang SQL injection
    if search:
        search_term = f"%{search.strip()}%"  # Wildcard para sa partial match
        query = query.filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.contact_number.ilike(search_term)
            )
        )

    # I-filter ayon sa kasarian
    if sex:
        query = query.filter(Patient.sex == sex)

    # I-filter ayon sa edad (kailangan kalkulahin mula sa birthdate)
    if age_from is not None or age_to is not None:
        today = date.today()
        if age_to is not None:
            # Minimum birthdate (pinaka-bata)
            min_birthdate = date(today.year - age_to - 1, today.month, today.day)
            query = query.filter(Patient.birthdate >= min_birthdate)
        if age_from is not None:
            # Maximum birthdate (pinakatanda)
            max_birthdate = date(today.year - age_from, today.month, today.day)
            query = query.filter(Patient.birthdate <= max_birthdate)

    # I-filter ayon sa petsa ng paglikha ng record
    if date_from:
        query = query.filter(Patient.created_at >= date_from)
    if date_to:
        query = query.filter(Patient.created_at <= date_to)

    # I-apply ang pagination at i-order ayon sa pangalan
    patients = query.order_by(Patient.last_name, Patient.first_name).offset(skip).limit(limit).all()

    # I-format ang response
    result = []
    for patient in patients:
        result.append(PatientResponse(
            patient_id     = patient.patient_id,
            barangay_id    = patient.barangay_id,
            barangay_name  = patient.barangay.barangay_name if patient.barangay else None,
            first_name     = patient.first_name,
            last_name      = patient.last_name,
            middle_name    = patient.middle_name,
            birthdate      = patient.birthdate,
            sex            = patient.sex,
            civil_status   = patient.civil_status,
            address        = patient.address,
            contact_number = patient.contact_number,
            philhealth_no  = patient.philhealth_no,
            age            = calculate_age(patient.birthdate),
            created_at     = patient.created_at
        ))

    return result


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    request: Request,
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mag-register ng bagong pasyente.
    BHW: pwede lamang sa kanilang assigned barangay.
    Admin: pwede sa lahat ng barangay.
    """
    ip_address, _ = get_client_info(request)

    # Suriin kung may access ang user sa barangay na ito
    if current_user.role == "bhw" and patient_data.barangay_id != current_user.barangay_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add patients to your assigned barangay."
        )

    # Suriin kung valid ang barangay
    barangay = db.query(Barangay).filter(
        Barangay.barangay_id == patient_data.barangay_id
    ).first()
    if not barangay:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid barangay ID."
        )

    # Gumawa ng bagong patient record
    new_patient = Patient(
        barangay_id    = patient_data.barangay_id,
        first_name     = patient_data.first_name.strip().title(),
        last_name      = patient_data.last_name.strip().title(),
        middle_name    = patient_data.middle_name.strip().title() if patient_data.middle_name else None,
        birthdate      = patient_data.birthdate,
        sex            = patient_data.sex.value if hasattr(patient_data.sex, 'value') else patient_data.sex,
        civil_status   = patient_data.civil_status,
        address        = patient_data.address.strip(),
        contact_number = patient_data.contact_number,
        philhealth_no  = patient_data.philhealth_no
    )

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    log_audit(
        db, current_user.user_id,
        f"ADDED PATIENT: {new_patient.last_name}, {new_patient.first_name} (ID: {new_patient.patient_id})",
        table_name="patient", record_id=new_patient.patient_id,
        ip_address=ip_address
    )

    return PatientResponse(
        patient_id     = new_patient.patient_id,
        barangay_id    = new_patient.barangay_id,
        barangay_name  = barangay.barangay_name,
        first_name     = new_patient.first_name,
        last_name      = new_patient.last_name,
        middle_name    = new_patient.middle_name,
        birthdate      = new_patient.birthdate,
        sex            = new_patient.sex,
        civil_status   = new_patient.civil_status,
        address        = new_patient.address,
        contact_number = new_patient.contact_number,
        philhealth_no  = new_patient.philhealth_no,
        age            = calculate_age(new_patient.birthdate),
        created_at     = new_patient.created_at
    )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Kunin ang detalye ng isang specific na pasyente.
    """
    patient = db.query(Patient).filter(
        Patient.patient_id == patient_id,
        Patient.is_archived == False
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found."
        )

    # Suriin kung may access ang BHW sa pasyenteng ito
    if current_user.role == "bhw" and patient.barangay_id != current_user.barangay_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This patient belongs to a different barangay."
        )

    return PatientResponse(
        patient_id     = patient.patient_id,
        barangay_id    = patient.barangay_id,
        barangay_name  = patient.barangay.barangay_name if patient.barangay else None,
        first_name     = patient.first_name,
        last_name      = patient.last_name,
        middle_name    = patient.middle_name,
        birthdate      = patient.birthdate,
        sex            = patient.sex,
        civil_status   = patient.civil_status,
        address        = patient.address,
        contact_number = patient.contact_number,
        philhealth_no  = patient.philhealth_no,
        age            = calculate_age(patient.birthdate),
        created_at     = patient.created_at
    )


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    request: Request,
    patient_data: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    I-update ang impormasyon ng isang pasyente.
    """
    ip_address, _ = get_client_info(request)

    patient = db.query(Patient).filter(
        Patient.patient_id == patient_id,
        Patient.is_archived == False
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    # I-check ang barangay access ng BHW
    if current_user.role == "bhw" and patient.barangay_id != current_user.barangay_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # I-update ang mga fields
    for field, value in patient_data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(patient, field, value)

    db.commit()
    db.refresh(patient)

    log_audit(db, current_user.user_id, f"UPDATED PATIENT ID: {patient_id}",
              table_name="patient", record_id=patient_id, ip_address=ip_address)

    return PatientResponse(
        patient_id     = patient.patient_id,
        barangay_id    = patient.barangay_id,
        barangay_name  = patient.barangay.barangay_name if patient.barangay else None,
        first_name     = patient.first_name,
        last_name      = patient.last_name,
        middle_name    = patient.middle_name,
        birthdate      = patient.birthdate,
        sex            = patient.sex,
        civil_status   = patient.civil_status,
        address        = patient.address,
        contact_number = patient.contact_number,
        philhealth_no  = patient.philhealth_no,
        age            = calculate_age(patient.birthdate),
        created_at     = patient.created_at
    )


@router.delete("/{patient_id}")
async def archive_patient(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)  # Admin only ang pwedeng mag-archive
):
    """
    I-archive ang patient record (soft delete - Admin only).
    Hindi namin actual na dine-delete para sa data integrity.
    """
    ip_address, _ = get_client_info(request)

    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    patient.is_archived = True
    db.commit()

    log_audit(db, current_user.user_id, f"ARCHIVED PATIENT: {patient.last_name}, {patient.first_name}",
              table_name="patient", record_id=patient_id, ip_address=ip_address)

    return {"message": "Patient record has been archived."}


@router.get("/stats/summary")
async def get_patient_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Kunin ang summary statistics ng mga pasyente.
    Para sa Dashboard summary cards.
    """
    # Base query depende sa role
    base_query = db.query(Patient).filter(Patient.is_archived == False)
    if current_user.role == "bhw":
        base_query = base_query.filter(Patient.barangay_id == current_user.barangay_id)

    total_patients = base_query.count()
    male_patients  = base_query.filter(Patient.sex == "Male").count()
    female_patients = base_query.filter(Patient.sex == "Female").count()

    return {
        "total_patients":   total_patients,
        "male_patients":    male_patients,
        "female_patients":  female_patients,
        "barangay_filter":  current_user.barangay_id if current_user.role == "bhw" else None
    }
