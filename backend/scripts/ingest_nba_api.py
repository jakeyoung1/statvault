"""Fetch the current NBA season's player stats + rosters via the `nba_api`
package and load them into the `nba` schema.

Implements time.sleep() delays between calls to respect stats.nba.com's strict
rate limits.

IMPORTANT: stats.nba.com blocks many datacenter / sandbox IPs. If this script
times out, run the offline fallback instead:
    ./.venv/bin/python scripts/ingest_nba.py

Run from the backend directory:
    ./.venv/bin/python scripts/ingest_nba_api.py            # current season
    ./.venv/bin/python scripts/ingest_nba_api.py 2024-25
"""
from __future__ import annotations

import os
import sys
import time

import pandas as pd
from sqlalchemy import insert, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base, SessionLocal, engine  # noqa: E402
from app.db.models import NbaPlayerStat  # noqa: E402

CURRENT_SEASON = "2025-26"
REQUEST_DELAY = 0.8  # seconds between stats.nba.com calls (rate-limit courtesy)

# LeagueDashPlayerStats column -> nba.player_stats column
STAT_MAP = {
    "PLAYER_ID": "player_id", "PLAYER_NAME": "player_name",
    "TEAM_ABBREVIATION": "team_abbreviation", "GP": "games_played",
    "MIN": "minutes", "PTS": "pts", "FGM": "fgm", "FGA": "fga",
    "FG3M": "fg3m", "FG3A": "fg3a", "FTM": "ftm", "FTA": "fta",
    "REB": "reb", "AST": "ast", "STL": "stl", "BLK": "blk", "TOV": "tov",
}


def fetch_player_stats(season: str) -> pd.DataFrame:
    from nba_api.stats.endpoints import leaguedashplayerstats

    print(f"  fetching LeagueDashPlayerStats {season} ...")
    resp = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="Totals",
        timeout=30,
    )
    time.sleep(REQUEST_DELAY)
    return resp.get_data_frames()[0]


def fetch_positions(season: str) -> dict[str, str]:
    """Per-team rosters give player positions. One call per team, throttled."""
    from nba_api.stats.endpoints import commonteamroster
    from nba_api.stats.static import teams

    positions: dict[str, str] = {}
    for tm in teams.get_teams():
        try:
            roster = commonteamroster.CommonTeamRoster(
                team_id=tm["id"], season=season, timeout=30
            ).get_data_frames()[0]
            for _, row in roster.iterrows():
                positions[str(row["PLAYER_ID"])] = row.get("POSITION")
        except Exception as exc:  # noqa: BLE001 — one bad team shouldn't abort all
            print(f"    roster fetch failed for {tm['abbreviation']}: {exc}")
        time.sleep(REQUEST_DELAY)  # respect rate limit between every team
    return positions


def load(session, records: list[dict]) -> None:
    session.execute(text("TRUNCATE TABLE nba.player_stats RESTART IDENTITY CASCADE"))
    for r in records:
        session.execute(insert(NbaPlayerStat), r)
    session.commit()


def main(season: str) -> None:
    Base.metadata.create_all(engine)
    print(f"Ingesting NBA season {season} via nba_api ...")

    df = fetch_player_stats(season)
    positions = fetch_positions(season)

    df = df[[c for c in STAT_MAP if c in df.columns]].rename(columns=STAT_MAP)
    df["player_id"] = df["player_id"].astype(str)
    df["season"] = season
    df["position"] = df["player_id"].map(positions)
    df["source"] = "nba_api"
    df = df.astype(object).where(df.notna(), None)
    records = df.to_dict(orient="records")

    session = SessionLocal()
    try:
        load(session, records)
        print(f"  nba.player_stats: {len(records):,} players")
    finally:
        session.close()
    print("NBA ingestion (nba_api) complete.")


if __name__ == "__main__":
    s = sys.argv[1] if len(sys.argv) > 1 else CURRENT_SEASON
    main(s)
