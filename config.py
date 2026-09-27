"""
config.py — Google Photos Discovery Engine
Central configuration. Fill in your credentials before running any scraper.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # loads .env from the project root

# ── Groq LLM API ───────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str   = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# ── Google Play Store ──────────────────────────────────────────────────────────
# Package name from the Play Store URL:
# https://play.google.com/store/apps/details?id=<PLAY_STORE_PACKAGE>
PLAY_STORE_PACKAGE: str = "com.google.android.apps.photos"

# ── Apple App Store ────────────────────────────────────────────────────────────
# Numeric App ID from the App Store URL:
# https://apps.apple.com/in/app/google-photos-backup-edit/id<APP_STORE_ID>
APP_STORE_ID: str = "962194608"

# ISO 3166-1 alpha-2 country code for the App Store storefront to scrape
APP_STORE_COUNTRY: str = "in"

# ── YouTube Data API v3 ────────────────────────────────────────────────────────
# Loaded automatically from .env (YOUTUBE_API_KEY=...)
# Get a free key at: https://console.cloud.google.com → Enable "YouTube Data API v3"
YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")

# Video IDs to scrape — just the ID portion of https://www.youtube.com/watch?v=<ID>
YOUTUBE_VIDEO_IDS: list[str] = [
    "Go9ce2eMqxk",
    "IEJH0n6xuJk",
    "Dxlfa4Mqh08",
    "IeRUY_eeS14",
    "gGQjcjpmGlo",
    "vNripSbijAU",
    "0Xzl8qY4VGE",
    "wL-T6dSRjZU",
]

# ── Scraper limits ─────────────────────────────────────────────────────────────
PLAY_STORE_MAX_REVIEWS: int = 1000
APP_STORE_MAX_REVIEWS:  int = 500
YOUTUBE_MAX_COMMENTS_PER_VIDEO: int = 100   # per video; YouTube API quota-aware
