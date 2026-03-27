"""Shared test fixtures for findICE."""

from __future__ import annotations

from pathlib import Path

import pytest

from findICE.config import AppConfig
from findICE.models import ResultState, SearchResult


@pytest.fixture()
def base_config(tmp_path: Path) -> AppConfig:
    """Minimal valid AppConfig pointing at tmp_path for artifacts/state."""
    return AppConfig(
        a_number="123456789",
        country="MEXICO",
        attempts_per_run=1,
        artifact_base_dir=tmp_path / "artifacts",
        state_file=tmp_path / "state" / "findice_state.json",
    )


@pytest.fixture()
def positive_result() -> SearchResult:
    """A LIKELY_POSITIVE SearchResult with typical field values."""
    return SearchResult(
        state=ResultState.LIKELY_POSITIVE,
        raw_text=(
            "1 Search Result\n"
            "Detainee Information\n"
            "A-Number: 123456789\n"
            "Book-In Date: 01/15/2024\n"
            "Current Detention Facility: Example Facility\n"
        ),
        attempt_number=1,
        detention_facility="Example Facility",
    )


@pytest.fixture()
def zero_result() -> SearchResult:
    """A ZERO_RESULT SearchResult."""
    return SearchResult(
        state=ResultState.ZERO_RESULT,
        raw_text="0 Search Results",
        attempt_number=1,
    )
