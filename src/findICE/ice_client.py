"""ICE locator client using Playwright.

Each attempt uses a FRESH browser context to avoid session state carry-over.
The site is a flaky SPA; this module is built to tolerate that.
"""

from __future__ import annotations

import logging
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from findICE.classification import classify_page_text
from findICE.exceptions import BotChallengeError
from findICE.models import ResultState, SearchResult
from findICE.selectors import (
    A_NUMBER_INPUT,
    COUNTRY_SELECT,
    ELEMENT_TIMEOUT_MS,
    ICE_LOCATOR_URL,
    PAGE_LOAD_TIMEOUT_MS,
    RESULT_CONTAINER,
    SEARCH_BUTTON,
    SEARCH_RESULT_TIMEOUT_MS,
    resolve_locator,
)

logger = logging.getLogger(__name__)

# Text to wait for in result area before extracting content
_RESULT_READY_SIGNALS = [
    "search results",
    "0 search results",
    "no records",
    "facility",
    "detainee",
]


def _select_country_option(country_sel, country: str, timeout_ms: int) -> None:
    """Select country by value/label with case-tolerant fallback."""
    for kwargs in (
        {"value": country},
        {"label": country},
        {"label": country.upper()},
        {"label": country.title()},
    ):
        try:
            country_sel.select_option(**kwargs, timeout=timeout_ms)
            return
        except Exception:
            continue

    option_locs = country_sel.locator("option")
    option_count = option_locs.count()
    for idx in range(option_count):
        label = option_locs.nth(idx).inner_text().strip()
        if label.lower() == country.strip().lower():
            country_sel.select_option(label=label, timeout=timeout_ms)
            return

    raise RuntimeError(f"Could not select country '{country}'")


def _normalise_a_number_for_form(a_number: str) -> str:
    """Return digits-only A-number expected by the locator input control."""
    return re.sub(r"\D", "", a_number)


def _extract_page_text(page) -> str:
    """Extract visible text from the result container, falling back to full body."""
    result_loc = resolve_locator(page, RESULT_CONTAINER)
    if result_loc:
        try:
            text = result_loc.inner_text(timeout=5_000)
            if text.strip():
                return text
        except Exception:
            pass
    try:
        return page.inner_text("body", timeout=5_000)
    except Exception:
        return ""


def _wait_for_result(page, timeout_ms: int = SEARCH_RESULT_TIMEOUT_MS) -> None:
    """Wait until the page shows a recognisable result signal."""
    try:
        page.wait_for_function(
            """() => {
                const body = document.body.innerText.toLowerCase();
                return (
                    body.includes('search results') ||
                    body.includes('no records') ||
                    body.includes('facility') ||
                    body.includes('detainee') ||
                    body.includes('0 results')
                );
            }""",
            timeout=timeout_ms,
        )
    except Exception:
        logger.debug("wait_for_result timed out – continuing anyway")


