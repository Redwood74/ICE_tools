@echo off
setlocal enabledelayedexpansion
title ICEpicks Installer
color 0F

echo.
echo  ====================================================
echo    ICEpicks - One-Click Installer for Windows
echo  ====================================================
echo.
echo  This installer will:
echo    1. Check for Python (install if needed)
echo    2. Set up ICEpicks and its dependencies
echo    3. Install the browser used for checking
echo    4. Walk you through configuration
echo.
echo  No admin rights required.
echo  Press Ctrl+C at any time to cancel.
echo.
pause

REM ── Locate this script's directory (= repo root) ──────────────────────────
set "REPO=%~dp0"
cd /d "%REPO%"

REM ── Step 1: Find Python ────────────────────────────────────────────────────
echo.
echo  [Step 1/5] Checking for Python...
echo.

set "PYTHON_CMD="

REM Try 'py -3' first (Python Launcher, usually in PATH on modern Windows)
py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -3"
    goto :python_found
)

REM Try 'python'
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :python_found
)

REM Try 'python3'
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python3"
    goto :python_found
)

REM ── Python not found — try winget ──────────────────────────────────────────
echo  Python was not found on this computer.
echo.

winget --version >nul 2>&1
if %errorlevel% equ 0 (
    echo  Installing Python via Windows Package Manager...
    echo  (This may take a minute or two)
    echo.
    winget install Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        goto :python_manual
    )
    echo.
    echo  ============================================================
    echo   Python was just installed, but this window needs to restart
    echo   to see it. Please CLOSE this window and double-click
    echo   install.bat again.
    echo  ============================================================
    echo.
    pause
    exit /b 0
) else (
    goto :python_manual
)

:python_manual
echo  ============================================================
echo   Please install Python manually:
echo.
echo   1. Go to https://www.python.org/downloads/
echo   2. Click "Download Python 3.12"
echo   3. Run the installer
echo   4. IMPORTANT: Check the box that says
echo      "Add Python to PATH" on the first screen
echo   5. Click "Install Now"
echo   6. When done, close this window and
echo      double-click install.bat again
echo  ============================================================
echo.
pause
exit /b 1

:python_found
for /f "tokens=*" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "PYVER=%%v"
echo  Found: %PYVER%

REM ── Step 2: Create virtual environment ─────────────────────────────────────
echo.
echo  [Step 2/5] Setting up ICEpicks environment...
echo.

if not exist ".venv\Scripts\python.exe" (
    echo  Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if !errorlevel! neq 0 (
        echo.
        echo  ERROR: Could not create virtual environment.
        echo  Make sure Python 3.10 or newer is installed.
        pause
        exit /b 1
    )
    echo  Virtual environment created.
) else (
    echo  Virtual environment already exists — using it.
)

REM ── Step 3: Install dependencies ───────────────────────────────────────────
echo.
echo  [Step 3/5] Installing ICEpicks software...
echo  (This may take a minute on first install)
echo.

.venv\Scripts\python.exe -m pip install --upgrade pip --quiet 2>nul
if !errorlevel! neq 0 (
    echo  WARNING: pip upgrade failed, continuing anyway...
)

.venv\Scripts\pip.exe install -r requirements.txt --quiet
if !errorlevel! neq 0 (
    echo  ERROR: Failed to install dependencies.
    echo  Check your internet connection and try again.
    pause
    exit /b 1
)

.venv\Scripts\pip.exe install -e . --quiet
if !errorlevel! neq 0 (
    echo  ERROR: Failed to install ICEpicks CLI.
    pause
    exit /b 1
)
echo  Software installed successfully.

REM ── Step 4: Install browser ────────────────────────────────────────────────
echo.
echo  [Step 4/5] Installing browser for website checks...
echo.
echo  NOTE: This downloads Chromium (~150 MB). It may take
echo  several minutes on a slow connection. Please wait.
echo.

.venv\Scripts\playwright.exe install chromium
if !errorlevel! neq 0 (
    echo.
    echo  WARNING: Browser installation had issues.
    echo  You can try running this command later:
    echo    .venv\Scripts\playwright.exe install chromium
    echo.
)
echo.
echo  Browser installed.

