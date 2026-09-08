"""Ingest NFL seasonal data from the open-source nflverse-data GitHub releases.

Fetches weekly player stats + rosters, cleans with pandas, and loads them into
the `nfl` PostgreSQL schema. The ANY/A view is built separately by
`scripts/create_views.py`.

Run from the backend directory:
    ./.venv/bin/python scripts/ingest_nfl.py            # latest season (2024)
    ./.venv/bin/python scripts/ingest_nfl.py 2023       # specific season
"""
from __future__ import annotations

import os
import sys
import urllib.request

import pandas as pd
from sqlalchemy import insert, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base, SessionLocal, engine  # noqa: E402
from app.db.models import NflPlayerStat, NflRoster  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
RELEASE = "https://github.com/nflverse/nflverse-data/releases/download"
CHUNK = 5_000

PLAYER_COLS = {
    "player_id": "player_id",
    "player_display_name": "player_name",
    "position": "position",
    "recent_team": "recent_team",
    "season": "season",
    "week": "week",
    "season_type": "season_type",
    "completions": "completions",
    "attempts": "attempts",
    "passing_yards": "passing_yards",
    "passing_tds": "passing_tds",
    "interceptions": "interceptions",
    "sacks": "sacks",
    "sack_yards": "sack_yards",
    "carries": "carries",
    "rushing_yards": "rushing_yards",
    "rushing_tds": "rushing_tds",
    "receptions": "receptions",
    "targets": "targets",
    "receiving_yards": "receiving_yards",
    "receiving_tds": "receiving_tds",
}
PLAYER_INT = ["season", "week", "completions", "attempts", "passing_tds",
              "interceptions", "carries", "rushing_tds", "receptions", "targets",
              "receiving_tds"]
PLAYER_FLOAT = ["passing_yards", "sacks", "sack_yards", "rushing_yards",
                "receiving_yards"]

ROSTER_COLS = {
    "season": "season", "team": "team", "position": "position",
    "full_name": "full_name", "gsis_id": "gsis_id",
    "jersey_number": "jersey_number", "status": "status",
    "years_exp": "years_exp", "college": "college",
}
ROSTER_INT = ["season", "jersey_number", "years_exp"]


def fetch(url: str, dest: str) -> str:
    path = os.path.join(DATA_DIR, dest)
    if os.path.exists(path):
        print(f"  using cached {dest}")
        return path
    print(f"  downloading {url}")
    urllib.request.urlretrieve(url, path)
    return path


def _clean(df: pd.DataFrame, colmap: dict, int_cols, float_cols, key: str) -> list[dict]:
    wanted = [c for c in colmap if c in df.columns]
    df = df[wanted].rename(columns=colmap)
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[df[key].notna()]
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict(orient="records")


def load(session, model, records: list[dict]) -> None:
    session.execute(text(f"TRUNCATE TABLE {model.__table_args__['schema']}.{model.__tablename__} RESTART IDENTITY CASCADE"))
    for i in range(0, len(records), CHUNK):
        session.execute(insert(model), records[i:i + CHUNK])
    session.commit()


def main(season: int) -> None:
    Base.metadata.create_all(engine)
    print(f"Ingesting NFL season {season} from nflverse-data ...")

    ps_path = fetch(f"{RELEASE}/player_stats/player_stats_{season}.csv",
                    f"nfl_player_stats_{season}.csv")
    rs_path = fetch(f"{RELEASE}/rosters/roster_{season}.csv",
                    f"nfl_roster_{season}.csv")

    session = SessionLocal()
    try:
        ps = pd.read_csv(ps_path, dtype=str, low_memory=False)
        ps_records = _clean(ps, PLAYER_COLS, PLAYER_INT, PLAYER_FLOAT, "player_id")
        load(session, NflPlayerStat, ps_records)
        print(f"  nfl.player_stats: {len(ps_records):,} weekly rows")

        rs = pd.read_csv(rs_path, dtype=str, low_memory=False)
        rs_records = _clean(rs, ROSTER_COLS, ROSTER_INT, [], "gsis_id")
        load(session, NflRoster, rs_records)
        print(f"  nfl.rosters: {len(rs_records):,} rows")
    finally:
        session.close()
    print("NFL ingestion complete.")


if __name__ == "__main__":
    yr = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    main(yr)
