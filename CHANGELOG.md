# Changelog

All notable changes to ICEpicks will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.1.0] – 2024

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
