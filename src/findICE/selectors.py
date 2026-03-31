"""Centralised selector definitions with layered fallback resolution.

Resolution order per element:
  1. label-based   – ARIA label / visible label text
  2. placeholder   – input placeholder attribute
  3. role-based    – ARIA role + name
  4. CSS fallback  – tightly scoped CSS selector

Keeping selectors here means you only need to update one file
when the ICE site DOM changes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Selector definitions
# ---------------------------------------------------------------------------

# As of March 2026, the working search form route is #/search.
ICE_LOCATOR_URL = "https://locator.ice.gov/odls/#/search"

# The page sometimes redirects or loads slowly; give it time.
PAGE_LOAD_TIMEOUT_MS = 30_000
ELEMENT_TIMEOUT_MS = 15_000
SEARCH_RESULT_TIMEOUT_MS = 20_000


@dataclass
class SelectorGroup:
    """Ordered list of Playwright locator expressions for a single UI element.

    Candidates are ordered from most-specific (label/ARIA-based) to
    least-specific (heuristic last-resort).  The ``heuristic_index``
    marks where the "precise" selectors end and the heuristic fallbacks
    begin — used by ``resolve_locator`` to escalate logging when a
    heuristic candidate is needed.
    """

    name: str
    candidates: list[str] = field(default_factory=list)
    heuristic_index: int = 999  # index where heuristic fallbacks start


# --- Input: Alien Registration Number ---
A_NUMBER_INPUT = SelectorGroup(
    name="a_number_input",
    candidates=[
        "input[aria-label*='Alien' i]",
        "input[aria-label*='A-Number' i]",
        "input[placeholder*='Alien' i]",
        "input[placeholder*='A-Number' i]",
        "input[placeholder*='A Number' i]",
        "[role='textbox'][aria-label*='Alien' i]",
        "input[name*='alienNumber' i]",
        "input[name*='anumber' i]",
        "input[id*='alienNumber' i]",
        "input[id*='anumber' i]",
        # --- heuristic fallbacks (index 10) ---
        "form input[type='text']:first-of-type",
        "input[type='text']:visible",
    ],
    heuristic_index=10,
)

# --- Select: Country of Birth / Country of Origin ---
COUNTRY_SELECT = SelectorGroup(
    name="country_select",
    candidates=[
        "select[aria-label*='Country' i]",
        "select[aria-label*='Birth' i]",
        "[role='combobox'][aria-label*='Country' i]",
        "select[name*='country' i]",
        "select[id*='country' i]",
        "select[name*='birth' i]",
        "select[id*='birth' i]",
        # --- heuristic fallbacks (index 7) ---
        "form select:first-of-type",
        "select:has(option)",
        "select:visible",
    ],
    heuristic_index=7,
)

# --- Button: Search / Submit ---
SEARCH_BUTTON = SelectorGroup(
    name="search_button",
    candidates=[
        "button:has-text('Search')",
        "input[type='submit'][value*='Search' i]",
        "[role='button']:has-text('Search')",
        "button[type='submit']",
        "input[type='submit']",
        "button.search-button",
        "button[class*='search' i]",
        "#searchButton",
        # --- heuristic fallbacks (index 8) ---
        "button:visible:last-of-type",
    ],
    heuristic_index=8,
)

# --- Result area ---
RESULT_CONTAINER = SelectorGroup(
    name="result_container",
    candidates=[
        "#resultsPage",
        "#detentionPage",
        "[aria-label*='result' i]",
        ".search-results",
        "#searchResults",
        "#results",
        "[id*='result' i]",
        "[class*='result' i]",
        # --- heuristic fallbacks (index 8) ---
        "table",
        "main",
        "body",
    ],
    heuristic_index=8,
)

DETENTION_FACILITY_LINK = SelectorGroup(
    name="detention_facility_link",
    candidates=[
        "#resultsPage span.detention-link",
        "span.detention-link",
        ".detention-link",
    ],
)

# Phrases that indicate a definitive zero result from the site
ZERO_RESULT_PHRASES: list[str] = [
    "0 search results",
    "0 results",
    "zero (0) matching records",
    "returned zero",
    "0 matching records",
    "no records found",
    "not found",
    "no match",
    "unable to locate",
]

# Phrases that indicate a real positive / detainee record found
POSITIVE_PHRASES: list[str] = [
    "1 search result",
    "search results:",
    "book-in date",
    "book in date",
    "detainee information",
    "current detention facility",
    "a-number:",
    "status : in ice custody",
    "status: in ice custody",
]

# Phrases that indicate the site loaded, but returned an internal/problem page
AMBIGUOUS_PAGE_PHRASES: list[str] = [
    "internal error",
    "an error occurred processing your request",
    "our apologies",
    "go to locator home",
]

# Phrases that suggest a bot challenge or block
BOT_CHALLENGE_PHRASES: list[str] = [
    "captcha",
    "verify you are human",
    "robot",
    "access denied",
    "forbidden",
    "unusual traffic",
    "rate limit",
    "service unavailable",
    "temporarily unavailable",
    "403",
    "429",
]


# ---------------------------------------------------------------------------
# Fallback resolver
# ---------------------------------------------------------------------------

# Tracks which selector resolved for each group during the current run.
# Populated by resolve_locator(); read by log_selector_health().
_selector_health: dict[str, dict] = {}


def resolve_locator(page: Page, group: SelectorGroup) -> object | None:
    """Try each candidate selector in order and return the first that matches.

    Returns the Playwright Locator if found, otherwise None.
    Logs at WARNING when a heuristic fallback is used.
    """
    for idx, selector in enumerate(group.candidates):
        try:
            loc = page.locator(selector)
            if loc.count() > 0:
                is_heuristic = idx >= group.heuristic_index
                if is_heuristic:
                    logger.warning(
                        "Selector '%s' resolved via HEURISTIC fallback [%d]: %s "
                        "(primary selectors [0–%d] all failed)",
                        group.name,
                        idx,
                        selector,
                        group.heuristic_index - 1,
                    )
                else:
                    logger.debug(
                        "Resolved selector for '%s' using [%d]: %s",
                        group.name,
                        idx,
                        selector,
                    )
                _selector_health[group.name] = {
                    "selector": selector,
                    "index": idx,
                    "is_heuristic": is_heuristic,
                }
                return loc.first
        except Exception:
            logger.debug(
                "Selector candidate failed for '%s' [%d]: %s",
                group.name,
                idx,
                selector,
            )
            continue
    logger.warning(
        "No selector resolved for '%s' (tried %d candidates)",
        group.name,
        len(group.candidates),
    )
    _selector_health[group.name] = {
        "selector": None,
        "index": -1,
        "is_heuristic": False,
    }
    return None


def log_selector_health() -> dict[str, dict]:
    """Log a summary of which selectors resolved and return the health dict.

    Call at the end of each run to surface selector drift.
    """
    if not _selector_health:
        logger.debug("No selector health data recorded (no selectors resolved)")
        return {}

    heuristic_used = [name for name, info in _selector_health.items() if info.get("is_heuristic")]
    failed = [name for name, info in _selector_health.items() if info.get("index") == -1]

    if heuristic_used:
        logger.warning(
            "Selector health: %d element(s) used heuristic fallback: %s",
            len(heuristic_used),
            ", ".join(heuristic_used),
        )
    if failed:
        logger.error(
            "Selector health: %d element(s) UNRESOLVED: %s",
            len(failed),
            ", ".join(failed),
        )
    if not heuristic_used and not failed:
        logger.info("Selector health: all elements resolved via primary selectors")

    result = dict(_selector_health)
    return result


def reset_selector_health() -> None:
    """Clear accumulated selector health data between runs."""
    _selector_health.clear()
