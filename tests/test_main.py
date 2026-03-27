"""Tests for run orchestration behavior."""

from __future__ import annotations

from pathlib import Path

from findICE.config import AppConfig
from findICE.main import execute_run
from findICE.models import ResultState, SearchResult
from findICE.state_store import StateStore


class _AlwaysOkNotifier:
    def send(self, payload) -> bool:
        return True


def _positive_result() -> SearchResult:
    return SearchResult(
        state=ResultState.LIKELY_POSITIVE,
        raw_text="detainee facility country of birth book-in date",
        attempt_number=1,
    )


def _base_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        a_number="123456789",
        country="MEXICO",
        attempts_per_run=1,
        artifact_base_dir=tmp_path / "artifacts",
        state_file=tmp_path / "state" / "findice_state.json",
    )


class TestExecuteRunNotificationState:
    def test_dry_run_positive_does_not_record_hash(self, tmp_path, monkeypatch):
        cfg = _base_config(tmp_path)
        cfg.dry_run = True

        monkeypatch.setattr("findICE.main.run_with_retries", lambda **kwargs: [_positive_result()])
        monkeypatch.setattr(
            "findICE.main.build_notifier",
            lambda **kwargs: [_AlwaysOkNotifier()],
        )

        summary = execute_run(cfg, run_id="run_test_dry")
        assert summary.best_state == ResultState.LIKELY_POSITIVE
        assert summary.notified is False

        store = StateStore(cfg.state_file)
        assert store.is_new_positive(_positive_result().content_hash) is True

    def test_real_notification_records_hash(self, tmp_path, monkeypatch):
        cfg = _base_config(tmp_path)
        cfg.dry_run = False
        cfg.teams_webhook_url = "https://example.com/webhook"

        monkeypatch.setattr("findICE.main.run_with_retries", lambda **kwargs: [_positive_result()])
        monkeypatch.setattr(
            "findICE.main.build_notifier",
            lambda **kwargs: [_AlwaysOkNotifier()],
        )

        summary = execute_run(cfg, run_id="run_test_real")
        assert summary.best_state == ResultState.LIKELY_POSITIVE
        assert summary.notified is True

        store = StateStore(cfg.state_file)
        assert store.is_new_positive(_positive_result().content_hash) is False
