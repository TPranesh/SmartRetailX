"""
user_service/main.py
FastAPI application for the User Service.
Runs on: http://localhost:8001
Swagger UI: http://localhost:8001/docs

Phase 2:
  - Startup seeds default admin + customer accounts (if table is empty).
  - /login issues a signed HS256 JWT with {sub, email, role, exp} claims.
  - /users POST hashes passwords with bcrypt before persisting.
"""

import logging

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from user_service.database import engine, get_db, Base, SessionLocal
from user_service.models import User
from user_service.schemas import UserCreate, UserUpdate, UserResponse, LoginRequest, LoginResponse
from user_service.security import hash_password, verify_password, create_access_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("user_service")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SmartRetailX — User Service",
    description=(
        "Manages user accounts, authentication, and profiles. "
        "POST /login returns a signed JWT (HS256). "
        "Use the Swagger Authorize button (🔒) to test protected endpoints on other services."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Seed Data ─────────────────────────────────────────────────────────────────

SEED_USERS = [
    {
        "full_name": "Admin User",
        "email": "admin@smartretailx.com",
        "password": "AdminPass123!",
        "role": "admin",
        "company": "SmartRetailX HQ",
    },
    {
        "full_name": "Jane Smith",
        "email": "customer@smartretailx.com",
        "password": "CustomerPass123!",
        "role": "customer",
        "company": "Acme Corp",
    },
]


def seed_users(db: Session) -> None:
    """Inserts default users on first startup if the table is empty."""
    if db.query(User).count() == 0:
        for rec in SEED_USERS:
            plain_pw = rec.pop("password")
            user = User(**rec, hashed_password=hash_password(plain_pw))
            db.add(user)
        db.commit()
        logger.info("Seeded %d default user accounts.", len(SEED_USERS))
    else:
        logger.info("Users table already populated — skipping seed.")


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_tasks():
    db = SessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"], summary="Service health check")
@app.get("/users/health", tags=["Health"], summary="Service health check (routed)")
def health_check():
    """Returns service liveness status."""
    return {"status": "healthy", "service": "user-service", "port": 8001, "phase": 2}


# ── Authentication ────────────────────────────────────────────────────────────

@app.post(
    "/login",
    response_model=LoginResponse,
    tags=["Authentication"],
    summary="User login — returns a signed JWT",
)
@app.post(
    "/users/login",
    response_model=LoginResponse,
    tags=["Authentication"],
    summary="User login — routed alternative",
)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Validates email and bcrypt password, then issues a signed JWT access token.

    The token payload contains:
    - `sub` (str): user ID
    - `email` (str): user's email
    - `role` (str): 'customer' or 'admin'
    - `exp` (int): Unix timestamp expiry

    **Use the returned `access_token` as a Bearer token on protected endpoints.**
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
    })

    logger.info("User #%d (%s) logged in. Role: %s", user.id, user.email, user.role)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        role=user.role,
    )


# ── User CRUD ─────────────────────────────────────────────────────────────────

@app.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
    summary="Register a new user",
)
@app.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@app.post("/users/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    """
    Creates a new user account.
    Password is bcrypt-hashed before storage — the plain text is never persisted.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists.")

    data = payload.model_dump()
    plain_password = data.pop("password")
    new_user = User(**data, hashed_password=hash_password(plain_password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info("New user registered: #%d (%s) role=%s", new_user.id, new_user.email, new_user.role)
    return new_user


@app.get(
    "/users",
    response_model=List[UserResponse],
    tags=["Users"],
    summary="List all users",
)
@app.get("", response_model=List[UserResponse], include_in_schema=False)
@app.get("/users/users", response_model=List[UserResponse], include_in_schema=False)
def list_users(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Returns a paginated list of all registered users."""
    return db.query(User).offset(skip).limit(limit).all()


@app.get(
    "/users/{user_id}",
    response_model=UserResponse,
    tags=["Users"],
    summary="Get a user by ID",
)
@app.get("/{user_id}", response_model=UserResponse, include_in_schema=False)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")
    return user


@app.put(
    "/users/{user_id}",
    response_model=UserResponse,
    tags=["Users"],
    summary="Update user details",
)
@app.put("/{user_id}", response_model=UserResponse, include_in_schema=False)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    """Partially updates a user's profile (full_name, company, role)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@app.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Users"],
    summary="Delete a user",
)
@app.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Permanently deletes a user account."""
    if user_id == 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Primary Admin account cannot be deleted.",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")
    if user.id == 1 or user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Primary Admin account cannot be deleted.",
        )
    db.delete(user)
    db.commit()

