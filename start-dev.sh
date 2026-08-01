#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

cd "$ROOT/backend"
if [[ ! -d .venv ]]; then
  python3.11 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi

echo "后端: http://127.0.0.1:8000"
echo "前端: http://127.0.0.1:5173"
echo "账号: admin / admin123"

(cd "$ROOT/backend" && .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) &
BACK_PID=$!
(cd "$ROOT/frontend" && npm run dev -- --host 127.0.0.1 --port 5173) &
FRONT_PID=$!

trap 'kill $BACK_PID $FRONT_PID 2>/dev/null || true' EXIT
wait
