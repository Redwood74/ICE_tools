# ICEpicks

<img width="1536" height="1024" alt="Designer (6)" src="https://github.com/user-attachments/assets/0246373c-ab44-481b-82c0-3787c4026b77" />

[![CI](https://github.com/Redwood74/ICE_tools/actions/workflows/ci.yml/badge.svg)](https://github.com/Redwood74/ICE_tools/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: IAPL](https://img.shields.io/badge/license-IAPL--1.0-green.svg)](LICENSE.md)

[🇪🇸 Leer en español](README.es.md)

**ICEpicks** is a local automation utility that monitors the
[ICE Online Detainee Locator](https://locator.ice.gov/odls/#/index) for a
specific person by alien registration number (A-number) and country of origin.

> ⚠️ **The ICE locator site is known to return false "0 Search Results" between
> actual results.** ICEpicks runs multiple fresh attempts per scheduled check
> and classifies outcomes conservatively so that you can distinguish a credible
> positive result from site noise.

---

## Quick install (recommended)

**No coding experience required.** Download the project, double-click the
installer, and answer three questions.

### Windows

1. **Download:** go to
   [Code → Download ZIP](https://github.com/Redwood74/ICE_tools/archive/refs/heads/main.zip)
   and save the file.
2. **Extract:** right-click the ZIP → **Extract All** → choose a folder
   (e.g. `C:\ICEpicks`).
3. **Install:** open the extracted folder and **double-click `install.bat`**.
4. Follow the on-screen prompts — you'll need:
   - The person's **A-Number** (alien registration number)
   - Their **country of origin** (exactly as it appears on the ICE site)
   - *(Optional)* a **Microsoft Teams webhook URL** for notifications

The installer handles Python, dependencies, browser, configuration, and
scheduling automatically.

### macOS

1. Download and extract the ZIP (same link above).
2. Open **Terminal**, drag the extracted folder into it, and press Enter.
3. Run: `bash install.command`
4. Follow the prompts.

### Linux

1. Download and extract the ZIP.
2. Open a terminal in the extracted folder.
3. Run: `bash install.command`
4. Follow the prompts.

> **Already have Python experience?** See [Manual setup](#manual-setup-windows)
> below for the traditional `pip install` workflow.

---

## What it does

1. Opens the ICE locator in a headless Chromium browser (via Playwright).
2. Enters the A-number and country, then clicks Search.
3. Repeats up to N times per run, each in a **fresh browser context**.
4. Classifies the result: `ZERO_RESULT`, `LIKELY_POSITIVE`,
   `AMBIGUOUS_REVIEW`, `BOT_CHALLENGE_OR_BLOCKED`, or `ERROR`.
5. Saves screenshots, HTML, and extracted text as local artifacts.
6. Sends a Microsoft Teams notification **only** when a credible new positive
   result appears (deduplication prevents repeated alerts for the same record).

## Why multiple attempts per run?

The ICE locator is a flaky single-page application that frequently returns
`0 Search Results` even when a person is actively detained. Running several
independent attempts (each with a fresh browser session) significantly reduces
the chance of a false negative on any given check.

> **Results are not authoritative.** A `ZERO_RESULT` does not confirm that
> a person is *not* detained. A `LIKELY_POSITIVE` does not replace official
> legal verification. Always review the saved artifacts and cross-reference
> with official sources.

---

## Requirements

- Python 3.10 or newer
- Windows 10/11 (also works on macOS/Linux for development)
- No admin rights required
- No Docker required

---

## Manual setup (Windows)

```powershell
# 1. Clone the repo
git clone https://github.com/Redwood74/ICE_tools.git
cd ICE_tools

# 2. Create and activate a virtualenv
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
pip install -e .          # installs the findice CLI

# 4. Install the Playwright browser
playwright install chromium

# 5. Copy the example config
copy .env.example .env
# Then edit .env and fill in A_NUMBER, COUNTRY, TEAMS_WEBHOOK_URL
```

> See [`docs/windows_task_scheduler.md`](docs/windows_task_scheduler.md) for
> scheduling guidance.

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `A_NUMBER` | ✅ | — | Alien registration number (8–9 digits) |
| `COUNTRY` | ✅ | — | Country of origin as listed in the ICE locator |
| `TEAMS_WEBHOOK_URL` | ☐ | — | Teams incoming webhook URL (blank = dry run) |
| `ATTEMPTS_PER_RUN` | ☐ | `4` | Number of fresh attempts per run |
| `ATTEMPT_DELAY_SECONDS` | ☐ | `5.0` | Seconds between attempts |
| `HEADLESS` | ☐ | `true` | Set `false` to watch the browser |
| `DRY_RUN` | ☐ | `false` | Skip Teams notification |
| `ARTIFACT_BASE_DIR` | ☐ | `artifacts` | Where artifacts are saved |
| `STATE_FILE` | ☐ | `state/findice_state.json` | Deduplication state |
| `LOG_LEVEL` | ☐ | `DEBUG` | `DEBUG` / `INFO` / `WARNING` |

See [`.env.example`](.env.example) for the full list.

---

## CLI usage

```powershell
# Interactive setup wizard — creates/updates .env
findice setup

# Run a check (uses .env config)
findice check-once

# Headed mode for visual debugging
findice check-once --headed

# Dry run (no Teams notification)
findice check-once --dry-run

# Override A-number and country on the command line
findice check-once --a-number A-123456789 --country MEXICO

# Print resolved config (redacted)
findice print-config

# Test Teams webhook connectivity
findice verify-webhook

# Classify a sample fixture (no live ICE query)
findice classify-sample positive
findice classify-sample zero
findice classify-sample ambiguous
findice classify-sample blocked
findice classify-sample --list

# Run smoke test on all local fixtures
findice smoke-test

# Run live smoke test using .env (forced dry-run, no Teams message)
findice smoke-test --live

# Run batch mode for multiple people (uses people.yml)
findice check-batch --dry-run
```

---

## Scheduling

Recommended: run `check-once` every **20 minutes** via Windows Task Scheduler.

See [`docs/windows_task_scheduler.md`](docs/windows_task_scheduler.md) for
step-by-step setup. The helper script [`scripts/run_check.ps1`](scripts/run_check.ps1)
is suitable for use as the Task Scheduler action.

Cross-platform scheduling (cron, launchd, Docker) is documented in
[`docs/scheduling.md`](docs/scheduling.md).

> Do not run more frequently than every 10 minutes; the ICE site may rate-limit
> or block requests. Finite scheduler-driven runs are safer than a forever loop.

---

## Artifact paths

After each run, artifacts are saved to:

```
artifacts/
  run_<TIMESTAMP>/
    attempt_01_<state>.png     # screenshot
    attempt_01_<state>.html    # raw page HTML
    attempt_01_<state>.txt     # extracted text
    run_summary.json           # run metadata and result hash
```

Review artifacts when a result looks suspicious before acting on it.

---

## Notification behavior

- **`LIKELY_POSITIVE`** – sends a Teams notification if the result is new
  (new = content hash not seen in recent runs).
- **`ZERO_RESULT`** – no notification; logs only.
- **`AMBIGUOUS_REVIEW`** – saves artifacts and logs a warning; no notification.
- **`BOT_CHALLENGE_OR_BLOCKED`** – saves artifacts and exits with code `3`.
- **`ERROR`** – saves artifacts and logs; exits non-zero if all attempts fail.

Duplicate-positive suppression is based on a SHA-256 hash of the extracted
page text. The same record will not re-notify until the content changes.

---

## Limitations

- ICEpicks depends entirely on the ICE locator site structure. If ICE changes
  the site DOM, selectors may need updating (see
  [`src/findICE/selectors.py`](src/findICE/selectors.py)). Selector
  self-healing will log warnings when heuristic fallbacks are used.
- A `LIKELY_POSITIVE` result must be manually verified by an attorney or
  qualified legal representative.
- No cloud infrastructure is required or included.
- Docker deployment is available — see [`docs/docker.md`](docs/docker.md).

---

## Legal / license

This software is licensed under the
**ICE Advocacy Public License (IAPL) v1.0** (see [`LICENSE.md`](LICENSE.md)).

**Key points:**

- Source-available, **not** OSI-approved or open source.
- Free for non-commercial advocacy, legal aid, and humanitarian use.
- **Categorically prohibited for immigration enforcement, detention
  operations, surveillance, or any use that materially assists ICE/CBP/DHS
  enforcement activities.**
- Automatic license path available for Public Defenders, Federal Defenders,
  court-appointed counsel, legal aid organizations, and nonprofit immigration
  legal services providers. See [`FAQ.md`](FAQ.md).
- Commercial or media/journalism use requires a separate written license.

See [`FAQ.md`](FAQ.md) for licensing questions and the verification process.

---

## Trademark notice

**ICEpicks** and the **ICEpicks** logo are trademarks of Ray Quinney & Nebeker P.C.
See [`TRADEMARKS.md`](TRADEMARKS.md) for usage policy. The software license
grants no trademark rights.

---

## Ethical / prohibited-use summary

This tool **must not** be used to:

- Assist ICE, CBP, DHS, or any government agency in immigration enforcement
  or detention operations.
- Surveil, track, or monitor individuals for enforcement purposes.
- Facilitate deportation, detention, or removal proceedings against immigrants.

Any use that harms the people this tool is designed to help is a violation of
the license and morally prohibited.

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Security

See [`SECURITY.md`](SECURITY.md) for reporting vulnerabilities.