def run_single_attempt(
    a_number: str,
    country: str,
    attempt_number: int,
    playwright_instance,
    headless: bool = True,
    page_load_timeout_ms: int = PAGE_LOAD_TIMEOUT_MS,
    element_timeout_ms: int = ELEMENT_TIMEOUT_MS,
    run_dir: Path | None = None,
    save_screenshots: bool = True,
) -> SearchResult:
    """Execute a single search attempt in a fresh browser context.

    Args:
        a_number: Alien registration number (unmasked; will be masked in logs).
        country: Country of origin / birth as the site expects it.
        attempt_number: 1-based attempt counter (for artifact naming).
        playwright_instance: An active ``sync_playwright()`` context object.
        headless: Run Chromium in headless mode.
        page_load_timeout_ms: Timeout for page navigation.
        element_timeout_ms: Timeout for locating form elements.
        run_dir: Directory where artifacts are saved.
        save_screenshots: Whether to capture screenshots.

    Returns:
        A SearchResult describing the outcome.
    """
    from findICE.artifacts import save_attempt_artifacts
    from findICE.logging_utils import mask_a_number

    masked = mask_a_number(a_number)
    logger.info("Attempt %d: starting (a_number=%s)", attempt_number, masked)

    browser = playwright_instance.chromium.launch(headless=headless)
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
    )

    result = SearchResult(
        state=ResultState.ERROR,
        raw_text="",
        attempt_number=attempt_number,
        timestamp=datetime.now(timezone.utc),
    )
    page = None

    try:
        page = context.new_page()
        page.set_default_timeout(element_timeout_ms)
        page.set_default_navigation_timeout(page_load_timeout_ms)

        # Navigate to the ICE locator
        logger.debug("Attempt %d: navigating to %s", attempt_number, ICE_LOCATOR_URL)
        page.goto(ICE_LOCATOR_URL, wait_until="domcontentloaded", timeout=page_load_timeout_ms)
        result.page_title = page.title()
        logger.debug("Attempt %d: page title = '%s'", attempt_number, result.page_title)

        # Give SPA time to settle
        page.wait_for_load_state("networkidle", timeout=10_000)

        # --- Fill A-number ---
        a_input = resolve_locator(page, A_NUMBER_INPUT)
        if a_input is None:
            raise RuntimeError("Could not locate A-number input field")
        a_input.fill(_normalise_a_number_for_form(a_number), timeout=element_timeout_ms)
        logger.debug("Attempt %d: filled A-number field", attempt_number)

        # --- Select country ---
        country_sel = resolve_locator(page, COUNTRY_SELECT)
        if country_sel is None:
            raise RuntimeError("Could not locate country select element")
        _select_country_option(country_sel, country, element_timeout_ms)
        logger.debug("Attempt %d: selected country '%s'", attempt_number, country)

        # --- Click search ---
        search_btn = resolve_locator(page, SEARCH_BUTTON)
        if search_btn is None:
            raise RuntimeError("Could not locate Search button")
        search_btn.click(timeout=element_timeout_ms)
        logger.debug("Attempt %d: clicked Search button", attempt_number)

        # --- Wait for result ---
        _wait_for_result(page, timeout_ms=SEARCH_RESULT_TIMEOUT_MS)
        page_text = _extract_page_text(page)
        result.raw_text = page_text
        result.state = classify_page_text(page_text, page_title=page.title())
        result.page_title = page.title()

        logger.info(
            "Attempt %d: classified as %s (text_len=%d)",
            attempt_number,
            result.state.value,
            len(page_text),
        )

        # Save artifacts for this attempt
        if run_dir is not None:
            save_attempt_artifacts(
                page, result, run_dir, save_screenshots=save_screenshots
            )

        if result.state == ResultState.BOT_CHALLENGE_OR_BLOCKED:
            raise BotChallengeError(
                f"Attempt {attempt_number}: bot challenge or block detected"
            )

    except BotChallengeError:
        raise
    except Exception as exc:
        logger.warning("Attempt %d failed: %s", attempt_number, exc)
        result.state = ResultState.ERROR
        result.error_detail = str(exc)
        if run_dir is not None:
            # Try to save whatever we have
            try:
                save_attempt_artifacts(
                    page,
                    result,
                    run_dir,
                    save_screenshots=save_screenshots and page is not None,
                )
            except Exception:
                pass
    finally:
        try:
            context.close()
            browser.close()
        except Exception:
            pass

    return result


def run_with_retries(
    a_number: str,
    country: str,
    attempts: int = 4,
    delay_seconds: float = 5.0,
    jitter_seconds: float = 2.0,
    headless: bool = True,
    page_load_timeout_ms: int = PAGE_LOAD_TIMEOUT_MS,
    element_timeout_ms: int = ELEMENT_TIMEOUT_MS,
    run_dir: Path | None = None,
    save_screenshots: bool = True,
) -> list[SearchResult]:
    """Run multiple fresh attempts against the ICE locator.

    Between attempts, a randomised sleep with jitter is applied
    to avoid hammering the site.

    Returns:
        List of SearchResult objects (one per attempt).
    """
    from playwright.sync_api import sync_playwright

    results: list[SearchResult] = []

    with sync_playwright() as pw:
        for i in range(1, attempts + 1):
            if i > 1:
                sleep_time = delay_seconds + random.uniform(0, jitter_seconds)
                logger.info("Waiting %.1fs before attempt %d…", sleep_time, i)
                time.sleep(sleep_time)

            try:
                result = run_single_attempt(
                    a_number=a_number,
                    country=country,
                    attempt_number=i,
                    playwright_instance=pw,
                    headless=headless,
                    page_load_timeout_ms=page_load_timeout_ms,
                    element_timeout_ms=element_timeout_ms,
                    run_dir=run_dir,
                    save_screenshots=save_screenshots,
                )
                results.append(result)

                # Stop early on positive – we have what we need
                if result.state == ResultState.LIKELY_POSITIVE:
                    logger.info(
                        "LIKELY_POSITIVE found on attempt %d – stopping early", i
                    )
                    break

            except BotChallengeError as exc:
                logger.error(
                    "Bot challenge detected on attempt %d – aborting run: %s", i, exc
                )
                results.append(
                    SearchResult(
                        state=ResultState.BOT_CHALLENGE_OR_BLOCKED,
                        raw_text="",
                        attempt_number=i,
                        error_detail=str(exc),
                        timestamp=datetime.now(timezone.utc),
                    )
                )
                break

    return results
