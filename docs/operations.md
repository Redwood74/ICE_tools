# Operations Guide — ICEpicks

---

## Day-to-day operations

### Reviewing artifacts after a run

Each run saves artifacts to `artifacts/run_<TIMESTAMP>/`. Open the folder
to find:

- `attempt_01_<state>.png` – screenshot at the time of classification
- `attempt_01_<state>.html` – full page HTML
- `attempt_01_<state>.txt` – extracted visible text
- `run_summary.json` – machine-readable summary (states, timestamps, hashes)

If a result looks suspicious, open the `.html` file in a browser and compare
with a manual search on the ICE locator.

### Understanding result states

| State | Meaning | What to do |
|---|---|---|
| `ZERO_RESULT` | Site said 0 results | Note the time; check again later |
| `LIKELY_POSITIVE` | Page shows detainee indicators | Verify manually; contact attorney |
| `AMBIGUOUS_REVIEW` | Page loaded but unclear | Review `.html` artifact; retry |
| `BOT_CHALLENGE_OR_BLOCKED` | CAPTCHA / rate limit | Wait; review screenshot |
| `ERROR` | Browser/network failure | Check logs; retry |

A `ZERO_RESULT` does **not** confirm that the person is not detained.
A `LIKELY_POSITIVE` must be verified by a licensed attorney before acting.

### Testing without spamming Teams

Use `--dry-run` or set `DRY_RUN=true` in `.env`:

```powershell
findice check-once --dry-run
```

This runs all attempts and saves artifacts but sends no Teams notification.

For a quick `.env`-driven smoke check, run:

```powershell
findice smoke-test --live
```

Live smoke mode always forces dry-run, so it never sends a Teams alert.

Alternatively, `verify-webhook` sends a single test message:

```powershell
findice verify-webhook
```

### Running a manual one-off check

```powershell
# Activate virtualenv first
.venv\Scripts\Activate.ps1

# Run with default config
findice check-once

# Run headed (watch the browser)
findice check-once --headed

# Override A-number and country
findice check-once --a-number A-123456789 --country MEXICO
```

### Checking the current config

```powershell
findice print-config
```

A-numbers and webhook URLs are redacted in the output.

---

## Handling specific scenarios

### Bot challenge / CAPTCHA (exit code 3)

If the ICE site challenges the browser:
1. Check the screenshot in `artifacts/run_<TIMESTAMP>/attempt_01_bot_challenge_or_blocked.png`.
2. Wait at least 30–60 minutes before retrying.
3. Consider increasing `ATTEMPT_DELAY_SECONDS` in `.env`.
4. If it recurs, the ICE site may have changed its bot detection; check for
   selector or user-agent updates.

### Persistent AMBIGUOUS_REVIEW results

If multiple runs return `AMBIGUOUS_REVIEW`:
1. Open the `.html` artifact and inspect the page manually.
2. Check if the page is loading correctly (e.g., JavaScript errors).
3. Try a headed run: `findice check-once --headed`.
4. Review selectors in `src/findICE/selectors.py`.

### Site DOM change / selectors broken

Symptoms: all attempts return `ERROR` or `AMBIGUOUS_REVIEW` with very short
extracted text.

1. Run headed: `findice check-once --headed`.
2. Open browser DevTools on the ICE locator page.
3. Identify the new selector for the A-number input, country select, and
   search button.
4. Edit `src/findICE/selectors.py` – add new candidates at the TOP of each
   `SelectorGroup.candidates` list.
5. Run `pytest` and `findice smoke-test` to verify nothing is broken.

### Updating the Teams webhook

1. Generate a new incoming webhook URL in Teams.
2. Update `TEAMS_WEBHOOK_URL` in `.env`.
3. Test with `findice verify-webhook`.

---

## Artifact retention

Artifacts grow over time. Recommended retention: 30–90 days depending on
the case. To clean up:

```powershell
# Delete run directories older than 30 days
Get-ChildItem -Path artifacts -Directory |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
  Remove-Item -Recurse -Force
```

The state file (`state/findice_state.json`) should be preserved as long
as you want deduplication to work across sessions. It is small (< 10 KB)
and safe to keep indefinitely.

---

## Incident response

### False positive (LIKELY_POSITIVE that is not real)

1. Open the `.html` artifact and compare with a manual ICE locator search.
2. If confirmed false positive, make a note in your case records.
3. The dedup hash will suppress repeat notifications for the same content.
4. Report the pattern at `licensing.icepicks@rqn.com` if it recurs.

### Missed notification

1. Check `state/findice_state.json` – the `last_positive_hash` field shows
   what was last sent.
2. Check `artifacts/` for the relevant run and review the summary.
3. If the content hash matches a prior notification, dedup suppression is
   working correctly.

### Scheduled task not running

1. Open Task Scheduler and check "Last Run Result" for `ICEpicks_check`.
2. Common causes: virtualenv path changed, script path wrong, Playwright
   browsers moved.
3. Run `scripts\run_check.ps1` manually in PowerShell to see the error.

---

## Privacy and security reminders

- Do not commit `.env` to version control.
- Do not share `artifacts/` directories publicly; they contain A-numbers
  and personal locator data.
- Rotate the Teams webhook URL if it is accidentally exposed.
- A-numbers are masked in logs but present in artifact HTML/text files.
  Protect the `artifacts/` directory accordingly.
