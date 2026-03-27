"""Tests for B2-B10: new test coverage for publish readiness."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

import pytest

from findICE.classification import best_state_from_run, classify_page_text
from findICE.config import AppConfig, load_config
from findICE.exceptions import ConfigError
from findICE.models import ResultState, SearchResult

# =========================================================================
# B2: run_with_retries retry orchestration (mocked)
# =========================================================================


class TestRunWithRetriesOrchestration:
    """Verify retry loop mechanics without touching Playwright."""

    def test_stops_early_on_positive(self, monkeypatch):
        """When attempt 1 returns LIKELY_POSITIVE, attempt 2 should not run."""
        call_count = 0

        def fake_single(
            a_number,
            country,
            attempt_number,
            playwright_instance,
            **kwargs,
        ):
            nonlocal call_count
            call_count += 1
            return SearchResult(
                state=ResultState.LIKELY_POSITIVE,
                raw_text="detainee facility book-in date",
                attempt_number=attempt_number,
            )

        import findICE.ice_client as mod

        monkeypatch.setattr(mod, "run_single_attempt", fake_single)
        monkeypatch.setattr(mod, "reset_selector_health", lambda: None)
        monkeypatch.setattr(mod, "log_selector_health", lambda: None)

        # Patch sync_playwright where it's imported inside run_with_retries
        from contextlib import contextmanager

        @contextmanager
        def fake_pw():
            yield object()

        monkeypatch.setattr("playwright.sync_api.sync_playwright", fake_pw)

        results = mod.run_with_retries(
            a_number="123456789",
            country="MEXICO",
            attempts=3,
            delay_seconds=0,
            jitter_seconds=0,
        )
        assert len(results) == 1
        assert results[0].state == ResultState.LIKELY_POSITIVE
        assert call_count == 1

    def test_retries_on_zero_result(self, monkeypatch):
        """Non-positive results should be retried up to max attempts."""
        import findICE.ice_client as mod

        monkeypatch.setattr(mod, "reset_selector_health", lambda: None)
        monkeypatch.setattr(mod, "log_selector_health", lambda: None)

        def fake_single(a_number, country, attempt_number, playwright_instance, **kw):
            return SearchResult(
                state=ResultState.ZERO_RESULT,
                raw_text="0 search results",
                attempt_number=attempt_number,
            )

        monkeypatch.setattr(mod, "run_single_attempt", fake_single)

        from contextlib import contextmanager

        @contextmanager
        def fake_pw():
            yield object()

        monkeypatch.setattr("playwright.sync_api.sync_playwright", fake_pw)

        results = mod.run_with_retries(
            a_number="123456789",
            country="MEXICO",
            attempts=3,
            delay_seconds=0,
            jitter_seconds=0,
        )
        assert len(results) == 3

    def test_bot_challenge_aborts_immediately(self, monkeypatch):
        """BotChallengeError from attempt stops further retries."""
        import findICE.ice_client as mod
        from findICE.exceptions import BotChallengeError

        monkeypatch.setattr(mod, "reset_selector_health", lambda: None)
        monkeypatch.setattr(mod, "log_selector_health", lambda: None)

        def fake_single(a_number, country, attempt_number, playwright_instance, **kw):
            raise BotChallengeError("blocked")

        monkeypatch.setattr(mod, "run_single_attempt", fake_single)

        from contextlib import contextmanager

        @contextmanager
        def fake_pw():
            yield object()

        monkeypatch.setattr("playwright.sync_api.sync_playwright", fake_pw)

        results = mod.run_with_retries(
            a_number="123456789",
            country="MEXICO",
            attempts=3,
            delay_seconds=0,
            jitter_seconds=0,
        )
        assert len(results) == 1
        assert results[0].state == ResultState.BOT_CHALLENGE_OR_BLOCKED


# =========================================================================
# B3: cmd_check_batch CLI handler
# =========================================================================


class TestCmdCheckBatch:
    def test_batch_no_people_file_returns_error(self, monkeypatch):
        from findICE.cli import cmd_check_batch

        def fake_load_config(**kw):
            return AppConfig(a_number="123456789", country="MEXICO")

        monkeypatch.setattr("findICE.config.load_config", fake_load_config)

        args = argparse.Namespace(
            attempts=1,
            headed=False,
            dry_run=False,
            people=None,
            inter_delay=0,
            verbose=False,
            log_level="DEBUG",
        )
        rc = cmd_check_batch(args)
        assert rc == 1

    def test_batch_invalid_people_file_returns_error(self, monkeypatch, tmp_path):
        from findICE.cli import cmd_check_batch

        bad_file = tmp_path / "bad.yml"
        bad_file.write_text("not valid yaml: [[[", encoding="utf-8")

        def fake_load_config(**kw):
            return AppConfig(a_number="123456789", country="MEXICO")

        monkeypatch.setattr("findICE.config.load_config", fake_load_config)

        args = argparse.Namespace(
            attempts=1,
            headed=False,
            dry_run=False,
            people=str(bad_file),
            inter_delay=0,
            verbose=False,
            log_level="DEBUG",
        )
        rc = cmd_check_batch(args)
        assert rc == 1


# =========================================================================
# B4: cmd_setup interactive wizard (smoke test)
# =========================================================================


class TestCmdSetup:
    def test_setup_subcommand_exists(self):
        from findICE.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["setup"])
        assert args.command == "setup"


# =========================================================================
# B5: ConfigError on malformed numeric env vars
# =========================================================================


class TestConfigErrorOnMalformedNumeric:
    def test_attempts_non_integer_raises(self, monkeypatch):
        monkeypatch.setenv("A_NUMBER", "123456789")
        monkeypatch.setenv("COUNTRY", "MEXICO")
        monkeypatch.setenv("ATTEMPTS_PER_RUN", "not_a_number")
        with pytest.raises(ConfigError, match="ATTEMPTS_PER_RUN"):
            load_config()

    def test_delay_non_float_raises(self, monkeypatch):
        monkeypatch.setenv("A_NUMBER", "123456789")
        monkeypatch.setenv("COUNTRY", "MEXICO")
        monkeypatch.setenv("ATTEMPT_DELAY_SECONDS", "abc")
        with pytest.raises(ConfigError, match="ATTEMPT_DELAY_SECONDS"):
            load_config()

    def test_page_load_timeout_non_integer_raises(self, monkeypatch):
        monkeypatch.setenv("A_NUMBER", "123456789")
        monkeypatch.setenv("COUNTRY", "MEXICO")
        monkeypatch.setenv("PAGE_LOAD_TIMEOUT_MS", "slow")
        with pytest.raises(ConfigError, match="PAGE_LOAD_TIMEOUT_MS"):
            load_config()

    def test_element_timeout_non_integer_raises(self, monkeypatch):
        monkeypatch.setenv("A_NUMBER", "123456789")
        monkeypatch.setenv("COUNTRY", "MEXICO")
        monkeypatch.setenv("ELEMENT_TIMEOUT_MS", "10.5")
        with pytest.raises(ConfigError, match="ELEMENT_TIMEOUT_MS"):
            load_config()

    def test_timeline_retention_non_float_raises(self, monkeypatch):
        monkeypatch.setenv("A_NUMBER", "123456789")
        monkeypatch.setenv("COUNTRY", "MEXICO")
        monkeypatch.setenv("TIMELINE_RETENTION_HOURS", "never")
        with pytest.raises(ConfigError, match="TIMELINE_RETENTION_HOURS"):
            load_config()

    def test_jitter_non_float_raises(self, monkeypatch):
        monkeypatch.setenv("A_NUMBER", "123456789")
        monkeypatch.setenv("COUNTRY", "MEXICO")
        monkeypatch.setenv("ATTEMPT_JITTER_SECONDS", "jittery")
        with pytest.raises(ConfigError, match="ATTEMPT_JITTER_SECONDS"):
            load_config()

    def test_inter_person_delay_non_float_raises(self, monkeypatch):
        monkeypatch.setenv("A_NUMBER", "123456789")
        monkeypatch.setenv("COUNTRY", "MEXICO")
        monkeypatch.setenv("INTER_PERSON_DELAY_SECONDS", "nope")
        with pytest.raises(ConfigError, match="INTER_PERSON_DELAY_SECONDS"):
            load_config()


# =========================================================================
# B6: _collect_facility_details extraction
# =========================================================================


class TestCollectFacilityDetails:
    def test_returns_none_when_no_facility_link(self, monkeypatch):
        """No facility link means no detail collection."""
        import findICE.ice_client as mod

        monkeypatch.setattr(mod, "resolve_locator", lambda page, sg: None)

        result = SearchResult(
            state=ResultState.LIKELY_POSITIVE,
            raw_text="test",
            attempt_number=1,
        )
        ret = mod._collect_facility_details(object(), result, 5000)
        assert ret is None


# =========================================================================
# B7: build_notification_payload edge cases
# =========================================================================


class TestBuildNotificationPayloadEdgeCases:
    def test_empty_raw_text_gives_empty_preview(self):
        from findICE.notifications import build_notification_payload

        result = SearchResult(
            state=ResultState.LIKELY_POSITIVE,
            raw_text="",
            attempt_number=1,
        )
        payload = build_notification_payload(
            a_number_masked="A-*******89",
            country="MEXICO",
            result=result,
            attempts=1,
            run_id="test_run",
        )
        assert payload.text_preview == ""

    def test_long_raw_text_truncated_to_200(self):
        from findICE.notifications import build_notification_payload

        result = SearchResult(
            state=ResultState.LIKELY_POSITIVE,
            raw_text="x" * 500,
            attempt_number=1,
        )
        payload = build_notification_payload(
            a_number_masked="A-*******89",
            country="MEXICO",
            result=result,
            attempts=1,
        )
        assert len(payload.text_preview) <= 200

    def test_newlines_replaced_in_preview(self):
        from findICE.notifications import build_notification_payload

        result = SearchResult(
            state=ResultState.LIKELY_POSITIVE,
            raw_text="line1\nline2\nline3",
            attempt_number=1,
        )
        payload = build_notification_payload(
            a_number_masked="A-*******89",
            country="MEXICO",
            result=result,
            attempts=1,
        )
        assert "\n" not in payload.text_preview

    def test_notification_payload_fields(self):
        from findICE.notifications import build_notification_payload

        result = SearchResult(
            state=ResultState.ZERO_RESULT,
            raw_text="0 search results",
            attempt_number=2,
        )
        payload = build_notification_payload(
            a_number_masked="A-*******89",
            country="EL SALVADOR",
            result=result,
            attempts=4,
            run_id="run_abc",
        )
        assert payload.country == "EL SALVADOR"
        assert payload.state == ResultState.ZERO_RESULT
        assert payload.attempts == 4
        assert payload.run_id == "run_abc"


# =========================================================================
# B8: generate_html_report XSS hardening (expanded)
# =========================================================================


class TestHtmlReportXssHardening:
    def test_script_tags_escaped_in_facility(self, tmp_path):
        from findICE.artifacts import generate_html_report
        from findICE.models import RunSummary

        xss = '<script>alert("xss")</script>'
        result = SearchResult(
            state=ResultState.LIKELY_POSITIVE,
            raw_text="test",
            attempt_number=1,
            detention_facility=xss,
        )
        summary = RunSummary(
            a_number_masked="A-*******89",
            country="MEXICO",
            attempts_total=1,
            best_state=ResultState.LIKELY_POSITIVE,
            best_result=result,
        )
        run_dir = tmp_path / "run_xss"
        run_dir.mkdir()
        generate_html_report(summary, run_dir)
        html = (run_dir / "report.html").read_text(encoding="utf-8")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_angle_brackets_escaped_in_country(self, tmp_path):
        from findICE.artifacts import generate_html_report
        from findICE.models import RunSummary

        summary = RunSummary(
            a_number_masked="A-*******89",
            country='<img src=x onerror="alert(1)">',
            attempts_total=1,
            best_state=ResultState.ZERO_RESULT,
            best_result=None,
        )
        run_dir = tmp_path / "run_xss2"
        run_dir.mkdir()
        generate_html_report(summary, run_dir)
        html = (run_dir / "report.html").read_text(encoding="utf-8")
        assert "<img src=x" not in html


# =========================================================================
# B9: Parametrized classification tests
# =========================================================================


class TestClassifyParametrized:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("0 search results", ResultState.ZERO_RESULT),
            ("0 results found for your query", ResultState.ZERO_RESULT),
            ("no records found", ResultState.ZERO_RESULT),
            ("not found", ResultState.ZERO_RESULT),
            ("no match for this number", ResultState.ZERO_RESULT),
            ("unable to locate the detainee", ResultState.ZERO_RESULT),
        ],
        ids=[
            "0-search-results",
            "0-results",
            "no-records",
            "not-found",
            "no-match",
            "unable-to-locate",
        ],
    )
    def test_zero_result_phrases(self, text, expected):
        assert classify_page_text(text) == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            (
                "captcha challenge detected on the page with enough content here",
                ResultState.BOT_CHALLENGE_OR_BLOCKED,
            ),
            (
                "verify you are human before continuing please",
                ResultState.BOT_CHALLENGE_OR_BLOCKED,
            ),
            (
                "access denied to this page forbidden resource",
                ResultState.BOT_CHALLENGE_OR_BLOCKED,
            ),
        ],
        ids=["captcha", "verify-human", "access-denied"],
    )
    def test_bot_challenge_phrases(self, text, expected):
        assert classify_page_text(text) == expected


class TestBestStateFromRun:
    def test_empty_returns_error(self):
        assert best_state_from_run([]) == ResultState.ERROR

    def test_single_state(self):
        assert best_state_from_run([ResultState.ZERO_RESULT]) == ResultState.ZERO_RESULT

    def test_positive_wins_over_zero(self):
        states = [ResultState.ZERO_RESULT, ResultState.LIKELY_POSITIVE]
        assert best_state_from_run(states) == ResultState.LIKELY_POSITIVE

    def test_ambiguous_wins_over_zero(self):
        states = [ResultState.ZERO_RESULT, ResultState.AMBIGUOUS_REVIEW]
        assert best_state_from_run(states) == ResultState.AMBIGUOUS_REVIEW

    def test_positive_wins_over_bot(self):
        states = [
            ResultState.BOT_CHALLENGE_OR_BLOCKED,
            ResultState.LIKELY_POSITIVE,
        ]
        assert best_state_from_run(states) == ResultState.LIKELY_POSITIVE


# =========================================================================
# B10: purge_old_artifacts edge cases
# =========================================================================


class TestPurgeOldArtifactsEdgeCases:
    def test_unparseable_dir_name_skipped(self, tmp_path):
        from findICE.state_store import StateStore

        sf = tmp_path / "state" / "s.json"
        store = StateStore(sf, retention_hours=1.0)
        art_dir = tmp_path / "artifacts"
        art_dir.mkdir()
        (art_dir / "run_INVALID_TS").mkdir()
        purged = store.purge_old_artifacts(art_dir)
        assert purged == 0
        assert (art_dir / "run_INVALID_TS").exists()

    def test_empty_artifact_dir(self, tmp_path):
        from findICE.state_store import StateStore

        sf = tmp_path / "state" / "s.json"
        store = StateStore(sf, retention_hours=1.0)
        art_dir = tmp_path / "artifacts"
        art_dir.mkdir()
        purged = store.purge_old_artifacts(art_dir)
        assert purged == 0

    def test_recent_dirs_not_purged(self, tmp_path):
        from findICE.state_store import StateStore

        sf = tmp_path / "state" / "s.json"
        store = StateStore(sf, retention_hours=24.0)
        art_dir = tmp_path / "artifacts"
        art_dir.mkdir()
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (art_dir / f"run_{ts}").mkdir()
        purged = store.purge_old_artifacts(art_dir)
        assert purged == 0
