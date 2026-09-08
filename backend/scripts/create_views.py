"""Build advanced-metric materialized views + indexes for all sports.

  mlb.pitching_metrics  — ERA, FIP (per-season FIP constant)
  nfl.passing_metrics   — ANY/A (Adjusted Net Yards per Pass Attempt), QBs
  nba.scoring_metrics   — TS% (True Shooting Percentage)

Run from the backend directory:
    ./.venv/bin/python scripts/create_views.py
Each view is rebuilt only if its source table has data, so this is safe to run
before a given sport has been ingested.
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import engine  # noqa: E402

# --------------------------------------------------------------------------
# MLB — ERA & FIP
# --------------------------------------------------------------------------
MLB_SQL = """
DROP MATERIALIZED VIEW IF EXISTS mlb.pitching_metrics;
CREATE MATERIALIZED VIEW mlb.pitching_metrics AS
WITH season_totals AS (
    SELECT year_id,
        SUM(er) AS lg_er, SUM(ipouts) AS lg_ipouts, SUM(hr) AS lg_hr,
        SUM(bb) AS lg_bb, SUM(COALESCE(hbp,0)) AS lg_hbp, SUM(so) AS lg_so
    FROM mlb.pitching
    WHERE ipouts IS NOT NULL AND ipouts > 0
    GROUP BY year_id
),
season_constant AS (
    SELECT year_id,
        (9.0 * lg_er) / NULLIF(lg_ipouts/3.0, 0)
          - ((13.0*lg_hr) + (3.0*(lg_bb+lg_hbp)) - (2.0*lg_so)) / NULLIF(lg_ipouts/3.0,0)
          AS fip_constant
    FROM season_totals
)
SELECT
    p.player_id,
    TRIM(COALESCE(pe.name_first,'') || ' ' || COALESCE(pe.name_last,'')) AS player_name,
    p.year_id AS season, p.team_id, p.lg_id,
    p.g, p.gs, p.w, p.l, p.sv,
    ROUND((p.ipouts/3.0)::numeric, 1) AS innings_pitched,
    p.so, p.bb, p.hr, p.er,
    ROUND((9.0 * p.er / NULLIF(p.ipouts/3.0,0))::numeric, 2) AS era,
    ROUND((
        ((13.0*p.hr) + (3.0*(p.bb + COALESCE(p.hbp,0))) - (2.0*p.so)) / NULLIF(p.ipouts/3.0,0)
        + c.fip_constant
    )::numeric, 2) AS fip
FROM mlb.pitching p
JOIN mlb.people pe         ON pe.player_id = p.player_id
JOIN season_constant c     ON c.year_id   = p.year_id
WHERE p.ipouts IS NOT NULL AND p.ipouts > 0;
"""
MLB_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_pm_season ON mlb.pitching_metrics (season)",
    "CREATE INDEX IF NOT EXISTS idx_pm_player_name ON mlb.pitching_metrics (LOWER(player_name))",
    "CREATE INDEX IF NOT EXISTS idx_pm_player_id ON mlb.pitching_metrics (player_id)",
    "CREATE INDEX IF NOT EXISTS idx_pm_season_fip ON mlb.pitching_metrics (season, fip)",
]

# --------------------------------------------------------------------------
# NFL — ANY/A = (PassYds + 20*PassTD - 45*INT - SackYds) / (Att + Sacks)
# Weekly rows aggregated to season for qualifying QBs (regular season).
# --------------------------------------------------------------------------
NFL_SQL = """
DROP MATERIALIZED VIEW IF EXISTS nfl.passing_metrics;
CREATE MATERIALIZED VIEW nfl.passing_metrics AS
SELECT
    player_id,
    MAX(player_name) AS player_name,
    season,
    (ARRAY_AGG(recent_team ORDER BY week DESC))[1] AS team,
    COUNT(*) FILTER (WHERE attempts > 0) AS games,
    SUM(completions) AS completions,
    SUM(attempts)    AS attempts,
    SUM(passing_yards) AS passing_yards,
    SUM(passing_tds)   AS passing_tds,
    SUM(interceptions) AS interceptions,
    SUM(sacks)       AS sacks,
    SUM(sack_yards)  AS sack_yards,
    ROUND((SUM(passing_yards) / NULLIF(SUM(attempts),0))::numeric, 2) AS yards_per_attempt,
    ROUND((
        (SUM(passing_yards) + 20*SUM(passing_tds) - 45*SUM(interceptions) - SUM(sack_yards))
        / NULLIF(SUM(attempts) + SUM(sacks), 0)
    )::numeric, 2) AS any_a
