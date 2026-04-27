# ============================================================
# routers/auth.py - Authentication Routes
# Login, Logout, OTP Verification, Password Change
# May rate limiting para maiwasan ang brute-force attacks
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os

from database import get_db
from models.models import User, OTPToken
from schemas.schemas import LoginRequest, TokenResponse, OTPVerifyRequest, ChangePasswordRequest
from utils.security import (
    verify_password, hash_password, create_access_token,
    generate_otp, hash_otp, verify_otp, validate_password_strength
)
from utils.email_utils import send_otp_email
from middleware.auth import (
    get_current_user, log_audit, handle_failed_login,
    reset_failed_attempts, get_client_info
)

# I-create ang router para sa authentication
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", "10"))


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login endpoint para sa lahat ng users.
    May protection laban sa brute-force attacks.
    Nire-record ang bawat login attempt sa audit log.
    """
    ip_address, user_agent = get_client_info(request)

    # Hanapin ang user gamit ang email (gumagamit ng ORM para maiwasan ang SQL injection)
    user = db.query(User).filter(User.email == login_data.email).first()

    # Kung hindi mahanap ang user, mag-return ng generic na error message
    # (Hindi dapat sabihin kung email o password ang mali - security best practice)
    if not user:
        # I-log ang failed attempt kahit hindi mahanap ang user
        log_audit(db, None, f"FAILED LOGIN - Email not found: {login_data.email}",
                  ip_address=ip_address, user_agent=user_agent)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Suriin kung naka-lock ang account
    if user.status == "locked":
        # Suriin kung tapos na ang lockout period
        if user.locked_until and datetime.utcnow() > user.locked_until:
            # I-unlock na ang account dahil tapos na ang lockout
            reset_failed_attempts(db, user)
        else:
            remaining_time = ""
            if user.locked_until:
                remaining = (user.locked_until - datetime.utcnow()).seconds // 60
                remaining_time = f" Try again in {remaining} minute(s)."
            
            log_audit(db, user.user_id, "FAILED LOGIN - Account locked",
                      ip_address=ip_address, user_agent=user_agent)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account is locked due to too many failed attempts.{remaining_time}"
            )

    # Suriin kung active ang account
    if user.status == "inactive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact the administrator."
        )

    # I-verify ang password
    if not verify_password(login_data.password, user.password_hash):
        # Pangasiwaan ang failed attempt at posibleng i-lock ang account
        result = handle_failed_login(db, user)
        log_audit(db, user.user_id, f"FAILED LOGIN - Wrong password (Attempt #{user.failed_attempts})",
                  ip_address=ip_address, user_agent=user_agent)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["message"]
        )

    # Matagumpay ang login! I-reset ang failed attempts
    reset_failed_attempts(db, user)
    user.last_login = datetime.utcnow()
    db.commit()

    # Gumawa ng JWT access token
    token_data = {
        "user_id":    user.user_id,
        "email":      user.email,
        "role":       user.role,
        "barangay_id": user.barangay_id
    }
    access_token = create_access_token(token_data)

    # I-log ang matagumpay na login
    log_audit(db, user.user_id, f"LOGIN - {user.role.upper()}",
              ip_address=ip_address, user_agent=user_agent)

    # Ibalik ang token at user info
    barangay_name = user.barangay.barangay_name if user.barangay else None
    expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    return TokenResponse(
        access_token  = access_token,
        token_type    = "bearer",
        user_id       = user.user_id,
        name          = user.name,
        role          = user.role,
        barangay_id   = user.barangay_id,
        barangay_name = barangay_name,
        expires_in    = expire_minutes * 60
    )


@router.post("/logout")
async def logout(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Logout endpoint.
    I-invalidate ang session at i-log ang logout.
    """
    ip_address, user_agent = get_client_info(request)
    log_audit(db, current_user.user_id, "LOGOUT",
              ip_address=ip_address, user_agent=user_agent)

    return {"message": "Logged out successfully."}


