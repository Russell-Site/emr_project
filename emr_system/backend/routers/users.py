# ============================================================
# routers/users.py — User Management
# Admin can register BHW directly — NO OTP required
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.models import User
from middleware.auth import get_current_user, require_admin, get_client_info
from utils.security import hash_password, validate_password_strength

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/")
async def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    role:   Optional[str] = None,
    status: Optional[str] = None
):
    """Kunin ang listahan ng lahat ng health staff (Admin only). Hindi kasama ang sariling Admin account."""
    query = db.query(User).filter(User.user_id != current_user.user_id)
    if role:   query = query.filter(User.role   == role)
    if status: query = query.filter(User.status == status)
    users = query.order_by(User.name).all()
    return [_format_user(u) for u in users]


@router.post("/register", status_code=201)
async def register_bhw(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Mag-register ng bagong BHW account (Admin only).
    Walang OTP verification — direktang nire-register ng Admin.
    Roles: admin, bhw, midwife, doctor
    """
    body = await request.json()
    name     = body.get("name", "").strip()
    email    = body.get("email", "").strip().lower()
    password = body.get("password", "")
    position = body.get("position", "")
    role     = body.get("role", "bhw")

    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="Name, email, and password are required.")

    # Check duplicate email
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered.")

    # Validate password strength
    is_strong, msg = validate_password_strength(password)
    if not is_strong:
        raise HTTPException(status_code=400, detail=msg)

    new_user = User(
        name           = name,
        email          = email,
        password_hash  = hash_password(password),
        role           = role if role in ["admin", "bhw", "midwife", "doctor"] else "bhw",
        position       = position or None,
        status         = "active",
        is_first_login = True   # BHW must change password on first login
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return _format_user(new_user)


@router.get("/stats/summary")
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Summary statistics ng users para sa Admin Dashboard."""
    total_staff  = db.query(User).filter(User.role != "admin").count()
    active_staff = db.query(User).filter(User.role != "admin", User.status == "active").count()
    inactive     = db.query(User).filter(User.role != "admin", User.status == "inactive").count()
    locked       = db.query(User).filter(User.status == "locked").count()
    by_role      = {}
    for role in ["bhw", "midwife", "doctor"]:
        by_role[role] = db.query(User).filter(User.role == role).count()

    return {
        "total_bhw":       total_staff,   # kept for compatibility
        "active_bhw":      active_staff,
        "inactive_bhw":    inactive,
        "locked_accounts": locked,
        "total_staff":     total_staff,
        "active_staff":    active_staff,
        "by_role":         by_role
    }


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Kunin ang detalye ng isang user (Admin only)."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return _format_user(user)


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    I-update ang health staff account (Admin only).
    Pwedeng i-update ang: name, email, role, position, status.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    body = await request.json()

    if "name" in body and body["name"].strip():
        user.name = body["name"].strip()

    if "email" in body and body["email"].strip():
        new_email = body["email"].strip().lower()
        # Check if email is already taken by another user
        existing = db.query(User).filter(
            User.email == new_email,
            User.user_id != user_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email is already in use by another account.")
        user.email = new_email

    if "role" in body and body["role"] in ["admin", "bhw", "midwife", "doctor"]:
        user.role = body["role"]

    if "position" in body:
        user.position = body["position"].strip() or None

    if "status" in body and body["status"] in ["active", "inactive"]:
        user.status = body["status"]
        if body["status"] == "active":
            # Reset lockout when reactivating
            user.failed_attempts = 0
            user.locked_until    = None

    db.commit()
    db.refresh(user)
    return _format_user(user)


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """I-deactivate ang isang BHW account (soft delete)."""
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account.")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.status = "inactive"
    db.commit()
    return {"message": f"User {user.name} deactivated."}


def _format_user(user: User) -> dict:
    """Helper para i-format ang user response."""
    return {
        "user_id":        user.user_id,
        "name":           user.name,
        "email":          user.email,
        "role":           user.role,
        "position":       user.position,
        "status":         user.status,
        "is_first_login": getattr(user, 'is_first_login', True),
        "last_login":     str(user.last_login) if user.last_login else None,
        "created_at":     str(user.created_at)
    }