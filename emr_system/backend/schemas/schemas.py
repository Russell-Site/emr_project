# ============================================================
# schemas/schemas.py - Pydantic Schemas
# Para sa validation ng request at response data
# Ito ang nagpoprotekta sa sistema mula sa invalid na data
# ============================================================

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


# --- Enums ---
class UserRole(str, Enum):
    admin = "admin"
    bhw   = "bhw"

class UserStatus(str, Enum):
    active   = "active"
    inactive = "inactive"
    locked   = "locked"

class SexEnum(str, Enum):
    male   = "Male"
    female = "Female"


# ============================================================
# AUTH SCHEMAS
# ============================================================
class LoginRequest(BaseModel):
    """Schema para sa login request ng user."""
    email:    EmailStr = Field(..., description="Email address ng user")
    password: str      = Field(..., min_length=1, description="Password ng user")

    class Config:
        # Iwasan ang extra fields para ma-prevent ang mass assignment
        extra = "forbid"


class TokenResponse(BaseModel):
    """Schema para sa response pagkatapos ng matagumpay na login."""
    access_token:  str
    token_type:    str = "bearer"
    user_id:       int
    name:          str
    role:          str
    barangay_id:   Optional[int]
    barangay_name: Optional[str]
    expires_in:    int  # Seconds hanggang mag-expire ang token


class OTPVerifyRequest(BaseModel):
    """Schema para sa pag-verify ng OTP."""
    otp_code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$",
                          description="6-digit OTP code")
    purpose:  str = Field(default="registration")

    class Config:
        extra = "forbid"


# ============================================================
# USER SCHEMAS
# ============================================================
class UserCreate(BaseModel):
    """Schema para sa paglikha ng bagong BHW account (Admin only)."""
    barangay_id: int    = Field(..., gt=0)
    name:        str    = Field(..., min_length=2, max_length=150)
    email:       EmailStr
    password:    str    = Field(..., min_length=8)
    position:    Optional[str] = Field(None, max_length=100)
    role:        UserRole = Field(default=UserRole.bhw)

    @validator("name")
    def validate_name(cls, v):
        """Suriin kung may valid na characters ang pangalan."""
        if not all(c.isalpha() or c in " .-'" for c in v):
            raise ValueError("Name can only contain letters, spaces, hyphens, dots, and apostrophes.")
        return v.strip()

    class Config:
        extra = "forbid"


class UserUpdate(BaseModel):
    """Schema para sa pag-update ng user information."""
    name:        Optional[str]        = Field(None, min_length=2, max_length=150)
    position:    Optional[str]        = Field(None, max_length=100)
    status:      Optional[UserStatus] = None
    barangay_id: Optional[int]        = Field(None, gt=0)

    class Config:
        extra = "forbid"


class UserResponse(BaseModel):
    """Schema para sa response ng user data (walang password)."""
    user_id:       int
    barangay_id:   Optional[int]
    barangay_name: Optional[str]
    name:          str
    email:         str
    role:          str
    position:      Optional[str]
    status:        str
    last_login:    Optional[datetime]
    created_at:    datetime

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    """Schema para sa pagpapalit ng password."""
    current_password: str = Field(..., min_length=1)
    new_password:     str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        """Suriin kung magkaparehong ang dalawang passwords."""
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match.")
        return v

    class Config:
        extra = "forbid"


# ============================================================
# PATIENT SCHEMAS
# ============================================================
class PatientCreate(BaseModel):
    """Schema para sa paglikha ng bagong patient record."""
    barangay_id:    int     = Field(..., gt=0)
    first_name:     str     = Field(..., min_length=1, max_length=100)
    last_name:      str     = Field(..., min_length=1, max_length=100)
    middle_name:    Optional[str]  = Field(None, max_length=100)
    birthdate:      date
    sex:            SexEnum
    civil_status:   Optional[str]  = None
    address:        str     = Field(..., min_length=5)
    contact_number: Optional[str]  = Field(None, max_length=20)
    philhealth_no:  Optional[str]  = Field(None, max_length=30)

    occupation:       Optional[str]  = Field(None, max_length=150)
    mother_name:      Optional[str]  = Field(None, max_length=150)
    father_name:      Optional[str]  = Field(None, max_length=150)
    guardian_contact: Optional[str]  = Field(None, max_length=20)
    # Pregnancy fields
    is_pregnant:      Optional[bool] = False
    gravida:          Optional[int]  = Field(None, ge=0)
    para:             Optional[int]  = Field(None, ge=0)
    last_delivery_date: Optional[date] = None

    @validator("contact_number")
    def validate_contact(cls, v):
        """Basic validation ng contact number."""
        if v and not all(c.isdigit() or c in " +-" for c in v):
            raise ValueError("Contact number must contain only digits, spaces, plus, or hyphen.")
        return v

    class Config:
        extra = "forbid"


