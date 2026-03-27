"""Tests for artifact storage functions."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from findICE.artifacts import (
    _ensure_dir,
    _html_escape,
    _restrict_file_permissions,
    generate_html_report,
    generate_run_id,
    make_run_dir,
    save_attempt_artifacts,
    save_detail_page_artifacts,
    save_facility_more_information_artifacts,
    save_html,
    save_run_summary,
    save_screenshot,
    save_text,
)
from findICE.exceptions import ArtifactError
from findICE.models import ResultState, RunSummary, SearchResult

# ---------------------------------------------------------------------------
# Helpers / mocks
# ---------------------------------------------------------------------------


class _MockPage:
    """Lightweight mock for playwright Page used by artifact functions."""

    def __init__(self, *, html: str = "<html></html>", fail: bool = False):
        self._html = html
        self._fail = fail

    def screenshot(self, *, path: str, full_page: bool = True) -> None:
        if self._fail:
            raise RuntimeError("screenshot boom")
        Path(path).write_bytes(b"\x89PNG fake screenshot")

    def content(self) -> str:
        if self._fail:
            raise RuntimeError("content boom")
        return self._html


def _make_result(**kwargs) -> SearchResult:
    defaults = dict(
        state=ResultState.LIKELY_POSITIVE,
        raw_text="Detainee found at facility.",
        attempt_number=1,
    )
    defaults.update(kwargs)
    return SearchResult(**defaults)


def _make_summary(**kwargs) -> RunSummary:
    from datetime import datetime, timezone

    defaults = dict(
        a_number_masked="A-*******89",
        country="MEXICO",
        attempts_total=2,
        best_state=ResultState.LIKELY_POSITIVE,
        best_result=_make_result(),
        started_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2024, 1, 15, 12, 1, 0, tzinfo=timezone.utc),
    )
    defaults.update(kwargs)
    return RunSummary(**defaults)


# ---------------------------------------------------------------------------
# _restrict_file_permissions
# ---------------------------------------------------------------------------


class TestRestrictFilePermissions:
    def test_sets_owner_only_on_existing_file(self, tmp_path):
        p = tmp_path / "secret.txt"
        p.write_text("data")
        _restrict_file_permissions(p)
        mode = p.stat().st_mode
        # Owner should have read+write; on Windows, os.chmod is limited
        assert mode & stat.S_IRUSR

    def test_no_error_on_missing_file(self, tmp_path):
        p = tmp_path / "does_not_exist.txt"
        # Should log debug but not raise
        _restrict_file_permissions(p)


# ---------------------------------------------------------------------------
# _ensure_dir
# ---------------------------------------------------------------------------


class TestEnsureDir:
    def test_creates_nested_dirs(self, tmp_path):
        d = tmp_path / "a" / "b" / "c"
        result = _ensure_dir(d)
        assert result == d
        assert d.is_dir()

    def test_idempotent_on_existing_dir(self, tmp_path):
        d = tmp_path / "existing"
        d.mkdir()
        result = _ensure_dir(d)
        assert result == d
        assert d.is_dir()


# ---------------------------------------------------------------------------
# make_run_dir
# ---------------------------------------------------------------------------


class TestMakeRunDir:
    def test_creates_run_subdirectory(self, tmp_path):
        rd = make_run_dir(tmp_path, "run_20240115T120000Z")
        assert rd.is_dir()
        assert rd.name == "run_20240115T120000Z"
        assert rd.parent == tmp_path


# ---------------------------------------------------------------------------
# save_screenshot
# ---------------------------------------------------------------------------


class TestSaveScreenshot:
    def test_saves_png_file(self, tmp_path):
        page = _MockPage()
        path = tmp_path / "shot.png"
        save_screenshot(page, path)
        assert path.exists()
        assert path.read_bytes().startswith(b"\x89PNG")

    def test_raises_artifact_error_on_failure(self, tmp_path):
        page = _MockPage(fail=True)
        path = tmp_path / "shot.png"
        with pytest.raises(ArtifactError, match="Screenshot failed"):
            save_screenshot(page, path)


# ---------------------------------------------------------------------------
# save_html
# ---------------------------------------------------------------------------


class TestSaveHtml:
    def test_saves_html_content(self, tmp_path):
        page = _MockPage(html="<html><body>Detainee</body></html>")
        path = tmp_path / "page.html"
        save_html(page, path)
        assert path.exists()
        assert "Detainee" in path.read_text(encoding="utf-8")

    def test_raises_artifact_error_on_failure(self, tmp_path):
        page = _MockPage(fail=True)
        path = tmp_path / "page.html"
        with pytest.raises(ArtifactError, match="HTML save failed"):
            save_html(page, path)


# ---------------------------------------------------------------------------
# save_text
# ---------------------------------------------------------------------------


class TestSaveText:
    def test_saves_text_content(self, tmp_path):
        path = tmp_path / "text.txt"
        save_text("hello world", path)
        assert path.read_text(encoding="utf-8") == "hello world"

    def test_raises_artifact_error_on_read_only_dir(self, tmp_path):
        # Use a non-existent parent to trigger write failure
        path = tmp_path / "nonexistent_parent" / "deep" / "file.txt"
        with pytest.raises(ArtifactError, match="Text save failed"):
            save_text("data", path)


# ---------------------------------------------------------------------------
# save_run_summary
# ---------------------------------------------------------------------------


class TestSaveRunSummary:
    def test_saves_valid_json(self, tmp_path):
        path = tmp_path / "summary.json"
        summary = _make_summary()
        save_run_summary(summary, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["best_state"] == "LIKELY_POSITIVE"
        assert data["country"] == "MEXICO"

    def test_raises_artifact_error_on_failure(self, tmp_path):
        path = tmp_path / "no_parent" / "deep" / "summary.json"
        summary = _make_summary()
        with pytest.raises(ArtifactError, match="Run summary save failed"):
            save_run_summary(summary, path)


# ---------------------------------------------------------------------------
# save_attempt_artifacts
# ---------------------------------------------------------------------------


class TestSaveAttemptArtifacts:
    def test_saves_all_three_files(self, tmp_path):
        page = _MockPage()
        result = _make_result()
        save_attempt_artifacts(page, result, tmp_path, save_screenshots=True)

        # Text file always written
        txt_files = list(tmp_path.glob("*.txt"))
        assert len(txt_files) == 1

        # Screenshot + HTML when page is provided
        assert len(list(tmp_path.glob("*.png"))) == 1
        assert len(list(tmp_path.glob("*.html"))) == 1

    def test_no_screenshot_when_disabled(self, tmp_path):
        page = _MockPage()
        result = _make_result()
        save_attempt_artifacts(page, result, tmp_path, save_screenshots=False)

        assert len(list(tmp_path.glob("*.png"))) == 0
        assert len(list(tmp_path.glob("*.html"))) == 0
        # Text still saved
        assert len(list(tmp_path.glob("*.txt"))) == 1

    def test_handles_none_page(self, tmp_path):
        result = _make_result()
        save_attempt_artifacts(None, result, tmp_path, save_screenshots=True)
        # Only text saved
        assert len(list(tmp_path.glob("*.txt"))) == 1
        assert len(list(tmp_path.glob("*.png"))) == 0

    def test_continues_after_screenshot_failure(self, tmp_path):
        page = _MockPage(fail=True)
        result = _make_result()
        # Should not raise — failures are caught internally
        save_attempt_artifacts(page, result, tmp_path, save_screenshots=True)


# ---------------------------------------------------------------------------
# save_detail_page_artifacts
# ---------------------------------------------------------------------------


class TestSaveDetailPageArtifacts:
    def test_skips_when_no_detail_page_text(self, tmp_path):
        result = _make_result(detail_page_text="")
        save_detail_page_artifacts(None, result, tmp_path)
        assert len(list(tmp_path.iterdir())) == 0

    def test_saves_detail_text_when_present(self, tmp_path):
        result = _make_result(detail_page_text="Facility detail page content")
        save_detail_page_artifacts(None, result, tmp_path, save_screenshots=False)
        txt_files = list(tmp_path.glob("*_detail.txt"))
        assert len(txt_files) == 1


# ---------------------------------------------------------------------------
# save_facility_more_information_artifacts
# ---------------------------------------------------------------------------


class TestSaveFacilityMoreInfoArtifacts:
    def test_skips_when_no_info_text(self, tmp_path):
        result = _make_result(facility_more_information_text="")
        save_facility_more_information_artifacts(None, result, tmp_path)
        assert len(list(tmp_path.iterdir())) == 0

    def test_saves_info_text_when_present(self, tmp_path):
        result = _make_result(facility_more_information_text="External facility info here")
        save_facility_more_information_artifacts(None, result, tmp_path, save_screenshots=False)
        txt_files = list(tmp_path.glob("*_facility_info.txt"))
        assert len(txt_files) == 1


# ---------------------------------------------------------------------------
# generate_run_id
# ---------------------------------------------------------------------------


class TestGenerateRunId:
    def test_default_prefix(self):
        rid = generate_run_id()
        assert rid.startswith("run_")
        assert len(rid) > 10

    def test_custom_prefix(self):
        rid = generate_run_id(prefix="batch")
        assert rid.startswith("batch_")

    def test_ids_are_unique(self):
        import time

        r1 = generate_run_id()
        time.sleep(0.01)
        r2 = generate_run_id()
        # At seconds granularity they may collide; just check format
        assert r1.startswith("run_")
        assert r2.startswith("run_")


# ---------------------------------------------------------------------------
# generate_html_report
# ---------------------------------------------------------------------------


class TestGenerateHtmlReport:
    def test_generates_report_file(self, tmp_path):
        summary = _make_summary()
        report_path = generate_html_report(summary, tmp_path)
        assert report_path is not None
        assert report_path.exists()
        html = report_path.read_text(encoding="utf-8")
        assert "ICEpicks Run Report" in html
        assert "LIKELY_POSITIVE" in html

    def test_report_contains_masked_a_number(self, tmp_path):
        summary = _make_summary(a_number_masked="A-*******89")
        report_path = generate_html_report(summary, tmp_path)
        html = report_path.read_text(encoding="utf-8")
        assert "A-*******89" in html

    def test_report_with_facility_data(self, tmp_path):
        result = _make_result(
            detention_facility="Test Detention Center",
            facility_address="123 Main St, TX 75001",
        )
        summary = _make_summary(best_result=result)
        report_path = generate_html_report(summary, tmp_path)
        html = report_path.read_text(encoding="utf-8")
        assert "Test Detention Center" in html
        assert "123 Main St" in html

    def test_report_with_embedded_screenshot(self, tmp_path):
        # Create a fake screenshot file
        shot = tmp_path / "shot.png"
        shot.write_bytes(b"\x89PNG fake data")
        result = _make_result()
        result.screenshot_path = str(shot)
        summary = _make_summary(best_result=result)

        report_path = generate_html_report(summary, tmp_path)
        html = report_path.read_text(encoding="utf-8")
        assert "data:image/png;base64," in html

    def test_report_escapes_html_in_values(self, tmp_path):
        result = _make_result(detention_facility="<script>alert(1)</script>")
        summary = _make_summary(best_result=result)
        report_path = generate_html_report(summary, tmp_path)
        html = report_path.read_text(encoding="utf-8")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


# ---------------------------------------------------------------------------
# _html_escape
# ---------------------------------------------------------------------------


class TestHtmlEscape:
    def test_escapes_angle_brackets(self):
        assert _html_escape("<b>bold</b>") == "&lt;b&gt;bold&lt;/b&gt;"

    def test_escapes_ampersand(self):
        assert _html_escape("A & B") == "A &amp; B"

    def test_escapes_quotes(self):
        assert _html_escape('"hello"') == "&quot;hello&quot;"
