#!/usr/bin/env bash
# Runs all three demo processes in one container. Only the dashboard's
# $PORT is exposed publicly by Railway; backend/voice stay on loopback
# and are reached through next.config.mjs's /role3 and /role1 rewrites.
set -e

python -m src.backend &
BACKEND_PID=$!

python -m src.voice &
VOICE_PID=$!

npm start &
DASHBOARD_PID=$!

# If any one process dies, stop the container so Railway restarts it
# instead of serving a partially-broken demo.
wait -n "$BACKEND_PID" "$VOICE_PID" "$DASHBOARD_PID"
EXIT_CODE=$?
kill "$BACKEND_PID" "$VOICE_PID" "$DASHBOARD_PID" 2>/dev/null
exit $EXIT_CODE
