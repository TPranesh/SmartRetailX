"""
user_service/security.py
JWT signing/verification and password hashing utilities.

Uses the `bcrypt` library directly (bypassing passlib) for Python 3.14 /
bcrypt 5.x compatibility.

Environment variables:
  JWT_SECRET_KEY  — HMAC-SHA256 signing secret (change in production!)
  JWT_ALGORITHM   — Default: HS256
  JWT_EXPIRE_MINS — Token lifetime in minutes (default: 60)
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

# ── Configuration (read from environment, with safe defaults) ─────────────────
SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "CHANGE_ME_super_secret_key_for_smartretailx_2025")
ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("JWT_EXPIRE_MINS", "60"))


# ── Password hashing (bcrypt 4.x / 5.x compatible) ────────────────────────────
def hash_password(plain_password: str) -> str:
    """
    Returns a bcrypt hash of the given plain-text password.
    Uses bcrypt directly (not passlib) for Python 3.14 + bcrypt 5.x compatibility.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against its bcrypt hash.
    Returns True if they match, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ── JWT helpers ────────────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    """
    Signs a JWT token containing 'data' as the payload.
    Automatically appends an 'exp' expiry claim.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decodes and validates a JWT token string.
    Raises JWTError if the token is expired or tampered.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
