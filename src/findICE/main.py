"""Main orchestration logic for a single findICE run.

This module coordinates:
  - artifact directory creation
  - multi-attempt ICE locator queries
  - state deduplication
  - notification dispatch
  - run summary persistence
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

from findICE.artifacts import (
    generate_html_report,
    generate_run_id,
    make_run_dir,
    save_run_summary,
)
from findICE.classification import best_state_from_run
from findICE.config import AppConfig
from findICE.exceptions import BotChallengeError
from findICE.ice_client import run_with_retries
from findICE.models import ResultState, RunSummary
from findICE.notifications import (
    build_notification_payload,
    build_notifier,
)
from findICE.state_store import StateStore

logger = logging.getLogger(__name__)


def execute_run(
    config: AppConfig,
    run_id: str | None = None,
    verbose_console: bool = False,
) -> RunSummary:
    """Execute a complete multi-attempt ICE locator run.

    Args:
        config: Validated AppConfig.
        run_id: Override the auto-generated run identifier.
        verbose_console: If True, also print notifications to stdout.

    Returns:
        RunSummary describing the entire run.
    """
    if run_id is None:
        run_id = generate_run_id()

    logger.info("Run %s started", run_id)
    config.log_summary()

    run_dir = make_run_dir(config.artifact_base_dir, run_id)
    state_store = StateStore(
        config.state_file,
        retention_hours=config.timeline_retention_hours,
    )
    notifiers = build_notifier(
        webhook_url=config.teams_webhook_url,
        dry_run=config.dry_run,
        verbose_console=verbose_console,
    )

    summary = RunSummary(
        a_number_masked=config.a_number_masked,
        country=config.country,
        attempts_total=config.attempts_per_run,
        best_state=ResultState.ERROR,
        best_result=None,
        started_at=datetime.now(timezone.utc),
        artifact_dir=str(run_dir),
    )

    try:
        results = run_with_retries(
            a_number=config.a_number,
            country=config.country,
            attempts=config.attempts_per_run,
            delay_seconds=config.attempt_delay_seconds,
            jitter_seconds=config.attempt_jitter_seconds,
            headless=config.headless,
            page_load_timeout_ms=config.page_load_timeout_ms,
            element_timeout_ms=config.element_timeout_ms,
            run_dir=run_dir,
            save_screenshots=True,
        )
    except Exception as exc:
        logger.error("Unexpected error during run: %s", exc)
        summary.best_state = ResultState.ERROR
        summary.completed_at = datetime.now(timezone.utc)
        state_store.record_run(
            summary.to_dict(),
            run_id=run_id,
            state_value=summary.best_state.value,
        )
        return summary

    summary.all_states = [r.state for r in results]
    summary.best_state = best_state_from_run(summary.all_states)

    # Identify the best individual result for notification
    for r in results:
        if r.state == summary.best_state:
            summary.best_result = r
            break

    summary.completed_at = datetime.now(timezone.utc)
    logger.info(
        "Run %s complete – best_state=%s attempts=%d",
        run_id,
        summary.best_state.value,
        len(results),
    )

    # --- Notification logic ---
    def _persist() -> None:
        """Save run summary and record run state – called on every exit path."""
        save_run_summary(summary, run_dir / "run_summary.json")
        generate_html_report(summary, run_dir)
        content_hash = summary.best_result.content_hash if summary.best_result else None
        state_store.record_run(
            summary.to_dict(),
            run_id=run_id,
            state_value=summary.best_state.value,
            content_hash=content_hash,
        )
        # Auto-purge old artifacts outside the retention window
        state_store.purge_old_artifacts(config.artifact_base_dir)

    if summary.best_state == ResultState.BOT_CHALLENGE_OR_BLOCKED:
        logger.error(
            "Bot challenge detected – saving artifacts and exiting with code %d",
            BotChallengeError.EXIT_CODE,
        )
        _persist()
        sys.exit(BotChallengeError.EXIT_CODE)

    if summary.best_state == ResultState.LIKELY_POSITIVE and summary.best_result:
        content_hash = summary.best_result.content_hash
        if state_store.is_new_positive(content_hash):
            logger.info("New LIKELY_POSITIVE result – dispatching notification")
            payload = build_notification_payload(
                a_number_masked=config.a_number_masked,
                country=config.country,
                result=summary.best_result,
                attempts=len(results),
                run_id=run_id,
            )
            success = all(n.send(payload) for n in notifiers)
            if success:
                if config.has_webhook and not config.dry_run:
                    state_store.record_positive_sent(content_hash)
                    summary.notified = True
                    logger.info("Notification sent and hash recorded")
                else:
                    logger.info(
                        "Notification path is dry-run/no-webhook; hash not recorded"
                    )
            else:
                logger.warning("One or more notifiers failed")
        else:
            logger.info(
                "LIKELY_POSITIVE but hash %s already seen – skipping notification",
                summary.best_result.hash_prefix,
            )

    elif summary.best_state == ResultState.AMBIGUOUS_REVIEW:
        logger.warning(
            "Result is AMBIGUOUS_REVIEW – artifacts saved to %s for manual inspection",
            run_dir,
        )

    elif summary.best_state == ResultState.ZERO_RESULT:
        logger.info("ZERO_RESULT across all attempts – no notification sent")

    elif summary.best_state == ResultState.ERROR:
        logger.warning(
            "All attempts resulted in ERROR – check artifacts at %s", run_dir
        )

    _persist()

    return summary
