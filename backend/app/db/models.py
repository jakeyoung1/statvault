"""SQLAlchemy ORM models: raw Lahman tables + StatVault app tables."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# --------------------------------------------------------------------------
# Raw Lahman tables
# --------------------------------------------------------------------------
class Person(Base):
    __tablename__ = "people"
    __table_args__ = {"schema": "mlb"}

    player_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name_first: Mapped[str | None] = mapped_column(String(64))
    name_last: Mapped[str | None] = mapped_column(String(64))
    name_given: Mapped[str | None] = mapped_column(String(128))
    bats: Mapped[str | None] = mapped_column(String(2))
    throws: Mapped[str | None] = mapped_column(String(2))
    birth_year: Mapped[int | None] = mapped_column(Integer)
    debut: Mapped[str | None] = mapped_column(String(16))
    final_game: Mapped[str | None] = mapped_column(String(16))
    weight: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    bbref_id: Mapped[str | None] = mapped_column(String(16))


class Pitching(Base):
    __tablename__ = "pitching"
    __table_args__ = {"schema": "mlb"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("mlb.people.player_id"), index=True
    )
    year_id: Mapped[int] = mapped_column(Integer, index=True)
    stint: Mapped[int | None] = mapped_column(Integer)
    team_id: Mapped[str | None] = mapped_column(String(8))
    lg_id: Mapped[str | None] = mapped_column(String(4))
    w: Mapped[int | None] = mapped_column(Integer)
    l: Mapped[int | None] = mapped_column(Integer)
    g: Mapped[int | None] = mapped_column(Integer)
    gs: Mapped[int | None] = mapped_column(Integer)
    cg: Mapped[int | None] = mapped_column(Integer)
    sho: Mapped[int | None] = mapped_column(Integer)
    sv: Mapped[int | None] = mapped_column(Integer)
    ipouts: Mapped[int | None] = mapped_column(Integer)
    h: Mapped[int | None] = mapped_column(Integer)
    er: Mapped[int | None] = mapped_column(Integer)
    hr: Mapped[int | None] = mapped_column(Integer)
    bb: Mapped[int | None] = mapped_column(Integer)
    so: Mapped[int | None] = mapped_column(Integer)
    hbp: Mapped[int | None] = mapped_column(Integer)
    ibb: Mapped[int | None] = mapped_column(Integer)
    bfp: Mapped[int | None] = mapped_column(Integer)
    r: Mapped[int | None] = mapped_column(Integer)
    era: Mapped[float | None] = mapped_column(Float)


class Batting(Base):
    __tablename__ = "batting"
    __table_args__ = {"schema": "mlb"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("mlb.people.player_id"), index=True
    )
    year_id: Mapped[int] = mapped_column(Integer, index=True)
    stint: Mapped[int | None] = mapped_column(Integer)
    team_id: Mapped[str | None] = mapped_column(String(8))
    lg_id: Mapped[str | None] = mapped_column(String(4))
    g: Mapped[int | None] = mapped_column(Integer)
    ab: Mapped[int | None] = mapped_column(Integer)
    r: Mapped[int | None] = mapped_column(Integer)
    h: Mapped[int | None] = mapped_column(Integer)
    doubles: Mapped[int | None] = mapped_column(Integer)
    triples: Mapped[int | None] = mapped_column(Integer)
    hr: Mapped[int | None] = mapped_column(Integer)
    rbi: Mapped[int | None] = mapped_column(Integer)
    sb: Mapped[int | None] = mapped_column(Integer)
    cs: Mapped[int | None] = mapped_column(Integer)
    bb: Mapped[int | None] = mapped_column(Integer)
    so: Mapped[int | None] = mapped_column(Integer)
    ibb: Mapped[int | None] = mapped_column(Integer)
    hbp: Mapped[int | None] = mapped_column(Integer)
    sh: Mapped[int | None] = mapped_column(Integer)
    sf: Mapped[int | None] = mapped_column(Integer)
    gidp: Mapped[int | None] = mapped_column(Integer)


# --------------------------------------------------------------------------
# App tables (mock user DB + API keys)
# --------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(32), default="free")
    monthly_limit: Mapped[int] = mapped_column(Integer, default=1000)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    api_keys: Mapped[list["ApiKey"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(64), default="default")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    requests_used: Mapped[int] = mapped_column(Integer, default=0)
    period_start: Mapped[dt.date] = mapped_column(Date, default=dt.date.today)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="api_keys")


# --------------------------------------------------------------------------
# NFL raw tables (nfl schema) — sourced from nflverse-data
# --------------------------------------------------------------------------
class NflPlayerStat(Base):
    """Weekly player stats (one row per player per game week)."""

    __tablename__ = "player_stats"
    __table_args__ = {"schema": "nfl"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(String(16), index=True)
    player_name: Mapped[str | None] = mapped_column(String(128))
    position: Mapped[str | None] = mapped_column(String(8), index=True)
    recent_team: Mapped[str | None] = mapped_column(String(8))
    season: Mapped[int] = mapped_column(Integer, index=True)
    week: Mapped[int | None] = mapped_column(Integer)
    season_type: Mapped[str | None] = mapped_column(String(8))
    # Passing
    completions: Mapped[int | None] = mapped_column(Integer)
    attempts: Mapped[int | None] = mapped_column(Integer)
    passing_yards: Mapped[float | None] = mapped_column(Float)
    passing_tds: Mapped[int | None] = mapped_column(Integer)
    interceptions: Mapped[int | None] = mapped_column(Integer)
    sacks: Mapped[float | None] = mapped_column(Float)
    sack_yards: Mapped[float | None] = mapped_column(Float)
    # Rushing / receiving (kept for completeness)
    carries: Mapped[int | None] = mapped_column(Integer)
    rushing_yards: Mapped[float | None] = mapped_column(Float)
    rushing_tds: Mapped[int | None] = mapped_column(Integer)
    receptions: Mapped[int | None] = mapped_column(Integer)
    targets: Mapped[int | None] = mapped_column(Integer)
    receiving_yards: Mapped[float | None] = mapped_column(Float)
    receiving_tds: Mapped[int | None] = mapped_column(Integer)


class NflRoster(Base):
    __tablename__ = "rosters"
    __table_args__ = {"schema": "nfl"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    team: Mapped[str | None] = mapped_column(String(8), index=True)
    position: Mapped[str | None] = mapped_column(String(8))
    full_name: Mapped[str | None] = mapped_column(String(128))
    gsis_id: Mapped[str | None] = mapped_column(String(16), index=True)
    jersey_number: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(32))
    years_exp: Mapped[int | None] = mapped_column(Integer)
    college: Mapped[str | None] = mapped_column(String(64))


# --------------------------------------------------------------------------
# NBA raw table (nba schema) — season-level per-player totals.
# Both the live nba_api script and the offline fallback produce this shape.
# --------------------------------------------------------------------------
class NbaPlayerStat(Base):
    __tablename__ = "player_stats"
    __table_args__ = {"schema": "nba"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(String(24), index=True)
    player_name: Mapped[str | None] = mapped_column(String(128), index=True)
    team_abbreviation: Mapped[str | None] = mapped_column(String(8))
    position: Mapped[str | None] = mapped_column(String(16))
    season: Mapped[str] = mapped_column(String(12), index=True)
    games_played: Mapped[int | None] = mapped_column(Integer)
    minutes: Mapped[float | None] = mapped_column(Float)
    pts: Mapped[float | None] = mapped_column(Float)
    fgm: Mapped[float | None] = mapped_column(Float)
    fga: Mapped[float | None] = mapped_column(Float)
    fg3m: Mapped[float | None] = mapped_column(Float)
    fg3a: Mapped[float | None] = mapped_column(Float)
    ftm: Mapped[float | None] = mapped_column(Float)
    fta: Mapped[float | None] = mapped_column(Float)
    reb: Mapped[float | None] = mapped_column(Float)
    ast: Mapped[float | None] = mapped_column(Float)
    stl: Mapped[float | None] = mapped_column(Float)
    blk: Mapped[float | None] = mapped_column(Float)
    tov: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str | None] = mapped_column(String(16))
