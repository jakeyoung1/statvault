"""Premium NFL passing metrics (ANY/A). Metered by the same API-key quota."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import ApiKey
from app.schemas import NflPassingOut, NflPassingResponse
from app.services.security import get_current_key, require_quota

router = APIRouter(prefix="/api/v1/nfl", tags=["nfl"])

SORTABLE = {
    "player_name", "season", "any_a", "yards_per_attempt", "passing_yards",
    "passing_tds", "attempts", "interceptions",
}


@router.get("/passing", response_model=NflPassingResponse)
def passing(
    api_key: ApiKey = Depends(require_quota),  # premium: counts against quota
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, description="Player name contains"),
    season: int | None = Query(default=None, ge=1999, le=2100),
    team: str | None = Query(default=None, description="Team code, e.g. PHI"),
    min_attempts: int = Query(default=0, ge=0),
    sort_by: str = Query(default="any_a"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> NflPassingResponse:
    sort_col = sort_by if sort_by in SORTABLE else "any_a"
    sort_dir = "ASC" if order == "asc" else "DESC"

    where = ["attempts >= :min_attempts"]
    params: dict = {"min_attempts": min_attempts}
    if search:
        where.append("LOWER(player_name) LIKE :search")
        params["search"] = f"%{search.lower()}%"
    if season is not None:
        where.append("season = :season")
        params["season"] = season
    if team:
        where.append("team = :team")
        params["team"] = team.upper()
    where_sql = " AND ".join(where)

    total = db.execute(
        text(f"SELECT COUNT(*) FROM nfl.passing_metrics WHERE {where_sql}"), params
    ).scalar_one()

    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    rows = db.execute(
        text(
            f"""
            SELECT player_id, player_name, season, team, games, completions,
                   attempts, passing_yards, passing_tds, interceptions, sacks,
                   sack_yards, yards_per_attempt, any_a
            FROM nfl.passing_metrics
            WHERE {where_sql}
            ORDER BY {sort_col} {sort_dir} NULLS LAST, player_name ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    return NflPassingResponse(
        total=total, page=page, page_size=page_size,
        items=[NflPassingOut(**r) for r in rows],
    )


@router.get("/seasons", response_model=list[int])
def seasons(
    api_key: ApiKey = Depends(get_current_key),  # auth only, not metered
    db: Session = Depends(get_db),
) -> list[int]:
    return list(
        db.execute(
            text("SELECT DISTINCT season FROM nfl.passing_metrics ORDER BY season DESC")
        ).scalars().all()
    )
