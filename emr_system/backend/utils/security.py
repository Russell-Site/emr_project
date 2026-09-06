# ============================================================
# utils/security.py - Security Utilities
# Lahat ng security-related functions ay nandito
# Password hashing, JWT tokens, OTP generation, at iba pa
# Gumagamit ng bcrypt library directly (hindi passlib)
# para maiwasan ang compatibility issue sa Python 3.14
# ============================================================

import os
import secrets
import hashlib
import bcrypt
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

# --- JWT Configuration ---
SECRET_KEY              = os.getenv("SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM           = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def hash_password(plain_password: str) -> str:
    """
    I-hash ang plain text password gamit ang bcrypt directly.
    Ginagamit ang bcrypt library (hindi passlib) para sa
    Python 3.14 compatibility.
    Hindi na mababasa ulit ang original password pagkatapos ng hashing.
    """
    # I-encode at i-truncate sa 72 bytes (bcrypt hard limit)
    password_bytes = plain_password.encode("utf-8")[:72]
    # Gumawa ng salt at i-hash
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    # I-return bilang string para sa database storage
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Suriin kung tama ang password ng user.
    Ikukumpara ang plain text sa hashed version.
    Returns True kung tama, False kung mali.
    """
    try:
        # I-truncate din para consistent sa hash_password
        password_bytes = plain_password.encode("utf-8")[:72]
        hashed_bytes   = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


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
    """
    return secrets.token_hex(64)


def sanitize_input(value: str) -> str:
    """
    Basic sanitization ng user input.
    Gumagamit palagi ng parameterized queries / ORM bilang pangunahing
    proteksyon laban sa SQL injection.
    """
    if not value:
        return value
    dangerous_chars = ["<", ">", "'", '"', ";", "--", "/*", "*/", "xp_"]
    sanitized = value
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")
    return sanitized.strip()


def validate_password_strength(password: str) -> tuple:
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