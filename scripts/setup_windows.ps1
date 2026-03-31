<#
.SYNOPSIS
    ICEpicks Windows setup script.
    Run this once after cloning the repository on a Windows machine.

.DESCRIPTION
    Creates a Python virtualenv, installs dependencies, installs the
    Playwright Chromium browser, and sets up a Task Scheduler task.

.NOTES
    Run from the ICEpicks repository root with PowerShell 5.1 or later.
    Does NOT require admin rights.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot | Split-Path -Parent
$venvPath = Join-Path $repoRoot ".venv"

Write-Host "=== ICEpicks Windows Setup ===" -ForegroundColor Cyan
Write-Host "Repo root: $repoRoot"

# ── Step 1: Check Python ────────────────────────────────────────────────────
Write-Host "`n[1/5] Checking Python version..."
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Error "Python 3.10+ is required but was not found in PATH. Install it from https://python.org"
    exit 1
}
$pythonVersion = & $pythonCmd.Name --version 2>&1
Write-Host "Found: $pythonVersion"

# ── Step 2: Create virtualenv ───────────────────────────────────────────────
Write-Host "`n[2/5] Creating virtualenv at $venvPath..."
if (Test-Path $venvPath) {
    Write-Host "  Virtualenv already exists – skipping creation."
} else {
    & $pythonCmd.Name -m venv $venvPath
    Write-Host "  Virtualenv created."
}

$pip = Join-Path $venvPath "Scripts\pip.exe"
$activate = Join-Path $venvPath "Scripts\Activate.ps1"

# ── Step 3: Install dependencies ────────────────────────────────────────────
Write-Host "`n[3/5] Installing dependencies..."
& $pip install --upgrade pip --quiet
& $pip install -r (Join-Path $repoRoot "requirements.txt") --quiet
& $pip install -e $repoRoot --quiet
Write-Host "  Dependencies installed."

# ── Step 4: Install Playwright browser ──────────────────────────────────────
Write-Host "`n[4/5] Installing Playwright Chromium browser..."
$playwright = Join-Path $venvPath "Scripts\playwright.exe"
& $playwright install chromium
Write-Host "  Playwright Chromium installed."

# ── Step 5: Copy .env.example if no .env exists ─────────────────────────────
Write-Host "`n[5/5] Checking .env..."
$envFile = Join-Path $repoRoot ".env"
$envExample = Join-Path $repoRoot ".env.example"
if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "  .env created from .env.example. Edit it now:"
    Write-Host "    notepad $envFile" -ForegroundColor Yellow
} else {
    Write-Host "  .env already exists – not overwriting."
}

# ── Task Scheduler registration (optional) ──────────────────────────────────
Write-Host "`n[Optional] Registering Task Scheduler task..."
$registerTask = Read-Host "Register ICEpicks_check in Task Scheduler? (y/N)"
if ($registerTask -eq "y" -or $registerTask -eq "Y") {
    $taskName = "ICEpicks_check"
    $findiceBg = Join-Path $repoRoot ".venv\Scripts\findice-bg.exe"
    $action = New-ScheduledTaskAction `
        -Execute $findiceBg `
        -Argument "check-once" `
        -WorkingDirectory $repoRoot

    $trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 20) -Once -At (Get-Date)
    $settings = New-ScheduledTaskSettingsSet `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -RunLevel Limited `
        -Force | Out-Null

    Write-Host "  Task '$taskName' registered." -ForegroundColor Green
    Write-Host "  Open Task Scheduler to verify and adjust the trigger if needed."
}

Write-Host "`n=== Setup complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Edit .env:  notepad .env" -ForegroundColor Yellow
Write-Host "  2. Test run:   $activate ; findice smoke-test" -ForegroundColor Yellow
Write-Host "  3. Dry run:    $activate ; findice check-once --dry-run" -ForegroundColor Yellow
