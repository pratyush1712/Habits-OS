#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/praty/Code/Habits-OS"
PYTHON="$PROJECT_DIR/.venv/bin/python"

export HOME="/Users/praty"
export PATH="/Users/praty/go/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export RMAPI_CONFIG="/Users/praty/.config/habitos/rmapi.conf"
export PYTHONPATH="$PROJECT_DIR"

# Needed for MongoDB Atlas TLS verification under launchd.
CERT_FILE="$($PYTHON -c 'import certifi; print(certifi.where())')"
export SSL_CERT_FILE="$CERT_FILE"
export REQUESTS_CA_BUNDLE="$CERT_FILE"

cd "$PROJECT_DIR"

exec "$PYTHON" -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8083
