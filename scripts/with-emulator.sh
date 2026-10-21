#!/usr/bin/env bash
# Run a command with FIRESTORE_EMULATOR_HOST set.
# Reuses an emulator that is already listening (e.g. from `make dev`); otherwise starts a
# throw-away one for the duration of the command via `firebase emulators:exec`.
set -euo pipefail
HOST="${FIRESTORE_EMULATOR_HOST:-127.0.0.1:8085}"
export FIRESTORE_PROJECT_ID="${FIRESTORE_PROJECT_ID:-demo-magaza}"
if (exec 3<>"/dev/tcp/${HOST%:*}/${HOST#*:}") 2>/dev/null; then
  export FIRESTORE_EMULATOR_HOST="$HOST"
  exec bash -c "$*"
fi
exec pnpm exec firebase emulators:exec --only firestore --project "$FIRESTORE_PROJECT_ID" "$*"
