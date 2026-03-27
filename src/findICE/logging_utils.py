"""Structured logging utilities for findICE.

Provides:
- A pre-configured logger factory that masks sensitive values.
- A redaction helper for A-numbers and other PII.
- A structured-log filter that enforces redaction at emit time.
"""

from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------------------------
# Redaction helpers
# ---------------------------------------------------------------------------

# A-numbers: 8 or 9 digits, sometimes written A-XXXXXXXX or AXXXXXXXXX
_A_NUMBER_RE = re.compile(r"\bA[-\s]?(\d{7,9})\b", re.IGNORECASE)

# Generic 8–9 digit sequences that look like A-numbers
_RAW_DIGIT_RE = re.compile(r"\b(\d{8,9})\b")


def mask_a_number(value: str) -> str:
    """Replace A-number digits with **** keeping prefix and last 2 digits visible.

    Example:
        "A-123456789" -> "A-*******89"
        "A 123456789" -> "A *******89"
        "123456789"   -> "*******89"
    """

    def _replace_prefixed(m: re.Match) -> str:
        # Group 1 is the digit portion; group 0 is the full match (e.g. "A-123456789")
        digits = m.group(1)
        masked_digits = ("*" * (len(digits) - 2)) + digits[-2:]
        full = m.group(0)
        return full.replace(digits, masked_digits)

    def _replace_raw(m: re.Match) -> str:
        digits = m.group(0)
        return ("*" * (len(digits) - 2)) + digits[-2:]

    # First mask A-prefixed patterns
    result = _A_NUMBER_RE.sub(_replace_prefixed, value)
    # Then mask any remaining standalone 8-9 digit sequences
    result = _RAW_DIGIT_RE.sub(_replace_raw, result)
    return result


def redact_text(text: str, a_number: str | None = None) -> str:
    """Redact an A-number (if known) and any lookalike digit sequences from text."""
    if a_number:
        # Strip formatting from the known A-number for matching
        digits_only = re.sub(r"\D", "", a_number)
        if digits_only:
            text = text.replace(a_number, mask_a_number(a_number))
            text = text.replace(digits_only, ("*" * (len(digits_only) - 2)) + digits_only[-2:])
    return mask_a_number(text)


# ---------------------------------------------------------------------------
# Logging filter
# ---------------------------------------------------------------------------


class RedactingFilter(logging.Filter):
    """A log filter that scrubs A-numbers from all log records at emit time."""

    def __init__(self, a_number: str | None = None) -> None:
        super().__init__()
        self.a_number = a_number

    def filter(self, record: logging.LogRecord) -> bool:
        if record.msg and isinstance(record.msg, str):
            record.msg = redact_text(record.msg, self.a_number)
        if record.args:

            def _redact_arg(arg):
                if isinstance(arg, str):
                    return redact_text(arg, self.a_number)
                return arg

            if isinstance(record.args, dict):
                record.args = {k: _redact_arg(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(_redact_arg(a) for a in record.args)
        return True


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------

_HANDLER_INSTALLED = False


def configure_logging(
    level: int = logging.DEBUG,
    a_number: str | None = None,
    log_file: str | None = None,
) -> None:
    """Configure the root logger with a consistent format and redaction filter.

    Call once at application startup (CLI entry point).
    """
    global _HANDLER_INSTALLED

    fmt = "%(asctime)s [%(levelname)-8s] %(name)s – %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%SZ"

    root = logging.getLogger()
    root.setLevel(level)

    if not _HANDLER_INSTALLED:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        root.addHandler(handler)
        _HANDLER_INSTALLED = True

    if log_file:
        fh = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        root.addHandler(fh)

    if a_number:
        redacting_filter = RedactingFilter(a_number)
        for h in root.handlers:
            h.addFilter(redacting_filter)


def get_logger(name: str) -> logging.Logger:
    """Return a named child logger under the 'findICE' hierarchy."""
    return logging.getLogger(f"findICE.{name}")
