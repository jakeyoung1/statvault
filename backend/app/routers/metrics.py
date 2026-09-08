"""Premium advanced-pitching-metrics endpoints (metered by API key)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import ApiKey
from app.schemas import MetricsResponse, PitchingMetricOut
from app.services.security import get_current_key, require_quota

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

# Whitelist of sortable columns -> guards against SQL injection via sort param.
SORTABLE = {
    "player_name", "season", "era", "fip", "so", "bb", "hr",
    "w", "l", "innings_pitched",
}


@router.get("/pitching", response_model=MetricsResponse)
def pitching_metrics(
    api_key: ApiKey = Depends(require_quota),  # premium: counts against quota
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, description="Player name contains"),
    season: int | None = Query(default=None, ge=1871, le=2100),
    team: str | None = Query(default=None, description="Team code, e.g. BOS"),
    min_ip: float = Query(default=0, ge=0, description="Minimum innings pitched"),
    sort_by: str = Query(default="fip"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> MetricsResponse:
    sort_col = sort_by if sort_by in SORTABLE else "fip"
    sort_dir = "ASC" if order == "asc" else "DESC"

    where = ["innings_pitched >= :min_ip"]
    params: dict = {"min_ip": min_ip}
    if search:
        where.append("LOWER(player_name) LIKE :search")
        params["search"] = f"%{search.lower()}%"
    if season is not None:
        where.append("season = :season")
        params["season"] = season
    if team:
        where.append("team_id = :team")
        params["team"] = team.upper()
    where_sql = " AND ".join(where)

    total = db.execute(
        text(f"SELECT COUNT(*) FROM mlb.pitching_metrics WHERE {where_sql}"), params
    ).scalar_one()

    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    rows = db.execute(
        text(
            f"""
            SELECT player_id, player_name, season, team_id, lg_id,
                   w, l, sv, innings_pitched, so, bb, hr, era, fip
            FROM mlb.pitching_metrics
            WHERE {where_sql}
            ORDER BY {sort_col} {sort_dir} NULLS LAST, player_name ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    return MetricsResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[PitchingMetricOut(**row) for row in rows],
    )


@router.get("/seasons", response_model=list[int])
def seasons(
    api_key: ApiKey = Depends(get_current_key),  # auth only, not metered
    db: Session = Depends(get_db),
) -> list[int]:
    rows = db.execute(
        text("SELECT DISTINCT season FROM mlb.pitching_metrics ORDER BY season DESC")
    ).scalars().all()
    return list(rows)
