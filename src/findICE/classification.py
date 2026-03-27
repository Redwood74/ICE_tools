"""Classification of ICE locator page content.

Classification is conservative: when in doubt, return a lower-confidence
state rather than a false positive. The goal is to minimise alert fatigue
while still catching real records.
"""

from __future__ import annotations

import logging

from findICE.models import ResultState
from findICE.selectors import (
    AMBIGUOUS_PAGE_PHRASES,
    BOT_CHALLENGE_PHRASES,
    POSITIVE_PHRASES,
    ZERO_RESULT_PHRASES,
)

logger = logging.getLogger(__name__)

# Minimum number of positive-indicator phrases required to classify
# as LIKELY_POSITIVE (prevents spurious hits on partial page loads).
MIN_POSITIVE_PHRASE_HITS = 2

# Minimum character count for extracted text to be considered meaningful.
# Pages with fewer characters are classified as ERROR (incomplete load).
MIN_VALID_TEXT_LENGTH = 50


def _normalise(text: str) -> str:
    return text.lower().strip()


def _count_phrase_hits(text: str, phrases: list[str]) -> int:
    lower = _normalise(text)
    return sum(1 for p in phrases if p in lower)


def classify_page_text(
    raw_text: str,
    page_title: str = "",
    http_status: int | None = None,
) -> ResultState:
    """Classify a page based on extracted text content.

    Args:
        raw_text: All visible text extracted from the result area.
        page_title: The page <title>, used as a secondary signal.
        http_status: HTTP status if known (e.g. 403, 429).

    Returns:
        A ResultState enum value.
    """
    if not raw_text and not page_title:
        logger.warning("classify_page_text: both raw_text and page_title are empty")
        return ResultState.ERROR

    full_text = f"{page_title}\n{raw_text}"
    lower = _normalise(full_text)

    # --- Bot / block ---
    bot_hits = _count_phrase_hits(lower, BOT_CHALLENGE_PHRASES)
    if bot_hits > 0 or http_status in (403, 429, 503):
        logger.info(
            "Classification: BOT_CHALLENGE_OR_BLOCKED "
            "(bot_hits=%d, http_status=%s)",
            bot_hits,
            http_status,
        )
        return ResultState.BOT_CHALLENGE_OR_BLOCKED

    # --- Explicit zero-result phrase ---
    zero_hits = _count_phrase_hits(lower, ZERO_RESULT_PHRASES)
    if zero_hits > 0:
        logger.info("Classification: ZERO_RESULT (zero_hits=%d)", zero_hits)
        return ResultState.ZERO_RESULT

    # --- Explicit ambiguous/problem page ---
    ambiguous_hits = _count_phrase_hits(lower, AMBIGUOUS_PAGE_PHRASES)
    if ambiguous_hits > 0:
        logger.info("Classification: AMBIGUOUS_REVIEW (ambiguous_hits=%d)", ambiguous_hits)
        return ResultState.AMBIGUOUS_REVIEW

    # --- Positive indicators ---
    positive_hits = _count_phrase_hits(lower, POSITIVE_PHRASES)
    if positive_hits >= MIN_POSITIVE_PHRASE_HITS:
        logger.info(
            "Classification: LIKELY_POSITIVE (positive_hits=%d)", positive_hits
        )
        return ResultState.LIKELY_POSITIVE

    # --- Page appears loaded but content is unclear ---
    if len(raw_text.strip()) < MIN_VALID_TEXT_LENGTH:
        logger.info(
            "Classification: ERROR – page text too short (%d chars)", len(raw_text)
        )
        return ResultState.ERROR

    # --- Ambiguous: something is there but we can't classify it ---
    logger.info(
        "Classification: AMBIGUOUS_REVIEW "
        "(positive_hits=%d, zero_hits=%d, bot_hits=%d, text_len=%d)",
        positive_hits,
        zero_hits,
        bot_hits,
        len(raw_text),
    )
    return ResultState.AMBIGUOUS_REVIEW


def best_state_from_run(states: list[ResultState]) -> ResultState:
    """Pick the 'best' (most informative) state from a list of attempt states.

    Priority:
      LIKELY_POSITIVE > AMBIGUOUS_REVIEW > ZERO_RESULT > ERROR > BOT_CHALLENGE
    """
    priority = {
        ResultState.LIKELY_POSITIVE: 5,
        ResultState.AMBIGUOUS_REVIEW: 4,
        ResultState.ZERO_RESULT: 3,
        ResultState.ERROR: 2,
        ResultState.BOT_CHALLENGE_OR_BLOCKED: 1,
    }
    if not states:
        return ResultState.ERROR
    return max(states, key=lambda s: priority.get(s, 0))
