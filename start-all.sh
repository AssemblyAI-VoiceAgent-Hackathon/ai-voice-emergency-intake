#!/usr/bin/env bash
# Runs all three demo processes in one container. Only the dashboard's
# $PORT is exposed publicly by Railway; backend/voice stay on loopback
# and are reached through next.config.mjs's /role3 and /role1 rewrites.
set -e

DASHBOARD_PORT="${PORT:-3000}"

# Railway sets a single $PORT for the whole container; that belongs to
# the dashboard only. Strip it here so the backend/voice fall back to
# their fixed internal ARIA_BIND_PORT/ARIA_VOICE_BIND_PORT (8000/8001)
# instead of racing the dashboard for the same port.
env -u PORT python -m src.backend &
BACKEND_PID=$!

env -u PORT python -m src.voice &
VOICE_PID=$!

PORT="$DASHBOARD_PORT" npm start &
DASHBOARD_PID=$!

# If any one process dies, stop the container so Railway restarts it
# instead of serving a partially-broken demo.
wait -n "$BACKEND_PID" "$VOICE_PID" "$DASHBOARD_PID"
EXIT_CODE=$?
kill "$BACKEND_PID" "$VOICE_PID" "$DASHBOARD_PID" 2>/dev/null
exit $EXIT_CODE
