#!/usr/bin/env bash
set -euo pipefail

METHOD="GET"
if [[ "${1:-}" == "-X" ]]; then
  METHOD="$2"
  shift 2
fi

URL="${1:?usage: scripts/api_json.sh [-X METHOD] URL}"
PYTHON="${PYTHON:-.venv/bin/python}"
TMP_BODY="$(mktemp)"
trap 'rm -f "$TMP_BODY"' EXIT

HTTP_STATUS=$(curl -sS -X "$METHOD" -H 'Accept: application/json' -o "$TMP_BODY" -w '%{http_code}' "$URL") || {
  code=$?
  cat >&2 <<ERR
HabitOS API request failed before a response was received.
URL: $URL
Method: $METHOD
Hint: the API is probably not running. Try: make service-status && make service-logs
ERR
  exit "$code"
}

if [[ ! "$HTTP_STATUS" =~ ^2 ]]; then
  echo "HabitOS API returned HTTP $HTTP_STATUS for $METHOD $URL" >&2
  if [[ -s "$TMP_BODY" ]]; then
    "$PYTHON" -m json.tool < "$TMP_BODY" || cat "$TMP_BODY" >&2
  fi
  exit 22
fi

if [[ ! -s "$TMP_BODY" ]]; then
  echo "HabitOS API returned an empty HTTP $HTTP_STATUS response for $METHOD $URL" >&2
  exit 52
fi

"$PYTHON" -m json.tool < "$TMP_BODY" || {
  echo "HabitOS API returned non-JSON HTTP $HTTP_STATUS response for $METHOD $URL:" >&2
  cat "$TMP_BODY" >&2
  exit 65
}
