#!/bin/zsh
set -euo pipefail

LABEL="com.pratyush.habitos.api"

launchctl kickstart -k "gui/$(id -u)/$LABEL"

sleep 5

curl -sS "http://127.0.0.1:8000/health" | jq
curl -sS "http://127.0.0.1:8000/automation/status" | jq '.scheduler'