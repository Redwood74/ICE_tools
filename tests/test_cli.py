"""Tests for CLI command handlers."""

from __future__ import annotations

import argparse

from findICE.cli import (
    _build_parser,
    cmd_classify_sample,
    cmd_print_config,
    cmd_smoke_test,
    cmd_verify_webhook,
    main,
)
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
        (fixture_dir / "zero_result.txt").write_text(
            "0 search results", encoding="utf-8"
        )
        (fixture_dir / "likely_positive.txt").write_text(
            (
                "1 Search Result\n"
                "Detainee Information\n"
                "A-Number: 123456789\n"
                "Book-In Date: 01/15/2024\n"
                "Current Detention Facility: Example Facility\n"
            ),
            encoding="utf-8",
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
        (fixture_dir / "likely_positive.txt").write_text(
            "0 search results", encoding="utf-8"
        )

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


# ---------------------------------------------------------------------------
# _build_parser
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_all_subcommands_present(self):
        parser = _build_parser()
        # Parse each known command to verify it's registered
        for cmd in [
            "check-once",
            "check-batch",
            "smoke-test",
            "print-config",
            "verify-webhook",
            "classify-sample",
            "setup",
        ]:
            args = parser.parse_args([cmd])
            assert args.command == cmd

    def test_version_flag(self, capsys):
        parser = _build_parser()
        import pytest

        with pytest.raises(SystemExit, match="0"):
            parser.parse_args(["--version"])

    def test_no_command_gives_none(self):
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.command is None


# ---------------------------------------------------------------------------
# cmd_print_config
# ---------------------------------------------------------------------------


class TestCmdPrintConfig:
    def test_prints_config(self, monkeypatch, capsys):
        def fake_load_config(**kwargs):
            return AppConfig(
                a_number="123456789",
                country="MEXICO",
                attempts_per_run=4,
            )

        monkeypatch.setattr("findICE.config.load_config", fake_load_config)
        args = argparse.Namespace()
        rc = cmd_print_config(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "MEXICO" in out


# ---------------------------------------------------------------------------
# cmd_classify_sample
# ---------------------------------------------------------------------------


class TestCmdClassifySample:
    def test_list_option(self, caplog):
        import logging

        with caplog.at_level(logging.INFO, logger="findICE.cli"):
            args = argparse.Namespace(sample=None, list=True)
            rc = cmd_classify_sample(args)
        assert rc == 0
        assert "zero" in caplog.text.lower()

    def test_unknown_sample(self):
        args = argparse.Namespace(sample="nonexistent", list=False)
        rc = cmd_classify_sample(args)
        assert rc == 1

    def test_no_sample_given(self):
        args = argparse.Namespace(sample=None, list=False)
        rc = cmd_classify_sample(args)
        assert rc == 1

    def test_classifies_zero_fixture(self, caplog):
        """Classify the 'zero' fixture using real fixture files."""
        import logging

        with caplog.at_level(logging.INFO, logger="findICE.cli"):
            args = argparse.Namespace(sample="zero", list=False)
            rc = cmd_classify_sample(args)
        assert rc == 0
        assert "ZERO_RESULT" in caplog.text


# ---------------------------------------------------------------------------
# cmd_verify_webhook
# ---------------------------------------------------------------------------


class TestCmdVerifyWebhook:
    def test_no_webhook_returns_1(self, monkeypatch, caplog):
        import logging

        def fake_load_config(**kwargs):
            return AppConfig(
                a_number="123456789",
                country="MEXICO",
                teams_webhook_url="",
            )

        monkeypatch.setattr("findICE.config.load_config", fake_load_config)
        with caplog.at_level(logging.ERROR, logger="findICE.cli"):
            args = argparse.Namespace()
            rc = cmd_verify_webhook(args)
        assert rc == 1
        assert "not configured" in caplog.text.lower()


# ---------------------------------------------------------------------------
# main() dispatch
# ---------------------------------------------------------------------------


class TestMainDispatch:
    def test_no_command_prints_help(self, capsys):
        import pytest

        with pytest.raises(SystemExit, match="0"):
            main([])

    def test_unknown_command_exits_1(self, capsys):
        import pytest

        with pytest.raises(SystemExit):
            main(["nonexistent-command"])
