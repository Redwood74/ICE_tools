#!/usr/bin/env bash
# ICEpicks scheduled check runner (Linux / macOS).
# Equivalent of scripts/run_check.ps1 for Unix.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VENV_ACTIVATE="$REPO_ROOT/.venv/bin/activate"
if [ ! -f "$VENV_ACTIVATE" ]; then
    echo "ERROR: Virtualenv not found at $VENV_ACTIVATE" >&2
    echo "       Run scripts/setup_cron.sh first." >&2
    exit 1
fi

# shellcheck disable=SC1090
source "$VENV_ACTIVATE"
cd "$REPO_ROOT"

echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] ICEpicks check starting..."
set +e
findice check-once
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -eq 3 ]; then
    echo "WARNING: Bot challenge or block detected (exit 3). Will retry next interval."
elif [ "$EXIT_CODE" -ne 0 ]; then
    echo "WARNING: findice exited with code $EXIT_CODE. Check artifacts and logs."
else
    echo "Check complete (exit code 0)."
fi

exit "$EXIT_CODE"
