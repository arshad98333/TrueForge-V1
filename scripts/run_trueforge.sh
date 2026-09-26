#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p .runtime
export SQLITE_PATH="$PWD/.runtime/trueforge.sqlite"
export HOST=127.0.0.1
export ACCESS_LOGS=false
export OUTBOUND_URL_ALLOWED_HOSTS='["127.0.0.1"]'
exec node scripts/run_trueforge.mjs --port 8790
