"""Tests for the classification module."""

from __future__ import annotations

from findICE.classification import best_state_from_run, classify_page_text
from findICE.models import ResultState


class TestClassifyPageText:
    """Unit tests for classify_page_text."""

    def test_zero_result_phrase(self):
        text = "Your search returned 0 Search Results. Please verify the information."
        assert classify_page_text(text) == ResultState.ZERO_RESULT

    def test_zero_result_no_records(self):
        text = "No records found for the provided information."
        assert classify_page_text(text) == ResultState.ZERO_RESULT

    def test_zero_result_not_found(self):
        text = "not found"
        # "not found" is a ZERO_RESULT phrase; phrase matching runs before
        # the minimum-text-length check, so this classifies as ZERO_RESULT.
        assert classify_page_text(text) == ResultState.ZERO_RESULT

    def test_likely_positive_full_record(self):
        text = (
            "1 Search Result\n"
            "First Name: JOHN\n"
            "Last Name: DOE\n"
            "Country of Birth: MEXICO\n"
            "Book-In Date: 01/15/2024\n"
            "Detention Facility: Some Facility\n"
        )
        assert classify_page_text(text) == ResultState.LIKELY_POSITIVE

    def test_likely_positive_multiple_indicators(self):
        text = (
            "Search Results: 1\n"
            "Detainee Information\n"
            "A-Number: 123456789\n"
            "Current Detention Facility: Some Facility\n"
        )
        assert classify_page_text(text) == ResultState.LIKELY_POSITIVE

    def test_generic_search_page_is_not_positive(self):
        text = (
            "Online Detainee Locator System\n"
            "Search by A-Number\n"
            "Country of Birth\n"
            "Search by Biographical Information\n"
            "First Name\n"
            "Last Name\n"
        )
        assert classify_page_text(text) == ResultState.AMBIGUOUS_REVIEW

    def test_bot_challenge_captcha(self):
        text = "Please verify you are human. Captcha required."
        assert classify_page_text(text) == ResultState.BOT_CHALLENGE_OR_BLOCKED

    def test_bot_challenge_access_denied(self):
        text = "Access Denied – forbidden to access this resource."
        assert classify_page_text(text) == ResultState.BOT_CHALLENGE_OR_BLOCKED

    def test_bot_challenge_http_status_403(self):
        text = "Normal looking page text without bot phrases but with long content here yes"
        assert classify_page_text(text, http_status=403) == ResultState.BOT_CHALLENGE_OR_BLOCKED

    def test_bot_challenge_http_status_429(self):
        text = "Normal looking page text without bot phrases but with long content here yes"
        assert classify_page_text(text, http_status=429) == ResultState.BOT_CHALLENGE_OR_BLOCKED

    def test_ambiguous_review(self):
        text = (
            "ICE Online Detainee Locator\n"
            "An error occurred processing your request. Please try again later.\n"
            "Error code: INTERNAL_SERVER_ERROR\n"
            "If you believe you have reached this page in error, please contact us.\n"
        )
        result = classify_page_text(text)
        assert result == ResultState.AMBIGUOUS_REVIEW

    def test_internal_error_page_with_site_chrome_is_ambiguous(self):
        text = (
            "Official Website of the Department of Homeland Security\n"
            "Internal Error\n"
            "Our apologies. An internal error has occurred.\n"
            "Go To Locator Home\n"
            "ICE Detention Facilities\n"
        )
        assert classify_page_text(text) == ResultState.AMBIGUOUS_REVIEW

    def test_error_empty_text(self):
        assert classify_page_text("", "") == ResultState.ERROR

    def test_error_very_short_text(self):
        assert classify_page_text("Hi") == ResultState.ERROR

    def test_case_insensitive_zero_result(self):
        text = "0 SEARCH RESULTS"
        assert classify_page_text(text) == ResultState.ZERO_RESULT

    def test_bot_before_zero_result(self):
        """Bot challenge takes precedence over zero result phrases."""
        text = "0 search results captcha verification required verify you are human"
        assert classify_page_text(text) == ResultState.BOT_CHALLENGE_OR_BLOCKED


class TestBestStateFromRun:
    """Unit tests for best_state_from_run."""

    def test_likely_positive_wins(self):
        states = [
            ResultState.ZERO_RESULT,
            ResultState.LIKELY_POSITIVE,
            ResultState.ERROR,
        ]
        assert best_state_from_run(states) == ResultState.LIKELY_POSITIVE

    def test_ambiguous_over_zero(self):
        states = [ResultState.ZERO_RESULT, ResultState.AMBIGUOUS_REVIEW]
        assert best_state_from_run(states) == ResultState.AMBIGUOUS_REVIEW

    def test_zero_over_error(self):
        states = [ResultState.ERROR, ResultState.ZERO_RESULT]
        assert best_state_from_run(states) == ResultState.ZERO_RESULT

    def test_single_state(self):
        assert best_state_from_run([ResultState.ERROR]) == ResultState.ERROR

    def test_empty_returns_error(self):
        assert best_state_from_run([]) == ResultState.ERROR

    def test_all_same(self):
        states = [ResultState.ZERO_RESULT] * 4
        assert best_state_from_run(states) == ResultState.ZERO_RESULT


class TestFixtures:
    """Smoke tests using fixture files."""

    def _load_fixture(self, name: str) -> str:
        from pathlib import Path

        fixture_dir = Path(__file__).parent / "fixtures"
        return (fixture_dir / f"{name}.txt").read_text(encoding="utf-8")

    def test_zero_result_fixture(self):
        text = self._load_fixture("zero_result")
        assert classify_page_text(text) == ResultState.ZERO_RESULT

    def test_likely_positive_fixture(self):
        text = self._load_fixture("likely_positive")
        assert classify_page_text(text) == ResultState.LIKELY_POSITIVE

    def test_ambiguous_fixture(self):
        text = self._load_fixture("ambiguous")
        assert classify_page_text(text) == ResultState.AMBIGUOUS_REVIEW

    def test_bot_blocked_fixture(self):
        text = self._load_fixture("bot_blocked")
        assert classify_page_text(text) == ResultState.BOT_CHALLENGE_OR_BLOCKED

    def test_zero_result_211_mexico(self):
        """Fake 211-prefix A-number + Mexico returns 'zero (0) matching records'."""
        text = self._load_fixture("zero_result_211_mexico")
        assert classify_page_text(text) == ResultState.ZERO_RESULT

    def test_internal_error_211_chile(self):
        """Same fake 211-prefix A-number + Chile returns ICE 'Internal Error' page."""
        text = self._load_fixture("internal_error_211_chile")
        assert classify_page_text(text) == ResultState.AMBIGUOUS_REVIEW
