"""Tests for the state store / deduplication logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from findICE.state_store import StateStore


@pytest.fixture()
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "state" / "test_state.json"


@pytest.fixture()
def store(state_file: Path) -> StateStore:
    return StateStore(state_file)


class TestStateStore:
    def test_new_store_is_empty(self, store: StateStore):
        assert store.last_positive_hash is None
        assert store.run_count == 0

    def test_new_positive_is_new_on_empty_store(self, store: StateStore):
        assert store.is_new_positive("abc123") is True

    def test_record_positive_sent_marks_as_seen(self, store: StateStore):
        h = "deadbeef" * 8
        store.record_positive_sent(h)
        assert store.is_new_positive(h) is False

    def test_different_hash_is_still_new(self, store: StateStore):
        h1 = "aaaa" * 16
        h2 = "bbbb" * 16
        store.record_positive_sent(h1)
        assert store.is_new_positive(h2) is True

    def test_run_count_increments(self, store: StateStore):
        store.record_run()
        store.record_run()
        assert store.run_count == 2

    def test_state_persists_across_instances(self, state_file: Path):
        h = "persist_hash" * 5
        store1 = StateStore(state_file)
        store1.record_positive_sent(h)

        store2 = StateStore(state_file)
        assert store2.is_new_positive(h) is False

    def test_recent_hashes_window(self, store: StateStore):
        from findICE.state_store import RECENT_HASH_WINDOW

        hashes = [f"hash{i:040d}" for i in range(RECENT_HASH_WINDOW + 5)]
        for h in hashes:
            store.record_positive_sent(h)

        # Oldest hashes (beyond window) should be gone
        oldest = hashes[0]
        assert store.is_new_positive(oldest) is True

        # Most recent should still be there
        newest = hashes[-1]
        assert store.is_new_positive(newest) is False

    def test_corrupted_state_file_starts_fresh(self, state_file: Path):
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("not valid json!!!", encoding="utf-8")
        store = StateStore(state_file)
        assert store.run_count == 0

    def test_record_run_saves_summary(self, store: StateStore, state_file: Path):
        store.record_run({"best_state": "ZERO_RESULT"})
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["last_run_summary"]["best_state"] == "ZERO_RESULT"
