# Contributing to ICEpicks

Thank you for considering contributing to ICEpicks. This project exists to
help people dealing with the ICE Online Detainee Locator. Contributions that
improve reliability, accuracy, and accessibility are welcome.

---

## Before you start

- Read [`LICENSE.md`](LICENSE.md). By contributing, you agree that your
  contributions will be licensed under the IAPL v1.0.
- Read [`SECURITY.md`](SECURITY.md) before reporting vulnerabilities.
- Review the existing issues and pull requests to avoid duplication.

---

## What to contribute

Contributions are welcome in these areas:

- **Bug fixes** – especially selector issues when the ICE site DOM changes
- **Classification improvements** – more reliable phrase detection
- **Test coverage** – additional unit and fixture-based tests
- **Documentation** – clarity, corrections, Windows-specific guidance
- **Notification backends** – e.g., email, Slack (must follow the pluggable
  notifier pattern in `notifications.py`)

Please **do not** contribute features that:

- Add cloud infrastructure or external service dependencies without strong
  justification
- Collect or transmit A-numbers or personal data to any external service
- Could enable enforcement, surveillance, or other prohibited uses

---

## Development setup

```bash
git clone https://github.com/Redwood74/ICEpicks.git
cd ICEpicks
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\Activate.ps1      # Windows PowerShell
pip install -r requirements-dev.txt
pip install -e .
playwright install chromium
```

---

## Running tests

```bash
# All non-live tests
pytest

# With coverage
pytest --cov=findICE --cov-report=term-missing

# Smoke test on local fixtures (no browser, no ICE site)
findice smoke-test
```

Live tests that require a real ICE site connection are marked `@pytest.mark.live`
and are excluded from normal CI runs. Run them manually:

```bash
pytest -m live
```

---

## Code style

This project uses `ruff` for linting and formatting:

```bash
ruff check src/ tests/
ruff format src/ tests/
```

Type hints are expected in all new code. Run mypy:

```bash
mypy src/
```

---

## Pull request checklist

Before submitting a pull request:

- [ ] Tests pass: `pytest`
- [ ] Linter passes: `ruff check src/ tests/`
- [ ] Type hints added for new functions/methods
- [ ] Documentation updated if behavior changed
- [ ] No hard-coded secrets or A-numbers
- [ ] No changes that would enable prohibited uses

---

## Selector updates

When the ICE site DOM changes and selectors break:

1. Run a check with `--headed` to watch the browser.
2. Inspect the saved HTML artifact in `artifacts/`.
3. Update `src/findICE/selectors.py` – add new candidates at the top of
   the relevant `SelectorGroup.candidates` list.
4. Run `findice smoke-test` and the test suite.
5. Open a PR with a clear description of what changed and why.

---

## Legal

By submitting a pull request, you:

- Certify that your contribution is your original work or that you have the
  right to submit it.
- Agree to license your contribution under the IAPL v1.0.
- Confirm that your contribution does not introduce functionality that would
  enable any prohibited use.

---

*Questions? Open an issue or email licensing.icepicks@rqn.com.*
