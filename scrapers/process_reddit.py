"""
scrapers/process_reddit.py — Google Photos Discovery Engine

Processes raw reddit_reviews.csv:
  1. Cleans encoding artifacts (e.g.  -> ')
  2. Converts dates from DD-MM-YYYY to ISO-8601 UTC format
  3. Validates/formats schema matching Play Store & App Store JSON outputs:
     {"source": "Reddit", "date": "...", "text": "...", "rating": None, "url": "..."}
  4. Applies shared filters (min 15 words, keyword check)
  5. Saves clean output to data/raw/reddit_reviews.json
"""

import os
import sys
import csv
import json
import re
from datetime import datetime, timezone

# ── Add project root to path ──────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.filters import apply_filters, print_filter_report

CSV_FILE  = os.path.join("data", "raw", "reddit_reviews.csv")
JSON_FILE = os.path.join("data", "raw", "reddit_reviews.json")


def clean_text(text: str) -> str:
    if not text:
        return ""
    # Clean unicode replacement character (\uFFFD / )
    text = text.replace("\ufffd", "'").replace("\u2019", "'").replace("\u2018", "'")
    # Normalize multiple whitespace
    text = re.sub(r'[ \t]+', ' ', text).strip()
    return text


def parse_date(date_str: str) -> str:
    date_str = date_str.strip()
    try:
        # Expected format: DD-MM-YYYY
        dt = datetime.strptime(date_str, "%d-%m-%Y").replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except ValueError:
        return date_str


def main():
    if not os.path.exists(CSV_FILE):
        print(f"ERROR: {CSV_FILE} not found.")
        sys.exit(1)

    records = []
    with open(CSV_FILE, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned_body = clean_text(row.get("text", ""))
            iso_date = parse_date(row.get("date", ""))
            url_val  = row.get("url", "").strip() or None
            
            rec = {
                "source": "Reddit",
                "date"  : iso_date,
                "text"  : cleaned_body,
                "rating": None,
                "url"   : url_val
            }
            records.append(rec)

    filter_res = apply_filters(records)
    passed_records = filter_res["passed"]

    os.makedirs(os.path.dirname(JSON_FILE), exist_ok=True)
    with open(JSON_FILE, mode="w", encoding="utf-8") as f:
        json.dump(passed_records, f, indent=2, ensure_ascii=False)

    print("\n=======================================================")
    print("  REDDIT REVIEWS PROCESSOR — SUMMARY")
    print("=======================================================")
    print_filter_report("Reddit", filter_res)
    print(f"  Reviews saved    : {len(passed_records)}")
    print(f"  Output file      : {os.path.abspath(JSON_FILE)}")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
