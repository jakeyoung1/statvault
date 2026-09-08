"""Migrate existing MLB objects from `public` into an `mlb` schema and create
the `nfl` / `nba` schemas. Idempotent and non-destructive (uses ALTER ... SET
SCHEMA, so existing rows are preserved — no re-ingest needed).

App tables (`users`, `api_keys`) intentionally stay in `public`: they are
cross-sport and not specific to baseball.

Run from the backend directory:
    ./.venv/bin/python scripts/migrate_to_schemas.py
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import engine  # noqa: E402

SCHEMAS = ["mlb", "nfl", "nba"]
MLB_TABLES = ["people", "pitching", "batting"]
MLB_MATVIEWS = ["pitching_metrics"]


def _table_schema(conn, name: str) -> str | None:
    return conn.execute(
        text(
            "SELECT table_schema FROM information_schema.tables "
            "WHERE table_name = :n AND table_schema IN ('public','mlb','nfl','nba')"
        ),
        {"n": name},
    ).scalar()


def _matview_schema(conn, name: str) -> str | None:
    return conn.execute(
        text("SELECT schemaname FROM pg_matviews WHERE matviewname = :n"),
        {"n": name},
    ).scalar()


def main() -> None:
    with engine.begin() as conn:
        for s in SCHEMAS:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {s}"))
            print(f"schema ready: {s}")

        # Move materialized views FIRST is unnecessary (deps are by OID), but we
        # move tables first then the views for readability.
        for tbl in MLB_TABLES:
            loc = _table_schema(conn, tbl)
            if loc == "public":
                conn.execute(text(f"ALTER TABLE public.{tbl} SET SCHEMA mlb"))
                print(f"moved table public.{tbl} -> mlb.{tbl}")
            elif loc == "mlb":
                print(f"table mlb.{tbl} already in place")
            else:
                print(f"table {tbl} not found (loc={loc}) — skipping")

        for mv in MLB_MATVIEWS:
            loc = _matview_schema(conn, mv)
            if loc == "public":
                conn.execute(text(f"ALTER MATERIALIZED VIEW public.{mv} SET SCHEMA mlb"))
                print(f"moved matview public.{mv} -> mlb.{mv}")
            elif loc == "mlb":
                print(f"matview mlb.{mv} already in place")
            else:
                print(f"matview {mv} not found (loc={loc}) — will be (re)built by create_views.py")

    print("Schema migration complete.")


if __name__ == "__main__":
    main()
