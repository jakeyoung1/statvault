"""Pydantic request/response schemas."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    plan: str
    monthly_limit: int


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    label: str
    active: bool
    requests_used: int
    period_start: dt.date


class UsageOut(BaseModel):
    requests_used: int
    monthly_limit: int
    remaining: int
    period_start: dt.date
    plan: str


class LoginResponse(BaseModel):
    user: UserOut
    api_key: str


class PitchingMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    player_id: str
    player_name: str
    season: int
    team_id: str | None
    lg_id: str | None
    w: int | None
    l: int | None
    sv: int | None
    innings_pitched: float | None
    so: int | None
    bb: int | None
    hr: int | None
    era: float | None
    fip: float | None


class MetricsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PitchingMetricOut]


# ---- NFL ----
class NflPassingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    player_id: str
    player_name: str | None
    season: int
    team: str | None
    games: int | None
    completions: int | None
    attempts: int | None
    passing_yards: float | None
    passing_tds: int | None
    interceptions: int | None
    sacks: float | None
    sack_yards: float | None
    yards_per_attempt: float | None
    any_a: float | None


class NflPassingResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[NflPassingOut]


# ---- NBA ----
class NbaScoringOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    player_id: str
    player_name: str | None
    team: str | None
    position: str | None
    season: str
    games_played: int | None
    pts: float | None
    ppg: float | None
    fga: float | None
    fta: float | None
    ts_pct: float | None


class NbaScoringResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[NbaScoringOut]
