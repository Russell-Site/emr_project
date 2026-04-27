# ============================================================
# models/models.py - SQLAlchemy Database Models
# Ito ang Python representation ng bawat table sa database
# Gumagamit ng ORM para maiwasan ang raw SQL at SQL injection
# ============================================================

from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime,
    Enum, ForeignKey, DECIMAL, SmallInteger, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


# --- Enum para sa User Role ---
class UserRole(str, enum.Enum):
    admin = "admin"
    bhw   = "bhw"


# --- Enum para sa User Status ---
class UserStatus(str, enum.Enum):
    active   = "active"
    inactive = "inactive"
    locked   = "locked"


# ============================================================
# BARANGAY MODEL
# ============================================================
class Barangay(Base):
    __tablename__ = "barangay"

    barangay_id   = Column(Integer, primary_key=True, index=True, autoincrement=True)
    barangay_name = Column(String(100), nullable=False, unique=True)
    district      = Column(String(50), nullable=False, default="District 1")
    created_at    = Column(DateTime, server_default=func.now())

    # Relationships - para ma-access ang related records
    patients      = relationship("Patient",      back_populates="barangay")
    users         = relationship("User",         back_populates="barangay")
    disease_cases = relationship("DiseaseCase",  back_populates="barangay")


# ============================================================
# USER MODEL
# ============================================================
class User(Base):
    __tablename__ = "users"

    user_id         = Column(Integer, primary_key=True, index=True, autoincrement=True)
    barangay_id     = Column(Integer, ForeignKey("barangay.barangay_id"), nullable=True)
    name            = Column(String(150), nullable=False)
    email           = Column(String(150), nullable=False, unique=True)
    password_hash   = Column(String(255), nullable=False)  # Naka-hash ang password
    role            = Column(Enum("admin", "bhw"), nullable=False, default="bhw")
    position        = Column(String(100), nullable=True)
    status          = Column(Enum("active", "inactive", "locked"), nullable=False, default="active")
    failed_attempts = Column(Integer, nullable=False, default=0)  # Para sa brute-force protection
    locked_until    = Column(DateTime, nullable=True)
    last_login      = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    barangay        = relationship("Barangay",       back_populates="users")
    audit_logs      = relationship("AuditLog",       back_populates="user")
    medical_records = relationship("MedicalRecord",  back_populates="encoder")
    immunizations   = relationship("Immunization",   back_populates="encoder")
    disease_cases   = relationship("DiseaseCase",    back_populates="encoder")
    otp_tokens      = relationship("OTPToken",       back_populates="user")
    sessions        = relationship("UserSession",    back_populates="user")


# ============================================================
# OTP TOKEN MODEL
# Para sa One-Time Password ng Admin
# ============================================================
class OTPToken(Base):
    __tablename__ = "otp_tokens"

    otp_id     = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    otp_code   = Column(String(10), nullable=False)   # Hashed OTP
    purpose    = Column(String(50), nullable=False, default="registration")
    expires_at = Column(DateTime, nullable=False)
    is_used    = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationship
    user = relationship("User", back_populates="otp_tokens")


# ============================================================
# PATIENT MODEL
# ============================================================
class Patient(Base):
    __tablename__ = "patient"

    patient_id     = Column(Integer, primary_key=True, index=True, autoincrement=True)
    barangay_id    = Column(Integer, ForeignKey("barangay.barangay_id"), nullable=False)
    first_name     = Column(String(100), nullable=False)
    last_name      = Column(String(100), nullable=False)
    middle_name    = Column(String(100), nullable=True)
    birthdate      = Column(Date, nullable=False)
    sex            = Column(Enum("Male", "Female"), nullable=False)
    civil_status   = Column(Enum("Single", "Married", "Widowed", "Separated"), nullable=True)
    address        = Column(Text, nullable=False)
    contact_number = Column(String(20), nullable=True)
    philhealth_no  = Column(String(30), nullable=True)
    is_archived    = Column(Boolean, nullable=False, default=False)
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    barangay        = relationship("Barangay",      back_populates="patients")
    medical_records = relationship("MedicalRecord", back_populates="patient", cascade="all, delete-orphan")
    immunizations   = relationship("Immunization",  back_populates="patient", cascade="all, delete-orphan")
    disease_cases   = relationship("DiseaseCase",   back_populates="patient")


