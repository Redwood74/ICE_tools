#!/usr/bin/env bash
# ICEpicks setup for Linux — creates venv, installs deps, registers cron.
# Run from the ICE_tools repository root.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$REPO_ROOT/.venv"
INTERVAL_MINUTES="${SCHEDULE_INTERVAL_MINUTES:-20}"

echo "=== ICEpicks Linux Setup ==="
echo "Repo root: $REPO_ROOT"

# ── 1. Python check ────────────────────────────────────────────────────────
echo ""
echo "[1/5] Checking Python..."
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PYTHON_CMD="$cmd"
        break
    fi
done
if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python 3.10+ is required." >&2
    exit 1
fi
echo "Found: $($PYTHON_CMD --version)"

# ── 2. Create virtualenv ───────────────────────────────────────────────────
echo ""
echo "[2/5] Creating virtualenv..."
if [ -d "$VENV_PATH" ]; then
    echo "  Virtualenv already exists — skipping."
else
    "$PYTHON_CMD" -m venv "$VENV_PATH"
    echo "  Virtualenv created."
fi

# shellcheck disable=SC1091
source "$VENV_PATH/bin/activate"

# ── 3. Install dependencies ────────────────────────────────────────────────
echo ""
echo "[3/5] Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r "$REPO_ROOT/requirements.txt" --quiet
pip install -e "$REPO_ROOT" --quiet
echo "  Dependencies installed."

# ── 4. Playwright browser ──────────────────────────────────────────────────
echo ""
echo "[4/5] Installing Playwright Chromium..."
playwright install chromium
echo "  Playwright Chromium installed."

# ── 5. .env file ───────────────────────────────────────────────────────────
echo ""
echo "[5/5] Checking .env..."
if [ ! -f "$REPO_ROOT/.env" ]; then
    cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
    echo "  .env created from .env.example. Edit it now:"
    echo "    nano $REPO_ROOT/.env"
else
    echo "  .env already exists — not overwriting."
fi

# ── Optional: cron registration ─────────────────────────────────────────────
echo ""
read -rp "Register cron job (every ${INTERVAL_MINUTES} min)? [y/N] " REGISTER_CRON
if [ "$REGISTER_CRON" = "y" ] || [ "$REGISTER_CRON" = "Y" ]; then
    RUNNER="$REPO_ROOT/scripts/run_check.sh"
    chmod +x "$RUNNER"
    CRON_LINE="*/${INTERVAL_MINUTES} * * * * $RUNNER >> $REPO_ROOT/icepicks_cron.log 2>&1"

    # Remove existing entry if present, then add new one
    (crontab -l 2>/dev/null | grep -v "run_check.sh" || true; echo "$CRON_LINE") | crontab -
    echo "  Cron job registered: every ${INTERVAL_MINUTES} minutes."
    echo "  Verify with: crontab -l"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env:  nano $REPO_ROOT/.env"
echo "  2. Test run:   source $VENV_PATH/bin/activate && findice smoke-test"
echo "  3. Dry run:    findice check-once --dry-run"
