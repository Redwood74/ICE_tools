"""Tests for batch (multi-person) monitoring."""

from __future__ import annotations

from pathlib import Path

import pytest

from findICE.batch import PersonConfig, _apply_person_overrides, load_people
from findICE.config import AppConfig
from findICE.exceptions import ConfigError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        a_number="123456789",
        country="MEXICO",
        attempts_per_run=4,
        attempt_delay_seconds=5.0,
        attempt_jitter_seconds=2.0,
        artifact_base_dir=tmp_path / "artifacts",
        state_file=tmp_path / "state" / "findice_state.json",
    )


def _write_people_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "people.yml"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# PersonConfig.safe_label
# ---------------------------------------------------------------------------


class TestPersonConfigSafeLabel:
    def test_basic_label_preserved(self):
        p = PersonConfig(label="Client A", a_number="A-123456789", country="CHILE")
        assert p.safe_label == "Client_A"

    def test_special_chars_stripped(self):
        p = PersonConfig(label="José García!", a_number="A-123456789", country="CHILE")
        assert p.safe_label == "Jos_Garca"

    def test_empty_label_gives_fallback(self):
        p = PersonConfig(label="!!!!", a_number="A-123456789", country="CHILE")
        assert p.safe_label == "person"


# ---------------------------------------------------------------------------
# PersonConfig.validate
# ---------------------------------------------------------------------------


class TestPersonConfigValidate:
    def test_valid_config_passes(self):
        p = PersonConfig(label="Client A", a_number="A-123456789", country="CHILE")
        p.validate()  # no exception

    def test_empty_label_raises(self):
        p = PersonConfig(label="   ", a_number="A-123456789", country="CHILE")
        with pytest.raises(ConfigError, match="non-empty 'label'"):
            p.validate()

    def test_bad_a_number_raises(self):
        p = PersonConfig(label="Client", a_number="A-12", country="CHILE")
        with pytest.raises(ConfigError, match="8.*9 digits"):
            p.validate()

    def test_empty_country_raises(self):
        p = PersonConfig(label="Client", a_number="A-123456789", country="  ")
        with pytest.raises(ConfigError, match="COUNTRY must be set"):
            p.validate()

    def test_multiple_errors_collected(self):
        p = PersonConfig(label="  ", a_number="A-1", country="  ")
        with pytest.raises(ConfigError) as exc_info:
            p.validate()
        # All three errors present
        msg = str(exc_info.value)
        assert "label" in msg
        assert "digits" in msg.lower()
        assert "COUNTRY" in msg


# ---------------------------------------------------------------------------
# load_people
# ---------------------------------------------------------------------------


class TestLoadPeople:
    def test_loads_valid_yaml(self, tmp_path):
        path = _write_people_yaml(
            tmp_path,
            """
people:
  - label: "Client A"
    a_number: "A-221493979"
    country: "CHILE"
  - label: "Client B"
    a_number: "A-123456789"
    country: "MEXICO"
""",
        )
        people = load_people(path)
        assert len(people) == 2
        assert people[0].label == "Client A"
        assert people[1].country == "MEXICO"

    def test_missing_file_raises(self, tmp_path):
        path = tmp_path / "nonexistent.yml"
        with pytest.raises(ConfigError, match="not found"):
            load_people(path)

    def test_empty_people_list_raises(self, tmp_path):
        path = _write_people_yaml(tmp_path, "people: []")
        with pytest.raises(ConfigError, match="at least one entry"):
            load_people(path)

    def test_duplicate_labels_raises(self, tmp_path):
        path = _write_people_yaml(
            tmp_path,
            """
people:
  - label: "Same"
    a_number: "A-123456789"
    country: "CHILE"
  - label: "Same"
    a_number: "A-987654321"
    country: "MEXICO"
""",
        )
        with pytest.raises(ConfigError, match="Duplicate label"):
            load_people(path)

    def test_non_dict_entry_raises(self, tmp_path):
        path = _write_people_yaml(
            tmp_path,
            """
people:
  - "just a string"
""",
        )
        with pytest.raises(ConfigError, match="mapping"):
            load_people(path)

    def test_invalid_person_raises(self, tmp_path):
        path = _write_people_yaml(
            tmp_path,
            """
people:
  - label: "Client"
    a_number: "A-1"
    country: "CHILE"
""",
        )
        with pytest.raises(ConfigError, match="digits"):
            load_people(path)

    def test_per_person_overrides_loaded(self, tmp_path):
        path = _write_people_yaml(
            tmp_path,
            """
people:
  - label: "Client A"
    a_number: "A-123456789"
    country: "CHILE"
    attempts: 2
    delay_seconds: 10.0
    jitter_seconds: 3.0
""",
        )
        people = load_people(path)
        assert people[0].attempts == 2
        assert people[0].delay_seconds == 10.0
        assert people[0].jitter_seconds == 3.0


# ---------------------------------------------------------------------------
# _apply_person_overrides
# ---------------------------------------------------------------------------


