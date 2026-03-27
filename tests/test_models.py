"""Tests for content hash / deduplication in SearchResult."""

from __future__ import annotations

from findICE.models import ResultState, SearchResult


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
