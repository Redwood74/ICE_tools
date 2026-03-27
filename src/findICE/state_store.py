"""Persistent state store for findICE.

Stores a rolling timeline of run results and recent positive hashes in a
local JSON file so that we can deduplicate notifications across runs.

Schema (state_store.json) — v2 (timeline-based):
{
  "schema_version": 2,
  "last_positive_hash": "<sha256 hex or null>",
  "last_positive_at": "<ISO-8601 or null>",
  "last_run_at": "<ISO-8601 or null>",
  "last_success_at": "<ISO-8601 or null>",
  "run_count": <int>,
  "timeline": [
    {
      "timestamp": "<ISO-8601>",
      "state": "<ResultState value>",
      "hash": "<sha256 hex or null>",
      "run_id": "<string>"
    }
  ],
  "recent_hashes": ["<hash>", ...]    // kept for backward compat
}
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import stat
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from filelock import FileLock

from findICE.exceptions import StateStoreError

logger = logging.getLogger(__name__)

# Maximum count of hashes to keep (safety cap alongside time-based)
MAX_RECENT_HASHES = 100

# Default timeline retention (can be overridden via config)
DEFAULT_RETENTION_HOURS = 24.0


class StateStore:
    """JSON-backed state store for deduplication and run tracking."""

    def __init__(
        self,
        path: Path,
        retention_hours: float = DEFAULT_RETENTION_HOURS,
    ) -> None:
        self.path = path
        self.retention_hours = retention_hours
        self._lock = FileLock(str(path) + ".lock")
        self._state: dict = {}
        self._load()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def is_new_positive(self, content_hash: str) -> bool:
        """Return True if *content_hash* has NOT been notified before.

        Only checks the ``recent_hashes`` list (populated by
        ``record_positive_sent``).  The timeline records all runs but is
        not used for dedup — a dry-run hash must not suppress future
        notifications.
        """
        self._prune_timeline()
        recent: list[str] = self._state.get("recent_hashes", [])
        return content_hash not in recent

    def record_positive_sent(self, content_hash: str) -> None:
        """Record that a positive result with *content_hash* was just notified."""
        now = datetime.now(timezone.utc).isoformat()
        recent: list[str] = self._state.get("recent_hashes", [])
        if content_hash not in recent:
            recent.insert(0, content_hash)
            self._state["recent_hashes"] = recent[:MAX_RECENT_HASHES]
        self._state["last_positive_hash"] = content_hash
        self._state["last_positive_at"] = now
        self._save()

    def record_run(
        self,
        summary_dict: dict | None = None,
        run_id: str = "",
        state_value: str = "",
        content_hash: str | None = None,
    ) -> None:
        """Update bookkeeping after each run completes."""
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        self._state["last_run_at"] = now_iso
        self._state["run_count"] = self._state.get("run_count", 0) + 1
        self._state["schema_version"] = 2

        # Record success timestamp for health-check
        if state_value and state_value != "ERROR":
            self._state["last_success_at"] = now_iso

        # Append to timeline
        timeline: list[dict] = self._state.setdefault("timeline", [])
        timeline.insert(
            0,
            {
                "timestamp": now_iso,
                "state": state_value or (summary_dict or {}).get("best_state", ""),
                "hash": content_hash,
                "run_id": run_id,
            },
        )

        if summary_dict:
            self._state["last_run_summary"] = summary_dict
        self._save()

    @property
    def last_positive_hash(self) -> str | None:
        return self._state.get("last_positive_hash")

    @property
    def last_success_at(self) -> str | None:
        return self._state.get("last_success_at")

    @property
    def run_count(self) -> int:
        return self._state.get("run_count", 0)

    @property
    def timeline(self) -> list[dict]:
        return self._state.get("timeline", [])

    # ------------------------------------------------------------------
    # Timeline pruning
    # ------------------------------------------------------------------

    def _prune_timeline(self) -> None:
        """Remove timeline entries older than the retention window."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        cutoff_iso = cutoff.isoformat()

        timeline: list[dict] = self._state.get("timeline", [])
        pruned = [e for e in timeline if e.get("timestamp", "") >= cutoff_iso]

        if len(pruned) < len(timeline):
            removed = len(timeline) - len(pruned)
            logger.debug(
                "Pruned %d timeline entries older than %.1fh",
                removed,
                self.retention_hours,
            )
            self._state["timeline"] = pruned

    def purge_old_artifacts(self, artifact_base_dir: Path) -> int:
        """Delete artifact run directories older than the retention window.

        Keeps run_summary.json from each deleted directory for history.

        Returns:
            Number of directories purged.
        """
        if not artifact_base_dir.exists():
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        purged = 0

        with self._lock:
            for run_dir in sorted(artifact_base_dir.iterdir()):
                if not run_dir.is_dir() or not run_dir.name.startswith("run_"):
                    continue

                # Parse timestamp from directory name: run_YYYYMMDDTHHMMSSZ
                try:
                    ts_str = run_dir.name.split("_", 1)[1]
                    dir_time = datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ").replace(
                        tzinfo=timezone.utc
                    )
                except (ValueError, IndexError):
                    continue

                if dir_time >= cutoff:
                    continue

                # Preserve run_summary.json before deleting
                summary_src = run_dir / "run_summary.json"
                if summary_src.exists():
                    archive_dir = artifact_base_dir / "_history"
                    archive_dir.mkdir(parents=True, exist_ok=True)
                    summary_dst = archive_dir / f"{run_dir.name}_summary.json"
                    try:
                        shutil.copy2(str(summary_src), str(summary_dst))
                    except OSError as exc:
                        logger.warning("Could not archive summary for %s: %s", run_dir.name, exc)

                try:
                    shutil.rmtree(str(run_dir))
                    purged += 1
                    logger.debug("Purged old artifact directory: %s", run_dir.name)
                except OSError as exc:
                    logger.warning("Could not purge %s: %s", run_dir.name, exc)

        if purged:
            logger.info(
                "Purged %d artifact directories older than %.1fh",
                purged,
                self.retention_hours,
            )

        return purged

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        with self._lock:
            if self.path.exists():
                try:
                    self._state = json.loads(self.path.read_text(encoding="utf-8"))
                    logger.debug("State loaded from %s", self.path)
                    # Migrate v1 → v2 if needed
                    if self._state.get("schema_version", 1) < 2:
                        self._state.setdefault("timeline", [])
                        self._state.setdefault("last_success_at", None)
                        self._state["schema_version"] = 2
                except Exception as exc:
                    logger.warning(
                        "Could not read state file %s: %s – starting fresh",
                        self.path,
                        exc,
                    )
                    self._state = {}
            else:
                logger.debug("No state file at %s – starting fresh", self.path)
                self._state = {}

    def _save(self) -> None:
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                # Atomic write via temp file to avoid corruption on crash
                fd, tmp_path = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(self._state, f, indent=2, default=str)
                    # Restrict permissions before moving into place
                    if sys.platform == "win32":
                        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
                    else:
                        os.chmod(tmp_path, 0o600)
                    shutil.move(tmp_path, str(self.path))
                except BaseException:
                    # Clean up temp file on failure
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    raise
                logger.debug("State saved to %s", self.path)
            except Exception as exc:
                raise StateStoreError(f"Failed to save state to {self.path}: {exc}") from exc
