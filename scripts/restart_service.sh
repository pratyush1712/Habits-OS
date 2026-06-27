#!/usr/bin/env bash
set -euo pipefail

LABEL="com.pratyush.habitos.api"

launchctl kickstart -k "gui/$(id -u)/$LABEL"

sleep 5

if ! curl -fsS "http://127.0.0.1:8083/health" | jq; then
  echo "HabitOS API did not become healthy after launchctl restart." >&2
  echo "Recent stderr log:" >&2
  tail -n 80 "$HOME/Library/Logs/HabitOS/api.err.log" >&2 || true
  exit 1
fi

curl -fsS "http://127.0.0.1:8083/automation/status" | jq '.scheduler'
