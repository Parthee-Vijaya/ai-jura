#!/usr/bin/env bash
# Start Tyr frontend i production-mode.
#
# Bygger statisk bundle (npm run build) hvis frontend/build ikke findes,
# og serverer det via `serve` på port 8090 bundet til 0.0.0.0 (så Tailscale
# virker fra iPhone).
#
# Forskel fra `npm start`: ingen hot-reload, ingen source maps, minified
# bundle, ~10x hurtigere første render. Til gengæld skal man manuelt
# rebuild når frontend-koden ændres — det sker ved at slette frontend/build/
# og køre dette script igen.
#
# Idempotent: tjekker port 8090 og pidfile før start.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDDIR="${TYR_PIDDIR:-$HOME/.tyr/run}"
LOGDIR="${TYR_LOG_DIR:-$HOME/Library/Logs/Tyr}"
PIDFILE="$PIDDIR/frontend.pid"
CONSOLE_LOG="$LOGDIR/frontend.console.log"

PORT="${FRONTEND_PORT:-8090}"
HOST="${FRONTEND_HOST:-0.0.0.0}"

REBUILD="${REBUILD:-no}"

mkdir -p "$PIDDIR" "$LOGDIR"

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Frontend (eller noget andet) kører allerede på port $PORT — stop den først"
    exit 1
fi

cd "$ROOT/frontend"

# Sørg for at build/ findes — byg hvis den mangler eller hvis REBUILD=yes
if [[ "$REBUILD" == "yes" || ! -d build ]]; then
    echo "Bygger frontend (npm run build)..."
    npm run build
else
    echo "Bruger eksisterende frontend/build/ (sæt REBUILD=yes for at rebuilde)"
fi

# Find serve — kan være i root node_modules (npm workspace hejser shared deps)
# eller i frontend/node_modules direkte
SERVE_BIN=""
for candidate in \
    "$ROOT/node_modules/.bin/serve" \
    "$ROOT/frontend/node_modules/.bin/serve"; do
    if [[ -x "$candidate" ]]; then
        SERVE_BIN="$candidate"
        break
    fi
done

if [[ -z "$SERVE_BIN" ]]; then
    echo "serve ikke installeret. Kør: cd $ROOT/frontend && npm install --save-dev serve"
    exit 1
fi

echo "Serverer frontend/build på http://$HOST:$PORT (Tailscale-tilgængelig)"
echo "Console log → $CONSOLE_LOG"
echo "serve binary: $SERVE_BIN"

# `serve` flags:
#   -s : single-page-app mode (alle 404 fallbacker til index.html — vigtig for React Router)
#   -l : listen address (host:port)
#   --no-clipboard : skip clipboard interactions
nohup "$SERVE_BIN" \
    -s build \
    -l "tcp://$HOST:$PORT" \
    --no-clipboard \
    >> "$CONSOLE_LOG" 2>&1 &
PID=$!
echo "$PID" > "$PIDFILE"

sleep 2
if ! kill -0 "$PID" 2>/dev/null; then
    echo "Frontend startede ikke (pid $PID døde inden 2s). Tjek $CONSOLE_LOG"
    rm -f "$PIDFILE"
    exit 1
fi

echo "Frontend startet (pid $PID)"
echo "Lokal: http://localhost:$PORT/"
echo "Tailscale: http://<din-mac-tailscale-ip>:$PORT/"
