# ============================================================
# main.py - FastAPI Application Entry Point
# Dito naka-configure ang lahat ng middleware, routes, at security
# Ito ang pangunahing file na pinapatakbo ng server
# ============================================================

import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from dotenv import load_dotenv

# I-load ang environment variables
load_dotenv()

# I-import ang lahat ng routers
from routers.auth      import router as auth_router
from routers.users     import router as users_router
from routers.patients  import router as patients_router
from routers.analytics import router as analytics_router
from routers.reports   import router as reports_router

# I-import ang database at models
from database import engine, test_connection, Base

# ============================================================
# RATE LIMITER SETUP
# Para maiwasan ang brute-force attacks at DDoS
# ============================================================
# Gumagamit ng IP address para sa rate limiting
limiter = Limiter(key_func=get_remote_address)


# ============================================================
# ROUTERS PARA SA MEDICAL RECORDS AT IMMUNIZATION
# (Inline definition para sa brevity - sa production, ilipat sa sariling file)
# ============================================================
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.models import MedicalRecord, Immunization, Patient, DiseaseCase, Disease, Barangay
from schemas.schemas import MedicalRecordCreate, ImmunizationCreate, DiseaseCaseCreate
from middleware.auth import get_current_user, require_admin, log_audit, get_client_info
from typing import Optional, List

# Medical Records Router
medical_router = APIRouter(prefix="/api/medical-records", tags=["Medical Records"])

