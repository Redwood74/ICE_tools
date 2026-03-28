# Architecture — ICEpicks

## Overview

ICEpicks is a modular Python application structured around a clear separation
of concerns. The main execution flow is:

```
CLI entry point (cli.py)
  → load config (config.py)
  → validate
  → execute_run (main.py)
      → create run directory (artifacts.py)
      → run_with_retries (ice_client.py)
          → [for each attempt]
          → launch fresh browser context (Playwright)
          → navigate to ICE locator
          → resolve selectors (selectors.py)
          → fill form, click search
          → wait for result
          → extract text
          → classify (classification.py)
          → save artifacts (artifacts.py)
          → close context
      → determine best_state (classification.py)
      → check dedup (state_store.py)
      → dispatch notification (notifications.py)
      → save run summary (artifacts.py)
      → record run (state_store.py)
```

---

## Module responsibilities

| Module | Responsibility |
|---|---|
| `cli.py` | Argument parsing; entry point dispatch |
| `main.py` | Run orchestration; ties all modules together |
| `config.py` | Config loading, validation, env/dotenv/keyring |
| `models.py` | Data classes: SearchResult, RunSummary, NotificationPayload |
| `selectors.py` | Centralised selector groups with fallback resolution |
| `ice_client.py` | Playwright automation; fresh-context search loop |
| `classification.py` | Text-based result classification |
| `notifications.py` | Pluggable notifiers: Teams, Console, NoOp |
| `state_store.py` | JSON-backed dedup state and run metadata |
| `artifacts.py` | Local file saving: screenshot, HTML, text, JSON |
| `logging_utils.py` | Structured logging; A-number redaction |
| `exceptions.py` | Custom exception hierarchy |

---

## Data flow

```
A-number + country
    │
    ▼
ice_client.run_with_retries()
    │
    ▼ (per attempt)
Playwright browser context
    │
    ▼
page text → classification.classify_page_text()
    │
    ▼
SearchResult(state, raw_text, hash, paths)
    │
    ▼
artifacts.save_attempt_artifacts()   ← screenshot, HTML, text
    │
    ▼
classification.best_state_from_run()
    │
    ▼
state_store.is_new_positive()
    │
    ▼ (if new LIKELY_POSITIVE)
notifications.TeamsNotifier.send()
    │
    ▼
state_store.record_positive_sent()
    │
    ▼
artifacts.save_run_summary()
state_store.record_run()
```

---

## Key design decisions

### Fresh browser context per attempt

The ICE locator is a stateful SPA. Reusing a tab or session can cause stale
results to persist. A fresh `browser.new_context()` per attempt is the
cleanest way to guarantee independence between attempts.

### Conservative classification

The classifier does not try to force a binary yes/no. The five-state model
lets the caller (and the human reviewing artifacts) make informed decisions
rather than acting on an automatic binary.

### Content-hash deduplication

Deduplication is based on a SHA-256 hash of normalised page text, not on
metadata. This means that if the same person is at the same facility with
the same status, one notification is sent. If anything changes (facility,
status, book-in date), the hash changes and a new notification is sent.

### Pluggable notifiers

The `Notifier` protocol means adding a new channel (email, Slack, etc.)
requires only implementing `send(payload) -> bool` and adding it to
`build_notifier()`. No changes to `main.py` required.

### No external database

A JSON state file is sufficient for v1. It is human-readable, easy to
inspect, and requires no setup. SQLite would add overhead without benefit
at this scale.

---

## Selector strategy

Selectors in `selectors.py` follow a four-layer fallback:

1. **ARIA label** – most stable; used if the site has accessible labels
2. **Placeholder text** – input attributes are usually stable
3. **ARIA role + name** – framework-generated but often stable
4. **CSS fallback** – position-based; last resort

When the ICE site changes, update `selectors.py` first. The layered approach
means a single change at the right level fixes all fallbacks below it.

---

## Extending ICEpicks

### Adding a new notifier

1. Create a class with a `send(payload: NotificationPayload) -> bool` method.
2. Add it to `build_notifier()` in `notifications.py`.
3. Expose the toggle in `config.py` and `.env.example`.

### Adding a new CLI command

1. Add a subparser in `cli._build_parser()`.
2. Implement `cmd_<name>(args) -> int` returning an exit code.
3. Add to the `dispatch` dict in `cli.main()`.
4. Document in `README.md`.

### Batch (multi-person) support

Not implemented in v1. The clean approach would be:
- A YAML/JSON config file listing multiple (A-number, country) pairs
- A `check-batch` command in `cli.py`
- Per-person state stores and artifact directories
- Careful rate-limit management

---

## Directory layout

```
ICEpicks/
├── src/
│   └── findICE/
│       ├── __init__.py
│       ├── cli.py
│       ├── main.py
│       ├── config.py
│       ├── models.py
│       ├── selectors.py
│       ├── ice_client.py
│       ├── classification.py
│       ├── notifications.py
│       ├── state_store.py
│       ├── artifacts.py
│       ├── logging_utils.py
│       └── exceptions.py
├── tests/
│   ├── fixtures/
│   │   ├── zero_result.txt
│   │   ├── likely_positive.txt
│   │   ├── ambiguous.txt
│   │   └── bot_blocked.txt
│   ├── test_classification.py
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_notifications.py
│   ├── test_redaction.py
│   ├── test_selectors.py
│   └── test_state_store.py
├── docs/
├── scripts/
├── artifacts/        ← created at runtime, git-ignored
├── state/            ← created at runtime, git-ignored
└── ...
```
