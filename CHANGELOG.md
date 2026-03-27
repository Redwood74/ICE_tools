# Changelog

All notable changes to ICEpicks will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added

- Batch (multi-person) monitoring via `check-batch` command and `batch.py`.
- Per-person overrides for attempts, delay, and jitter in `people.yml`.
- Interactive setup wizard (`findice setup`).
- HTML report generation with embedded screenshots (`generate_html_report`).
- Facility detail page and "More Information" tab collection.
- Structured facility tab extraction with phone, email, and link parsing.
- One-click installers: `install.bat` (Windows), `install.command` (macOS/Linux).
- `filelock`-based concurrent access protection on state file.
- Comprehensive test suites: `test_artifacts.py`, `test_batch.py`, expanded
  `test_ice_client.py`, `test_cli.py`, `test_state_store.py`,
  `test_notifications.py`, `test_main.py`.

### Changed

- Dependencies pinned to exact versions in `requirements.txt` /
  `requirements-dev.txt` (loose constraints remain in `requirements.in`).
- State file writes use atomic temp-file + rename pattern (`_save`).
- `BotChallengeError` raised instead of `sys.exit(3)` — batch continues.
- Rotating log handler replaces single-file handler.

### Security

- HTTPS + trusted-domain validation on Teams webhook URLs.
- `html.escape()` replaces custom HTML escaper in reports.
- Artifact directories created with `0700` permissions.
- State file written with `0600` permissions after atomic rename.
- A-number redacted from config validation error messages.
- Docker image runs as non-root user.

### Fixed

- Page resource leak on facility detail collection errors.
- `save_attempt_artifacts` continues after individual artifact failures.

---

## [0.1.0] – 2026-03-27

### Added

- Initial production-ready release.
- `findICE` Python package under `src/findICE/`.
- Core ICE locator automation via Playwright (`ice_client.py`).
- Conservative classification model: `ZERO_RESULT`, `LIKELY_POSITIVE`,
  `AMBIGUOUS_REVIEW`, `BOT_CHALLENGE_OR_BLOCKED`, `ERROR`.
- Multi-attempt fresh-context retry loop with linear + jitter backoff.
- Layered fallback selector resolution (`selectors.py`).
- Pluggable notifier architecture: `TeamsNotifier`, `ConsoleNotifier`,
  `NoOpNotifier`.
- Content-hash-based deduplication to prevent repeat Teams notifications.
- Local artifact saving: screenshot, HTML, extracted text, JSON summary.
- JSON state store for deduplication and run metadata.
- A-number redaction in logs and notifications.
- CLI commands: `check-once`, `smoke-test`, `print-config`,
  `verify-webhook`, `classify-sample`.
- Config precedence: env vars → `.env` → optional keyring.
- Fixture-based classification tests and unit test suite.
- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`.
- `.env.example` with full documentation.
- `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `FAQ.md`.
- `LICENSE.md` – ICE Advocacy Public License (IAPL) v1.0.
- `TRADEMARKS.md` – trademark usage policy.
- `docs/architecture.md`, `docs/windows_task_scheduler.md`,
  `docs/operations.md`, `docs/legal_overview.md`, `docs/email_templates.md`.
- `scripts/setup_windows.ps1`, `scripts/run_check.ps1`.
- GitHub Actions workflow for lint and test.

[Unreleased]: https://github.com/Redwood74/ICE_tools/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Redwood74/ICE_tools/releases/tag/v0.1.0