FROM nfl.player_stats
WHERE position = 'QB' AND season_type = 'REG'
GROUP BY player_id, season
HAVING SUM(attempts) >= 100;
"""
NFL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_nfl_pm_season ON nfl.passing_metrics (season)",
    "CREATE INDEX IF NOT EXISTS idx_nfl_pm_name ON nfl.passing_metrics (LOWER(player_name))",
    "CREATE INDEX IF NOT EXISTS idx_nfl_pm_team ON nfl.passing_metrics (team)",
    "CREATE INDEX IF NOT EXISTS idx_nfl_pm_anya ON nfl.passing_metrics (season, any_a)",
]

# --------------------------------------------------------------------------
# NBA — TS% = PTS / (2 * (FGA + 0.44*FTA))   (expressed as a percentage)
# --------------------------------------------------------------------------
NBA_SQL = """
DROP MATERIALIZED VIEW IF EXISTS nba.scoring_metrics;
CREATE MATERIALIZED VIEW nba.scoring_metrics AS
SELECT
    player_id,
    player_name,
    team_abbreviation AS team,
    position,
    season,
    games_played,
    ROUND(pts::numeric, 0) AS pts,
    ROUND((pts / NULLIF(games_played,0))::numeric, 1) AS ppg,
    ROUND(fga::numeric, 0) AS fga,
    ROUND(fta::numeric, 0) AS fta,
    ROUND((100.0 * pts / NULLIF(2*(fga + 0.44*fta),0))::numeric, 1) AS ts_pct
FROM nba.player_stats
WHERE (fga + fta) > 0;
"""
NBA_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_nba_sm_season ON nba.scoring_metrics (season)",
    "CREATE INDEX IF NOT EXISTS idx_nba_sm_name ON nba.scoring_metrics (LOWER(player_name))",
    "CREATE INDEX IF NOT EXISTS idx_nba_sm_ts ON nba.scoring_metrics (season, ts_pct)",
]

VIEWS = [
    ("mlb.pitching", "mlb.pitching_metrics", MLB_SQL, MLB_INDEXES),
    ("nfl.player_stats", "nfl.passing_metrics", NFL_SQL, NFL_INDEXES),
    ("nba.player_stats", "nba.scoring_metrics", NBA_SQL, NBA_INDEXES),
]


def _row_count(conn, qualified_table: str) -> int:
    schema, table = qualified_table.split(".")
    exists = conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema=:s AND table_name=:t"
        ),
        {"s": schema, "t": table},
    ).scalar()
    if not exists:
        return 0
    return conn.execute(text(f"SELECT COUNT(*) FROM {qualified_table}")).scalar() or 0


def main() -> None:
    with engine.begin() as conn:
        for src, view, sql, indexes in VIEWS:
            n = _row_count(conn, src)
            if n == 0:
                print(f"skip {view}: source {src} empty/missing")
                continue
            print(f"building {view} (source rows: {n:,}) ...")
            conn.execute(text(sql))
            for stmt in indexes:
                conn.execute(text(stmt))
            count = conn.execute(text(f"SELECT COUNT(*) FROM {view}")).scalar()
            print(f"  {view}: {count:,} rows")
    print("Views & indexes ready.")


if __name__ == "__main__":
    main()
