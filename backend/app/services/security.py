"""API key generation, validation, and monthly usage enforcement."""
from __future__ import annotations

import datetime as dt
import secrets

import bcrypt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import ApiKey, User

KEY_PREFIX = "sv_live_"


def generate_api_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(24)


def hash_password(raw: str) -> str:
    # bcrypt operates on at most 72 bytes; truncate longer secrets explicitly.
    return bcrypt.hashpw(raw.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def _roll_period_if_needed(api_key: ApiKey, db: Session) -> None:
    """Reset the usage counter at the start of a new calendar month."""
    today = dt.date.today()
    if api_key.period_start.year != today.year or api_key.period_start.month != today.month:
        api_key.requests_used = 0
        api_key.period_start = today.replace(day=1)
        db.commit()


def _lookup_key(raw_key: str | None, db: Session) -> ApiKey:
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Send it in the 'X-API-Key' header.",
        )
    api_key = db.scalar(select(ApiKey).where(ApiKey.key == raw_key))
    if api_key is None or not api_key.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )
    _roll_period_if_needed(api_key, db)
    return api_key


def get_current_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> ApiKey:
    """Authenticate a request by API key WITHOUT counting it against quota.

    Used for portal/management endpoints (view key, usage, regenerate).
    """
    return _lookup_key(x_api_key, db)


def require_quota(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> ApiKey:
    """Authenticate AND meter a premium data request (FIP, metrics, etc.)."""
    api_key = _lookup_key(x_api_key, db)
    user: User = api_key.user
    if api_key.requests_used >= user.monthly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Monthly request limit of {user.monthly_limit} reached for plan "
                f"'{user.plan}'. Upgrade or wait until next month."
            ),
        )
    api_key.requests_used += 1
    db.commit()
    return api_key