@medical_router.post("/")
async def create_medical_record(
    request: Request,
    record_data: MedicalRecordCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Mag-encode ng bagong medical record para sa pasyente."""
    ip_address, _ = get_client_info(request)

    # Suriin kung may access ang BHW sa pasyenteng ito
    patient = db.query(Patient).filter(Patient.patient_id == record_data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    if current_user.role == "bhw" and patient.barangay_id != current_user.barangay_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    new_record = MedicalRecord(
        patient_id      = record_data.patient_id,
        visit_date      = record_data.visit_date,
        chief_complaint = record_data.chief_complaint,
        symptoms        = record_data.symptoms,
        diagnosis       = record_data.diagnosis,
        treatment       = record_data.treatment,
        blood_pressure  = record_data.blood_pressure,
        temperature     = record_data.temperature,
        weight_kg       = record_data.weight_kg,
        height_cm       = record_data.height_cm,
        notes           = record_data.notes,
        user_id         = current_user.user_id
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    log_audit(db, current_user.user_id, f"ADDED MEDICAL RECORD for Patient ID: {record_data.patient_id}",
              "medical_records", new_record.record_id, ip_address)

    return {"message": "Medical record added.", "record_id": new_record.record_id}


@medical_router.get("/patient/{patient_id}")
async def get_patient_records(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Kunin ang lahat ng medical records ng isang pasyente."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    if current_user.role == "bhw" and patient.barangay_id != current_user.barangay_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    records = db.query(MedicalRecord).filter(
        MedicalRecord.patient_id == patient_id
    ).order_by(MedicalRecord.visit_date.desc()).all()

    return [
        {
            "record_id":       r.record_id,
            "visit_date":      r.visit_date,
            "chief_complaint": r.chief_complaint,
            "symptoms":        r.symptoms,
            "diagnosis":       r.diagnosis,
            "treatment":       r.treatment,
            "blood_pressure":  r.blood_pressure,
            "temperature":     float(r.temperature) if r.temperature else None,
            "weight_kg":       float(r.weight_kg) if r.weight_kg else None,
            "height_cm":       float(r.height_cm) if r.height_cm else None,
            "notes":           r.notes,
            "encoder":         r.encoder.name if r.encoder else None,
            "created_at":      r.created_at
        }
        for r in records
    ]


# Immunization Router
immun_router = APIRouter(prefix="/api/immunizations", tags=["Immunizations"])

@immun_router.post("/")
async def create_immunization(
    request: Request,
    immun_data: ImmunizationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Mag-record ng bagong immunization para sa pasyente."""
    ip_address, _ = get_client_info(request)

    patient = db.query(Patient).filter(Patient.patient_id == immun_data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    if current_user.role == "bhw" and patient.barangay_id != current_user.barangay_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    new_immun = Immunization(
        patient_id      = immun_data.patient_id,
        vaccine_name    = immun_data.vaccine_name,
        date_given      = immun_data.date_given,
        dose_number     = immun_data.dose_number,
        administered_by = immun_data.administered_by,
        batch_number    = immun_data.batch_number,
        next_schedule   = immun_data.next_schedule,
        remarks         = immun_data.remarks,
        user_id         = current_user.user_id
    )
    db.add(new_immun)
    db.commit()
    db.refresh(new_immun)

    log_audit(db, current_user.user_id, f"ADDED IMMUNIZATION for Patient ID: {immun_data.patient_id}",
              "immunization", new_immun.immunization_id, ip_address)

    return {"message": "Immunization record added.", "immunization_id": new_immun.immunization_id}


@immun_router.get("/patient/{patient_id}")
async def get_patient_immunizations(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Kunin ang lahat ng immunization records ng isang pasyente."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    if current_user.role == "bhw" and patient.barangay_id != current_user.barangay_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    immunizations = db.query(Immunization).filter(
        Immunization.patient_id == patient_id
    ).order_by(Immunization.date_given.desc()).all()

    return [
        {
            "immunization_id": i.immunization_id,
            "vaccine_name":    i.vaccine_name,
            "date_given":      i.date_given,
            "dose_number":     i.dose_number,
            "administered_by": i.administered_by,
            "batch_number":    i.batch_number,
            "next_schedule":   i.next_schedule,
            "remarks":         i.remarks
        }
        for i in immunizations
    ]


# Disease Cases Router
cases_router = APIRouter(prefix="/api/disease-cases", tags=["Disease Cases"])

@cases_router.post("/")
async def create_disease_case(
    request: Request,
    case_data: DiseaseCaseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Mag-record ng bagong disease case."""
    ip_address, _ = get_client_info(request)

    if current_user.role == "bhw" and case_data.barangay_id != current_user.barangay_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    new_case = DiseaseCase(
        disease_id      = case_data.disease_id,
        barangay_id     = case_data.barangay_id,
        patient_id      = case_data.patient_id,
        date_recorded   = case_data.date_recorded,
        number_of_cases = case_data.number_of_cases,
        age_group       = case_data.age_group,
        sex             = case_data.sex,
        remarks         = case_data.remarks,
        user_id         = current_user.user_id
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    log_audit(db, current_user.user_id, f"ADDED DISEASE CASE: Disease ID {case_data.disease_id}",
              "disease_cases", new_case.case_id, ip_address)

    return {"message": "Disease case recorded.", "case_id": new_case.case_id}


@cases_router.get("/diseases")
async def get_all_diseases(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Kunin ang master list ng lahat ng sakit."""
    diseases = db.query(Disease).order_by(Disease.disease_name).all()
    return [{"disease_id": d.disease_id, "disease_name": d.disease_name, 
             "icd_code": d.icd_code, "category": d.category} for d in diseases]


@cases_router.get("/barangays")
async def get_all_barangays(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Kunin ang listahan ng lahat ng barangay."""
    barangays = db.query(Barangay).order_by(Barangay.barangay_name).all()
    return [{"barangay_id": b.barangay_id, "barangay_name": b.barangay_name} for b in barangays]


# Audit Log Router
# Admin: nakikita lahat ng logs
# BHW: nakikita lang ang logs ng kanilang barangay
audit_router = APIRouter(prefix="/api/audit-logs", tags=["Audit Logs"])

@audit_router.get("/")
async def get_audit_logs(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """
    Kunin ang audit log.
    Admin: lahat ng LOGIN at LOGOUT events sa lahat ng barangay.
    BHW: LOGIN at LOGOUT events ng users sa kanilang barangay lamang.
    Limitado sa LOGIN at LOGOUT events para sa malinis na audit trail.
    """
    from models.models import AuditLog

    # Base query — tanging LOGIN at LOGOUT lang ang ipinakita
    query = db.query(AuditLog).filter(
        AuditLog.action.in_(["LOGIN - ADMIN", "LOGIN - BHW", "LOGOUT"])
    )

    if current_user.role == "admin":
        # Admin: makikita ang lahat ng logs
        pass
    else:
        # BHW: makikita lang ang logs ng users sa kanilang barangay
        if current_user.barangay_id:
            # Kunin ang lahat ng user_ids na nasa parehong barangay
            barangay_user_ids = [
                u.user_id for u in
                db.query(User).filter(User.barangay_id == current_user.barangay_id).all()
            ]
            query = query.filter(AuditLog.user_id.in_(barangay_user_ids))
        else:
            # Walang barangay assignment — walang makikitang logs
            return []

    logs = query.order_by(AuditLog.date_time.desc()).offset(skip).limit(limit).all()

    return [
        {
            "log_id":        l.log_id,
            "user_name":     l.user.name          if l.user else "Unknown",
            "user_role":     l.user.role          if l.user else "—",
            "barangay_name": l.user.barangay.barangay_name
                             if l.user and l.user.barangay else "—",
            "action":        l.action,
            "ip_address":    l.ip_address,
            "date_time":     l.date_time
        }
        for l in logs
    ]

@audit_router.get("/summary")
async def get_audit_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Summary ng login/logout activity.
    Kapaki-pakinabang para sa admin dashboard monitoring.
    """
    from models.models import AuditLog
    from sqlalchemy import func

    query = db.query(AuditLog).filter(
        AuditLog.action.in_(["LOGIN - ADMIN", "LOGIN - BHW", "LOGOUT"])
    )

    if current_user.role != "admin" and current_user.barangay_id:
        barangay_user_ids = [
            u.user_id for u in
            db.query(User).filter(User.barangay_id == current_user.barangay_id).all()
        ]
        query = query.filter(AuditLog.user_id.in_(barangay_user_ids))

    total_logins  = query.filter(AuditLog.action.like("LOGIN%")).count()
    total_logouts = query.filter(AuditLog.action == "LOGOUT").count()

    return {
        "total_logins":  total_logins,
        "total_logouts": total_logouts
    }


# ============================================================
# APPLICATION LIFESPAN (Startup & Shutdown events)
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Mga gagawin bago mag-start at pagkatapos mag-stop ang application.
    Sinusuri ang database connection sa startup.
    """
    # --- Startup ---
    print("🚀 Starting EMR System...")
    print("🔐 Security modules loaded.")

    # Subukan ang database connection
    if not test_connection():
        print("⚠️ Warning: Database connection failed! Check your .env configuration.")

    print("✅ EMR System is ready!")
    yield  # Dito nagtatakbo ang application

    # --- Shutdown ---
    print("🛑 Shutting down EMR System...")


# ============================================================
# FASTAPI APP INITIALIZATION
# ============================================================
app = FastAPI(
    title        = "District 1 Health EMR System",
    description  = "Electronic Medical Records System with Disease Trend Analytics",
    version      = "1.0.0",
    lifespan     = lifespan,
    # I-hide ang docs sa production para sa security
    docs_url     = "/api/docs" if os.getenv("DEBUG", "False").lower() == "true" else None,
    redoc_url    = None
)

# ============================================================
# MIDDLEWARE CONFIGURATION
# ============================================================

# 1. RATE LIMITING - Para maiwasan ang brute-force at DDoS attacks
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 2. CORS MIDDLEWARE - Kontrolin kung sino ang pwedeng mag-access ng API
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins     = allowed_origins,
    allow_credentials = True,
    allow_methods     = ["GET", "POST", "PUT", "DELETE"],  # I-limit ang allowed methods
    allow_headers     = ["Authorization", "Content-Type"],
    max_age           = 600  # Cache ang preflight requests ng 10 minuto
)

# 3. TRUSTED HOST MIDDLEWARE - Para maiwasan ang host header attacks
if os.getenv("DEBUG", "False").lower() != "true":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts = ["localhost", "127.0.0.1", "*.district1health.gov.ph"]
    )


# 4. SECURITY HEADERS MIDDLEWARE - Dagdag na security headers sa bawat response
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Magdagdag ng security headers sa bawat response.
    Nagpoprotekta laban sa XSS, clickjacking, at iba pang attacks.
    """
    response = await call_next(request)

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Enable XSS protection sa browser
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Strict transport security (HTTPS only)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Content security policy
    # Kasama na ang jsdelivr at cdnjs para sa Chart.js at ibang CDN libraries
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "worker-src 'self' blob:;"
    )
    # Remove server information para hindi malaman ng attacker ang tech stack
    response.headers["Server"] = "District1-EMR"

    return response


# 5. REQUEST LOGGING MIDDLEWARE - Para sa debugging at monitoring
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    I-log ang bawat HTTP request para sa monitoring.
    Ginagawa rin ito para ma-detect ang suspicious na activity.
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # I-log ang mabagal na requests (possible na attack o performance issue)
    if process_time > 5:  # 5 seconds threshold
        print(f"⚠️ Slow request: {request.method} {request.url.path} took {process_time:.2f}s")

    return response


# ============================================================
# INCLUDE ROUTERS
# ============================================================
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(patients_router)
app.include_router(analytics_router)
app.include_router(reports_router)
app.include_router(medical_router)
app.include_router(immun_router)
app.include_router(cases_router)
app.include_router(audit_router)


# ============================================================
# STATIC FILES AT FRONTEND SERVING
# I-serve ang HTML/CSS/JS files para sa frontend
# I-mount ang bawat subfolder ng frontend para ma-access
# ============================================================
import os

# I-compute ang absolute path ng frontend folder
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR  = os.path.join(BASE_DIR, "..", "frontend")
FRONTEND_DIR  = os.path.abspath(FRONTEND_DIR)

# I-mount ang CSS, JS, at Pages folders bilang static files
if os.path.exists(os.path.join(FRONTEND_DIR, "css")):
    app.mount("/frontend/css",   StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")),   name="css")

if os.path.exists(os.path.join(FRONTEND_DIR, "js")):
    app.mount("/frontend/js",    StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")),    name="js")

if os.path.exists(os.path.join(FRONTEND_DIR, "pages")):
    app.mount("/frontend/pages", StaticFiles(directory=os.path.join(FRONTEND_DIR, "pages")), name="pages")

if os.path.exists(os.path.join(FRONTEND_DIR, "assets")):
    app.mount("/frontend/assets",StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")),name="assets")


# ============================================================
# ROOT ENDPOINT - I-serve ang login page
# ============================================================
@app.get("/", include_in_schema=False)
async def serve_frontend():
    """I-serve ang login page bilang default na page."""
    login_page = os.path.join(FRONTEND_DIR, "pages", "login.html")
    if os.path.exists(login_page):
        return FileResponse(login_page)
    return {"message": "District 1 Health EMR System API", "status": "running"}


@app.get("/dashboard", include_in_schema=False)
async def serve_dashboard():
    """I-serve ang dashboard page."""
    dashboard_page = os.path.join(FRONTEND_DIR, "pages", "dashboard.html")
    if os.path.exists(dashboard_page):
        return FileResponse(dashboard_page)
    return {"message": "Dashboard not found."}


# Health check endpoint
@app.get("/api/health", tags=["System"])
@limiter.limit("30/minute")
async def health_check(request: Request):
    """Suriin kung gumagana ang API server."""
    return {"status": "ok", "system": "District 1 Health EMR", "version": "1.0.0"}


# ============================================================
# MAIN ENTRY POINT
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host    = os.getenv("APP_HOST", "0.0.0.0"),
        port    = int(os.getenv("APP_PORT", "8000")),
        reload  = os.getenv("DEBUG", "False").lower() == "true",
        workers = 1  # Para sa development; dagdagan sa production
    )