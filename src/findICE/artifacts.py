"""Local artifact storage for findICE.

Artifacts saved per attempt:
  - screenshot (.png)
  - raw HTML (.html)
  - extracted text (.txt)
  - JSON run summary (.json)

Directory layout:
  <artifact_base_dir>/
    <run_id>/
      attempt_<N>_<state>.png
      attempt_<N>_<state>.html
      attempt_<N>_<state>.txt
      run_summary.json
      run.log          ← log reference / snippet (written by caller)
"""

from __future__ import annotations

import json
import logging
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from findICE.exceptions import ArtifactError
from findICE.models import RunSummary, SearchResult

if TYPE_CHECKING:
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"


def _restrict_file_permissions(path: Path) -> None:
    """Best-effort owner-only read/write on saved artifact files."""
    try:
        if _IS_WINDOWS:
            # On Windows without admin, os.chmod is limited.
            # Remove group/other read bits as much as Python allows.
            os.chmod(str(path), stat.S_IRUSR | stat.S_IWUSR)
        else:
            os.chmod(str(path), 0o600)
    except OSError as exc:
        logger.debug("Could not restrict permissions on %s: %s", path, exc)


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_run_dir(base_dir: Path, run_id: str) -> Path:
    """Create and return the artifact directory for a specific run."""
    run_dir = base_dir / run_id
    _ensure_dir(run_dir)
    return run_dir


def save_screenshot(page: Page, path: Path) -> None:
    """Save a full-page screenshot to *path*."""
    try:
        page.screenshot(path=str(path), full_page=True)
        _restrict_file_permissions(path)
        logger.debug("Screenshot saved: %s", path)
    except Exception as exc:
        logger.warning("Screenshot failed: %s", exc)
        raise ArtifactError(f"Screenshot failed: {exc}") from exc


def save_html(page: Page, path: Path) -> None:
    """Save the current page HTML to *path*."""
    try:
        html = page.content()
        path.write_text(html, encoding="utf-8")
        _restrict_file_permissions(path)
        logger.debug("HTML saved: %s", path)
    except Exception as exc:
        logger.warning("HTML save failed: %s", exc)
        raise ArtifactError(f"HTML save failed: {exc}") from exc


def save_text(text: str, path: Path) -> None:
    """Save extracted page text to *path*."""
    try:
        path.write_text(text, encoding="utf-8")
        _restrict_file_permissions(path)
        logger.debug("Text saved: %s", path)
    except Exception as exc:
        logger.warning("Text save failed: %s", exc)
        raise ArtifactError(f"Text save failed: {exc}") from exc


def save_run_summary(summary: RunSummary, path: Path) -> None:
    """Serialise a RunSummary to JSON and write to *path*."""
    try:
        data = summary.to_dict()
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        _restrict_file_permissions(path)
        logger.debug("Run summary saved: %s", path)
    except Exception as exc:
        logger.warning("Run summary save failed: %s", exc)
        raise ArtifactError(f"Run summary save failed: {exc}") from exc


def save_attempt_artifacts(
    page: Page | None,
    result: SearchResult,
    run_dir: Path,
    save_screenshots: bool = True,
) -> SearchResult:
    """Save all per-attempt artifacts and update result paths in-place."""
    state_tag = result.state.value.lower()
    stem = f"attempt_{result.attempt_number:02d}_{state_tag}"

    if page is not None and save_screenshots:
        screenshot_path = run_dir / f"{stem}.png"
        try:
            save_screenshot(page, screenshot_path)
            result.screenshot_path = str(screenshot_path)
        except ArtifactError:
            pass  # Already logged; continue

        html_path = run_dir / f"{stem}.html"
        try:
            save_html(page, html_path)
            result.html_path = str(html_path)
        except ArtifactError:
            pass

    text_path = run_dir / f"{stem}.txt"
    try:
        save_text(result.raw_text, text_path)
    except ArtifactError:
        pass

    return result


def save_detail_page_artifacts(
    page: Page | None,
    result: SearchResult,
    run_dir: Path,
    save_screenshots: bool = True,
) -> SearchResult:
    """Save detail-page artifacts when a facility page was collected."""
    if not result.detail_page_text:
        return result

    state_tag = result.state.value.lower()
    stem = f"attempt_{result.attempt_number:02d}_{state_tag}_detail"

    if page is not None and save_screenshots:
        screenshot_path = run_dir / f"{stem}.png"
        try:
            save_screenshot(page, screenshot_path)
            result.detail_page_screenshot_path = str(screenshot_path)
        except ArtifactError:
            pass

        html_path = run_dir / f"{stem}.html"
        try:
            save_html(page, html_path)
            result.detail_page_html_path = str(html_path)
        except ArtifactError:
            pass

    text_path = run_dir / f"{stem}.txt"
    try:
        save_text(result.detail_page_text, text_path)
        result.detail_page_text_path = str(text_path)
    except ArtifactError:
        pass

    return result


def save_facility_more_information_artifacts(
    page: Page | None,
    result: SearchResult,
    run_dir: Path,
    save_screenshots: bool = True,
) -> SearchResult:
    """Save artifacts for the external facility information page."""
    if not result.facility_more_information_text:
        return result

    state_tag = result.state.value.lower()
    stem = f"attempt_{result.attempt_number:02d}_{state_tag}_facility_info"

    if page is not None and save_screenshots:
        screenshot_path = run_dir / f"{stem}.png"
        try:
            save_screenshot(page, screenshot_path)
            result.facility_more_information_screenshot_path = str(screenshot_path)
        except ArtifactError:
            pass

        html_path = run_dir / f"{stem}.html"
        try:
            save_html(page, html_path)
            result.facility_more_information_html_path = str(html_path)
        except ArtifactError:
            pass

    text_path = run_dir / f"{stem}.txt"
    try:
        save_text(result.facility_more_information_text, text_path)
        result.facility_more_information_text_path = str(text_path)
    except ArtifactError:
        pass

    return result


def generate_run_id(prefix: str = "run") -> str:
    """Generate a sortable run identifier from the current UTC timestamp."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{ts}"
