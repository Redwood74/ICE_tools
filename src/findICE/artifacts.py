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

__all__ = [
    "make_run_dir",
    "save_screenshot",
    "save_html",
    "save_text",
    "save_run_summary",
    "save_attempt_artifacts",
    "save_detail_page_artifacts",
    "save_facility_more_information_artifacts",
    "generate_run_id",
    "generate_html_report",
]

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
    try:
        if _IS_WINDOWS:
            os.chmod(str(path), stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        else:
            os.chmod(str(path), 0o700)
    except OSError as exc:
        logger.debug("Could not restrict directory permissions on %s: %s", path, exc)
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


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

_STATE_COLORS = {
    "LIKELY_POSITIVE": "#2e7d32",
    "ZERO_RESULT": "#616161",
    "AMBIGUOUS_REVIEW": "#ef6c00",
    "BOT_CHALLENGE_OR_BLOCKED": "#c62828",
    "ERROR": "#b71c1c",
}


def generate_html_report(summary: RunSummary, run_dir: Path) -> Path | None:
    """Generate a self-contained HTML report for the run.

    Embeds screenshots as base64 data-URIs so the report can be viewed
    standalone without external file references.

    Returns the path to the saved report, or None on failure.
    """

    best = summary.best_result
    state_val = summary.best_state.value
    color = _STATE_COLORS.get(state_val, "#424242")

    # Collect screenshots as base64
    screenshots: list[tuple[str, str]] = []
    if best and best.screenshot_path:
        _embed_screenshot(screenshots, best.screenshot_path, "Search Result")
    if best and best.detail_page_screenshot_path:
        _embed_screenshot(screenshots, best.detail_page_screenshot_path, "Detail Page")
    if best and best.facility_more_information_screenshot_path:
        _embed_screenshot(
            screenshots,
            best.facility_more_information_screenshot_path,
            "Facility Info",
        )

    # Build facility section
    facility_html = ""
    if best and best.detention_facility:
        rows = []
        if best.detention_facility:
            rows.append(("Facility", best.detention_facility))
        if best.facility_address:
            rows.append(("Address", best.facility_address))
        if best.ero_office_name:
            rows.append(("ERO Office", best.ero_office_name))
        if best.ero_office_phone:
            rows.append(("ERO Phone", best.ero_office_phone))
        if best.visitor_information:
            rows.append(("Visitor Info", best.visitor_information))
        table_rows = "\n".join(
            f'<tr><td style="font-weight:bold;padding:4px 12px 4px 0">'
            f"{_html_escape(k)}</td>"
            f'<td style="padding:4px 0">{_html_escape(v)}</td></tr>'
            for k, v in rows
        )
        facility_html = f"""
        <h2>Detention Facility</h2>
        <table style="border-collapse:collapse" aria-label="Detention facility details">{table_rows}</table>
        """

    # Build screenshot section
    screenshot_html = ""
    if screenshots:
        imgs = "\n".join(
            f'<div style="margin-bottom:16px">'
            f"<h3>{_html_escape(label)}</h3>"
            f'<img src="data:image/png;base64,{data}" '
            f'alt="Screenshot: {_html_escape(label)}" '
            f'style="max-width:100%;border:1px solid #ccc;border-radius:4px" />'
            f"</div>"
            for label, data in screenshots
        )
        screenshot_html = f"<h2>Screenshots</h2>\n{imgs}"

    # Build all-states bar
    states_html = ""
    if summary.all_states:
        badges = " ".join(
            f'<span role="status" aria-label="{s.value}" '
            f'style="display:inline-block;padding:2px 8px;margin:2px;'
            f"border-radius:3px;color:#fff;"
            f'background:{_STATE_COLORS.get(s.value, "#424242")}">'
            f"{s.value}</span>"
            for s in summary.all_states
        )
        states_html = (
            f'<p style="margin-top:8px"><strong>All attempts:</strong> {badges}</p>'
        )

    started = summary.started_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    completed = (
        summary.completed_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        if summary.completed_at
        else "—"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ICEpicks Run Report – {_html_escape(state_val)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         max-width: 900px; margin: 0 auto; padding: 24px; color: #212121; }}
  .badge {{ display:inline-block; padding:6px 16px; border-radius:4px;
            color:#fff; font-weight:bold; font-size:1.1em; }}
  table {{ border-collapse: collapse; }}
  td {{ vertical-align: top; }}
  h1 {{ margin-bottom: 4px; }}
  .meta {{ color: #757575; font-size: 0.9em; }}
</style>
</head>
<body>
<h1>ICEpicks Run Report</h1>
<p class="meta">
  {_html_escape(summary.a_number_masked)} &middot; {_html_escape(summary.country)}
  &middot; {started} &ndash; {completed}
</p>
<p>
  <span class="badge" style="background:{color}">{_html_escape(state_val)}</span>
  &nbsp; {summary.attempts_total} attempt(s)
  {" &middot; notified" if summary.notified else ""}
</p>
{states_html}
{facility_html}
{screenshot_html}
<hr style="margin-top:32px;border:none;border-top:1px solid #e0e0e0">
<p class="meta">Generated by ICEpicks &middot; artifacts in <code>{_html_escape(str(run_dir))}</code></p>
</body>
</html>"""

    report_path = run_dir / "report.html"
    try:
        report_path.write_text(html, encoding="utf-8")
        _restrict_file_permissions(report_path)
        logger.info("HTML report saved: %s", report_path)
        return report_path
    except Exception as exc:
        logger.warning("HTML report generation failed: %s", exc)
        return None


def _embed_screenshot(
    screenshots: list[tuple[str, str]], path_str: str, label: str
) -> None:
    """Read a screenshot file and append its base64 encoding."""
    import base64

    p = Path(path_str)
    if p.exists():
        try:
            data = base64.b64encode(p.read_bytes()).decode("ascii")
            screenshots.append((label, data))
        except Exception as exc:
            logger.debug("Could not embed screenshot %s: %s", p, exc)


def _html_escape(text: str) -> str:
    """HTML-escape report content using the standard library."""
    import html

    return html.escape(text, quote=True)
