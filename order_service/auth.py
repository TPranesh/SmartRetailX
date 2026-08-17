"""
order_service/auth.py
JWT validation FastAPI dependency shared across protected endpoints.

This module is intentionally self-contained: it re-implements token decoding
using the same SECRET_KEY env var as the User Service, so both services can
validate the same tokens without a shared library.

Phase 3 (AWS Cognito): Replace decode logic with Cognito JWKS URL validation
using python-jose's jwt.decode() with the Cognito public key set.
"""

import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

# ── Configuration (must match user_service/security.py) ───────────────────────
SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "smartretailx_secret_key_2025")
ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")

# This tells FastAPI where to get a token; used for Swagger UI "Authorize" button
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/login")


# ── Token payload schema ───────────────────────────────────────────────────────
class TokenData(BaseModel):
    user_id: int
    email: str
    role: str


# ── Dependency ─────────────────────────────────────────────────────────────────
def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    FastAPI dependency that validates the Bearer JWT and returns the decoded payload.
    Raises HTTP 401 if the token is missing, expired, or tampered with.

    Usage in a route:
        @app.post("/orders")
        def create_order(current_user: TokenData = Depends(get_current_user), ...):
            ...
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email: Optional[str] = payload.get("email")
        role: Optional[str] = payload.get("role")
        if user_id is None or email is None or role is None:
            raise credentials_exception
        return TokenData(user_id=int(user_id), email=email, role=role)
    except (JWTError, ValueError):
        raise credentials_exception


def require_role(required_role: str):
    """
    Factory that returns a FastAPI dependency enforcing a specific RBAC role.

    Usage:
        @app.delete("/users/{id}")
        def delete_user(current_user: TokenData = Depends(require_role("admin"))):
            ...
    """
    def role_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: '{required_role}', your role: '{current_user.role}'.",
            )
        return current_user
    return role_checker
