#!/usr/bin/env bash
#   ⚡ THUNDER-X ⚡   runs the whole project: Python env, Laya (Docker), service (:8000), UI (:5173)
#
#   ./run.sh                         Laya = cklxx/laya-browser (default)
#   LAYA_MODEL=mind2web ./run.sh     Laya = Quantum08/laya-browser-mind2web
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\e[36m⚡\e[0m %s\n' "$*"; }
ok()  { printf '\e[32m✔\e[0m %s\n' "$*"; }
die() { printf '\e[31m✘\e[0m %s\n' "$*" >&2; exit 1; }

# Which Laya
export LAYA_MODEL="${LAYA_MODEL:-browser}"
case "$LAYA_MODEL" in
  browser)  LAYA_SERVICE=laya-browser; LAYA_PORT=8002 ;;
  mind2web) LAYA_SERVICE=laya;         LAYA_PORT=8001 ;;
  *) die "LAYA_MODEL must be browser or mind2web, not '$LAYA_MODEL'" ;;
esac
LAYA_HEALTH="http://localhost:$LAYA_PORT/health"

# 1. Python environment (made again when pyproject.toml changes)
say "1/4 python environment"
if [[ ! -f .venv/.installed || pyproject.toml -nt .venv/.installed ]]; then
  command -v python3 >/dev/null || die "python3 not found"
  python3 -m venv .venv
  .venv/bin/python -m pip install --quiet --upgrade pip
  .venv/bin/python -m pip install --quiet -e .
  touch .venv/.installed
fi

# 2. Laya in Docker
say "2/4 Laya ($LAYA_MODEL)"
if ! curl -fs "$LAYA_HEALTH" >/dev/null 2>&1; then
  if command -v docker >/dev/null; then
    say "starting it (first time: builds the image and downloads the model, a few minutes)"
    docker compose up -d --build "$LAYA_SERVICE"
    for _ in $(seq 120); do
      curl -fs "$LAYA_HEALTH" >/dev/null 2>&1 && break
      sleep 3
    done
  fi
  curl -fs "$LAYA_HEALTH" >/dev/null 2>&1 || say "Laya not ready: the project runs without it (logs: docker compose logs -f $LAYA_SERVICE)"
fi

# 3. UI packages
say "3/4 UI packages"
command -v npm >/dev/null || die "npm not found (install Node.js)"
[[ -d frontend/node_modules ]] || (cd frontend && npm install --silent)

# 4. Service + UI
say "4/4 service + UI"
.venv/bin/python -m uvicorn thunderx.main:app --port 8000 &
service_pid=$!
trap 'kill $service_pid 2>/dev/null' EXIT

echo
ok "UI       -> http://localhost:5173"
ok "service  -> http://localhost:8000/docs"
ok "Laya     -> http://localhost:$LAYA_PORT/health  ($LAYA_MODEL)"
echo
(cd frontend && npm run dev)
