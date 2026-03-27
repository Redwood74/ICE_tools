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
    """Ordered list of Playwright locator expressions for a single UI element."""

    name: str
    candidates: list[str] = field(default_factory=list)


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
        # Last-resort: first visible text input in the search form
        "form input[type='text']:first-of-type",
        "input[type='text']:visible",
    ],
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
        # Last-resort: first visible select in the form
        "form select:first-of-type",
        "select:visible",
    ],
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
        "button:visible:last-of-type",
    ],
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
        "table",
        "main",
        "body",
    ],
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


def resolve_locator(page: Page, group: SelectorGroup) -> object | None:
    """Try each candidate selector in order and return the first that matches.

    Returns the Playwright Locator if found, otherwise None.
    """
    for selector in group.candidates:
        try:
            loc = page.locator(selector)
            if loc.count() > 0:
                logger.debug(
                    "Resolved selector for '%s' using: %s", group.name, selector
                )
                return loc.first
        except Exception:
            logger.debug(
                "Selector candidate failed for '%s': %s", group.name, selector
            )
            continue
    logger.warning(
        "No selector resolved for '%s' (tried %d candidates)",
        group.name,
        len(group.candidates),
    )
    return None
