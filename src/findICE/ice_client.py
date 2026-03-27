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
    DETENTION_FACILITY_LINK,
    ELEMENT_TIMEOUT_MS,
    ICE_LOCATOR_URL,
    PAGE_LOAD_TIMEOUT_MS,
    RESULT_CONTAINER,
    SEARCH_BUTTON,
    SEARCH_RESULT_TIMEOUT_MS,
    log_selector_health,
    reset_selector_health,
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

_PHONE_PATTERNS = [
    re.compile(r"\b1-\d{3}-[A-Z0-9-]{4,}\b"),
    re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]\d{3}[-.\s]\d{4}(?!\d)"),
]
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


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
        except Exception as exc:
            logger.debug("Country select option %s failed: %s", kwargs, exc)
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


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    """Return unique non-empty values without reordering them."""
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique.append(cleaned)
    return unique


def _slugify_facility_tab_label(label: str) -> str:
    """Convert a tab label into a stable snake_case key."""
    normalised = label.lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "_", normalised).strip("_")


def _build_facility_tab_detail(
    label: str,
    text: str,
    links: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Build structured data for a single facility-information tab."""
    link_values = [
        {
            "text": (link.get("text") or "").strip(),
            "url": (link.get("url") or "").strip(),
        }
        for link in (links or [])
        if (link.get("url") or "").strip()
    ]
    cleaned_links = []
    seen_links: set[tuple[str, str]] = set()
    for link in link_values:
        key = (link["text"], link["url"])
        if key in seen_links:
            continue
        seen_links.add(key)
        cleaned_links.append(link)

    phones = _dedupe_preserve_order(
        [match.group(0) for pattern in _PHONE_PATTERNS for match in pattern.finditer(text)]
    )
    emails = _dedupe_preserve_order(_EMAIL_PATTERN.findall(text))

    return {
        "title": label,
        "slug": _slugify_facility_tab_label(label),
        "text": text,
        "phones": phones,
        "emails": emails,
        "links": cleaned_links,
    }


def _extract_page_text(page) -> str:
    """Extract visible text from the result container, falling back to full body."""
    result_loc = resolve_locator(page, RESULT_CONTAINER)
    if result_loc:
        try:
            text = result_loc.inner_text(timeout=5_000)
            if text.strip():
                return text
        except Exception as exc:
            logger.debug("Result container inner_text failed: %s", exc)
    try:
        return page.inner_text("body", timeout=5_000)
    except Exception as exc:
        logger.debug("Body inner_text failed: %s", exc)
        return ""


def _extract_detention_facility(page) -> str | None:
    """Return the current detention facility shown on the results page."""
    facility_loc = resolve_locator(page, DETENTION_FACILITY_LINK)
    if facility_loc is None:
        return None
    try:
        text = facility_loc.inner_text(timeout=5_000).strip()
        return text or None
    except Exception as exc:
        logger.debug("Detention facility link inner_text failed: %s", exc)
        return None


def _extract_detail_page_data(page) -> dict[str, str]:
    """Extract structured fields from the facility detail page."""
    data = page.evaluate(
        """() => {
            const root = document.querySelector('app-detention-facility')
                || document.querySelector('#detentionPage');
            if (!root) {
                return {};
            }

            const clean = (value) => (value || '').replace(/\\s+/g, ' ').trim();
            const detentionPage = root.querySelector('#detentionPage') || root;
            const facilityInfo = detentionPage.querySelector('.facility-info.info');
            const eroBlock = Array.from(root.querySelectorAll('.facility-info'))
                .find((el) => clean(el.innerText).toLowerCase().includes('phone number'));

            const facilityDivs = facilityInfo
                ? Array.from(facilityInfo.children).filter((el) => el.tagName === 'DIV')
                : [];
            const facilityName = facilityDivs.length > 0 ? clean(facilityDivs[0].innerText) : '';
            const addressContainer = facilityDivs.length > 1 ? facilityDivs[1] : null;
            const addressLines = addressContainer
                ? Array.from(addressContainer.querySelectorAll(':scope > div'))
                    .map((el) => clean(el.innerText))
                    .filter(Boolean)
                : [];

            const visitorNode = facilityInfo
                ? Array.from(facilityInfo.querySelectorAll('p'))
                    .find((el) => clean(el.innerText).toLowerCase().includes('visitor information'))
                : null;

            const eroOfficeNode = eroBlock
                ? Array.from(eroBlock.querySelectorAll('div'))
                    .find((el) => {
                        const text = clean(el.innerText);
                        return text && !text.toLowerCase().startsWith('phone number:');
                    })
                : null;
            const eroPhoneNode = eroBlock
                ? Array.from(eroBlock.querySelectorAll('div'))
                    .find((el) => clean(el.innerText).toLowerCase().startsWith('phone number:'))
                : null;

            const moreInfoLink = document.querySelector('#facility-info')
                ? document.querySelector('#facility-info').closest('a')
                : null;

            return {
                detail_page_text: clean(root.innerText),
                detail_page_title: clean(document.title),
                detail_page_url: clean(window.location.href),
                detention_facility: facilityName,
                facility_address: addressLines.join(', '),
                visitor_information: visitorNode
                    ? clean(visitorNode.innerText).replace(/^Visitor Information:\\s*/i, '')
                    : '',
                ero_office_name: eroOfficeNode ? clean(eroOfficeNode.innerText) : '',
                ero_office_phone: eroPhoneNode
                    ? clean(eroPhoneNode.innerText).replace(/^Phone Number:\\s*/i, '')
                    : '',
                facility_more_information_url: moreInfoLink ? clean(moreInfoLink.href) : '',
            };
        }"""
    )
    return {key: value for key, value in data.items() if value}


def _apply_detail_page_data(result: SearchResult, data: dict[str, object]) -> None:
    """Apply extracted detail-page data to the search result in-place."""
    for key, value in data.items():
        setattr(result, key, value)


def _extract_panel_content(page, panel_id: str) -> dict[str, object]:
    """Extract normalised text and links from a tab panel."""
    data = page.evaluate(
        """(panelId) => {
            const panel = document.getElementById(panelId);
            if (!panel) {
                return { text: "", links: [] };
            }

            const clean = (value) => (value || "").replace(/\\s+/g, " ").trim();
            const links = Array.from(panel.querySelectorAll("a[href]"))
                .map((link) => ({
                    text: clean(link.innerText) || clean(link.textContent) || clean(link.href),
                    url: clean(link.href),
                }))
                .filter((link) => link.url);

            return {
                text: clean(panel.innerText),
                links,
            };
        }""",
        panel_id,
    )
    return {
        "text": str(data.get("text") or "").strip(),
        "links": list(data.get("links") or []),
    }


def _extract_more_information_data(page) -> dict[str, object]:
    """Extract all tab content from the external facility information page."""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=10_000)
    except Exception as exc:
        logger.debug("More-info page load state wait failed: %s", exc)

    try:
        page.locator("[role='tab'][aria-controls]").first.wait_for(timeout=10_000)
    except Exception as exc:
        logger.debug("More-info tab locator wait failed: %s", exc)

    tab_locs = page.locator("[role='tab'][aria-controls]")
    tab_count = tab_locs.count()
    tabs: dict[str, str] = {}
    tab_details: dict[str, dict[str, object]] = {}

    for idx in range(tab_count):
        tab = tab_locs.nth(idx)
        label = re.sub(r"\s+", " ", tab.inner_text(timeout=5_000)).strip()
        panel_id = tab.get_attribute("aria-controls") or ""
        if not label or not panel_id:
            continue
        tab.click(timeout=5_000)
        page.wait_for_timeout(300)
        panel = page.locator(f"#{panel_id}")
        try:
            panel.wait_for(timeout=5_000)
        except Exception as exc:
            logger.debug("Panel %s wait failed: %s", panel_id, exc)
            continue
        panel_content = _extract_panel_content(page, panel_id)
        panel_text = panel_content["text"]
        tabs[label] = panel_text
        tab_detail = _build_facility_tab_detail(
            label,
            panel_text,
            links=panel_content["links"],
        )
        tab_details[str(tab_detail["slug"])] = tab_detail

    if tabs:
        facility_more_information_text = "\n\n".join(
            f"{label}\n{text}" for label, text in tabs.items()
        )
    else:
        try:
            facility_more_information_text = re.sub(
                r"\s+", " ", page.inner_text("main", timeout=5_000)
            ).strip()
        except Exception as exc:
            logger.debug("More-info main inner_text failed, falling back to body: %s", exc)
            facility_more_information_text = re.sub(
                r"\s+", " ", page.inner_text("body", timeout=5_000)
            ).strip()

    return {
        "facility_more_information_title": page.title().strip(),
        "facility_more_information_url": page.url.strip(),
        "facility_more_information_text": facility_more_information_text,
        "facility_tabs": tabs,
        "facility_tab_details": tab_details,
        "facility_contacting_a_detainee": (
            str(tab_details.get("contacting_a_detainee", {}).get("text", ""))
        ),
        "facility_legal_and_case_information": (
            str(tab_details.get("legal_and_case_information", {}).get("text", ""))
        ),
        "facility_hours_of_visitation": (
            str(tab_details.get("hours_of_visitation", {}).get("text", ""))
        ),
        "facility_sending_items_to_detainees": (
            str(tab_details.get("sending_items_to_detainees", {}).get("text", ""))
        ),
        "facility_press_and_media": (str(tab_details.get("press_and_media", {}).get("text", ""))),
        "facility_feedback_or_complaints": (
            str(tab_details.get("feedback_or_complaints", {}).get("text", ""))
        ),
    }


_ALLOWED_FACILITY_URL_PREFIXES = (
    "https://locator.ice.gov/",
    "https://www.ice.gov/",
)


def _collect_facility_more_information(page, result: SearchResult) -> object | None:
    """Open the external facility information page and extract all tab content."""
    if not result.facility_more_information_url:
        return None

    url = result.facility_more_information_url
    if not any(url.startswith(prefix) for prefix in _ALLOWED_FACILITY_URL_PREFIXES):
        logger.warning("Refusing to navigate to untrusted facility URL: %s", url)
        return None

    info_page = page.context.new_page()
    try:
        info_page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=PAGE_LOAD_TIMEOUT_MS,
        )
        info_page.wait_for_timeout(1_000)
        more_info_data = _extract_more_information_data(info_page)
        _apply_detail_page_data(result, more_info_data)
    except Exception as exc:
        logger.debug("Facility more-information collection failed: %s", exc)
        info_page.close()
        raise
    return info_page


def _collect_facility_details(page, result: SearchResult, timeout_ms: int) -> object | None:
    """Follow the facility link and collect the detail page when available."""
    facility_loc = resolve_locator(page, DETENTION_FACILITY_LINK)
    if facility_loc is None:
        return None

    try:
        facility_loc.click(timeout=timeout_ms)
        page.wait_for_function(
            """() => window.location.hash.includes('/details') || !!document.querySelector('#detentionPage')""",
            timeout=timeout_ms,
        )
        page.wait_for_timeout(1_000)
        detail_data = _extract_detail_page_data(page)
        _apply_detail_page_data(result, detail_data)
        return _collect_facility_more_information(page, result)
    except Exception as exc:
        logger.warning("Could not collect facility detail page: %s", exc)
        return None


def _wait_for_result(page, timeout_ms: int = SEARCH_RESULT_TIMEOUT_MS) -> None:
    """Wait until the page shows a recognisable result signal."""
    try:
        page.wait_for_function(
            """() => {
                const body = document.body.innerText.toLowerCase();
                const hash = window.location.hash.toLowerCase();
                return (
                    document.querySelector('#resultsPage') ||
                    document.querySelector('#detentionPage') ||
                    hash.includes('/results') ||
                    hash.includes('/details') ||
                    body.includes('search results:') ||
                    body.includes('no records') ||
                    body.includes('0 search results') ||
                    body.includes('current detention facility')
                );
            }""",
            timeout=timeout_ms,
        )
    except Exception as exc:
        logger.debug("wait_for_result timed out – continuing anyway: %s", exc)


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
    from findICE.artifacts import (
        save_attempt_artifacts,
        save_detail_page_artifacts,
        save_facility_more_information_artifacts,
    )
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
        result.detention_facility = _extract_detention_facility(page)

        logger.info(
            "Attempt %d: classified as %s (text_len=%d)",
            attempt_number,
            result.state.value,
            len(page_text),
        )

        # Save the result page before following any facility link.
        if run_dir is not None:
            save_attempt_artifacts(page, result, run_dir, save_screenshots=save_screenshots)

        if result.detention_facility:
            logger.info(
                "Attempt %d: found detention facility '%s'",
                attempt_number,
                result.detention_facility,
            )
            info_page = _collect_facility_details(page, result, element_timeout_ms)
            if result.detail_page_text and run_dir is not None:
                save_detail_page_artifacts(page, result, run_dir, save_screenshots=save_screenshots)
            if result.facility_more_information_text and run_dir is not None:
                save_facility_more_information_artifacts(
                    info_page,
                    result,
                    run_dir,
                    save_screenshots=save_screenshots,
                )
            if info_page is not None:
                info_page.close()

        if result.state == ResultState.BOT_CHALLENGE_OR_BLOCKED:
            raise BotChallengeError(f"Attempt {attempt_number}: bot challenge or block detected")

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
            except Exception as exc:
                logger.debug("Error-path artifact save failed: %s", exc)
    finally:
        try:
            context.close()
            browser.close()
        except Exception as exc:
            logger.debug("Browser cleanup failed: %s", exc)

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
    reset_selector_health()

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
                    logger.info("LIKELY_POSITIVE found on attempt %d – stopping early", i)
                    break

            except BotChallengeError as exc:
                logger.error("Bot challenge detected on attempt %d – aborting run: %s", i, exc)
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

    log_selector_health()
    return results