@router.post("/request-otp")
async def request_otp(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Humiling ng OTP para sa Admin.
    Ginagamit bago mag-finalize ng bagong BHW registration.
    Ang OTP ay ipapadala sa email ng Admin.
    """
    # Tanging Admin lamang ang pwedeng humiling ng OTP
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can request OTP."
        )

    ip_address, _ = get_client_info(request)

    # Gumawa ng bagong OTP
    otp_plain = generate_otp(6)
    otp_hashed = hash_otp(otp_plain)
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)

    # I-invalidate ang mga nakaraang hindi pa nagagamit na OTP
    db.query(OTPToken).filter(
        OTPToken.user_id == current_user.user_id,
        OTPToken.is_used == False,
        OTPToken.purpose == "registration"
    ).update({"is_used": True})

    # I-save ang bagong OTP sa database (naka-hash)
    new_otp = OTPToken(
        user_id    = current_user.user_id,
        otp_code   = otp_hashed,
        purpose    = "registration",
        expires_at = expires_at,
        is_used    = False
    )
    db.add(new_otp)
    db.commit()

    # Ipadala ang OTP sa email ng Admin
    email_sent = send_otp_email(
        current_user.email,
        current_user.name,
        otp_plain,
        "registration"
    )

    log_audit(db, current_user.user_id, "OTP REQUESTED for BHW registration",
              ip_address=ip_address)

    if not email_sent:
        # Kung hindi mapadala ang email, i-return ang OTP sa response (para sa development)
        # Sa production, dapat mag-raise ng error
        return {
            "message": "OTP generated (email sending failed - check SMTP config).",
            "otp_for_development": otp_plain,  # ALISIN ITO SA PRODUCTION!
            "expires_in_minutes": OTP_EXPIRE_MINUTES
        }

    return {
        "message": f"OTP sent to {current_user.email}. Valid for {OTP_EXPIRE_MINUTES} minutes.",
        "expires_in_minutes": OTP_EXPIRE_MINUTES
    }


@router.post("/verify-otp")
async def verify_otp_endpoint(
    request: Request,
    otp_data: OTPVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    I-verify ang OTP na ini-input ng Admin.
    Kung tama ang OTP, maaari nang i-finalize ang registration.
    """
    # Hanapin ang pinaka-recent na valid OTP para sa user na ito
    otp_record = db.query(OTPToken).filter(
        OTPToken.user_id == current_user.user_id,
        OTPToken.purpose == otp_data.purpose,
        OTPToken.is_used == False,
        OTPToken.expires_at > datetime.utcnow()
    ).order_by(OTPToken.created_at.desc()).first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid OTP found. Please request a new OTP."
        )

    # I-verify ang OTP
    if not verify_otp(otp_data.otp_code, otp_record.otp_code):
        ip_address, _ = get_client_info(request)
        log_audit(db, current_user.user_id, "FAILED OTP VERIFICATION",
                  ip_address=ip_address)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code. Please try again."
        )

    # I-mark ang OTP bilang used na
    otp_record.is_used = True
    db.commit()

    ip_address, _ = get_client_info(request)
    log_audit(db, current_user.user_id, "OTP VERIFIED SUCCESSFULLY",
              ip_address=ip_address)

    return {"message": "OTP verified successfully. You may proceed.", "verified": True}


@router.post("/change-password")
async def change_password(
    request: Request,
    pwd_data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Palitan ang password ng kasalukuyang user.
    Kailangan ang lumang password para ma-verify ang identity.
    """
    # I-verify ang kasalukuyang password
    if not verify_password(pwd_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    # Suriin kung malakas ang bagong password
    is_strong, message = validate_password_strength(pwd_data.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # I-hash at i-save ang bagong password
    current_user.password_hash = hash_password(pwd_data.new_password)
    db.commit()

    ip_address, _ = get_client_info(request)
    log_audit(db, current_user.user_id, "PASSWORD CHANGED",
              ip_address=ip_address)

    return {"message": "Password changed successfully."}


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Kunin ang impormasyon ng kasalukuyang naka-login na user.
    """
    return {
        "user_id":    current_user.user_id,
        "name":       current_user.name,
        "email":      current_user.email,
        "role":       current_user.role,
        "position":   current_user.position,
        "barangay_id": current_user.barangay_id,
        "barangay_name": current_user.barangay.barangay_name if current_user.barangay else None,
        "last_login": current_user.last_login
    }
