"""Configuration loading for findICE.

Precedence (highest to lowest):
  1. Explicit environment variables
  2. .env file (via python-dotenv)
  3. Keyring (optional; only if FINDICE_USE_KEYRING=true)

All secrets are validated at startup and redacted in logs.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["AppConfig", "load_config"]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENV_FILE_PATHS = [Path(".env"), Path("~/.findice/.env").expanduser()]
KEYRING_SERVICE = "findICE"


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------


@dataclass
class AppConfig:
    """All runtime configuration for findICE.

    Values are sourced from environment variables (see .env.example).
    Do NOT add hard-coded secrets here.
    """

    # --- Required search parameters ---
    a_number: str = ""
    country: str = ""

    # --- Run behaviour ---
    attempts_per_run: int = 4
    attempt_delay_seconds: float = 5.0
    attempt_jitter_seconds: float = 2.0
    headless: bool = True
    page_load_timeout_ms: int = 30_000
    element_timeout_ms: int = 15_000

    # --- Notification ---
    teams_webhook_url: str = ""
    dry_run: bool = False

    # --- Artifact / state paths ---
    artifact_base_dir: Path = field(default_factory=lambda: Path("artifacts"))
    state_file: Path = field(default_factory=lambda: Path("state", "findice_state.json"))

    # --- Logging ---
    log_level: str = "DEBUG"
    log_file: str | None = None

    # --- Keyring ---
    use_keyring: bool = False

    # --- Batch / multi-person ---
    people_file: Path | None = None
    inter_person_delay_seconds: float = 10.0
    timeline_retention_hours: float = 24.0

    # ---------------------------------------------------------------------------
    # Derived / computed properties
    # ---------------------------------------------------------------------------

    @property
    def a_number_masked(self) -> str:
        """A-number with all-but-last-two digits replaced with *."""
        from findICE.logging_utils import mask_a_number

        return mask_a_number(self.a_number)

    @property
    def has_webhook(self) -> bool:
        return bool(self.teams_webhook_url)

    # ---------------------------------------------------------------------------
    # Validation
    # ---------------------------------------------------------------------------

    def validate(self) -> None:
        """Raise ConfigError if required fields are missing or obviously invalid."""
        from findICE.exceptions import ConfigError

        errors: list[str] = []

        a_digits = re.sub(r"\D", "", self.a_number)
        if not a_digits or len(a_digits) not in (8, 9):
            errors.append(
                "A_NUMBER must be an 8- or 9-digit alien registration number "
                f"(got {len(a_digits)} digit(s))"
            )

        if not self.country.strip():
            errors.append("COUNTRY must be set (e.g. 'Mexico' or 'EL SALVADOR')")

        if self.attempts_per_run < 1:
            errors.append("ATTEMPTS_PER_RUN must be >= 1")

        if errors:
            raise ConfigError("Configuration invalid:\n" + "\n".join(f"  • {e}" for e in errors))

    def log_summary(self) -> None:
        """Log a redacted summary of the active config."""
        logger.info(
            "Config: a_number=%s country=%s attempts=%d headless=%s dry_run=%s",
            self.a_number_masked,
            self.country,
            self.attempts_per_run,
            self.headless,
            self.dry_run,
        )


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _load_dotenv() -> None:
    """Attempt to load .env from standard locations (silent if not found)."""
    try:
        from dotenv import load_dotenv as _load
    except ImportError:
        logger.debug("python-dotenv not available; skipping .env loading")
        return

    for path in ENV_FILE_PATHS:
        if path.exists():
            _load(dotenv_path=path, override=False)
            logger.debug("Loaded .env from %s", path)
            return
    logger.debug("No .env file found; using environment only")


def _keyring_get(key: str) -> str | None:
    """Try to retrieve a secret from keyring (returns None if unavailable)."""
    try:
        import keyring  # type: ignore

        value = keyring.get_password(KEYRING_SERVICE, key)
        return value
    except Exception:
        return None


def _get_value(key: str, use_keyring: bool = False) -> str:
    """Resolve a config key: env var first, then keyring."""
    value = os.getenv(key, "")
    if not value and use_keyring:
        value = _keyring_get(key) or ""
    return value


def load_config(
    override_a_number: str | None = None,
    override_country: str | None = None,
    override_attempts: int | None = None,
    override_headless: bool | None = None,
    override_dry_run: bool | None = None,
) -> AppConfig:
    """Load and return a fully-populated AppConfig.

    CLI overrides take precedence over everything else.
    """
    _load_dotenv()

    use_keyring = os.getenv("FINDICE_USE_KEYRING", "false").lower() in (
        "1",
        "true",
        "yes",
    )

    def _safe_int(key: str, default: str) -> int:
        raw = _get_value(key) or default
        try:
            return int(raw)
        except ValueError as err:
            from findICE.exceptions import ConfigError

            raise ConfigError(f"{key} must be an integer (got {raw!r})") from err

    def _safe_float(key: str, default: str) -> float:
        raw = _get_value(key) or default
        try:
            return float(raw)
        except ValueError as err:
            from findICE.exceptions import ConfigError

            raise ConfigError(f"{key} must be a number (got {raw!r})") from err

    cfg = AppConfig(
        a_number=(
            override_a_number
            if override_a_number is not None
            else _get_value("A_NUMBER", use_keyring)
        ),
        country=(
            override_country if override_country is not None else _get_value("COUNTRY", use_keyring)
        ),
        attempts_per_run=(
            override_attempts
            if override_attempts is not None
            else _safe_int("ATTEMPTS_PER_RUN", "4")
        ),
        attempt_delay_seconds=_safe_float("ATTEMPT_DELAY_SECONDS", "5.0"),
        attempt_jitter_seconds=_safe_float("ATTEMPT_JITTER_SECONDS", "2.0"),
        headless=(
            override_headless
            if override_headless is not None
            # An empty/absent HEADLESS env var defaults to True (headless).
            # Only explicit "false", "0", or "no" values disable headless mode.
            else _get_value("HEADLESS", use_keyring).lower() not in ("0", "false", "no")
        ),
        page_load_timeout_ms=_safe_int("PAGE_LOAD_TIMEOUT_MS", "30000"),
        element_timeout_ms=_safe_int("ELEMENT_TIMEOUT_MS", "15000"),
        teams_webhook_url=_get_value("TEAMS_WEBHOOK_URL", use_keyring),
        dry_run=(
            override_dry_run
            if override_dry_run is not None
            else _get_value("DRY_RUN").lower() in ("1", "true", "yes")
        ),
        artifact_base_dir=Path(_get_value("ARTIFACT_BASE_DIR") or "artifacts"),
        state_file=Path(_get_value("STATE_FILE") or "state/findice_state.json"),
        log_level=(_get_value("LOG_LEVEL") or "DEBUG").upper(),
        log_file=_get_value("LOG_FILE") or None,
        use_keyring=use_keyring,
        people_file=(Path(_get_value("PEOPLE_FILE")) if _get_value("PEOPLE_FILE") else None),
        inter_person_delay_seconds=_safe_float("INTER_PERSON_DELAY_SECONDS", "10.0"),
        timeline_retention_hours=_safe_float("TIMELINE_RETENTION_HOURS", "24.0"),
    )

    return cfg
