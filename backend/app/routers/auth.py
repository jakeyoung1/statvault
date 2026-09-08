"""Developer-portal login. Returns the user's primary API key as the session."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import ApiKey, User
from app.schemas import LoginRequest, LoginResponse, UserOut
from app.services.security import verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    api_key = db.scalar(
        select(ApiKey).where(ApiKey.user_id == user.id, ApiKey.active.is_(True))
    )
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active API key on this account.",
        )
    return LoginResponse(user=UserOut.model_validate(user), api_key=api_key.key)
