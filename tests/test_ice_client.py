"""Tests for ICE client helpers."""

from __future__ import annotations

import pytest

from findICE.ice_client import (
    _apply_detail_page_data,
    _build_facility_tab_detail,
    _dedupe_preserve_order,
    _extract_detention_facility,
    _extract_page_text,
    _normalise_a_number_for_form,
    _select_country_option,
    _slugify_facility_tab_label,
    _wait_for_result,
)
from findICE.models import ResultState, SearchResult


class _MockOption:
    def __init__(self, label: str):
        self._label = label

    def inner_text(self) -> str:
        return self._label


class _MockOptionList:
    def __init__(self, labels: list[str]):
        self._labels = labels

    def count(self) -> int:
        return len(self._labels)

    def nth(self, idx: int) -> _MockOption:
        return _MockOption(self._labels[idx])


class _MockCountrySelect:
    def __init__(self, options: list[str], accepted: set[tuple[str, str]]):
        self._options = options
        self._accepted = accepted
        self.calls: list[dict] = []

    def select_option(self, timeout: int, **kwargs):
        self.calls.append(kwargs)
        key, value = next(iter(kwargs.items()))
        if (key, value) not in self._accepted:
            raise RuntimeError("no match")

    def locator(self, selector: str):
        assert selector == "option"
        return _MockOptionList(self._options)


class TestSelectCountryOption:
    def test_uses_direct_value_when_available(self):
        sel = _MockCountrySelect(options=["Chile"], accepted={("value", "CHILE")})
        _select_country_option(sel, "CHILE", 10_000)
        assert sel.calls[0] == {"value": "CHILE"}

    def test_falls_back_to_case_insensitive_option_scan(self):
        sel = _MockCountrySelect(options=["Chile"], accepted={("label", "Chile")})
        _select_country_option(sel, "CHILE", 10_000)
        assert {"label": "Chile"} in sel.calls

    def test_raises_when_country_not_found(self):
        sel = _MockCountrySelect(options=["Mexico"], accepted=set())
        with pytest.raises(RuntimeError, match="Could not select country"):
            _select_country_option(sel, "Neverland", 10_000)


class TestNormaliseANumber:
    def test_strips_prefix_and_punctuation(self):
        assert _normalise_a_number_for_form("A-123456789") == "123456789"

    def test_digits_only_is_unchanged(self):
        assert _normalise_a_number_for_form("12345678") == "12345678"


class TestFacilityTabHelpers:
    def test_slugify_facility_tab_label(self):
        assert _slugify_facility_tab_label("Press & Media") == "press_and_media"

    def test_build_facility_tab_detail_extracts_contacts_and_links(self):
        detail = _build_facility_tab_detail(
            "Contacting a Detainee",
            (
                "Call (318) 668-5900 or 1-833-4ICE-OPR. "
                "Email slipcnotify@geogroup.com for scheduling."
            ),
            links=[
                {"text": "Facility Page", "url": "https://example.com/facility"},
                {"text": "Facility Page", "url": "https://example.com/facility"},
            ],
        )

        assert detail["slug"] == "contacting_a_detainee"
        assert detail["phones"] == ["1-833-4ICE-OPR", "(318) 668-5900"]
        assert detail["emails"] == ["slipcnotify@geogroup.com"]
        assert detail["links"] == [
            {"text": "Facility Page", "url": "https://example.com/facility"}
        ]


# ---------------------------------------------------------------------------
# _dedupe_preserve_order
# ---------------------------------------------------------------------------


class TestDedupePreserveOrder:
    def test_removes_duplicates(self):
        assert _dedupe_preserve_order(["a", "b", "a", "c"]) == ["a", "b", "c"]

    def test_preserves_order(self):
        assert _dedupe_preserve_order(["c", "b", "a"]) == ["c", "b", "a"]

    def test_strips_whitespace(self):
        assert _dedupe_preserve_order(["  hello  ", "hello"]) == ["hello"]

    def test_removes_empty_strings(self):
        assert _dedupe_preserve_order(["", "a", "  ", "b"]) == ["a", "b"]

    def test_empty_input(self):
        assert _dedupe_preserve_order([]) == []


# ---------------------------------------------------------------------------
# _apply_detail_page_data
# ---------------------------------------------------------------------------


