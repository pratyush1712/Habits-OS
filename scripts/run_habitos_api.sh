#!/bin/zsh
set -euo pipefail

cd /Users/praty/Desktop/Habits-OS

export PATH="/Users/praty/go/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export RMAPI_CONFIG="/Users/praty/.config/habitos/rmapi.conf"

exec /Users/praty/Desktop/Habits-OS/.venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