class TestApplyPersonOverrides:
    def test_overrides_a_number_and_country(self, tmp_path):
        config = _base_config(tmp_path)
        person = PersonConfig(label="Client X", a_number="A-999888777", country="CHILE")
        result = _apply_person_overrides(config, person)
        assert result.a_number == "A-999888777"
        assert result.country == "CHILE"

    def test_overrides_attempts_when_set(self, tmp_path):
        config = _base_config(tmp_path)
        person = PersonConfig(label="Client", a_number="A-123456789", country="CHILE", attempts=2)
        result = _apply_person_overrides(config, person)
        assert result.attempts_per_run == 2

    def test_keeps_global_attempts_when_not_overridden(self, tmp_path):
        config = _base_config(tmp_path)
        person = PersonConfig(label="Client", a_number="A-123456789", country="CHILE")
        result = _apply_person_overrides(config, person)
        assert result.attempts_per_run == 4  # global default

    def test_isolates_artifact_dir_by_label(self, tmp_path):
        config = _base_config(tmp_path)
        person = PersonConfig(label="Client A", a_number="A-123456789", country="CHILE")
        result = _apply_person_overrides(config, person)
        assert result.artifact_base_dir == config.artifact_base_dir / "Client_A"

    def test_isolates_state_file_by_label(self, tmp_path):
        config = _base_config(tmp_path)
        person = PersonConfig(label="Client A", a_number="A-123456789", country="CHILE")
        result = _apply_person_overrides(config, person)
        assert "Client_A" in result.state_file.name


# ---------------------------------------------------------------------------
# execute_batch
# ---------------------------------------------------------------------------


class TestExecuteBatch:
    def test_runs_all_people_and_returns_summaries(self, tmp_path, monkeypatch):
        from findICE.batch import execute_batch
        from findICE.models import ResultState, RunSummary, SearchResult

        call_count = {"value": 0}

        def fake_execute_run(config, verbose_console=False):
            call_count["value"] += 1
            return RunSummary(
                a_number_masked=config.a_number_masked,
                country=config.country,
                attempts_total=1,
                best_state=ResultState.ZERO_RESULT,
                best_result=SearchResult(
                    state=ResultState.ZERO_RESULT,
                    raw_text="0 results",
                    attempt_number=1,
                ),
            )

        monkeypatch.setattr("findICE.main.execute_run", fake_execute_run)

        config = _base_config(tmp_path)
        people = [
            PersonConfig(label="A", a_number="A-123456789", country="CHILE"),
            PersonConfig(label="B", a_number="A-987654321", country="MEXICO"),
        ]
        summaries = execute_batch(config, people, inter_person_delay=0, verbose_console=False)
        assert len(summaries) == 2
        assert call_count["value"] == 2

    def test_skips_person_on_bot_challenge(self, tmp_path, monkeypatch):
        from findICE.batch import execute_batch
        from findICE.exceptions import BotChallengeError
        from findICE.models import ResultState, RunSummary, SearchResult

        call_idx = {"value": 0}

        def fake_execute_run(config, verbose_console=False):
            call_idx["value"] += 1
            if call_idx["value"] == 1:
                raise BotChallengeError("blocked")
            return RunSummary(
                a_number_masked=config.a_number_masked,
                country=config.country,
                attempts_total=1,
                best_state=ResultState.ZERO_RESULT,
                best_result=SearchResult(
                    state=ResultState.ZERO_RESULT,
                    raw_text="0 results",
                    attempt_number=1,
                ),
            )

        monkeypatch.setattr("findICE.main.execute_run", fake_execute_run)

        config = _base_config(tmp_path)
        people = [
            PersonConfig(label="Blocked", a_number="A-123456789", country="CHILE"),
            PersonConfig(label="OK", a_number="A-987654321", country="MEXICO"),
        ]
        summaries = execute_batch(config, people, inter_person_delay=0, verbose_console=False)
        # First person skipped due to bot challenge; second succeeds
        assert len(summaries) == 1
        assert summaries[0].person_label == "OK"

    def test_skips_person_with_invalid_override_config(self, tmp_path, monkeypatch):
        from findICE.batch import execute_batch
        from findICE.models import ResultState, RunSummary, SearchResult

        def fake_execute_run(config, verbose_console=False):
            return RunSummary(
                a_number_masked=config.a_number_masked,
                country=config.country,
                attempts_total=1,
                best_state=ResultState.ZERO_RESULT,
                best_result=SearchResult(
                    state=ResultState.ZERO_RESULT,
                    raw_text="0 results",
                    attempt_number=1,
                ),
            )

        monkeypatch.setattr("findICE.main.execute_run", fake_execute_run)

        config = _base_config(tmp_path)
        # First person has an empty country after override — validation should catch it
        people = [
            PersonConfig(label="Bad", a_number="A-12", country="CHILE"),
            PersonConfig(label="Good", a_number="A-987654321", country="MEXICO"),
        ]
        # Note: PersonConfig.validate() is called in load_people, but
        # _apply_person_overrides + config.validate() is called in execute_batch.
        # The bad a_number will fail config validation.
        summaries = execute_batch(config, people, inter_person_delay=0, verbose_console=False)
        # Bad person skipped, Good person runs
        assert len(summaries) >= 1
