"""
scrapers/app_store_scraper.py — Myntra Wishlist-to-Purchase Behavior Analyzer

Fetches up to APP_STORE_MAX_REVIEWS reviews from the Apple App Store
for the app defined in config.py, using the `app-store-scraper` library.

Output schema per record:
    source  : "App Store"
    date    : ISO-8601 string (UTC)
    text    : review body text
    rating  : int  1–5
    url     : null (App Store reviews have no direct permalink)

Output file: data/raw/app_store_reviews.json

Install dependency:
    pip install app-store-scraper

Run:
    python scrapers/app_store_scraper.py
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone

# ── Import app-store-scraper, avoiding self-import collision ───────────────────
# When run as `python scrapers/app_store_scraper.py`, Python inserts the
# scrapers/ directory at sys.path[0], which causes `from app_store_scraper
# import AppStore` to import THIS file instead of the installed package.
# Fix: temporarily strip scrapers/ from sys.path while loading the library.
_SCRAPERS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT    = os.path.dirname(_SCRAPERS_DIR)

# Remove scrapers/ from path, add project root for config, then import
_saved_path = sys.path[:]
sys.path = [p for p in sys.path if os.path.abspath(p) != _SCRAPERS_DIR]
if _PROJ_ROOT not in sys.path:
    sys.path.insert(0, _PROJ_ROOT)

from scrapers.filters import apply_filters, print_filter_report

try:
    from app_store_scraper import AppStore
except ImportError:
    sys.path = _saved_path
    print(
        "ERROR: app-store-scraper is not installed.\n"
        "Fix: pip install app-store-scraper"
    )
    sys.exit(1)
finally:
    # Restore scrapers/ so any relative imports within this file still work
    if _SCRAPERS_DIR not in sys.path:
        sys.path.append(_SCRAPERS_DIR)

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR     = os.path.join(BASE_DIR, "data", "raw")
OUTPUT_FILE = os.path.join(RAW_DIR, "app_store_reviews.json")
os.makedirs(RAW_DIR, exist_ok=True)


import time
import requests as _requests

# Apple's MZStore userReviewsRow endpoint — the only reliably working public
# reviews API (RSS and amp-api endpoints are either dead or require auth).
_MZSTORE_URL = (
    "https://itunes.apple.com/WebObjects/MZStore.woa/wa/userReviewsRow"
    "?id={app_id}&displayable-kind=11&sort=4"
    "&startIndex={start}&endIndex={end}"
)
_HEADERS = {
    "User-Agent": "iTunes/12.12.4",
    "X-Apple-Store-Front": "143441-1,29",  # US English storefront
    "Accept": "application/json",
}
_PAGE_SIZE = 20  # API returns up to 19 reviews per call


def _to_iso(value) -> str:
    """Convert a date string or datetime to an ISO-8601 UTC string."""
    if not value:
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    try:
        dt = datetime.fromisoformat(str(value))
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return str(value)


def fetch_app_store_reviews(
    app_id: str,
    country: str,
    max_reviews: int,
) -> list[dict]:
    """
    Fetch up to `max_reviews` reviews via Apple's MZStore userReviewsRow API.
    Returns raw review dicts (keys: userReviewId, body, title, rating, date, …).
    Note: `country` param is kept for API compatibility but MZStore uses the
    X-Apple-Store-Front header (143441-1 = US); swap the header value to target
    other storefronts (e.g. 143440-1 for India).
    """
    logger.info(
        f"Fetching up to {max_reviews} App Store reviews for app_id='{app_id}' "
        f"via MZStore API (storefront: {_HEADERS['X-Apple-Store-Front']}) ..."
    )

    all_entries: list[dict] = []
    start = 0

    while start < max_reviews:
        end = min(start + _PAGE_SIZE - 1, max_reviews - 1)
        url = _MZSTORE_URL.format(app_id=app_id, start=start, end=end)

        try:
            resp = _requests.get(url, headers=_HEADERS, timeout=20)
            resp.raise_for_status()
            reviews = resp.json().get("userReviewList", [])
        except Exception as exc:
            logger.error(f"  Offset {start} fetch error: {exc}")
            break

        if not reviews:
            logger.info(f"  No reviews at offset {start} — stopping.")
            break

        all_entries.extend(reviews)
        logger.info(f"  Offset {start}: {len(reviews)} reviews (total: {len(all_entries)})")
        start += _PAGE_SIZE
        time.sleep(0.3)

    logger.info(f"Fetched {len(all_entries)} raw App Store reviews.")
    return all_entries[:max_reviews]



def _label(entry: dict, key: str, default="") -> str:
    """Extract the 'label' string from an iTunes RSS nested dict field."""
    val = entry.get(key, {})
    if isinstance(val, dict):
        return str(val.get("label", default)).strip()
    return str(val).strip() if val else default


def normalise(raw: dict) -> dict:
    """
    Map a MZStore userReviewsRow dict to the project output schema.
    MZStore entries look like:
      { "userReviewId": "…", "title": "…", "body": "…", "rating": 5, "date": "…" }
    """
    title  = str(raw.get("title", "")).strip()
    body   = str(raw.get("body",  "")).strip()
    text   = f"{title} — {body}" if title and body else (title or body)

    try:
        rating = int(raw.get("rating", 0))
        rating = rating if 1 <= rating <= 5 else None
    except (ValueError, TypeError):
        rating = None

    date_raw = raw.get("date", "")

    return {
        "source": "App Store",
        "date":   _to_iso(date_raw),
        "text":   text,
        "rating": rating,
        "url":    None,   # App Store reviews have no direct permalink
    }


def main():
    app_id      = config.APP_STORE_ID
    country     = config.APP_STORE_COUNTRY
    max_reviews = config.APP_STORE_MAX_REVIEWS

    if not app_id or app_id == "0":
        logger.error(
            "APP_STORE_ID is not configured.\n"
            "Edit config.py and set the correct numeric App Store ID."
        )
        sys.exit(1)

    # ── Fetch ──────────────────────────────────────────────────────────────────
    raw_reviews = fetch_app_store_reviews(
        app_id=app_id,
        country=country,
        max_reviews=max_reviews,
    )

    if not raw_reviews:
        logger.warning("No reviews fetched. Check the app ID, country, and internet connection.")

    # ── Normalise ──────────────────────────────────────────────────────────────
    records = [normalise(r) for r in raw_reviews]

    # ── Filter: min-word gate + topic-relevance keyword check ───────────────────
    result  = apply_filters(records)
    records = result["passed"]

    # ── Save ───────────────────────────────────────────────────────────────────
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, default=str)

    # ── Summary ────────────────────────────────────────────────────────────────
    rated = [r for r in records if r["rating"] is not None]
    avg_rating = round(sum(r["rating"] for r in rated) / len(rated), 2) if rated else "N/A"
    rating_dist = {i: sum(1 for r in rated if r["rating"] == i) for i in range(1, 6)}

    print("\n" + "=" * 55)
    print("  APP STORE SCRAPER — SUMMARY")
    print("=" * 55)
    print(f"  App ID           : {app_id}")
    print(f"  Country          : {country}")
    print_filter_report("App Store", result)
    print(f"  Reviews saved    : {len(records)}")
    print(f"  Average rating   : {avg_rating} / 5")
    print(f"  Rating breakdown : {rating_dist}")
    print(f"  Output file      : {OUTPUT_FILE}")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    main()
