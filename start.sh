#!/usr/bin/env bash
# StatVault one-command launcher: Postgres + FastAPI backend + Vite frontend.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PG_BIN="/opt/homebrew/opt/postgresql@16/bin"
PG_DATA="/opt/homebrew/var/postgresql@16"
export PATH="$PG_BIN:$PATH"
export LC_ALL="en_US.UTF-8"

echo "▶ Ensuring Postgres is up..."
if ! pg_isready -h localhost -p 5432 -q; then
  "$PG_BIN/postgres" -D "$PG_DATA" >/tmp/statvault_pg.log 2>&1 &
  for _ in $(seq 1 20); do pg_isready -h localhost -p 5432 -q && break; sleep 0.5; done
fi
createdb -h localhost statvault 2>/dev/null || true

echo "▶ Starting FastAPI backend on :8010..."
( cd "$ROOT/backend" && ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010 ) &
BACK_PID=$!

echo "▶ Starting Vite frontend on :5173..."
( cd "$ROOT/frontend" && npm run dev ) &
FRONT_PID=$!

echo ""
echo "StatVault running:"
echo "  API   → http://127.0.0.1:8010  (docs: /docs)"
echo "  Portal→ http://localhost:5173"
echo "Press Ctrl+C to stop."

trap 'kill $BACK_PID $FRONT_PID 2>/dev/null || true' INT TERM
wait
