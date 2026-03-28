<#
.SYNOPSIS
    ICEpicks scheduled check runner.
    Called by Windows Task Scheduler every 20 minutes.

.DESCRIPTION
    Activates the virtualenv, runs findice check-once, and exits.
    Designed to be safe for repeated automated execution.

.NOTES
    Run from the ICEpicks repository root.
    Exit code 3 means bot challenge; handled gracefully.
#>

Set-StrictMode -Version Latest

# Resolve repo root relative to this script
$repoRoot = $PSScriptRoot | Split-Path -Parent
$venvActivate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"
$findice = Join-Path $repoRoot ".venv\Scripts\findice.exe"

# ── Activate virtualenv ──────────────────────────────────────────────────────
if (-not (Test-Path $venvActivate)) {
    Write-Error "Virtualenv not found at $venvActivate. Run scripts\setup_windows.ps1 first."
    exit 1
}
. $venvActivate

# ── Change to repo root ──────────────────────────────────────────────────────
Set-Location $repoRoot

# ── Run check ───────────────────────────────────────────────────────────────
Write-Host "[$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')] ICEpicks check starting..."

& $findice check-once
$exitCode = $LASTEXITCODE

if ($exitCode -eq 3) {
    Write-Warning "Bot challenge or block detected (exit code 3). Artifacts saved. Will retry at next scheduled interval."
} elseif ($exitCode -ne 0) {
    Write-Warning "findice exited with code $exitCode. Check artifacts and logs."
} else {
    Write-Host "Check complete (exit code 0)."
}

exit $exitCode
