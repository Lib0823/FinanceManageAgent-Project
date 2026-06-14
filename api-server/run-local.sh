#!/usr/bin/env bash
# Loads api-server/.env (gitignored secrets) and starts the server.
# Usage: ./run-local.sh   (pass extra gradle args after if needed)
set -euo pipefail
cd "$(dirname "$0")"
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
  echo "[run-local] loaded .env (DART_API_KEY set: $([ -n "${DART_API_KEY:-}" ] && echo yes || echo no), KIS_QUOTE_APP_KEY set: $([ -n "${KIS_QUOTE_APP_KEY:-}" ] && echo yes || echo no))"
else
  echo "[run-local] WARNING: .env not found — KIS quote / DART will be disabled"
fi
exec ./gradlew bootRun "$@"
