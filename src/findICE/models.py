"""Data models for findICE."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ResultState(str, Enum):
    """Conservative classification of an ICE locator query outcome."""

    ZERO_RESULT = "ZERO_RESULT"
    LIKELY_POSITIVE = "LIKELY_POSITIVE"
    AMBIGUOUS_REVIEW = "AMBIGUOUS_REVIEW"
    BOT_CHALLENGE_OR_BLOCKED = "BOT_CHALLENGE_OR_BLOCKED"
    ERROR = "ERROR"


@dataclass
class SearchResult:
    """Result of a single ICE locator search attempt."""

    state: ResultState
    raw_text: str
    page_title: str = ""
    screenshot_path: str | None = None
    html_path: str | None = None
    error_detail: str | None = None
    attempt_number: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def content_hash(self) -> str:
        """Stable SHA-256 hash of the normalised raw text, for deduplication."""
        normalised = self.raw_text.strip().lower()
        return hashlib.sha256(normalised.encode()).hexdigest()

    @property
    def hash_prefix(self) -> str:
        """Short (12-char) prefix of the content hash for display."""
        return self.content_hash[:12]


@dataclass
class RunSummary:
    """Aggregated summary of a full multi-attempt run."""

    a_number_masked: str
    country: str
    attempts_total: int
    best_state: ResultState
    best_result: SearchResult | None
    all_states: list[ResultState] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    notified: bool = False
    artifact_dir: str | None = None

    def to_dict(self) -> dict:
        return {
            "a_number_masked": self.a_number_masked,
            "country": self.country,
            "attempts_total": self.attempts_total,
            "best_state": self.best_state.value,
            "all_states": [s.value for s in self.all_states],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notified": self.notified,
            "artifact_dir": self.artifact_dir,
            "best_result_hash": self.best_result.content_hash if self.best_result else None,
            "best_result_hash_prefix": self.best_result.hash_prefix if self.best_result else None,
        }


@dataclass
class NotificationPayload:
    """Structured payload for a Teams (or other) notification."""

    a_number_masked: str
    country: str
    state: ResultState
    attempts: int
    hash_prefix: str
    text_preview: str
    timestamp: datetime
    run_id: str = ""

    def to_teams_card(self) -> dict:
        """Render as a Microsoft Teams Adaptive Card (message card format)."""
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0076D7",
            "summary": f"ICEpicks alert – {self.state.value}",
            "sections": [
                {
                    "activityTitle": f"🔎 ICEpicks – {self.state.value}",
                    "activitySubtitle": self.timestamp.strftime("%Y-%m-%d %H:%M UTC"),
                    "facts": [
                        {"name": "A-Number", "value": self.a_number_masked},
                        {"name": "Country", "value": self.country},
                        {"name": "Result State", "value": self.state.value},
                        {"name": "Attempts", "value": str(self.attempts)},
                        {"name": "Hash prefix", "value": self.hash_prefix},
                        {"name": "Preview", "value": self.text_preview[:200]},
                        {"name": "Run ID", "value": self.run_id or "(none)"},
                    ],
                    "markdown": True,
                }
            ],
        }
