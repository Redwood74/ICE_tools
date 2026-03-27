"""Tests for selector resolution logic."""

from __future__ import annotations

from findICE.selectors import (
    A_NUMBER_INPUT,
    BOT_CHALLENGE_PHRASES,
    COUNTRY_SELECT,
    POSITIVE_PHRASES,
    SEARCH_BUTTON,
    ZERO_RESULT_PHRASES,
)


class TestSelectorGroupStructure:
    """Verify that SelectorGroups have the expected shape."""

    def test_a_number_input_has_candidates(self):
        assert len(A_NUMBER_INPUT.candidates) > 0
        assert A_NUMBER_INPUT.name == "a_number_input"

    def test_country_select_has_candidates(self):
        assert len(COUNTRY_SELECT.candidates) > 0

    def test_search_button_has_candidates(self):
        assert len(SEARCH_BUTTON.candidates) > 0

    def test_a_number_input_includes_label_selector(self):
        """Label-based selectors should appear before CSS fallbacks."""
        label_selectors = [c for c in A_NUMBER_INPUT.candidates if "aria-label" in c]
        css_fallbacks = [c for c in A_NUMBER_INPUT.candidates if "first-of-type" in c]
        assert label_selectors, "No label-based selectors found"
        assert css_fallbacks, "No CSS fallback selectors found"
        # Label-based should appear earlier
        first_label = A_NUMBER_INPUT.candidates.index(label_selectors[0])
        first_css = A_NUMBER_INPUT.candidates.index(css_fallbacks[0])
        assert first_label < first_css, "Label-based selectors should precede CSS fallbacks"


class TestPhraseListsNotEmpty:
    """Ensure phrase lists are populated."""

    def test_zero_result_phrases_populated(self):
        assert len(ZERO_RESULT_PHRASES) > 0
        assert any("0" in p for p in ZERO_RESULT_PHRASES)

    def test_positive_phrases_populated(self):
        assert len(POSITIVE_PHRASES) > 0
        assert any("facility" in p for p in POSITIVE_PHRASES)

    def test_bot_challenge_phrases_populated(self):
        assert len(BOT_CHALLENGE_PHRASES) > 0
        assert any("captcha" in p for p in BOT_CHALLENGE_PHRASES)


class TestResolveLocator:
    """Test the resolve_locator function using a mock page."""

    def _make_mock_page(self, selector_hit: str | None = None):
        """Build a minimal mock Playwright page."""

        class MockLocator:
            def __init__(self, hit: bool):
                self._hit = hit

            def count(self) -> int:
                return 1 if self._hit else 0

            @property
            def first(self):
                return self

        class MockPage:
            def __init__(self, hit_selector: str | None):
                self._hit = hit_selector

            def locator(self, selector: str):
                return MockLocator(selector == self._hit)

        return MockPage(selector_hit)

    def test_resolves_first_matching_selector(self):
        from findICE.selectors import resolve_locator

        # Use the first candidate of A_NUMBER_INPUT as the 'hit'
        hit_selector = A_NUMBER_INPUT.candidates[0]
        page = self._make_mock_page(hit_selector)
        result = resolve_locator(page, A_NUMBER_INPUT)
        assert result is not None

    def test_returns_none_when_no_match(self):
        from findICE.selectors import resolve_locator

        page = self._make_mock_page(None)  # Nothing matches
        result = resolve_locator(page, A_NUMBER_INPUT)
        assert result is None

    def test_falls_back_through_candidates(self):
        from findICE.selectors import resolve_locator

        # Hit only the LAST candidate
        last_selector = A_NUMBER_INPUT.candidates[-1]
        page = self._make_mock_page(last_selector)
        result = resolve_locator(page, A_NUMBER_INPUT)
        assert result is not None
