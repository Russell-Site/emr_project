# ============================================================
# utils/security.py - Security Utilities
# Lahat ng security-related functions ay nandito
# Password hashing, JWT tokens, OTP generation, at iba pa
# ============================================================

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# --- Password Hashing Configuration ---
# Gumagamit ng bcrypt - ang pinaka-secure na password hashing algorithm
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

# --- JWT Configuration ---
SECRET_KEY              = os.getenv("SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM           = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def hash_password(plain_password: str) -> str:
    """
    I-hash ang plain text password gamit ang bcrypt.
    Hindi na mababasa ulit ang original password pagkatapos ng hashing.
    Laging gamitin ito bago i-save ang password sa database.
    Bcrypt ay may 72-byte limit kaya i-encode at i-truncate natin muna.
    """
    # I-encode bilang bytes at i-truncate sa 72 bytes (bcrypt limit)
    truncated = plain_password.encode("utf-8")[:72]
    return pwd_context.hash(truncated)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Suriin kung tama ang password ng user.
    Ikukumpara ang plain text sa hashed version.
    Returns True kung tama, False kung mali.
    Truncate din ang input sa 72 bytes para consistent sa hashing.
    """
    # I-truncate din para consistent sa hash_password function
    truncated = plain_password.encode("utf-8")[:72]
    return pwd_context.verify(truncated, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Gumawa ng JWT access token para sa authenticated na user.
    Ang token ay may expiration para mas secure.
    Kasama sa data: user_id, role, at barangay_id.
    """
    to_encode = data.copy()

    # Itakda ang expiration ng token
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MIN)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    # I-encode ang token gamit ang secret key
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    I-decode at i-verify ang JWT token.
    Returns ang payload kung valid, None kung hindi.
    Sinisigurado na hindi na-tamper ang token.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_otp(length: int = 6) -> str:
    """
    Gumawa ng random OTP (One-Time Password).
    Ginagamit ang secrets module para sa cryptographically secure random numbers.
    Default ay 6-digit numeric OTP.
    """
    # Gumamit ng secrets para sa mas secure na random number generation
    otp = "".join([str(secrets.randbelow(10)) for _ in range(length)])
    return otp


def hash_otp(otp_code: str) -> str:
    """
    I-hash ang OTP bago i-save sa database.
    Ginagamit ang SHA-256 para hindi ma-expose ang actual OTP
    kahit ma-access ang database.
    """
    return hashlib.sha256(otp_code.encode()).hexdigest()


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    """
    Suriin kung tama ang OTP na ini-input ng user.
    Ikukumpara ang SHA-256 hash ng plain OTP sa stored hash.
    """
    return hashlib.sha256(plain_otp.encode()).hexdigest() == hashed_otp


def generate_session_id() -> str:
    """
    Gumawa ng random session ID para sa user session.
    Ginagamit ang secrets.token_hex para sa cryptographically secure na ID.
    """
    return secrets.token_hex(64)  # 128-character hex string


def sanitize_input(value: str) -> str:
    """
    Basic sanitization ng user input.
    HINDI ito sapat para sa SQL injection prevention -
    gamitin palagi ang parameterized queries / ORM.
    Ito ay para sa additional layer ng protection lamang.
    """
    if not value:
        return value

    # Alisin ang mga dangerous characters
    dangerous_chars = ["<", ">", "'", '"', ";", "--", "/*", "*/", "xp_"]
    sanitized = value
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")

    return sanitized.strip()


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Suriin kung malakas ang password.
    Dapat may uppercase, lowercase, number, at special character.
    Minimum 8 characters ang haba.
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."

    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character."

    return True, "Password is strong."