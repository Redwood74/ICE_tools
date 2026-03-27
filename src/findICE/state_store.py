"""Persistent state store for findICE.

Stores the last-sent positive hash and recent run metadata in a local JSON
file so that we can deduplicate Teams alerts across runs.

Schema (state_store.json):
{
  "last_positive_hash": "<sha256 hex or null>",
  "last_positive_at": "<ISO-8601 or null>",
  "last_run_at": "<ISO-8601 or null>",
  "run_count": <int>,
  "recent_hashes": ["<hash>", ...]   // sliding window, newest first
}
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from findICE.exceptions import StateStoreError

logger = logging.getLogger(__name__)

# How many recent hashes to remember for deduplication
RECENT_HASH_WINDOW = 20


class StateStore:
    """JSON-backed state store for deduplication and run tracking."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._state: dict = {}
        self._load()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def is_new_positive(self, content_hash: str) -> bool:
        """Return True if *content_hash* has NOT been seen before."""
        recent: list[str] = self._state.get("recent_hashes", [])
        return content_hash not in recent

    def record_positive_sent(self, content_hash: str) -> None:
        """Record that a positive result with *content_hash* was just notified."""
        now = datetime.now(timezone.utc).isoformat()
        recent: list[str] = self._state.get("recent_hashes", [])
        if content_hash not in recent:
            recent.insert(0, content_hash)
            # Trim to window size
            self._state["recent_hashes"] = recent[:RECENT_HASH_WINDOW]
        self._state["last_positive_hash"] = content_hash
        self._state["last_positive_at"] = now
        self._save()

    def record_run(self, summary_dict: dict | None = None) -> None:
        """Update bookkeeping after each run completes."""
        self._state["last_run_at"] = datetime.now(timezone.utc).isoformat()
        self._state["run_count"] = self._state.get("run_count", 0) + 1
        if summary_dict:
            self._state["last_run_summary"] = summary_dict
        self._save()

    @property
    def last_positive_hash(self) -> str | None:
        return self._state.get("last_positive_hash")

    @property
    def run_count(self) -> int:
        return self._state.get("run_count", 0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._state = json.loads(self.path.read_text(encoding="utf-8"))
                logger.debug("State loaded from %s", self.path)
            except Exception as exc:
                logger.warning(
                    "Could not read state file %s: %s – starting fresh", self.path, exc
                )
                self._state = {}
        else:
            logger.debug("No state file at %s – starting fresh", self.path)
            self._state = {}

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self._state, indent=2, default=str), encoding="utf-8"
            )
            logger.debug("State saved to %s", self.path)
        except Exception as exc:
            raise StateStoreError(f"Failed to save state to {self.path}: {exc}") from exc
