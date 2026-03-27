#!/bin/bash
# ============================================================
#  ICEpicks — One-Click Installer for macOS / Linux
# ============================================================
#
#  Double-click this file in Finder (macOS) or run:
#    bash install.command
#
#  No admin rights required.
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ===================================================="
echo "    ICEpicks — One-Click Installer"
echo "  ===================================================="
echo ""
echo "  This installer will:"
echo "    1. Check for Python (install if needed)"
echo "    2. Set up ICEpicks and its dependencies"
echo "    3. Install the browser used for checking"
echo "    4. Walk you through configuration"
echo ""
echo "  No admin rights required."
echo "  Press Ctrl+C at any time to cancel."
echo ""
read -rp "  Press Enter to continue..."

# ── Step 1: Find Python ─────────────────────────────────────────────────────
echo ""
echo "  [Step 1/5] Checking for Python..."
echo ""

PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        # Verify it's Python 3.10+
        version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "  Python 3.10+ was not found on this computer."
    echo ""

    # Try Homebrew on macOS
    if [ "$(uname)" = "Darwin" ]; then
        if command -v brew >/dev/null 2>&1; then
            echo "  Installing Python via Homebrew..."
            brew install python@3.12
            PYTHON_CMD="python3"
        else
            echo "  ===================================================="
            echo "   Please install Python:"
            echo ""
            echo "   Option A (recommended): Install Homebrew first:"
            echo "     /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            echo "     brew install python@3.12"
            echo ""
            echo "   Option B: Download from https://www.python.org/downloads/"
            echo ""
            echo "   Then run this installer again."
            echo "  ===================================================="
            exit 1
        fi
    else
        # Linux
        echo "  ===================================================="
        echo "   Please install Python 3.10+:"
        echo ""
        echo "   Ubuntu/Debian:  sudo apt install python3 python3-venv python3-pip"
        echo "   Fedora:         sudo dnf install python3"
        echo "   Arch:           sudo pacman -S python"
        echo ""
        echo "   Then run this installer again."
        echo "  ===================================================="
        exit 1
    fi
fi

PYVER=$("$PYTHON_CMD" --version 2>&1)
echo "  Found: $PYVER"

# ── Step 2: Create virtual environment ──────────────────────────────────────
echo ""
echo "  [Step 2/5] Setting up ICEpicks environment..."
echo ""

if [ ! -f ".venv/bin/python" ]; then
    echo "  Creating virtual environment..."
    "$PYTHON_CMD" -m venv .venv
    echo "  Virtual environment created."
else
    echo "  Virtual environment already exists — using it."
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# ── Step 3: Install dependencies ────────────────────────────────────────────
echo ""
echo "  [Step 3/5] Installing ICEpicks software..."
echo "  (This may take a minute on first install)"
echo ""

pip install --upgrade pip --quiet 2>/dev/null || true
pip install -r requirements.txt --quiet
pip install -e . --quiet
echo "  Software installed successfully."

# ── Step 4: Install browser ─────────────────────────────────────────────────
echo ""
echo "  [Step 4/5] Installing browser for website checks..."
echo ""
echo "  NOTE: This downloads Chromium (~150 MB). It may take"
echo "  several minutes on a slow connection. Please wait."
echo ""

playwright install chromium || {
    echo ""
    echo "  WARNING: Browser installation had issues."
    echo "  You may need to install system dependencies:"
    echo "    playwright install-deps chromium"
    echo ""
}

echo ""
echo "  Browser installed."

# ── Step 5: Configuration ───────────────────────────────────────────────────
echo ""
echo "  [Step 5/5] Configuration"
echo ""
echo "  You will now be asked a few questions to set up ICEpicks."
echo "  You need:"
echo "    - The person's Alien Registration Number (A-Number)"
echo "    - Their country of origin"
echo "    - (Optional) A Microsoft Teams webhook URL"
echo ""
echo "  If you don't have the Teams webhook URL, just press Enter"
echo "  to skip it — you can add it later."
echo ""
read -rp "  Press Enter to continue..."

findice setup || {
    echo ""
    echo "  Configuration had an issue. You can run it again later:"
    echo "    source .venv/bin/activate && findice setup"
}

# ── Test run ─────────────────────────────────────────────────────────────────
echo ""
echo "  ===================================================="
echo "   Installation complete!"
echo "  ===================================================="
echo ""
read -rp "  Would you like to run a test check now? (Y/n): " TESTRUN
if [ "${TESTRUN:-Y}" != "n" ] && [ "${TESTRUN:-Y}" != "N" ]; then
    echo ""
    echo "  Running test check (dry run — no notifications sent)..."
    echo ""
    findice check-once --dry-run || true
    echo ""
    echo "  Test complete. Check the artifacts/ folder for results."
fi

# ── Scheduling ───────────────────────────────────────────────────────────────
echo ""
echo "  ===================================================="
echo "   Automatic Scheduling (Recommended)"
echo "  ===================================================="
echo ""
echo "  ICEpicks works best when it runs automatically every"
echo "  20 minutes."
echo ""

INTERVAL=20
RUNNER="$SCRIPT_DIR/scripts/run_check.sh"
chmod +x "$RUNNER" 2>/dev/null || true

if [ "$(uname)" = "Darwin" ]; then
    # macOS — launchd
    read -rp "  Set up automatic scheduling via launchd? (Y/n): " SCHEDULE
    if [ "${SCHEDULE:-Y}" != "n" ] && [ "${SCHEDULE:-Y}" != "N" ]; then
        PLIST_LABEL="com.icepicks.check"
        PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
        INTERVAL_SECONDS=$((INTERVAL * 60))

        mkdir -p "$HOME/Library/LaunchAgents"
        cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${RUNNER}</string>
    </array>
    <key>StartInterval</key>
    <integer>${INTERVAL_SECONDS}</integer>
    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/icepicks.log</string>
    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/icepicks.log</string>
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>
</dict>
</plist>
PLIST

        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        launchctl load "$PLIST_PATH"
        echo "  Automatic checks will run every ${INTERVAL} minutes."
    fi
else
    # Linux — cron
    read -rp "  Set up automatic scheduling via cron? (Y/n): " SCHEDULE
    if [ "${SCHEDULE:-Y}" != "n" ] && [ "${SCHEDULE:-Y}" != "N" ]; then
        CRON_LINE="*/${INTERVAL} * * * * ${RUNNER} >> ${SCRIPT_DIR}/icepicks.log 2>&1"
        (crontab -l 2>/dev/null | grep -v "run_check.sh" || true; echo "$CRON_LINE") | crontab -
        echo "  Automatic checks will run every ${INTERVAL} minutes."
        echo "  Verify with: crontab -l"
    fi
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "  ===================================================="
echo "   You're all set!"
echo "  ===================================================="
echo ""
echo "   What happens next:"
echo "     - ICEpicks will check the ICE locator automatically"
echo "     - If a match is found, you'll get a Teams notification"
echo "       (if you configured a webhook URL)"
echo "     - Results are saved in the artifacts/ folder"
echo ""
echo "   Useful commands:"
echo "     source .venv/bin/activate"
echo "     findice check-once            Run a check now"
echo "     findice check-once --dry-run  Test without notifying"
echo "     findice print-config          Show your settings"
echo "     findice setup                 Change settings"
echo ""
echo "   Need help? See README.md or the docs/ folder."
echo ""
