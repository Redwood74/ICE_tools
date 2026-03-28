# Scheduling ICEpicks

ICEpicks is designed to be run at regular intervals by your operating
system's scheduler. This page covers setup for all supported platforms.

> **Recommended interval:** every 20 minutes. Do not run more frequently
> than every 10 minutes — the ICE site may rate-limit or block requests.

---

## Windows (Task Scheduler)

The recommended approach is to use the Windows Task Scheduler.
See [`windows_task_scheduler.md`](windows_task_scheduler.md)
for full step-by-step instructions, or run:

```powershell
.\scripts\setup_windows.ps1
```

The setup script creates the virtualenv, installs dependencies, and
optionally registers a Task Scheduler job.

**Manual registration** (if you prefer):

```powershell
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -File .\scripts\run_check.ps1" `
    -WorkingDirectory (Get-Location)

$trigger = New-ScheduledTaskTrigger `
    -RepetitionInterval (New-TimeSpan -Minutes 20) `
    -Once -At (Get-Date)

Register-ScheduledTask `
    -TaskName "ICEpicks_check" `
    -Action $action `
    -Trigger $trigger `
    -RunLevel Limited
```

---

## Linux (cron)

Run the setup script:

```bash
chmod +x scripts/setup_cron.sh
./scripts/setup_cron.sh
```

The script creates the virtualenv, installs dependencies, and optionally
registers a cron job.

**Manual registration**:

```bash
# Open crontab editor
crontab -e

# Add this line (runs every 20 minutes):
*/20 * * * * /path/to/ICEpicks/scripts/run_check.sh >> /path/to/ICEpicks/icepicks_cron.log 2>&1
```

Make sure `run_check.sh` is executable:

```bash
chmod +x scripts/run_check.sh
```

---

## macOS (launchd)

Run the setup script:

```bash
chmod +x scripts/setup_launchd.sh
./scripts/setup_launchd.sh
```

The script creates the virtualenv, installs dependencies, and optionally
registers a LaunchAgent that runs every 20 minutes.

**Manual registration** — create
`~/Library/LaunchAgents/com.icepicks.check.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.icepicks.check</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/ICEpicks/scripts/run_check.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>1200</integer>
    <key>WorkingDirectory</key>
    <string>/path/to/ICEpicks</string>
</dict>
</plist>
```

Then load it:

```bash
launchctl load ~/Library/LaunchAgents/com.icepicks.check.plist
```

---

## Docker

See [`docker.md`](docker.md) for Docker deployment. For scheduled execution
with Docker, use host-based scheduling (cron / Task Scheduler) to invoke
`docker run` at the desired interval.

---

## Custom interval

Set the `SCHEDULE_INTERVAL_MINUTES` environment variable before running
the setup scripts to change the default 20-minute interval:

```bash
SCHEDULE_INTERVAL_MINUTES=30 ./scripts/setup_cron.sh
```

On Windows, adjust the `-RepetitionInterval` parameter in Task Scheduler.

---

## Tips

- **Check the exit code**: exit 0 = success, exit 3 = bot challenge (wait),
  exit 1 = error (check logs).
- **Stagger multiple people**: use `check-batch` for multi-person monitoring
  instead of separate scheduler tasks. Built-in inter-person delay avoids
  rapid sequential requests.
- **Log rotation**: the shell scripts append to a log file. Consider
  `logrotate` (Linux) or periodic cleanup to avoid unbounded growth.
