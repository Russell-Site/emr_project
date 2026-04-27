# ============================================================
# routers/users.py - User Management Routes (Admin Only)
# CRUD operations para sa BHW accounts
# Tanging Admin lamang ang may access dito
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models.models import User, Barangay
from schemas.schemas import UserCreate, UserUpdate, UserResponse
from utils.security import hash_password, validate_password_strength
from utils.email_utils import send_account_created_email
from middleware.auth import (
    get_current_user, require_admin, log_audit, get_client_info
)

router = APIRouter(prefix="/api/users", tags=["User Management"])


@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),  # Admin only
    role: Optional[str] = None,
    status: Optional[str] = None,
    barangay_id: Optional[int] = None
):
    """
    Kunin ang listahan ng lahat ng users (Admin only).
    Maaaring i-filter ayon sa role, status, at barangay.
    """
    # Gumawa ng base query gamit ang ORM (walang raw SQL = walang SQL injection)
    query = db.query(User)

    # I-apply ang mga filters kung may naibigay
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    if barangay_id:
        query = query.filter(User.barangay_id == barangay_id)

    users = query.order_by(User.name).all()

    # I-format ang response para isama ang barangay name
    result = []
    for user in users:
        result.append(UserResponse(
            user_id       = user.user_id,
            barangay_id   = user.barangay_id,
            barangay_name = user.barangay.barangay_name if user.barangay else None,
            name          = user.name,
            email         = user.email,
            role          = user.role,
            position      = user.position,
            status        = user.status,
            last_login    = user.last_login,
            created_at    = user.created_at
        ))

    return result


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_bhw(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)  # Admin only
):
    """
    Mag-register ng bagong BHW account (Admin only).
    Bago gamitin ito, kailangan munang ma-verify ang OTP.
    
    NOTE: Sa production, dapat suriin muna kung verified ang OTP
    ng Admin bago pwedeng mag-register.
    """
    ip_address, _ = get_client_info(request)

    # Suriin kung mayroon nang account sa email na iyan
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered."
        )

    # Suriin kung valid ang barangay_id
    barangay = db.query(Barangay).filter(
        Barangay.barangay_id == user_data.barangay_id
    ).first()
    if not barangay:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid barangay ID."
        )

    # Suriin kung malakas ang password
    is_strong, message = validate_password_strength(user_data.password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # I-hash ang password bago i-save
    hashed_pwd = hash_password(user_data.password)

    # Gumawa ng bagong user record
    new_user = User(
        barangay_id   = user_data.barangay_id,
        name          = user_data.name.strip(),
        email         = str(user_data.email).lower(),
        password_hash = hashed_pwd,
        role          = user_data.role.value if hasattr(user_data.role, 'value') else user_data.role,
        position      = user_data.position,
        status        = "active"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Ipadala ang notification email sa bagong BHW (optional)
    send_account_created_email(new_user.email, new_user.name, user_data.password)

    # I-log ang paglikha ng bagong account
    log_audit(
        db, current_user.user_id,
        f"REGISTERED NEW BHW: {new_user.name} ({new_user.email}) - {barangay.barangay_name}",
        table_name="users", record_id=new_user.user_id,
        ip_address=ip_address
    )

    return UserResponse(
        user_id       = new_user.user_id,
        barangay_id   = new_user.barangay_id,
        barangay_name = barangay.barangay_name,
        name          = new_user.name,
        email         = new_user.email,
        role          = new_user.role,
        position      = new_user.position,
        status        = new_user.status,
        last_login    = new_user.last_login,
        created_at    = new_user.created_at
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Kunin ang impormasyon ng isang specific na user (Admin only).
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    return UserResponse(
        user_id       = user.user_id,
        barangay_id   = user.barangay_id,
        barangay_name = user.barangay.barangay_name if user.barangay else None,
        name          = user.name,
        email         = user.email,
        role          = user.role,
        position      = user.position,
        status        = user.status,
        last_login    = user.last_login,
        created_at    = user.created_at
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: Request,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    I-update ang impormasyon ng isang user (Admin only).
    Maaaring baguhin ang: pangalan, posisyon, status, at barangay.
    """
    ip_address, _ = get_client_info(request)

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Hindi pwedeng i-edit ang account ng Admin (sarili niya o iba pang Admin)
    if user.role == "admin" and current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify another admin's account."
        )

    # I-update ang mga fields na may bagong value
    if user_data.name is not None:
        user.name = user_data.name.strip()
    if user_data.position is not None:
        user.position = user_data.position
    if user_data.status is not None:
        user.status = user_data.status.value if hasattr(user_data.status, 'value') else user_data.status
        # Kung in-activate ulit ang account, i-reset ang failed attempts
        if user_data.status == "active":
            user.failed_attempts = 0
            user.locked_until = None
    if user_data.barangay_id is not None:
        # Suriin kung valid ang barangay
        barangay = db.query(Barangay).filter(
            Barangay.barangay_id == user_data.barangay_id
        ).first()
        if not barangay:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid barangay ID."
            )
        user.barangay_id = user_data.barangay_id

    db.commit()
    db.refresh(user)

    log_audit(
        db, current_user.user_id,
        f"UPDATED USER: {user.name} (ID: {user_id})",
        table_name="users", record_id=user_id,
        ip_address=ip_address
    )

    return UserResponse(
        user_id       = user.user_id,
        barangay_id   = user.barangay_id,
        barangay_name = user.barangay.barangay_name if user.barangay else None,
        name          = user.name,
        email         = user.email,
        role          = user.role,
        position      = user.position,
        status        = user.status,
        last_login    = user.last_login,
        created_at    = user.created_at
    )


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    I-deactivate ang isang BHW account (Admin only).
    Hindi namin actual na dine-delete ang account para sa audit trail.
    """
    ip_address, _ = get_client_info(request)

    # Hindi pwedeng i-deactivate ang sariling account
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account."
        )

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # I-set ang status sa inactive (soft delete)
    user.status = "inactive"
    db.commit()

    log_audit(
        db, current_user.user_id,
        f"DEACTIVATED USER: {user.name} (ID: {user_id})",
        table_name="users", record_id=user_id,
        ip_address=ip_address
    )

    return {"message": f"User {user.name} has been deactivated."}


@router.get("/stats/summary")
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Kunin ang summary statistics ng lahat ng users.
    Para sa Admin Dashboard.
    """
    # Bilang ng BHW ayon sa status
    total_bhw        = db.query(User).filter(User.role == "bhw").count()
    active_bhw       = db.query(User).filter(User.role == "bhw", User.status == "active").count()
    inactive_bhw     = db.query(User).filter(User.role == "bhw", User.status == "inactive").count()
    locked_accounts  = db.query(User).filter(User.status == "locked").count()

    return {
        "total_bhw":       total_bhw,
        "active_bhw":      active_bhw,
        "inactive_bhw":    inactive_bhw,
        "locked_accounts": locked_accounts
    }
