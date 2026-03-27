"""Command-line interface for findICE.

Commands:
  check-once       Run a single multi-attempt ICE locator query.
  check-batch      Run checks for multiple people defined in a YAML file.
  smoke-test       Run the classification pipeline on local fixtures only.
  print-config     Print the resolved config (redacted).
  verify-webhook   Send a test message to the configured Teams webhook.
  classify-sample  Classify a named sample fixture and print the result.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from findICE import __version__
from findICE.logging_utils import configure_logging

# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="findice",
        description=(
            "ICEpicks – ICE Online Detainee Locator monitor.\n"
            "Run 'findice <command> --help' for per-command help."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # --- check-once ---
    p_check = subparsers.add_parser(
        "check-once",
        help="Run a multi-attempt ICE locator check.",
        description="Runs N fresh browser attempts and notifies if a new positive is found.",
    )
    p_check.add_argument(
        "--a-number", metavar="ANUMBER", help="Alien registration number"
    )
    p_check.add_argument("--country", metavar="COUNTRY", help="Country of origin")
    p_check.add_argument("--attempts", type=int, metavar="N", help="Attempts per run")
    p_check.add_argument(
        "--headed", action="store_true", help="Run browser in headed mode"
    )
    p_check.add_argument(
        "--dry-run", action="store_true", help="Skip Teams notification"
    )
    p_check.add_argument(
        "--verbose", "-v", action="store_true", help="Print to console too"
    )
    p_check.add_argument(
        "--log-level", default=None, metavar="LEVEL", help="DEBUG/INFO/WARNING"
    )

    # --- smoke-test ---
    p_smoke = subparsers.add_parser(
        "smoke-test",
        help="Run fixture smoke tests or a live dry-run smoke check.",
        description=(
            "Default mode classifies local fixtures only. "
            "Use --live to run a one-off check with .env config."
        ),
    )
    p_smoke.add_argument(
        "--fixture-dir",
        default=None,
        metavar="DIR",
        help="Override default fixture directory",
    )
    p_smoke.add_argument(
        "--live",
        action="store_true",
        help="Run a live one-off smoke check using .env values (forced dry-run).",
    )
    p_smoke.add_argument(
        "--attempts",
        type=int,
        default=1,
        metavar="N",
        help="Number of attempts for --live mode (default: 1)",
    )
    p_smoke.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode for --live smoke checks",
    )

    # --- print-config ---
    subparsers.add_parser(
        "print-config",
        help="Show the resolved configuration (secrets redacted).",
    )

    # --- verify-webhook ---
    subparsers.add_parser(
        "verify-webhook",
        help="Send a test message to the configured Teams webhook.",
    )

    # --- classify-sample ---
    p_classify = subparsers.add_parser(
        "classify-sample",
        help="Classify a named sample fixture (zero/positive/ambiguous/blocked).",
        description=(
            "Classify a named fixture without running the browser.\n"
            "Valid names: zero, positive, ambiguous, blocked"
        ),
    )
    p_classify.add_argument(
        "sample",
        metavar="SAMPLE",
        nargs="?",
        default=None,
        help="Fixture name: zero | positive | ambiguous | blocked",
    )
    p_classify.add_argument(
        "--list", action="store_true", help="List all available fixture names"
    )

    # --- check-batch ---
    p_batch = subparsers.add_parser(
        "check-batch",
        help="Run checks for multiple people defined in a YAML file.",
        description=(
            "Loads person configs from a YAML file and runs "
            "a full check-once cycle for each person sequentially."
        ),
    )
    p_batch.add_argument(
        "--people",
        metavar="FILE",
        help="Path to people YAML file (default: env PEOPLE_FILE)",
    )
    p_batch.add_argument(
        "--headed", action="store_true", help="Run browser in headed mode"
    )
    p_batch.add_argument(
        "--dry-run", action="store_true", help="Skip Teams notification"
    )
    p_batch.add_argument(
        "--attempts", type=int, metavar="N", help="Override attempts per person"
    )
    p_batch.add_argument(
        "--inter-delay",
        type=float,
        metavar="SECONDS",
        help="Delay between people (default: env or 10s)",
    )
    p_batch.add_argument(
        "--verbose", "-v", action="store_true", help="Print to console too"
    )
    p_batch.add_argument(
        "--log-level", default=None, metavar="LEVEL", help="DEBUG/INFO/WARNING"
    )

    # --- setup ---
    subparsers.add_parser(
        "setup",
        help="Interactive setup wizard — create or update .env configuration.",
        description=(
            "Walks through the required and optional settings and writes "
            "a .env file. Existing values are shown as defaults."
        ),
    )

    return parser


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------


def cmd_check_once(args: argparse.Namespace) -> int:
    from findICE.config import load_config
    from findICE.main import execute_run

    cfg = load_config(
        override_a_number=args.a_number,
        override_country=args.country,
        override_attempts=args.attempts,
        override_headless=not args.headed if args.headed else None,
        override_dry_run=args.dry_run or None,
    )

    log_level = getattr(
        logging, (args.log_level or cfg.log_level).upper(), logging.DEBUG
    )
    configure_logging(level=log_level, a_number=cfg.a_number, log_file=cfg.log_file)

    try:
        cfg.validate()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = execute_run(cfg, verbose_console=getattr(args, "verbose", False))
    facility = ""
    if summary.best_result and summary.best_result.detention_facility:
        facility = f" detention_facility={summary.best_result.detention_facility}"
    print(f"Run complete: best_state={summary.best_state.value}{facility}")
    return 0


def cmd_smoke_test(args: argparse.Namespace) -> int:
    """Run fixture classification smoke tests or a live dry-run smoke check."""
    from findICE.models import ResultState

    if getattr(args, "live", False):
        from findICE.config import load_config
        from findICE.main import execute_run

        cfg = load_config(
            override_attempts=args.attempts,
            override_headless=not args.headed if args.headed else None,
            override_dry_run=True,  # smoke checks must never notify
        )
        log_level = getattr(logging, cfg.log_level.upper(), logging.INFO)
        configure_logging(level=log_level, a_number=cfg.a_number, log_file=cfg.log_file)

        try:
            cfg.validate()
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

        print(
            "Running live smoke test with .env config "
            f"(attempts={cfg.attempts_per_run}, headless={cfg.headless}, dry_run=True)"
        )
        summary = execute_run(cfg, verbose_console=False)
        facility = ""
        if summary.best_result and summary.best_result.detention_facility:
            facility = f" detention_facility={summary.best_result.detention_facility}"
        print(
            f"Live smoke test complete: best_state={summary.best_state.value}{facility}"
        )
        if summary.best_state == ResultState.ERROR:
            return 1
        return 0

    from findICE.classification import classify_page_text

    fixture_dir = (
        Path(args.fixture_dir)
        if args.fixture_dir
        else Path(__file__).parent.parent.parent / "tests" / "fixtures"
    )

    configure_logging(level=logging.INFO)

    expected_states: dict[str, ResultState] = {
        "zero_result": ResultState.ZERO_RESULT,
        "likely_positive": ResultState.LIKELY_POSITIVE,
        "ambiguous": ResultState.AMBIGUOUS_REVIEW,
        "bot_blocked": ResultState.BOT_CHALLENGE_OR_BLOCKED,
    }

    txt_files = sorted(fixture_dir.glob("*.txt"))
    if not txt_files:
        print(f"No fixture .txt files found in {fixture_dir}", file=sys.stderr)
        return 1

    print(f"Running smoke test on {len(txt_files)} fixtures in {fixture_dir}")
    all_passed = True
    for fpath in txt_files:
        text = fpath.read_text(encoding="utf-8")
        state = classify_page_text(text)
        expected = expected_states.get(fpath.stem)
        if expected is None:
            print(f"  {fpath.name:40s}  ->  {state.value} (no expectation)")
            continue
        if state == expected:
            print(f"  {fpath.name:40s}  ->  PASS ({state.value})")
        else:
            all_passed = False
            print(
                f"  {fpath.name:40s}  ->  FAIL "
                f"(expected={expected.value}, got={state.value})"
            )

    if all_passed:
        print("Smoke test complete: all fixture expectations passed.")
        return 0

    print(
        "Smoke test failed: one or more fixtures did not match expectations.",
        file=sys.stderr,
    )
    return 1


def cmd_print_config(args: argparse.Namespace) -> int:
    from findICE.config import load_config

    configure_logging(level=logging.WARNING)
    cfg = load_config()
    print("=== findICE resolved configuration (redacted) ===")
    print(f"  A-Number (masked)  : {cfg.a_number_masked or '(not set)'}")
    print(f"  Country            : {cfg.country or '(not set)'}")
    print(f"  Attempts per run   : {cfg.attempts_per_run}")
    print(f"  Delay (s)          : {cfg.attempt_delay_seconds}")
    print(f"  Jitter (s)         : {cfg.attempt_jitter_seconds}")
    print(f"  Headless           : {cfg.headless}")
    print(f"  Dry-run            : {cfg.dry_run}")
    print(
        f"  Teams webhook      : {'(configured)' if cfg.has_webhook else '(not set)'}"
    )
    print(f"  Artifact dir       : {cfg.artifact_base_dir}")
    print(f"  State file         : {cfg.state_file}")
    print(f"  Log level          : {cfg.log_level}")
    print(f"  Use keyring        : {cfg.use_keyring}")
    return 0


def cmd_verify_webhook(args: argparse.Namespace) -> int:
    from datetime import datetime, timezone

    from findICE.config import load_config
    from findICE.models import NotificationPayload, ResultState
    from findICE.notifications import TeamsNotifier

    configure_logging(level=logging.INFO)
    cfg = load_config()

    if not cfg.has_webhook:
        print("TEAMS_WEBHOOK_URL is not configured.", file=sys.stderr)
        return 1

    payload = NotificationPayload(
        a_number_masked="A-*******99",
        country="TEST",
        state=ResultState.LIKELY_POSITIVE,
        attempts=1,
        hash_prefix="test000000",
        text_preview="This is a connectivity test from ICEpicks verify-webhook.",
        timestamp=datetime.now(timezone.utc),
        run_id="verify-webhook-test",
    )

    notifier = TeamsNotifier(cfg.teams_webhook_url)
    ok = notifier.send(payload)
    if ok:
        print("Webhook test message sent successfully.")
        return 0
    else:
        print("Webhook test FAILED. Check logs for details.", file=sys.stderr)
        return 1


def cmd_classify_sample(args: argparse.Namespace) -> int:
    from findICE.classification import classify_page_text

    configure_logging(level=logging.WARNING)

    fixture_dir = Path(__file__).parent.parent.parent / "tests" / "fixtures"

    # Map friendly names to fixture file stems
    name_map = {
        "zero": "zero_result",
        "zero_result": "zero_result",
        "positive": "likely_positive",
        "likely_positive": "likely_positive",
        "ambiguous": "ambiguous",
        "blocked": "bot_blocked",
        "bot_blocked": "bot_blocked",
    }

    if getattr(args, "list", False):
        print("Available fixture names:")
        for k in sorted(name_map.keys()):
            print(f"  {k}")
        return 0

    if not args.sample:
        print("Provide a sample name. Use --list to see options.", file=sys.stderr)
        return 1

    key = args.sample.lower().strip()
    stem = name_map.get(key)
    if not stem:
        print(
            f"Unknown sample '{args.sample}'. Use --list to see options.",
            file=sys.stderr,
        )
        return 1

    fpath = fixture_dir / f"{stem}.txt"
    if not fpath.exists():
        print(f"Fixture file not found: {fpath}", file=sys.stderr)
        return 1

    text = fpath.read_text(encoding="utf-8")
    state = classify_page_text(text)
    print(f"Sample '{args.sample}' classified as: {state.value}")
    return 0


def cmd_check_batch(args: argparse.Namespace) -> int:
    """Run batch checks for multiple people from a YAML config."""
    from findICE.batch import load_people, execute_batch
    from findICE.config import load_config

    cfg = load_config(
        override_attempts=args.attempts,
        override_headless=not args.headed if args.headed else None,
        override_dry_run=args.dry_run or None,
    )

    log_level = getattr(
        logging, (args.log_level or cfg.log_level).upper(), logging.DEBUG
    )
    configure_logging(level=log_level, a_number="BATCH", log_file=cfg.log_file)

    people_path = Path(args.people) if args.people else cfg.people_file
    if not people_path:
        print(
            "ERROR: No people file specified. Use --people or set PEOPLE_FILE env var.",
            file=sys.stderr,
        )
        return 1

    try:
        people = load_people(people_path)
    except Exception as exc:
        print(f"ERROR loading people file: {exc}", file=sys.stderr)
        return 1

    inter_delay = (
        args.inter_delay
        if args.inter_delay is not None
        else cfg.inter_person_delay_seconds
    )

    print(f"Batch run: {len(people)} people from {people_path}")
    summaries = execute_batch(
        config=cfg,
        people=people,
        inter_person_delay=inter_delay,
        verbose_console=getattr(args, "verbose", False),
    )

    # Print summary table
    print(f"\n{'='*60}")
    print(f"Batch complete: {len(summaries)} of {len(people)} runs finished")
    print(f"{'='*60}")
    for s in summaries:
        label = s.person_label or "unknown"
        facility = ""
        if s.best_result and s.best_result.detention_facility:
            facility = f" facility={s.best_result.detention_facility}"
        print(f"  {label:20s}  {s.best_state.value}{facility}")

    errors = [s for s in summaries if s.best_state.value == "ERROR"]
    if errors:
        return 1
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    """Interactive setup wizard — create or update .env configuration."""
    env_path = Path(".env")

    # Load existing values if .env already exists
    existing: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                existing[key.strip()] = val.strip()
        print(f"Found existing .env — current values shown as defaults.\n")
    else:
        print("No .env file found — creating a new one.\n")

    def _prompt(
        label: str, key: str, *, required: bool = False, hide: bool = False
    ) -> str:
        default = existing.get(key, "")
        display_default = "(configured)" if hide and default else default
        suffix = f" [{display_default}]" if display_default else ""
        while True:
            value = input(f"  {label}{suffix}: ").strip()
            if not value:
                value = default
            if required and not value:
                print(f"    ⚠ {label} is required.")
                continue
            return value

    print("=" * 50)
    print("  ICEpicks Setup Wizard")
    print("=" * 50)

    print("\n── Required ──")
    a_number = _prompt(
        "Alien registration number (A-XXXXXXXXX)", "A_NUMBER", required=True
    )
    country = _prompt("Country of origin (e.g. MEXICO)", "COUNTRY", required=True)

    print("\n── Notifications ──")
    webhook = _prompt("Teams webhook URL (blank = dry-run)", "TEAMS_WEBHOOK_URL")

    print("\n── Run behavior (press Enter for defaults) ──")
    attempts = _prompt("Attempts per run", "ATTEMPTS_PER_RUN") or "4"
    delay = (
        _prompt("Delay between attempts (seconds)", "ATTEMPT_DELAY_SECONDS") or "5.0"
    )
    jitter = _prompt("Random jitter (seconds)", "ATTEMPT_JITTER_SECONDS") or "2.0"
    headless = _prompt("Headless mode (true/false)", "HEADLESS") or "true"
    dry_run = _prompt("Dry run (true/false)", "DRY_RUN") or "false"

    print("\n── Paths (press Enter for defaults) ──")
    artifact_dir = _prompt("Artifact directory", "ARTIFACT_BASE_DIR") or "artifacts"
    state_file = _prompt("State file path", "STATE_FILE") or "state/findice_state.json"

    print("\n── Logging (press Enter for defaults) ──")
    log_level = _prompt("Log level (DEBUG/INFO/WARNING)", "LOG_LEVEL") or "DEBUG"
    log_file = _prompt("Log file path (blank = stderr only)", "LOG_FILE") or ""

    lines = [
        "# ============================================================",
        "# ICEpicks – environment configuration",
        "# Generated by 'findice setup'",
        "# NEVER commit this file to version control.",
        "# ============================================================",
        "",
        "# ----- Required -----",
        f"A_NUMBER={a_number}",
        f"COUNTRY={country}",
        "",
        "# ----- Notification -----",
        f"TEAMS_WEBHOOK_URL={webhook}",
        "",
        "# ----- Run behavior -----",
        f"ATTEMPTS_PER_RUN={attempts}",
        f"ATTEMPT_DELAY_SECONDS={delay}",
        f"ATTEMPT_JITTER_SECONDS={jitter}",
        f"HEADLESS={headless}",
        f"DRY_RUN={dry_run}",
        "",
        "# ----- Paths -----",
        f"ARTIFACT_BASE_DIR={artifact_dir}",
        f"STATE_FILE={state_file}",
        "",
        "# ----- Logging -----",
        f"LOG_LEVEL={log_level}",
        f"LOG_FILE={log_file}",
    ]

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n✓ Configuration saved to {env_path.resolve()}")
    print("  Run 'findice check-once --dry-run' to verify.")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "check-once": cmd_check_once,
        "check-batch": cmd_check_batch,
        "smoke-test": cmd_smoke_test,
        "print-config": cmd_print_config,
        "verify-webhook": cmd_verify_webhook,
        "classify-sample": cmd_classify_sample,
        "setup": cmd_setup,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    sys.exit(handler(args))


if __name__ == "__main__":
    main()