# ============================================================
# MEDICAL RECORD MODEL
# ============================================================
class MedicalRecord(Base):
    __tablename__ = "medical_records"

    record_id       = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id      = Column(Integer, ForeignKey("patient.patient_id", ondelete="CASCADE"), nullable=False)
    visit_date      = Column(Date, nullable=False)
    chief_complaint = Column(String(500), nullable=True)
    symptoms        = Column(Text, nullable=True)
    diagnosis       = Column(Text, nullable=True)
    treatment       = Column(Text, nullable=True)
    blood_pressure  = Column(String(20), nullable=True)
    temperature     = Column(DECIMAL(4, 1), nullable=True)
    weight_kg       = Column(DECIMAL(5, 2), nullable=True)
    height_cm       = Column(DECIMAL(5, 2), nullable=True)
    notes           = Column(Text, nullable=True)
    user_id         = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="medical_records")
    encoder = relationship("User",    back_populates="medical_records")


# ============================================================
# IMMUNIZATION MODEL
# ============================================================
class Immunization(Base):
    __tablename__ = "immunization"

    immunization_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id      = Column(Integer, ForeignKey("patient.patient_id", ondelete="CASCADE"), nullable=False)
    vaccine_name    = Column(String(150), nullable=False)
    date_given      = Column(Date, nullable=False)
    dose_number     = Column(Integer, nullable=True, default=1)
    administered_by = Column(String(150), nullable=True)
    batch_number    = Column(String(50), nullable=True)
    next_schedule   = Column(Date, nullable=True)
    remarks         = Column(Text, nullable=True)
    user_id         = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    created_at      = Column(DateTime, server_default=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="immunizations")
    encoder = relationship("User",    back_populates="immunizations")


# ============================================================
# DISEASE MODEL
# ============================================================
class Disease(Base):
    __tablename__ = "disease"

    disease_id    = Column(Integer, primary_key=True, index=True, autoincrement=True)
    disease_name  = Column(String(200), nullable=False, unique=True)
    icd_code      = Column(String(20), nullable=True)
    category      = Column(String(100), nullable=True)
    is_notifiable = Column(Boolean, nullable=False, default=False)
    created_at    = Column(DateTime, server_default=func.now())

    # Relationship
    cases = relationship("DiseaseCase", back_populates="disease")


# ============================================================
# DISEASE CASES MODEL (Para sa Analytics)
# ============================================================
class DiseaseCase(Base):
    __tablename__ = "disease_cases"

    case_id         = Column(Integer, primary_key=True, index=True, autoincrement=True)
    disease_id      = Column(Integer, ForeignKey("disease.disease_id"), nullable=False)
    barangay_id     = Column(Integer, ForeignKey("barangay.barangay_id"), nullable=False)
    patient_id      = Column(Integer, ForeignKey("patient.patient_id", ondelete="SET NULL"), nullable=True)
    date_recorded   = Column(Date, nullable=False)
    number_of_cases = Column(Integer, nullable=False, default=1)
    age_group       = Column(String(20), nullable=True)
    sex             = Column(Enum("Male", "Female", "Both"), nullable=True)
    remarks         = Column(Text, nullable=True)
    user_id         = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    created_at      = Column(DateTime, server_default=func.now())

    # Relationships
    disease  = relationship("Disease",  back_populates="cases")
    barangay = relationship("Barangay", back_populates="disease_cases")
    patient  = relationship("Patient",  back_populates="disease_cases")
    encoder  = relationship("User",     back_populates="disease_cases")


# ============================================================
# AUDIT LOG MODEL
# Lahat ng aksyon ay nire-record dito
# ============================================================
class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id     = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    action     = Column(String(500), nullable=False)
    table_name = Column(String(50), nullable=True)
    record_id  = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    date_time  = Column(DateTime, server_default=func.now())

    # Relationship
    user = relationship("User", back_populates="audit_logs")


# ============================================================
# USER SESSION MODEL
# Para sa server-side session management
# ============================================================
class UserSession(Base):
    __tablename__ = "user_sessions"

    session_id = Column(String(128), primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    is_active  = Column(Boolean, nullable=False, default=True)

    # Relationship
    user = relationship("User", back_populates="sessions")