"""Tests for ICE client helpers."""

from __future__ import annotations

import pytest

from findICE.ice_client import (
    _build_facility_tab_detail,
    _normalise_a_number_for_form,
    _select_country_option,
    _slugify_facility_tab_label,
)


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