class PatientUpdate(BaseModel):
    """Schema para sa pag-update ng patient information."""
    barangay_id:    Optional[int]  = Field(None, gt=0)
    first_name:     Optional[str]  = Field(None, min_length=1, max_length=100)
    last_name:      Optional[str]  = Field(None, min_length=1, max_length=100)
    middle_name:    Optional[str]  = Field(None, max_length=100)
    birthdate:      Optional[date] = None
    sex:            Optional[SexEnum] = None
    civil_status:   Optional[str]  = None
    address:        Optional[str]  = Field(None, min_length=5)
    contact_number: Optional[str]  = Field(None, max_length=20)
    philhealth_no:  Optional[str]  = Field(None, max_length=30)

    class Config:
        extra = "forbid"


class PatientResponse(BaseModel):
    """Schema para sa response ng patient data."""
    patient_id:     int
    barangay_id:    int
    barangay_name:  Optional[str]
    first_name:     str
    last_name:      str
    middle_name:    Optional[str]
    birthdate:      date
    sex:            str
    civil_status:   Optional[str]
    address:        str
    contact_number: Optional[str]
    philhealth_no:  Optional[str]
    age:            Optional[int]  # Computed field
    created_at:     datetime

    class Config:
        from_attributes = True


# ============================================================
# MEDICAL RECORD SCHEMAS
# ============================================================
class MedicalRecordCreate(BaseModel):
    """Schema para sa paglikha ng bagong medical record."""
    patient_id:      int    = Field(..., gt=0)
    visit_date:      date
    chief_complaint: Optional[str]          = Field(None, max_length=500)
    symptoms:        Optional[str]          = None
    diagnosis:       Optional[str]          = None
    treatment:       Optional[str]          = None
    blood_pressure:  Optional[str]          = Field(None, max_length=20)
    temperature:     Optional[float]        = Field(None, ge=30.0, le=45.0)
    weight_kg:       Optional[float]        = Field(None, ge=0.5, le=500.0)
    height_cm:       Optional[float]        = Field(None, ge=30.0, le=300.0)
    heart_rate:       Optional[int]          = Field(None, ge=30, le=300)
    respiratory_rate: Optional[int]          = Field(None, ge=5,  le=80)
    lmp:              Optional[date]         = None   # Female patients only
    notes:            Optional[str]          = None

    class Config:
        extra = "forbid"


class MedicalRecordResponse(BaseModel):
    """Schema para sa response ng medical record data."""
    record_id:       int
    patient_id:      int
    patient_name:    Optional[str]
    visit_date:      date
    chief_complaint: Optional[str]
    symptoms:        Optional[str]
    diagnosis:       Optional[str]
    treatment:       Optional[str]
    blood_pressure:  Optional[str]
    temperature:     Optional[float]
    weight_kg:       Optional[float]
    height_cm:       Optional[float]
    notes:           Optional[str]
    encoder_name:    Optional[str]
    created_at:      datetime

    class Config:
        from_attributes = True


# ============================================================
# IMMUNIZATION SCHEMAS
# ============================================================
class ImmunizationCreate(BaseModel):
    """Schema para sa paglikha ng bagong immunization record."""
    patient_id:      int    = Field(..., gt=0)
    vaccine_name:    str    = Field(..., min_length=2, max_length=150)
    date_given:      date
    dose_number:     Optional[int]   = Field(None, ge=1, le=10)
    administered_by: Optional[str]   = Field(None, max_length=150)
    batch_number:    Optional[str]   = Field(None, max_length=50)
    next_schedule:   Optional[date]  = None
    remarks:         Optional[str]   = None

    class Config:
        extra = "forbid"


