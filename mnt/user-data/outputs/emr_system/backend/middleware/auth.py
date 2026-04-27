# ============================================================
# middleware/auth.py - Authentication Middleware
# Para sa pag-verify ng JWT tokens at user permissions
# Ginagamit bilang dependency sa bawat protected na route
# ============================================================

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os

from database import get_db
from models.models import User, AuditLog, UserSession
from utils.security import decode_access_token

# HTTP Bearer token scheme para sa JWT
security = HTTPBearer()

# Ilang beses pwedeng mag-fail bago ma-lock ang account
MAX_FAILED_ATTEMPTS = int(os.getenv("MAX_FAILED_ATTEMPTS", "5"))
LOCKOUT_DURATION_MIN = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Kunin ang kasalukuyang naka-login na user mula sa JWT token.
    Ito ang ginagamit na dependency sa lahat ng protected na routes.
    I-raise ang 401 error kung hindi valid ang token.
    """
    # I-decode ang JWT token
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please login again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Kunin ang user_id mula sa token payload
    user_id: int = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Hanapin ang user sa database
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Suriin kung active pa ang account
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive or locked. Please contact the administrator."
        )

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    I-require na Admin ang kasalukuyang user.
    Ginagamit sa mga route na para sa Admin lamang.
    I-raise ang 403 error kung hindi Admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    return current_user


def require_bhw_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    I-require na BHW o Admin ang kasalukuyang user.
    Puwedeng gamitin sa mga route na accessible ng dalawa.
    """
    if current_user.role not in ["admin", "bhw"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    return current_user


def check_barangay_access(
    barangay_id: int,
    current_user: User = Depends(get_current_user)
) -> bool:
    """
    Suriin kung may access ang BHW sa specific na barangay.
    Ang Admin ay may access sa lahat ng barangay.
    Ang BHW ay puwede lamang mag-access ng kanilang assigned na barangay.
    """
    # Admin ay may full access
    if current_user.role == "admin":
        return True

    # BHW ay puwede lamang sa kanilang barangay
    if current_user.barangay_id == barangay_id:
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You can only access records from your assigned barangay."
    )


def log_audit(
    db: Session,
    user_id: int | None,
    action: str,
    table_name: str | None = None,
    record_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None
):
    """
    I-record ang lahat ng aksyon sa audit log.
    Tinatawag ito sa bawat importante na operasyon sa sistema.
    
    Parameters:
        db: Database session
        user_id: ID ng user na gumanap ng aksyon
        action: Deskripsyon ng aksyon (e.g., "LOGIN", "EDIT PATIENT")
        table_name: Kung aling table ang na-affect
        record_id: ID ng na-affect na record
        ip_address: IP address ng user
        user_agent: Browser information
    """
    try:
        log_entry = AuditLog(
            user_id    = user_id,
            action     = action,
            table_name = table_name,
            record_id  = record_id,
            ip_address = ip_address,
            user_agent = user_agent[:500] if user_agent else None  # Limitahan ang haba
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        print(f"⚠️ Audit log failed: {e}")
        db.rollback()


def handle_failed_login(db: Session, user: User) -> dict:
    """
    Pangasiwaan ang failed login attempt.
    Dagdagan ang failed_attempts counter.
    I-lock ang account kung naabot na ang maximum na attempts.
    Returns ang status message.
    """
    user.failed_attempts += 1

    # Kung naabot na ang maximum na attempts, i-lock ang account
    if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
        user.status       = "locked"
        user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MIN)
        db.commit()
        return {
            "locked": True,
            "message": f"Account locked for {LOCKOUT_DURATION_MIN} minutes due to too many failed attempts."
        }

    db.commit()
    remaining = MAX_FAILED_ATTEMPTS - user.failed_attempts
    return {
        "locked": False,
        "message": f"Invalid password. {remaining} attempt(s) remaining before lockout."
    }


def reset_failed_attempts(db: Session, user: User):
    """
    I-reset ang failed login attempts pagkatapos ng matagumpay na login.
    Ginagamit rin ito pagkatapos ma-unlock ng Admin ang account.
    """
    user.failed_attempts = 0
    user.locked_until    = None
    if user.status == "locked":
        user.status = "active"
    db.commit()


def get_client_info(request: Request) -> tuple[str, str]:
    """
    Kunin ang IP address at User-Agent ng client.
    Para sa audit logging at security monitoring.
    """
    # Kunin ang real IP (kahit nasa proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else "Unknown"

    user_agent = request.headers.get("User-Agent", "Unknown")
    return ip_address, user_agent
