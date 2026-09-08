"""Ingest Lahman core CSVs into PostgreSQL via pandas + SQLAlchemy.

Run from the backend directory:
    ./.venv/bin/python scripts/ingest.py

Handles formatting issues gracefully: unexpected columns are ignored, numeric
columns are coerced (bad values become NULL rather than crashing the load).
"""
from __future__ import annotations

import os
import sys

import pandas as pd
from sqlalchemy import insert, text

# Make the `app` package importable when run as a plain script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base, SessionLocal, engine  # noqa: E402
from app.db.models import Batting, Person, Pitching  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CHUNK = 5_000

# Per-table config: CSV file, ORM model, {csv_column: model_column}, int/float cols.
TABLES = [
    {
        "csv": "People.csv",
        "model": Person,
        "rename": {
            "playerID": "player_id",
            "nameFirst": "name_first",
            "nameLast": "name_last",
            "nameGiven": "name_given",
            "bats": "bats",
            "throws": "throws",
            "birthYear": "birth_year",
            "debut": "debut",
            "finalGame": "final_game",
            "weight": "weight",
            "height": "height",
            "bbrefID": "bbref_id",
        },
        "int_cols": ["birth_year", "weight", "height"],
        "float_cols": [],
    },
    {
        "csv": "Pitching.csv",
        "model": Pitching,
        "rename": {
            "playerID": "player_id", "yearID": "year_id", "stint": "stint",
            "teamID": "team_id", "lgID": "lg_id", "W": "w", "L": "l", "G": "g",
            "GS": "gs", "CG": "cg", "SHO": "sho", "SV": "sv", "IPouts": "ipouts",
            "H": "h", "ER": "er", "HR": "hr", "BB": "bb", "SO": "so", "HBP": "hbp",
            "IBB": "ibb", "BFP": "bfp", "R": "r", "ERA": "era",
        },
        "int_cols": ["year_id", "stint", "w", "l", "g", "gs", "cg", "sho", "sv",
                     "ipouts", "h", "er", "hr", "bb", "so", "hbp", "ibb", "bfp", "r"],
        "float_cols": ["era"],
    },
    {
        "csv": "Batting.csv",
        "model": Batting,
        "rename": {
            "playerID": "player_id", "yearID": "year_id", "stint": "stint",
            "teamID": "team_id", "lgID": "lg_id", "G": "g", "AB": "ab", "R": "r",
            "H": "h", "2B": "doubles", "3B": "triples", "HR": "hr", "RBI": "rbi",
            "SB": "sb", "CS": "cs", "BB": "bb", "SO": "so", "IBB": "ibb",
            "HBP": "hbp", "SH": "sh", "SF": "sf", "GIDP": "gidp",
        },
        "int_cols": ["year_id", "stint", "g", "ab", "r", "h", "doubles", "triples",
                     "hr", "rbi", "sb", "cs", "bb", "so", "ibb", "hbp", "sh", "sf",
                     "gidp"],
        "float_cols": [],
    },
]


def load_table(cfg: dict, session) -> int:
    path = os.path.join(DATA_DIR, cfg["csv"])
    if not os.path.exists(path):
        print(f"  !! missing {cfg['csv']}, skipping")
        return 0

    # Read everything as string first so malformed numerics never crash the parse.
    df = pd.read_csv(path, dtype=str, keep_default_na=True, na_values=["", "NA"])

    wanted = [c for c in cfg["rename"] if c in df.columns]
    missing = set(cfg["rename"]) - set(df.columns)
    if missing:
        print(f"  (note) {cfg['csv']} missing cols ignored: {sorted(missing)}")
    df = df[wanted].rename(columns=cfg["rename"])

    # Coerce numerics; unparseable values become NULL instead of raising.
    for col in cfg["int_cols"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in cfg["float_cols"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows missing a required key.
    key = "player_id"
    before = len(df)
    df = df[df[key].notna()]
    dropped = before - len(df)
    if dropped:
        print(f"  (note) dropped {dropped} rows with null {key}")

    # Convert pandas NA/NaN to Python None for clean SQL inserts.
    df = df.astype(object).where(df.notna(), None)
    records = df.to_dict(orient="records")

    model = cfg["model"]
    session.execute(text(f'TRUNCATE TABLE {model.__tablename__} RESTART IDENTITY CASCADE'))
    for i in range(0, len(records), CHUNK):
        session.execute(insert(model), records[i:i + CHUNK])
    session.commit()
    return len(records)


def main() -> None:
    print("Creating tables (if absent)...")
    Base.metadata.create_all(engine)

    session = SessionLocal()
    try:
        # People must load before pitching/batting (FK dependency).
        for cfg in TABLES:
            print(f"Loading {cfg['csv']} -> {cfg['model'].__tablename__} ...")
            n = load_table(cfg, session)
            print(f"  inserted {n:,} rows")
    finally:
        session.close()
    print("Ingestion complete.")


if __name__ == "__main__":
    main()
