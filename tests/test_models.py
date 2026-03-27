"""Tests for model helpers and serialization."""

from __future__ import annotations

from findICE.models import ResultState, RunSummary, SearchResult


class TestContentHash:
    def test_same_text_same_hash(self):
        r1 = SearchResult(state=ResultState.LIKELY_POSITIVE, raw_text="some result text")
        r2 = SearchResult(state=ResultState.LIKELY_POSITIVE, raw_text="some result text")
        assert r1.content_hash == r2.content_hash

    def test_different_text_different_hash(self):
        r1 = SearchResult(state=ResultState.LIKELY_POSITIVE, raw_text="result A")
        r2 = SearchResult(state=ResultState.LIKELY_POSITIVE, raw_text="result B")
        assert r1.content_hash != r2.content_hash

    def test_normalisation_ignores_trailing_whitespace(self):
        r1 = SearchResult(state=ResultState.LIKELY_POSITIVE, raw_text="result text\n  ")
        r2 = SearchResult(state=ResultState.LIKELY_POSITIVE, raw_text="result text")
        assert r1.content_hash == r2.content_hash

    def test_normalisation_ignores_case(self):
        r1 = SearchResult(state=ResultState.LIKELY_POSITIVE, raw_text="RESULT TEXT")
        r2 = SearchResult(state=ResultState.LIKELY_POSITIVE, raw_text="result text")
        assert r1.content_hash == r2.content_hash

    def test_hash_prefix_is_12_chars(self):
        r = SearchResult(state=ResultState.LIKELY_POSITIVE, raw_text="test")
        assert len(r.hash_prefix) == 12

    def test_hash_prefix_matches_hash(self):
        r = SearchResult(state=ResultState.LIKELY_POSITIVE, raw_text="test")
        assert r.content_hash.startswith(r.hash_prefix)

    def test_detail_page_text_affects_hash(self):
        r1 = SearchResult(
            state=ResultState.LIKELY_POSITIVE,
            raw_text="result text",
            detail_page_text="facility details a",
        )
        r2 = SearchResult(
            state=ResultState.LIKELY_POSITIVE,
            raw_text="result text",
            detail_page_text="facility details b",
        )
        assert r1.content_hash != r2.content_hash

    def test_more_information_text_affects_hash(self):
        r1 = SearchResult(
            state=ResultState.LIKELY_POSITIVE,
            raw_text="result text",
            facility_more_information_text="tab a",
        )
        r2 = SearchResult(
            state=ResultState.LIKELY_POSITIVE,
            raw_text="result text",
            facility_more_information_text="tab b",
        )
        assert r1.content_hash != r2.content_hash


class TestRunSummary:
    def test_to_dict_includes_facility_fields(self):
        result = SearchResult(
            state=ResultState.LIKELY_POSITIVE,
            raw_text="result text",
            detention_facility="Facility A",
            facility_address="123 Main St",
            visitor_information="(555) 000-1111",
            ero_office_name="Salt Lake City",
            ero_office_phone="(801) 736-1200",
            detail_page_url="https://example.com/details",
            facility_more_information_url="https://example.com/facility",
            facility_more_information_title="Facility Page",
            facility_tabs={"Contacting a Detainee": "Call the facility"},
            facility_tab_details={
                "contacting_a_detainee": {
                    "title": "Contacting a Detainee",
                    "slug": "contacting_a_detainee",
                    "text": "Call the facility",
                    "phones": ["(555) 000-1111"],
                    "emails": [],
                    "links": [],
                }
            },
            facility_contacting_a_detainee="Call the facility",
        )
        summary = RunSummary(
            a_number_masked="A-*******89",
            country="CHILE",
            attempts_total=1,
            best_state=ResultState.LIKELY_POSITIVE,
            best_result=result,
        )

        data = summary.to_dict()
        assert data["detention_facility"] == "Facility A"
        assert data["facility_address"] == "123 Main St"
        assert data["ero_office_phone"] == "(801) 736-1200"
        assert data["facility_more_information_title"] == "Facility Page"
        assert data["facility_tabs"]["Contacting a Detainee"] == "Call the facility"
        assert (
            data["facility_tab_details"]["contacting_a_detainee"]["phones"][0] == "(555) 000-1111"
        )
        assert data["facility_contacting_a_detainee"] == "Call the facility"
