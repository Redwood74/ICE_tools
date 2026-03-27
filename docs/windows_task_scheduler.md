# Windows Task Scheduler Setup — ICEpicks

This guide explains how to schedule ICEpicks to run every 20 minutes using
Windows Task Scheduler. No admin rights are required for basic setup.

---

## Prerequisites

Complete the local setup from [`README.md`](../README.md) first:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
playwright install chromium
copy .env.example .env
# Edit .env with your A_NUMBER, COUNTRY, and optionally TEAMS_WEBHOOK_URL
```

Verify the setup works manually before scheduling:

```powershell
findice smoke-test
findice print-config
findice check-once --dry-run
```

---

## Quick setup using the provided script

```powershell
# From the ICEpicks directory, with .venv activated:
.\scripts\setup_windows.ps1
```

This script registers a Task Scheduler task named **ICEpicks_check** that
runs every 20 minutes using `scripts\run_check.ps1`.

Review and edit `scripts\setup_windows.ps1` if you need to change the
schedule or working directory.

---

## Manual setup (Task Scheduler GUI)

1. Open **Task Scheduler** (search for it in the Start menu).

2. Click **Create Task** (not "Create Basic Task" — you need the full dialog).

3. **General tab:**
   - Name: `ICEpicks_check`
   - Description: `ICEpicks – ICE locator monitor`
   - Check **"Run whether user is logged on or not"** (optional, requires
     saving credentials)
   - Uncheck **"Run with highest privileges"** (not required)

4. **Triggers tab → New:**
   - Begin the task: **On a schedule**
   - Settings: **Daily**
   - Repeat task every: **20 minutes** (select from dropdown)
   - For a duration of: **Indefinitely**
   - Click OK.

5. **Actions tab → New:**
   - Action: **Start a program**
   - Program/script:
     ```
     powershell.exe
     ```
   - Add arguments:
     ```
     -ExecutionPolicy Bypass -File "C:\path\to\ICEpicks\scripts\run_check.ps1"
     ```
   - Start in:
     ```
     C:\path\to\ICEpicks
     ```
   - Replace `C:\path\to\ICEpicks` with the actual path to your repo.

6. **Conditions tab:**
   - Uncheck **"Start the task only if the computer is on AC power"** if
     you want it to run on battery.
   - Optionally check **"Wake the computer to run this task"** (requires
     admin rights).

7. **Settings tab:**
   - Check **"If the task is already running, do not start a new instance"**
     (important: prevents overlapping runs).
   - Run task as soon as possible after a scheduled start is missed: your
     preference.

8. Click **OK** and enter your Windows password if prompted.

---

## Verifying the schedule

In Task Scheduler, right-click **ICEpicks_check** → **Run** to test
immediately. Check:

- The `artifacts/` directory for a new run folder.
- The Teams channel (if configured) for a test message.
- Log output in the run folder.

---

## Why scheduled runs instead of a forever loop?

- **Finite runs are safer.** A loop that crashes or hangs cannot be easily
  inspected; a scheduled task that completes cleanly is much easier to
  monitor.
- **Rate limiting.** Hammering the ICE site risks getting your IP blocked.
  20-minute intervals are conservative enough to avoid this.
- **Restartability.** If the machine reboots, the Task Scheduler resumes
  automatically without you needing to restart a background process.
- **Inspectability.** Each run leaves a dated artifact directory, making
  it easy to review the history.

---

## Managing artifact growth

Each run creates a new subdirectory under `artifacts/`. Over time these can
accumulate. Options:

1. **Manual cleanup:** Delete old run directories periodically.
2. **Retention script:** Add a cleanup step to `scripts\run_check.ps1` that
   deletes run directories older than N days:
   ```powershell
   Get-ChildItem -Path artifacts -Directory |
     Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
     Remove-Item -Recurse -Force
   ```

---

## Stopping the schedule

To disable: right-click **ICEpicks_check** in Task Scheduler → **Disable**.
To delete: right-click → **Delete**.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Task shows "Last Run Result: 0x1" | Script path wrong or virtualenv not activated | Check the path in the Action; run manually first |
| Task runs but no artifacts appear | Working directory wrong | Set "Start in" to the repo root |
| Browser fails to launch | Playwright browsers not installed | Run `playwright install chromium` |
| Teams notification not sent | Webhook URL missing or wrong | Check `.env` and run `findice verify-webhook` |
| Exit code 3 | Bot challenge / CAPTCHA | Wait and retry; check `artifacts/` for screenshot |
