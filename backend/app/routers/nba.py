"""Premium NBA scoring metrics (TS%). Metered by the same API-key quota."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import ApiKey
from app.schemas import NbaScoringOut, NbaScoringResponse
from app.services.security import get_current_key, require_quota

router = APIRouter(prefix="/api/v1/nba", tags=["nba"])

SORTABLE = {
    "player_name", "season", "ts_pct", "ppg", "pts", "fga", "games_played",
}


@router.get("/scoring", response_model=NbaScoringResponse)
def scoring(
    api_key: ApiKey = Depends(require_quota),  # premium: counts against quota
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, description="Player name contains"),
    season: str | None = Query(default=None, description="Season, e.g. 2022-23"),
    team: str | None = Query(default=None, description="Team code, e.g. DEN"),
    min_games: int = Query(default=0, ge=0),
    sort_by: str = Query(default="ts_pct"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> NbaScoringResponse:
    sort_col = sort_by if sort_by in SORTABLE else "ts_pct"
    sort_dir = "ASC" if order == "asc" else "DESC"

    where = ["games_played >= :min_games"]
    params: dict = {"min_games": min_games}
    if search:
        where.append("LOWER(player_name) LIKE :search")
        params["search"] = f"%{search.lower()}%"
    if season:
        where.append("season = :season")
        params["season"] = season
    if team:
        where.append("team = :team")
        params["team"] = team.upper()
    where_sql = " AND ".join(where)

    total = db.execute(
        text(f"SELECT COUNT(*) FROM nba.scoring_metrics WHERE {where_sql}"), params
    ).scalar_one()

    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    rows = db.execute(
        text(
            f"""
            SELECT player_id, player_name, team, position, season, games_played,
                   pts, ppg, fga, fta, ts_pct
            FROM nba.scoring_metrics
            WHERE {where_sql}
            ORDER BY {sort_col} {sort_dir} NULLS LAST, player_name ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    return NbaScoringResponse(
        total=total, page=page, page_size=page_size,
        items=[NbaScoringOut(**r) for r in rows],
    )


@router.get("/seasons", response_model=list[str])
def seasons(
    api_key: ApiKey = Depends(get_current_key),  # auth only, not metered
    db: Session = Depends(get_db),
) -> list[str]:
    return list(
        db.execute(
            text("SELECT DISTINCT season FROM nba.scoring_metrics ORDER BY season DESC")
        ).scalars().all()
    )