REM ── Step 5: Configuration ──────────────────────────────────────────────────
echo.
echo  [Step 5/5] Configuration
echo.
echo  You will now be asked a few questions to set up ICEpicks.
echo  You need:
echo    - The person's Alien Registration Number (A-Number)
echo    - Their country of origin
echo    - (Optional) A Microsoft Teams webhook URL
echo.
echo  If you don't have the Teams webhook URL, just press Enter
echo  to skip it — you can add it later.
echo.
pause

.venv\Scripts\findice.exe setup
if !errorlevel! neq 0 (
    echo.
    echo  Configuration had an issue. You can run it again later:
    echo    .venv\Scripts\findice.exe setup
)

REM ── Test run ───────────────────────────────────────────────────────────────
echo.
echo  ====================================================
echo   Installation complete!
echo  ====================================================
echo.
set /p "TESTRUN=  Would you like to run a test check now? (Y/n): "
if /i "%TESTRUN%"=="n" goto :skip_test

echo.
echo  Running test check (dry run — no notifications sent)...
echo.
.venv\Scripts\findice.exe check-once --dry-run
echo.
echo  Test complete. Check the artifacts/ folder for results.
echo.

:skip_test

REM ── Task Scheduler ─────────────────────────────────────────────────────────
echo.
echo  ====================================================
echo   Automatic Scheduling (Recommended)
echo  ====================================================
echo.
echo  ICEpicks works best when it runs automatically every
echo  20 minutes. This requires setting up Windows Task
echo  Scheduler.
echo.
set /p "SCHEDULE=  Set up automatic scheduling? (Y/n): "
if /i "%SCHEDULE%"=="n" goto :skip_schedule

echo.
echo  Setting up Task Scheduler...
set "FINDICE_BG=%REPO%.venv\Scripts\findice-bg.exe"
set "TASK_NAME=ICEpicks_check"

powershell -ExecutionPolicy Bypass -Command ^
    "$action = New-ScheduledTaskAction -Execute '\"%FINDICE_BG%\"' -Argument 'check-once' -WorkingDirectory '%REPO%'; ^
     $trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 20) -Once -At (Get-Date); ^
     $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 15); ^
     Register-ScheduledTask -TaskName '%TASK_NAME%' -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null; ^
     Write-Host '  Task registered successfully.'"

if !errorlevel! neq 0 (
    echo.
    echo  NOTE: Task Scheduler setup requires additional permissions.
    echo  You can set it up manually later. See:
    echo    docs\windows_task_scheduler.md
) else (
    echo.
    echo  Automatic checks will run every 20 minutes.
    echo  You can manage this in Task Scheduler (search for
    echo  "%TASK_NAME%" in the Start menu).
)

:skip_schedule

REM ── Desktop shortcut ───────────────────────────────────────────────────────
echo.
set /p "SHORTCUT=  Create a desktop shortcut for manual checks? (Y/n): "
if /i "%SHORTCUT%"=="n" goto :done

powershell -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $sc = $ws.CreateShortcut([IO.Path]::Combine($ws.SpecialFolders('Desktop'), 'ICEpicks Check.lnk')); ^
     $sc.TargetPath = '%REPO%.venv\Scripts\findice.exe'; ^
     $sc.Arguments = 'check-once'; ^
     $sc.WorkingDirectory = '%REPO%'; ^
     $sc.Description = 'Run ICEpicks detainee locator check'; ^
     $sc.Save(); ^
     Write-Host '  Desktop shortcut created.'"

:done
echo.
echo  ====================================================
echo   You're all set!
echo  ====================================================
echo.
echo   What happens next:
echo     - ICEpicks will check the ICE locator automatically
echo     - If a match is found, you'll get a Teams notification
echo       (if you configured a webhook URL)
echo     - Results are saved in the artifacts\ folder
echo.
echo   Useful commands (open PowerShell in this folder):
echo     .venv\Scripts\findice.exe check-once          Run a check now
echo     .venv\Scripts\findice.exe check-once --dry-run Test without notifying
echo     .venv\Scripts\findice.exe print-config         Show your settings
echo     .venv\Scripts\findice.exe setup                Change settings
echo.
echo   Need help? See README.md or docs\ folder.
echo.
pause
