"""Account & API-key management endpoints (authenticated, NOT metered)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import ApiKey
from app.schemas import ApiKeyOut, UsageOut, UserOut
from app.services.security import generate_api_key, get_current_key

router = APIRouter(prefix="/api/v1/account", tags=["account"])


@router.get("/me", response_model=UserOut)
def me(api_key: ApiKey = Depends(get_current_key)) -> UserOut:
    return UserOut.model_validate(api_key.user)


@router.get("/key", response_model=ApiKeyOut)
def get_key(api_key: ApiKey = Depends(get_current_key)) -> ApiKeyOut:
    return ApiKeyOut.model_validate(api_key)


@router.post("/key/regenerate", response_model=ApiKeyOut)
def regenerate_key(
    api_key: ApiKey = Depends(get_current_key),
    db: Session = Depends(get_db),
) -> ApiKeyOut:
    """Rotate the secret in place. Usage counter is preserved for the period."""
    api_key.key = generate_api_key()
    db.commit()
    db.refresh(api_key)
    return ApiKeyOut.model_validate(api_key)


@router.get("/usage", response_model=UsageOut)
def usage(api_key: ApiKey = Depends(get_current_key)) -> UsageOut:
    user = api_key.user
    return UsageOut(
        requests_used=api_key.requests_used,
        monthly_limit=user.monthly_limit,
        remaining=max(user.monthly_limit - api_key.requests_used, 0),
        period_start=api_key.period_start,
        plan=user.plan,
    )
