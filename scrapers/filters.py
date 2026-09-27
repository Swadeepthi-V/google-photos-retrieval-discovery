"""
scrapers/filters.py — Google Photos Discovery Engine
Shared filtering logic applied by every scraper before saving to data/raw/.

Two-stage filter:
  1. Min-word gate   — discard reviews under MIN_WORDS words (noise/ratings-only)
  2. Topic-relevance — discard reviews with no retrieval/memory-domain keyword

Designed to be imported by play_store_scraper.py, app_store_scraper.py,
youtube_comments_scraper.py, and any future scraper.
"""

import re
from typing import List

# ── Stage 1: minimum word count ────────────────────────────────────────────────
MIN_WORDS: int = 15

# ── Stage 2: topic-relevance keywords ─────────────────────────────────────────
# A review must contain at least ONE word/phrase from this set to pass.
# Grouped by semantic category for readability; all checked as one flat set.
RETRIEVAL_KEYWORDS: List[str] = [
    # Core retrieval actions
    "search", "find", "found", "finding", "locate", "look for", "looking for",
    "browse", "scroll", "filter",
    # Memory & recollection
    "memory", "memories", "remember", "recall", "forgotten", "forgot", "reminds",
    "nostalgia", "flashback", "throwback",
    # Photo/media objects
    "photo", "photos", "picture", "pictures", "image", "images", "video", "videos",
    "album", "albums",
    # Loss / disappearance
    "lost", "missing", "disappeared", "gone", "can't find", "cannot find",
    "deleted", "delete", "restore", "recover", "backup", "backed up",
    # Storage & library
    "storage", "library", "archive", "sync", "synced", "upload", "uploaded",
    # Discovery UX
    "on this day", "highlights", "explore", "suggested", "facial recognition",
    "face", "people", "places", "map",
]

# Pre-compile as a single alternation regex (word-boundary aware, case-insensitive)
_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(kw) for kw in RETRIEVAL_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


# ── Public API ─────────────────────────────────────────────────────────────────

def is_relevant(text: str) -> bool:
    """
    Return True if the review passes both filter stages:
      - At least MIN_WORDS words
      - Contains at least one retrieval/memory-domain keyword
    """
    words = text.split()
    if len(words) < MIN_WORDS:
        return False
    return bool(_PATTERN.search(text))


def apply_filters(records: List[dict], text_key: str = "text") -> dict:
    """
    Filter a list of normalised review dicts. Returns a summary dict:
    {
        "passed"      : List[dict],   # records that passed both filters
        "collected"   : int,          # total input
        "too_short"   : int,          # failed word-count gate
        "off_topic"   : int,          # passed length but failed keyword gate
        "kept"        : int,          # len(passed)
    }
    """
    collected  = len(records)
    too_short  = 0
    off_topic  = 0
    passed     = []

    for rec in records:
        text  = rec.get(text_key, "")
        words = text.split()

        if len(words) < MIN_WORDS:
            too_short += 1
            continue

        if not _PATTERN.search(text):
            off_topic += 1
            continue

        passed.append(rec)

    return {
        "passed"   : passed,
        "collected": collected,
        "too_short": too_short,
        "off_topic": off_topic,
        "kept"     : len(passed),
    }


def print_filter_report(source: str, result: dict) -> None:
    """Print a compact filter summary to stdout."""
    c = result["collected"]
    k = result["kept"]
    pct = round(100 * k / c, 1) if c else 0
    print(f"  Filter results   : {c} collected -> "
          f"{result['too_short']} too short, "
          f"{result['off_topic']} off-topic, "
          f"{k} kept ({pct}%)")
