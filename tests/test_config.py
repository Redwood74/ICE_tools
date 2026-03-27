"""Tests for config loading and validation."""

from __future__ import annotations

import pytest

from findICE.config import AppConfig, load_config
from findICE.exceptions import ConfigError


class TestAppConfigValidation:
    def test_valid_8digit_a_number(self):
        cfg = AppConfig(a_number="12345678", country="Mexico")
        cfg.validate()  # should not raise

    def test_valid_9digit_a_number(self):
        cfg = AppConfig(a_number="123456789", country="Mexico")
        cfg.validate()

    def test_valid_formatted_a_number(self):
        cfg = AppConfig(a_number="A-123456789", country="Mexico")
        cfg.validate()

    def test_invalid_a_number_too_short(self):
        cfg = AppConfig(a_number="1234567", country="Mexico")
        with pytest.raises(ConfigError, match="A_NUMBER"):
            cfg.validate()

    def test_invalid_a_number_too_long(self):
        cfg = AppConfig(a_number="1234567890", country="Mexico")
        with pytest.raises(ConfigError, match="A_NUMBER"):
            cfg.validate()

    def test_missing_a_number(self):
        cfg = AppConfig(a_number="", country="Mexico")
        with pytest.raises(ConfigError, match="A_NUMBER"):
            cfg.validate()

    def test_missing_country(self):
        cfg = AppConfig(a_number="123456789", country="")
        with pytest.raises(ConfigError, match="COUNTRY"):
            cfg.validate()

    def test_missing_country_whitespace(self):
        cfg = AppConfig(a_number="123456789", country="   ")
        with pytest.raises(ConfigError, match="COUNTRY"):
            cfg.validate()

    def test_zero_attempts_invalid(self):
        cfg = AppConfig(a_number="123456789", country="Mexico", attempts_per_run=0)
        with pytest.raises(ConfigError, match="ATTEMPTS_PER_RUN"):
            cfg.validate()

    def test_multiple_errors_reported(self):
        cfg = AppConfig(a_number="", country="")
        with pytest.raises(ConfigError) as exc_info:
            cfg.validate()
        msg = str(exc_info.value)
        assert "A_NUMBER" in msg
        assert "COUNTRY" in msg


class TestANumberMasking:
    def test_mask_9digit(self):
        cfg = AppConfig(a_number="123456789", country="Mexico")
        masked = cfg.a_number_masked
        assert masked.endswith("89")
        assert "12345" not in masked

    def test_mask_8digit(self):
        cfg = AppConfig(a_number="12345678", country="Mexico")
        masked = cfg.a_number_masked
        assert masked.endswith("78")

    def test_mask_formatted(self):
        cfg = AppConfig(a_number="A-123456789", country="Mexico")
        masked = cfg.a_number_masked
        assert "12345" not in masked


class TestLoadConfigFromEnv:
    def test_load_from_env_vars(self, monkeypatch):
        monkeypatch.setenv("A_NUMBER", "987654321")
        monkeypatch.setenv("COUNTRY", "El Salvador")
        monkeypatch.setenv("ATTEMPTS_PER_RUN", "3")
        monkeypatch.setenv("DRY_RUN", "true")

        cfg = load_config()
        assert cfg.a_number == "987654321"
        assert cfg.country == "El Salvador"
        assert cfg.attempts_per_run == 3
        assert cfg.dry_run is True

    def test_override_a_number(self, monkeypatch):
        monkeypatch.setenv("A_NUMBER", "111111111")
        cfg = load_config(override_a_number="999999999")
        assert cfg.a_number == "999999999"

    def test_override_attempts_zero_is_respected(self, monkeypatch):
        monkeypatch.setenv("ATTEMPTS_PER_RUN", "4")
        cfg = load_config(override_attempts=0)
        assert cfg.attempts_per_run == 0

    def test_headless_default_true(self, monkeypatch):
        # Keep HEADLESS explicitly empty so local .env files cannot override it.
        monkeypatch.setenv("HEADLESS", "")
        cfg = load_config()
        assert cfg.headless is True

    def test_headless_false(self, monkeypatch):
        monkeypatch.setenv("HEADLESS", "false")
        cfg = load_config()
        assert cfg.headless is False
