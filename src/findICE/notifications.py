"""Notification backends for findICE.

Supported notifiers:
  - TeamsNotifier  – posts to a Microsoft Teams incoming webhook
  - ConsoleNotifier – prints to stdout (useful for dry-run / testing)

Pluggable design: both implement the Notifier protocol so you can swap
or chain them without touching the call sites.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Protocol

from findICE.models import NotificationPayload

logger = logging.getLogger(__name__)

_TEAMS_CONTENT_TYPE = "application/json"
_TEAMS_TIMEOUT_SECONDS = 15


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class Notifier(Protocol):
    """Protocol that all notifier implementations must satisfy."""

    def send(self, payload: NotificationPayload) -> bool:
        """Send a notification.  Returns True on success, False on failure."""
        ...


# ---------------------------------------------------------------------------
# Teams notifier
# ---------------------------------------------------------------------------


class TeamsNotifier:
    """Send a message card to a Microsoft Teams incoming webhook."""

    def __init__(self, webhook_url: str) -> None:
        if not webhook_url:
            raise ValueError("webhook_url must not be empty")
        self.webhook_url = webhook_url

    def send(self, payload: NotificationPayload) -> bool:
        card = payload.to_teams_card()
        body = json.dumps(card).encode("utf-8")

        req = urllib.request.Request(
            self.webhook_url,
            data=body,
            headers={"Content-Type": _TEAMS_CONTENT_TYPE},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=_TEAMS_TIMEOUT_SECONDS) as resp:
                status = resp.status
                response_body = resp.read().decode("utf-8", errors="replace")
            if status == 200:
                logger.info("Teams notification sent successfully (status=200)")
                return True
            logger.warning(
                "Teams webhook returned unexpected status %d: %s", status, response_body
            )
            return False
        except Exception as exc:
            logger.error("Teams notification failed: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Console notifier
# ---------------------------------------------------------------------------


class ConsoleNotifier:
    """Print a formatted notification to stdout.  Always succeeds."""

    def send(self, payload: NotificationPayload) -> bool:
        divider = "=" * 60
        print(divider)
        print("ICEpicks ALERT")
        print(divider)
        print(f"  A-Number (masked) : {payload.a_number_masked}")
        print(f"  Country           : {payload.country}")
        print(f"  Result State      : {payload.state.value}")
        print(f"  Attempts          : {payload.attempts}")
        print(f"  Hash prefix       : {payload.hash_prefix}")
        print(f"  Timestamp         : {payload.timestamp.isoformat()}")
        print(f"  Preview           : {payload.text_preview[:200]}")
        print(divider)
        return True


# ---------------------------------------------------------------------------
# No-op / dry-run notifier
# ---------------------------------------------------------------------------


class NoOpNotifier:
    """Silently discards notifications.  Used when no webhook is configured."""

    def send(self, payload: NotificationPayload) -> bool:
        logger.info(
            "DRY-RUN / no-op notification (state=%s, hash=%s)",
            payload.state.value,
            payload.hash_prefix,
        )
        return True


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_notifier(
    webhook_url: str = "",
    dry_run: bool = False,
    verbose_console: bool = False,
) -> list[Notifier]:
    """Return a list of active notifiers based on config.

    Rules:
    - If dry_run or no webhook: use NoOpNotifier (+ ConsoleNotifier if verbose).
    - Otherwise: use TeamsNotifier (+ ConsoleNotifier if verbose).
    """
    notifiers: list[Notifier] = []

    if dry_run or not webhook_url:
        notifiers.append(NoOpNotifier())
    else:
        notifiers.append(TeamsNotifier(webhook_url))

    if verbose_console:
        notifiers.append(ConsoleNotifier())

    return notifiers


def build_notification_payload(
    a_number_masked: str,
    country: str,
    result,  # SearchResult
    attempts: int,
    run_id: str = "",
) -> NotificationPayload:
    """Convenience factory for NotificationPayload from a SearchResult."""
    preview = (result.raw_text or "")[:200].replace("\n", " ").strip()
    return NotificationPayload(
        a_number_masked=a_number_masked,
        country=country,
        state=result.state,
        attempts=attempts,
        hash_prefix=result.hash_prefix,
        text_preview=preview,
        timestamp=datetime.now(timezone.utc),
        run_id=run_id,
    )
