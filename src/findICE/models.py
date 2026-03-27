"""Data models for findICE."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

__all__ = ["ResultState", "SearchResult", "RunSummary", "NotificationPayload"]


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
    detention_facility: str | None = None
    facility_address: str | None = None
    visitor_information: str | None = None
    ero_office_name: str | None = None
    ero_office_phone: str | None = None
    facility_more_information_url: str | None = None
    facility_more_information_title: str = ""
    facility_more_information_text: str = ""
    facility_tabs: dict[str, str] = field(default_factory=dict)
    facility_tab_details: dict[str, dict[str, object]] = field(default_factory=dict)
    facility_contacting_a_detainee: str = ""
    facility_legal_and_case_information: str = ""
    facility_hours_of_visitation: str = ""
    facility_sending_items_to_detainees: str = ""
    facility_press_and_media: str = ""
    facility_feedback_or_complaints: str = ""
    detail_page_text: str = ""
    detail_page_title: str = ""
    detail_page_url: str = ""
    screenshot_path: str | None = None
    html_path: str | None = None
    detail_page_screenshot_path: str | None = None
    detail_page_html_path: str | None = None
    detail_page_text_path: str | None = None
    facility_more_information_screenshot_path: str | None = None
    facility_more_information_html_path: str | None = None
    facility_more_information_text_path: str | None = None
    error_detail: str | None = None
    attempt_number: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def content_hash(self) -> str:
        """Stable SHA-256 hash of the normalised raw text, for deduplication."""
        normalised = (
            (
                f"{self.raw_text}\n{self.detail_page_text}\n{self.facility_more_information_text}"
            )
            .strip()
            .lower()
        )
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
    person_label: str | None = None

    def to_dict(self) -> dict:
        return {
            "person_label": self.person_label,
            "a_number_masked": self.a_number_masked,
            "country": self.country,
            "attempts_total": self.attempts_total,
            "best_state": self.best_state.value,
            "all_states": [s.value for s in self.all_states],
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "notified": self.notified,
            "artifact_dir": self.artifact_dir,
            "best_result_hash": (
                self.best_result.content_hash if self.best_result else None
            ),
            "best_result_hash_prefix": (
                self.best_result.hash_prefix if self.best_result else None
            ),
            "detention_facility": (
                self.best_result.detention_facility if self.best_result else None
            ),
            "facility_address": (
                self.best_result.facility_address if self.best_result else None
            ),
            "visitor_information": (
                self.best_result.visitor_information if self.best_result else None
            ),
            "ero_office_name": (
                self.best_result.ero_office_name if self.best_result else None
            ),
            "ero_office_phone": (
                self.best_result.ero_office_phone if self.best_result else None
            ),
            "detail_page_url": (
                self.best_result.detail_page_url if self.best_result else None
            ),
            "facility_more_information_url": (
                self.best_result.facility_more_information_url
                if self.best_result
                else None
            ),
            "facility_more_information_title": (
                self.best_result.facility_more_information_title
                if self.best_result
                else None
            ),
            "facility_tabs": (
                self.best_result.facility_tabs if self.best_result else None
            ),
            "facility_tab_details": (
                self.best_result.facility_tab_details if self.best_result else None
            ),
            "facility_contacting_a_detainee": (
                self.best_result.facility_contacting_a_detainee
                if self.best_result
                else None
            ),
            "facility_legal_and_case_information": (
                self.best_result.facility_legal_and_case_information
                if self.best_result
                else None
            ),
            "facility_hours_of_visitation": (
                self.best_result.facility_hours_of_visitation
                if self.best_result
                else None
            ),
            "facility_sending_items_to_detainees": (
                self.best_result.facility_sending_items_to_detainees
                if self.best_result
                else None
            ),
            "facility_press_and_media": (
                self.best_result.facility_press_and_media if self.best_result else None
            ),
            "facility_feedback_or_complaints": (
                self.best_result.facility_feedback_or_complaints
                if self.best_result
                else None
            ),
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
