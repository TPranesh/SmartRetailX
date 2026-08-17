"""
user_service/schemas.py
Pydantic v2 schemas for request validation and response serialisation.
Phase 2: LoginResponse now returns a real JWT access_token.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# ── Request Schemas ──────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150, examples=["Jane Smith"])
    email: EmailStr = Field(..., examples=["jane@acme.com"])
    password: str = Field(..., min_length=6, examples=["secret123"])
    role: Optional[str] = Field(default="customer", examples=["customer", "admin"])
    company: Optional[str] = Field(default=None, examples=["Acme Corp"])


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=150)
    company: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=None)


class LoginRequest(BaseModel):
    """Standard email+password login. Returns a signed JWT on success."""
    email: EmailStr = Field(..., examples=["jane@acme.com"])
    password: str = Field(..., examples=["secret123"])


# ── Response Schemas ─────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    company: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """
    Phase 2: Full JWT response. access_token is a signed HS256 JWT containing
    {sub: user_id, email: email, role: role, exp: expiry_timestamp}.
    Compatible with the OAuth2 Bearer flow.
    """
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    role: str
