"""Batch (multi-person) monitoring for findICE.

Loads a YAML file listing multiple people to monitor and runs each in
sequence with isolated artifacts and state.

Schema (people.yml):
  people:
    - label: "Client A"
      a_number: "A-221493979"
      country: "CHILE"
    - label: "Client B"
      a_number: "A-123456789"
      country: "MEXICO"
      attempts: 2            # optional per-person override
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from findICE.config import AppConfig
from findICE.exceptions import ConfigError

logger = logging.getLogger(__name__)

__all__ = ["PersonConfig", "load_people", "execute_batch"]

# Safe subset of characters for directory names
_LABEL_RE = re.compile(r"[^a-zA-Z0-9_\- ]")


@dataclass
class PersonConfig:
    """Configuration for a single monitored person."""

    label: str
    a_number: str
    country: str

    # Optional per-person overrides (None = use global AppConfig default)
    attempts: int | None = None
    delay_seconds: float | None = None
    jitter_seconds: float | None = None

    @property
    def safe_label(self) -> str:
        """Filesystem-safe version of the label (for directory names)."""
        cleaned = _LABEL_RE.sub("", self.label).strip().replace(" ", "_")
        return cleaned or "person"

    def validate(self) -> None:
        """Raise ConfigError if this person's config is invalid."""
        errors: list[str] = []

        if not self.label.strip():
            errors.append("Each person must have a non-empty 'label'")

        a_digits = re.sub(r"\D", "", self.a_number)
        if not a_digits or len(a_digits) not in (8, 9):
            errors.append(f"A_NUMBER must be 8–9 digits for '{self.label}' (got '{self.a_number}')")

        if not self.country.strip():
            errors.append(f"COUNTRY must be set for '{self.label}'")

        if errors:
            raise ConfigError(
                f"Person config invalid for '{self.label}':\n"
                + "\n".join(f"  • {e}" for e in errors)
            )


def load_people(path: Path) -> list[PersonConfig]:
    """Load and validate a people.yml file.

    Returns:
        List of PersonConfig, one per person to monitor.

    Raises:
        ConfigError: if the file is missing, malformed, or any person invalid.
    """
    if not path.exists():
        raise ConfigError(f"People file not found: {path}")

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        raise ConfigError(
            "PyYAML is required for multi-person mode. Install with: pip install pyyaml"
        ) from None

    try:
        raw = path.read_text(encoding="utf-8")
        data: dict[str, Any] = yaml.safe_load(raw) or {}
    except Exception as exc:
        raise ConfigError(f"Could not parse {path}: {exc}") from exc

    people_list = data.get("people")
    if not isinstance(people_list, list) or not people_list:
        raise ConfigError(f"'{path}' must contain a 'people' list with at least one entry")

    # Validate entries are dicts before accessing attributes
    for entry in people_list:
        if not isinstance(entry, dict):
            raise ConfigError(f"Each item in 'people' must be a mapping, got: {entry!r}")

    # Check for duplicate labels
    labels = [p.get("label", "") for p in people_list]
    seen: set[str] = set()
    for lbl in labels:
        if lbl in seen:
            raise ConfigError(f"Duplicate label '{lbl}' in {path}")
        seen.add(lbl)

    people: list[PersonConfig] = []
    for entry in people_list:
        person = PersonConfig(
            label=str(entry.get("label", "")),
            a_number=str(entry.get("a_number", "")),
            country=str(entry.get("country", "")),
            attempts=entry.get("attempts"),
            delay_seconds=entry.get("delay_seconds"),
            jitter_seconds=entry.get("jitter_seconds"),
        )
        person.validate()
        people.append(person)

    logger.info("Loaded %d people from %s", len(people), path)
    return people


def _apply_person_overrides(config: AppConfig, person: PersonConfig) -> AppConfig:
    """Return a copy of *config* with per-person overrides applied.

    The person's a_number and country always replace the global values.
    Optional per-person fields (attempts, delay, jitter) override only if set.
    Artifacts and state are isolated by person label.
    """
    from dataclasses import replace

    return replace(
        config,
        a_number=person.a_number,
        country=person.country,
        attempts_per_run=(
            person.attempts if person.attempts is not None else config.attempts_per_run
        ),
        attempt_delay_seconds=(
            person.delay_seconds
            if person.delay_seconds is not None
            else config.attempt_delay_seconds
        ),
        attempt_jitter_seconds=(
            person.jitter_seconds
            if person.jitter_seconds is not None
            else config.attempt_jitter_seconds
        ),
        artifact_base_dir=config.artifact_base_dir / person.safe_label,
        state_file=config.state_file.parent / f"{person.safe_label}_state.json",
    )


def execute_batch(
    config: AppConfig,
    people: list[PersonConfig],
    inter_person_delay: float = 10.0,
    verbose_console: bool = False,
) -> list:
    """Run execute_run() for each person with isolated state and artifacts.

    Args:
        config: Base AppConfig (global settings).
        people: List of PersonConfig to monitor.
        inter_person_delay: Seconds to wait between people.
        verbose_console: Print results to console.

    Returns:
        List of RunSummary objects, one per person.
    """
    from findICE.exceptions import BotChallengeError
    from findICE.main import execute_run

    summaries = []
    total = len(people)

    for i, person in enumerate(people, 1):
        logger.info("Batch [%d/%d]: starting check for '%s'", i, total, person.label)

        person_config = _apply_person_overrides(config, person)

        try:
            person_config.validate()
        except ConfigError as exc:
            logger.error("Skipping '%s': %s", person.label, exc)
            continue

        try:
            summary = execute_run(person_config, verbose_console=verbose_console)
        except BotChallengeError as exc:
            logger.error(
                "Batch [%d/%d]: '%s' hit bot challenge – skipping: %s",
                i,
                total,
                person.label,
                exc,
            )
            continue
        summary.person_label = person.label
        summaries.append(summary)

        facility = ""
        if summary.best_result and summary.best_result.detention_facility:
            facility = f" facility={summary.best_result.detention_facility}"
        logger.info(
            "Batch [%d/%d]: '%s' → %s%s",
            i,
            total,
            person.label,
            summary.best_state.value,
            facility,
        )

        # Inter-person delay (skip after the last person)
        if i < total and inter_person_delay > 0:
            logger.debug("Waiting %.1fs before next person", inter_person_delay)
            time.sleep(inter_person_delay)

    logger.info("Batch complete: %d/%d people checked", len(summaries), total)
    return summaries