class TestApplyDetailPageData:
    def test_sets_attributes_on_result(self):
        result = SearchResult(
            state=ResultState.LIKELY_POSITIVE,
            raw_text="some text",
            attempt_number=1,
        )
        _apply_detail_page_data(
            result,
            {
                "detention_facility": "Test Facility",
                "facility_address": "123 Main St",
            },
        )
        assert result.detention_facility == "Test Facility"
        assert result.facility_address == "123 Main St"

    def test_empty_dict_is_noop(self):
        result = SearchResult(
            state=ResultState.LIKELY_POSITIVE,
            raw_text="text",
            attempt_number=1,
        )
        _apply_detail_page_data(result, {})
        assert result.detention_facility is None  # unchanged


# ---------------------------------------------------------------------------
# _extract_page_text (mock-based)
# ---------------------------------------------------------------------------


class _MockLocator:
    """Mock for a Playwright locator."""

    def __init__(self, text: str = "", fail: bool = False):
        self._text = text
        self._fail = fail

    def inner_text(self, timeout: int = 5_000) -> str:
        if self._fail:
            raise RuntimeError("boom")
        return self._text


class _MockResultPage:
    """Mock for a Playwright page with resolve_locator support."""

    def __init__(
        self,
        result_text: str = "",
        body_text: str = "body fallback",
        result_locator_exists: bool = True,
    ):
        self._result_text = result_text
        self._body_text = body_text
        self._result_locator_exists = result_locator_exists

    def inner_text(self, selector: str, timeout: int = 5_000) -> str:
        return self._body_text


class TestExtractPageText:
    def test_returns_text_from_result_container(self, monkeypatch):
        mock_loc = _MockLocator(text="Search Results: 1 result found")
        monkeypatch.setattr(
            "findICE.ice_client.resolve_locator",
            lambda page, selector: mock_loc,
        )
        page = _MockResultPage()
        text = _extract_page_text(page)
        assert text == "Search Results: 1 result found"

    def test_falls_back_to_body_when_no_container(self, monkeypatch):
        monkeypatch.setattr(
            "findICE.ice_client.resolve_locator",
            lambda page, selector: None,
        )
        page = _MockResultPage(body_text="full body text")
        text = _extract_page_text(page)
        assert text == "full body text"

    def test_falls_back_to_body_on_container_error(self, monkeypatch):
        mock_loc = _MockLocator(fail=True)
        monkeypatch.setattr(
            "findICE.ice_client.resolve_locator",
            lambda page, selector: mock_loc,
        )
        page = _MockResultPage(body_text="body fallback text")
        text = _extract_page_text(page)
        assert text == "body fallback text"


# ---------------------------------------------------------------------------
# _extract_detention_facility (mock-based)
# ---------------------------------------------------------------------------


class TestExtractDetentionFacility:
    def test_returns_facility_name(self, monkeypatch):
        mock_loc = _MockLocator(text="  Test Detention Center  ")
        monkeypatch.setattr(
            "findICE.ice_client.resolve_locator",
            lambda page, selector: mock_loc,
        )
        page = _MockResultPage()
        assert _extract_detention_facility(page) == "Test Detention Center"

    def test_returns_none_when_no_locator(self, monkeypatch):
        monkeypatch.setattr(
            "findICE.ice_client.resolve_locator",
            lambda page, selector: None,
        )
        page = _MockResultPage()
        assert _extract_detention_facility(page) is None

    def test_returns_none_on_empty_text(self, monkeypatch):
        mock_loc = _MockLocator(text="   ")
        monkeypatch.setattr(
            "findICE.ice_client.resolve_locator",
            lambda page, selector: mock_loc,
        )
        page = _MockResultPage()
        assert _extract_detention_facility(page) is None

    def test_returns_none_on_locator_error(self, monkeypatch):
        mock_loc = _MockLocator(fail=True)
        monkeypatch.setattr(
            "findICE.ice_client.resolve_locator",
            lambda page, selector: mock_loc,
        )
        page = _MockResultPage()
        assert _extract_detention_facility(page) is None


# ---------------------------------------------------------------------------
# _wait_for_result (mock-based)
# ---------------------------------------------------------------------------


class _MockWaitPage:
    """Mock page for _wait_for_result — just needs wait_for_function."""

    def __init__(self, *, fail: bool = False):
        self._fail = fail
        self.called = False

    def wait_for_function(self, js: str, timeout: int = 30_000) -> None:
        self.called = True
        if self._fail:
            raise TimeoutError("timed out")


class TestWaitForResult:
    def test_calls_wait_for_function(self):
        page = _MockWaitPage()
        _wait_for_result(page, timeout_ms=5_000)
        assert page.called

    def test_does_not_raise_on_timeout(self):
        page = _MockWaitPage(fail=True)
        _wait_for_result(page, timeout_ms=100)  # should not raise
        assert page.called
