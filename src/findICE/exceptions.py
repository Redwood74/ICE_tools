"""Custom exceptions for findICE."""

from __future__ import annotations


class FindICEError(Exception):
    """Base class for all findICE errors."""


class ConfigError(FindICEError):
    """Raised when configuration is invalid or missing required values."""


class BotChallengeError(FindICEError):
    """Raised when the ICE site presents a bot/CAPTCHA challenge or blocks access."""

    EXIT_CODE: int = 3


class ArtifactError(FindICEError):
    """Raised when artifact saving fails."""


class NotificationError(FindICEError):
    """Raised when a notification attempt fails."""


class StateStoreError(FindICEError):
    """Raised when state persistence fails."""


class SelectorError(FindICEError):
    """Raised when no selector resolves to a usable element."""


class ClassificationError(FindICEError):
    """Raised when classification logic encounters an unrecoverable error."""
