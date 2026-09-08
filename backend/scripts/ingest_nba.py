"""Offline NBA fallback ingestion.

stats.nba.com (used by nba_api) is unreachable from some networks. This script
loads real NBA player data from the open-source hoopR-data GitHub repo
(game-level box scores), aggregates it to season-level per-player totals with
pandas, and loads it into the `nba` schema — the SAME table shape that
scripts/ingest_nba_api.py produces, so the TS% view works identically.

Run from the backend directory:
    ./.venv/bin/python scripts/ingest_nba.py            # latest available (2023 = 2022-23)
    ./.venv/bin/python scripts/ingest_nba.py 2023
"""
from __future__ import annotations

import os
import sys
import urllib.request

import pandas as pd
from sqlalchemy import insert, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base, SessionLocal, engine  # noqa: E402
from app.db.models import NbaPlayerStat  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
HOOPR = "https://raw.githubusercontent.com/sportsdataverse/hoopR-data/main/nba/player_box/csv"
REGULAR_SEASON = 2  # ESPN season_type: 1=pre, 2=regular, 3=post

SUM_COLS = {
    "points": "pts", "field_goals_made": "fgm", "field_goals_attempted": "fga",
    "three_point_field_goals_made": "fg3m", "three_point_field_goals_attempted": "fg3a",
    "free_throws_made": "ftm", "free_throws_attempted": "fta",
    "rebounds": "reb", "assists": "ast", "steals": "stl", "blocks": "blk",
    "turnovers": "tov", "minutes": "minutes",
}


def season_label(espn_year: int) -> str:
    # ESPN season year N == the (N-1)-N NBA season.
    return f"{espn_year - 1}-{str(espn_year)[-2:]}"


def fetch(espn_year: int) -> str:
    gz = os.path.join(DATA_DIR, f"nba_player_box_{espn_year}.csv.gz")
    if not os.path.exists(gz):
        url = f"{HOOPR}/player_box_{espn_year}.csv.gz"
        print(f"  downloading {url}")
        urllib.request.urlretrieve(url, gz)
    return gz


def main(espn_year: int) -> None:
    Base.metadata.create_all(engine)
    label = season_label(espn_year)
    print(f"Ingesting NBA season {label} (hoopR-data fallback) ...")

    gz = fetch(espn_year)
    df = pd.read_csv(gz, compression="gzip", low_memory=False)

    # Regular season only, and only rows where the player actually played.
    df = df[df["season_type"] == REGULAR_SEASON].copy()
    for col in SUM_COLS:
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    played = df["minutes"].fillna(0) > 0

    grp = df.groupby("athlete_id")
    agg = grp[list(SUM_COLS)].sum(min_count=1).rename(columns=SUM_COLS)
    agg["games_played"] = df[played].groupby("athlete_id")["game_id"].nunique()
    agg["player_name"] = grp["athlete_display_name"].first()
    # Team / position the player appeared with most often.
    agg["team_abbreviation"] = grp["team_abbreviation"].agg(
        lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else None
    )
    agg["position"] = grp["athlete_position_abbreviation"].agg(
        lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else None
    )
    agg = agg.reset_index().rename(columns={"athlete_id": "player_id"})
    agg["player_id"] = agg["player_id"].astype(str)
    agg["season"] = label
    agg["source"] = "hoopR-fallback"
    agg = agg.astype(object).where(agg.notna(), None)
    records = agg.to_dict(orient="records")

    session = SessionLocal()
    try:
        session.execute(text("TRUNCATE TABLE nba.player_stats RESTART IDENTITY CASCADE"))
        for i in range(0, len(records), 2000):
            session.execute(insert(NbaPlayerStat), records[i:i + 2000])
        session.commit()
        print(f"  nba.player_stats: {len(records):,} players (season {label})")
    finally:
        session.close()
    print("NBA ingestion (fallback) complete.")


if __name__ == "__main__":
    yr = int(sys.argv[1]) if len(sys.argv) > 1 else 2023
    main(yr)
