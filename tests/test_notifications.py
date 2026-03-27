"""Tests for notification payload construction and Teams card format."""

from __future__ import annotations

from datetime import datetime, timezone

from findICE.models import NotificationPayload, ResultState
from findICE.notifications import (
    ConsoleNotifier,
    NoOpNotifier,
    build_notification_payload,
    build_notifier,
)

FIXED_TS = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_payload(**kwargs) -> NotificationPayload:
    defaults = dict(
        a_number_masked="A-*******89",
        country="MEXICO",
        state=ResultState.LIKELY_POSITIVE,
        attempts=4,
        hash_prefix="abc123def456",
        text_preview="Detainee record found at facility.",
        timestamp=FIXED_TS,
        run_id="run_20240115T120000Z",
    )
    defaults.update(kwargs)
    return NotificationPayload(**defaults)


class TestNotificationPayload:
    def test_teams_card_structure(self):
        payload = _make_payload()
        card = payload.to_teams_card()
        assert card["@type"] == "MessageCard"
        assert card["@context"] == "http://schema.org/extensions"
        assert "sections" in card
        section = card["sections"][0]
        assert "activityTitle" in section
        assert "facts" in section

    def test_teams_card_contains_masked_a_number(self):
        payload = _make_payload(a_number_masked="A-*******89")
        card = payload.to_teams_card()
        facts = {f["name"]: f["value"] for f in card["sections"][0]["facts"]}
        assert facts["A-Number"] == "A-*******89"
        # Ensure unmasked digits not in the card
        assert "123456789" not in str(card)

    def test_teams_card_contains_state(self):
        payload = _make_payload(state=ResultState.LIKELY_POSITIVE)
        card = payload.to_teams_card()
        facts = {f["name"]: f["value"] for f in card["sections"][0]["facts"]}
        assert facts["Result State"] == "LIKELY_POSITIVE"

    def test_teams_card_preview_truncated(self):
        long_preview = "x" * 500
        payload = _make_payload(text_preview=long_preview)
        card = payload.to_teams_card()
        facts = {f["name"]: f["value"] for f in card["sections"][0]["facts"]}
        assert len(facts["Preview"]) <= 200

    def test_teams_card_timestamp_formatted(self):
        payload = _make_payload()
        card = payload.to_teams_card()
        subtitle = card["sections"][0]["activitySubtitle"]
        assert "2024-01-15" in subtitle


class TestBuildNotifier:
    def test_no_webhook_returns_noop(self):
        notifiers = build_notifier(webhook_url="", dry_run=False)
        assert len(notifiers) == 1
        assert isinstance(notifiers[0], NoOpNotifier)

    def test_dry_run_returns_noop(self):
        notifiers = build_notifier(webhook_url="https://example.com/webhook", dry_run=True)
        assert isinstance(notifiers[0], NoOpNotifier)

    def test_verbose_console_adds_console_notifier(self):
        notifiers = build_notifier(webhook_url="", dry_run=False, verbose_console=True)
        types = [type(n).__name__ for n in notifiers]
        assert "ConsoleNotifier" in types

    def test_webhook_configured_returns_teams(self):
        notifiers = build_notifier(
            webhook_url="https://outlook.office.com/webhook/test", dry_run=False
        )
        from findICE.notifications import TeamsNotifier
        assert isinstance(notifiers[0], TeamsNotifier)


class TestNoOpNotifier:
    def test_always_returns_true(self):
        notifier = NoOpNotifier()
        payload = _make_payload()
        assert notifier.send(payload) is True


class TestConsoleNotifier:
    def test_prints_and_returns_true(self, capsys):
        notifier = ConsoleNotifier()
        payload = _make_payload()
        result = notifier.send(payload)
        assert result is True
        captured = capsys.readouterr()
        assert "ICEpicks ALERT" in captured.out
        assert "A-*******89" in captured.out
        assert "LIKELY_POSITIVE" in captured.out


class TestBuildNotificationPayload:
    def test_builds_payload_from_search_result(self):
        from findICE.models import SearchResult

        result = SearchResult(
            state=ResultState.LIKELY_POSITIVE,
            raw_text="Detainee facility detention country of birth book-in date",
            attempt_number=2,
        )
        payload = build_notification_payload(
            a_number_masked="A-*******99",
            country="MEXICO",
            result=result,
            attempts=4,
        )
        assert payload.a_number_masked == "A-*******99"
        assert payload.state == ResultState.LIKELY_POSITIVE
        assert payload.attempts == 4
        assert len(payload.hash_prefix) == 12
