"""
scrapers/merge_datasets.py — Google Photos Discovery Engine

Loads raw feedback data across all sources (JSON & CSV):
  - data/raw/play_store_reviews.json
  - data/raw/app_store_reviews.json
  - data/raw/reddit_reviews.csv
  - data/raw/youtube_comments.json

Normalises schema, cleans encoding artifacts, deduplicates identical text,
and exports the unified dataset to data/processed/all_reviews.csv.
"""

import os
import sys
import json
import csv
import re
from datetime import datetime, timezone

# ── Add project root to path ──────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_DIR       = os.path.join("data", "raw")
PROCESSED_DIR = os.path.join("data", "processed")
OUTPUT_CSV    = os.path.join(PROCESSED_DIR, "all_reviews.csv")

RAW_FILES = [
    os.path.join(RAW_DIR, "play_store_reviews.json"),
    os.path.join(RAW_DIR, "app_store_reviews.json"),
    os.path.join(RAW_DIR, "reddit_reviews.csv"),
    os.path.join(RAW_DIR, "youtube_comments.json"),
]


def clean_text(text: str) -> str:
    """Clean encoding artifacts, corrupted characters, and normalise whitespace."""
    if not text:
        return ""
    # Clean replacement character & curly quotes
    text = text.replace("\ufffd", "'")
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    # Normalise whitespace (preserve newlines as spaces for CSV cleanly)
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text).strip()
    return text


def parse_date(date_str: str) -> tuple[datetime | None, str]:
    """Parse various date formats and return (dt_obj, iso_utc_string)."""
    if not date_str:
        return None, ""
    date_str = str(date_str).strip()
    
    # Try ISO format
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt, dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass

    # Try DD-MM-YYYY
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            return dt, dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            continue

    return None, date_str


def load_file(filepath: str) -> list[dict]:
    """Load records from either JSON or CSV file."""
    if not os.path.exists(filepath):
        print(f"  [WARNING] File not found: {filepath}")
        return []

    records = []
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".json":
        with open(filepath, "r", encoding="utf-8") as f:
            records = json.load(f)
    elif ext == ".csv":
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))

    return records


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    all_normalized = []
    seen_texts = set()
    
    source_counts = {}
    valid_dates = []

    for filepath in RAW_FILES:
        raw_recs = load_file(filepath)
        filename = os.path.basename(filepath)
        
        for r in raw_recs:
            src = r.get("source") or "Unknown"
            raw_text = r.get("text", "")
            cleaned = clean_text(raw_text)
            
            if not cleaned:
                continue
                
            # Deduplication on lowercase text
            dedup_key = cleaned.lower()
            if dedup_key in seen_texts:
                continue
            seen_texts.add(dedup_key)

            # Rating parsing
            raw_rating = r.get("rating")
            rating_val = ""
            if raw_rating not in (None, "", "null", "None"):
                try:
                    rating_val = str(int(float(raw_rating)))
                except (ValueError, TypeError):
                    rating_val = ""

            # Date parsing
            dt_obj, iso_date_str = parse_date(r.get("date", ""))
            if dt_obj:
                valid_dates.append(dt_obj)

            url_val = r.get("url") or ""

            rec = {
                "source": src,
                "date": iso_date_str,
                "text": cleaned,
                "rating": rating_val,
                "url": url_val
            }
            all_normalized.append(rec)
            source_counts[src] = source_counts.get(src, 0) + 1

    # Save to data/processed/all_reviews.csv
    fieldnames = ["source", "date", "text", "rating", "url"]
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_normalized)

    # Date range
    min_date_str = "N/A"
    max_date_str = "N/A"
    if valid_dates:
        min_date_str = min(valid_dates).strftime("%Y-%m-%d")
        max_date_str = max(valid_dates).strftime("%Y-%m-%d")

    print("\n=======================================================")
    print("  DATASET MERGER & NORMALIZER — SUMMARY")
    print("=======================================================")
    print("  Row count by source:")
    for src, count in source_counts.items():
        print(f"    - {src:<15}: {count:>5} rows")
    print(f"  -----------------------------------------------------")
    print(f"  Total combined rows: {len(all_normalized)}")
    print(f"  Date range covered : {min_date_str} to {max_date_str}")
    print(f"  Output CSV file    : {os.path.abspath(OUTPUT_CSV)}")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