# ============================================================
# DISEASE CASE SCHEMAS
# ============================================================
class DiseaseCaseCreate(BaseModel):
    """Schema para sa paglikha ng bagong disease case record."""
    disease_id:      int   = Field(..., gt=0)
    barangay_id:     int   = Field(..., gt=0)
    patient_id:      Optional[int]  = Field(None, gt=0)
    date_recorded:   date
    number_of_cases: int   = Field(..., ge=1)
    age_group:       Optional[str]  = None
    sex:             Optional[str]  = None
    remarks:         Optional[str]  = None

    class Config:
        extra = "forbid"


# ============================================================
# ANALYTICS SCHEMAS
# ============================================================
class DiseaseTrendResponse(BaseModel):
    """Schema para sa disease trend analytics data."""
    disease_name:  str
    barangay_name: str
    month:         str
    year:          int
    total_cases:   int


class BarangayStatResponse(BaseModel):
    """Schema para sa per-barangay statistics."""
    barangay_name:  str
    total_patients: int
    total_cases:    int
    top_disease:    Optional[str]


# ============================================================
# REPORT SCHEMAS
# ============================================================
class ReportFilter(BaseModel):
    """Schema para sa filtering ng reports."""
    barangay_id:  Optional[int]  = None
    date_from:    Optional[date] = None
    date_to:      Optional[date] = None
    report_type:  str = Field(..., pattern=r"^(patient|disease|immunization)$")

    class Config:
        extra = "forbid"


# ============================================================
# AUDIT LOG SCHEMA
# ============================================================
class AuditLogResponse(BaseModel):
    """Schema para sa audit log response."""
    log_id:     int
    user_name:  Optional[str]
    action:     str
    table_name: Optional[str]
    ip_address: Optional[str]
    date_time:  datetime

    class Config:
        from_attributes = True


# ============================================================
# HEALTH PROBLEMS SCHEMAS — Item 6
# ============================================================
class HealthProblemUpsert(BaseModel):
    """Schema para sa pag-create o pag-update ng health problems."""
    allergies:        Optional[str] = None
    has_asthma:       bool          = False
    chronic_diseases: Optional[str] = None
    other_concerns:   Optional[str] = None

    class Config:
        extra = "forbid"


class HealthProblemResponse(BaseModel):
    problem_id:       int
    patient_id:       int
    allergies:        Optional[str]
    has_asthma:       bool
    chronic_diseases: Optional[str]
    other_concerns:   Optional[str]
    updated_at:       Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================
# ITR SCHEMAS — Item 4
# ============================================================
class ITRCreate(BaseModel):
    """Schema para sa paglikha ng bagong ITR record."""
    patient_id:       int            = Field(..., gt=0)
    date_of_visit:    date
    # Health snapshot
    allergies:        Optional[str]  = None
    has_asthma:       bool           = False
    chronic_diseases: Optional[str]  = None
    # Vitals
    weight_kg:        Optional[float] = Field(None, ge=0.5, le=500)
    height_cm:        Optional[float] = Field(None, ge=30,  le=300)
    blood_pressure:   Optional[str]  = Field(None, max_length=20)
    temperature:      Optional[float] = Field(None, ge=30.0, le=45.0)
    heart_rate:       Optional[int]  = Field(None, ge=30,   le=300)
    respiratory_rate: Optional[int]  = Field(None, ge=5,    le=80)
    lmp:              Optional[date] = None
    # Treatment
    chief_complaint:  Optional[str]  = Field(None, max_length=500)
    diagnosis:        Optional[str]  = None
    treatment:        Optional[str]  = None
    medication:       Optional[str]  = None
    follow_up_date:   Optional[date] = None
    remarks:          Optional[str]  = None

    class Config:
        extra = "forbid"


class ITRResponse(BaseModel):
    itr_id:           int
    patient_id:       int
    date_of_visit:    date
    allergies:        Optional[str]
    has_asthma:       bool
    chronic_diseases: Optional[str]
    weight_kg:        Optional[float]
    height_cm:        Optional[float]
    blood_pressure:   Optional[str]
    temperature:      Optional[float]
    heart_rate:       Optional[int]
    respiratory_rate: Optional[int]
    lmp:              Optional[date]
    chief_complaint:  Optional[str]
    diagnosis:        Optional[str]
    treatment:        Optional[str]
    medication:       Optional[str]
    follow_up_date:   Optional[date]
    remarks:          Optional[str]
    encoder_name:     Optional[str]
    created_at:       datetime

    class Config:
        from_attributes = True