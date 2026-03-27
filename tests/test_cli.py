"""Tests for CLI command handlers."""

from __future__ import annotations

import argparse

from findICE.cli import cmd_smoke_test
from findICE.config import AppConfig
from findICE.models import ResultState, RunSummary


def _smoke_args(
    fixture_dir: str | None = None,
    live: bool = False,
    attempts: int = 1,
    headed: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        fixture_dir=fixture_dir,
        live=live,
        attempts=attempts,
        headed=headed,
    )


class TestSmokeTestFixtures:
    def test_fixture_mode_passes_when_expected_states_match(self, tmp_path):
        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir()
        (fixture_dir / "zero_result.txt").write_text("0 search results", encoding="utf-8")
        (fixture_dir / "likely_positive.txt").write_text(
            "facility detention book-in date", encoding="utf-8"
        )
        (fixture_dir / "ambiguous.txt").write_text(
            "This page loaded but classification should remain unclear with enough length.",
            encoding="utf-8",
        )
        (fixture_dir / "bot_blocked.txt").write_text(
            "verify you are human captcha required", encoding="utf-8"
        )

        rc = cmd_smoke_test(_smoke_args(fixture_dir=str(fixture_dir)))
        assert rc == 0

    def test_fixture_mode_fails_when_expected_state_mismatches(self, tmp_path):
        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir()
        (fixture_dir / "likely_positive.txt").write_text("0 search results", encoding="utf-8")

        rc = cmd_smoke_test(_smoke_args(fixture_dir=str(fixture_dir)))
        assert rc == 1


class TestSmokeTestLiveMode:
    def test_live_mode_uses_dotenv_config_forced_dry_run(self, monkeypatch):
        seen: dict[str, object] = {}

        def fake_load_config(
            override_a_number=None,
            override_country=None,
            override_attempts=None,
            override_headless=None,
            override_dry_run=None,
        ):
            seen["override_attempts"] = override_attempts
            seen["override_headless"] = override_headless
            seen["override_dry_run"] = override_dry_run
            return AppConfig(
                a_number="123456789",
                country="MEXICO",
                attempts_per_run=override_attempts or 1,
                headless=True if override_headless is None else override_headless,
                dry_run=bool(override_dry_run),
            )

        def fake_execute_run(cfg, run_id=None, verbose_console=False):
            return RunSummary(
                a_number_masked=cfg.a_number_masked,
                country=cfg.country,
                attempts_total=cfg.attempts_per_run,
                best_state=ResultState.ZERO_RESULT,
                best_result=None,
            )

        monkeypatch.setattr("findICE.config.load_config", fake_load_config)
        monkeypatch.setattr("findICE.main.execute_run", fake_execute_run)

        rc = cmd_smoke_test(_smoke_args(live=True, attempts=2, headed=False))

        assert rc == 0
        assert seen["override_attempts"] == 2
        assert seen["override_headless"] is None
        assert seen["override_dry_run"] is True
