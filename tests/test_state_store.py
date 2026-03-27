"""Tests for the state store / deduplication logic."""

from __future__ import annotations

import json
from datetime import datetime, timezone
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
        from findICE.state_store import MAX_RECENT_HASHES

        hashes = [f"hash{i:040d}" for i in range(MAX_RECENT_HASHES + 5)]
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


# ---------------------------------------------------------------------------
# _prune_timeline
# ---------------------------------------------------------------------------


class TestPruneTimeline:
    def test_removes_old_entries(self, state_file: Path):
        from datetime import timedelta

        store = StateStore(state_file, retention_hours=1.0)
        now = datetime.now(timezone.utc)
        old = (now - timedelta(hours=2)).isoformat()
        recent = now.isoformat()

        store._state["timeline"] = [
            {"timestamp": recent, "state": "ZERO_RESULT", "hash": None, "run_id": "r1"},
            {"timestamp": old, "state": "ERROR", "hash": None, "run_id": "r0"},
        ]
        store._prune_timeline()
        assert len(store._state["timeline"]) == 1
        assert store._state["timeline"][0]["run_id"] == "r1"

    def test_keeps_all_when_nothing_expired(self, state_file: Path):
        store = StateStore(state_file, retention_hours=24.0)
        now = datetime.now(timezone.utc).isoformat()
        store._state["timeline"] = [
            {"timestamp": now, "state": "ZERO_RESULT", "hash": None, "run_id": "r1"},
        ]
        store._prune_timeline()
        assert len(store._state["timeline"]) == 1


# ---------------------------------------------------------------------------
# purge_old_artifacts
# ---------------------------------------------------------------------------


class TestPurgeOldArtifacts:
    def test_purges_old_run_dirs(self, tmp_path, state_file: Path):
        store = StateStore(state_file, retention_hours=1.0)
        art_dir = tmp_path / "artifacts"
        art_dir.mkdir()

        # Create an "old" run dir with a parseable timestamp far in the past
        old_dir = art_dir / "run_20200101T000000Z"
        old_dir.mkdir()
        (old_dir / "run_summary.json").write_text('{"x": 1}', encoding="utf-8")
        (old_dir / "screenshot.png").write_bytes(b"fake")

        # Create a "recent" run dir with current timestamp
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        recent_dir = art_dir / f"run_{ts}"
        recent_dir.mkdir()

        purged = store.purge_old_artifacts(art_dir)
        assert purged == 1
        assert not old_dir.exists()
        assert recent_dir.exists()

        # Check that summary was archived
        history = art_dir / "_history"
        assert history.exists()
        archived = list(history.glob("*.json"))
        assert len(archived) == 1

    def test_no_purge_on_missing_dir(self, state_file: Path, tmp_path: Path):
        store = StateStore(state_file)
        purged = store.purge_old_artifacts(tmp_path / "nonexistent")
        assert purged == 0

    def test_skips_non_run_dirs(self, tmp_path, state_file: Path):
        store = StateStore(state_file, retention_hours=1.0)
        art_dir = tmp_path / "artifacts"
        art_dir.mkdir()
        (art_dir / "some_other_dir").mkdir()
        purged = store.purge_old_artifacts(art_dir)
        assert purged == 0


# ---------------------------------------------------------------------------
# _save atomic write
# ---------------------------------------------------------------------------


class TestSaveAtomicWrite:
    def test_save_creates_parent_dirs(self, tmp_path):
        deep_file = tmp_path / "a" / "b" / "c" / "state.json"
        store = StateStore(deep_file)
        store.record_run()
        assert deep_file.exists()
        data = json.loads(deep_file.read_text(encoding="utf-8"))
        assert data["run_count"] == 1

    def test_save_overwrites_existing(self, state_file: Path):
        store = StateStore(state_file)
        store.record_run()
        store.record_run()
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["run_count"] == 2

    def test_timeline_appended_with_run_id(self, state_file: Path):
        store = StateStore(state_file)
        store.record_run(run_id="run_test_1", state_value="ZERO_RESULT")
        store.record_run(run_id="run_test_2", state_value="LIKELY_POSITIVE")
        assert len(store.timeline) == 2
        assert store.timeline[0]["run_id"] == "run_test_2"  # newest first
        assert store.timeline[1]["run_id"] == "run_test_1"


# ---------------------------------------------------------------------------
# FileLock concurrency
# ---------------------------------------------------------------------------


class TestFileLockConcurrency:
    def test_lock_attribute_exists(self, state_file: Path):
        store = StateStore(state_file)
        assert hasattr(store, "_lock")

    def test_concurrent_writes_do_not_corrupt(self, state_file: Path):
        """Two StateStore instances writing in sequence should not corrupt."""
        s1 = StateStore(state_file)
        s2 = StateStore(state_file)

        s1.record_run(run_id="r1", state_value="ZERO_RESULT")
        s2._load()  # reload after s1 wrote
        s2.record_run(run_id="r2", state_value="LIKELY_POSITIVE")

        # Reload and verify both runs are visible
        s3 = StateStore(state_file)
        assert s3.run_count == 2

    def test_lock_does_not_prevent_single_instance(self, state_file: Path):
        """Basic smoke — single instance should work fine with locking."""
        store = StateStore(state_file)
        store.record_positive_sent("hash_abc")
        assert store.is_new_positive("hash_abc") is False
