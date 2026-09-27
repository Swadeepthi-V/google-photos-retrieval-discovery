"""
scripts/test_pipeline.py — Google Photos Discovery Engine

Runs 16 validation questions through the full RAG pipeline (retrieval + generation)
and prints for each question:
  - The Question
  - The Generated Answer
  - Top Result Similarity Score (1 - cosine distance)
"""

import os
import sys
import time
import logging

# Ensure UTF-8 output encoding for console prints on Windows
sys.stdout.reconfigure(encoding="utf-8")

# ── Add project root to path ──────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress verbose HTTP/HF/Groq loggers for clean raw output
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("groq").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("analysis.rag_engine").setLevel(logging.WARNING)

from analysis.rag_engine import generate_rag_response

QUESTIONS = [
    "What kinds of old photos do users struggle to retrieve?",
    "What information do people actually remember about a photo?",
    "What information have they forgotten?",
    "How do users formulate searches when their memory is incomplete?",
    "Do users struggle to put their memory of a photo into words?",
    "Does Google Photos search misunderstand or ignore the clues users provide?",
    "When users get search results, do they struggle to identify the right photo among similar ones?",
    "What do users do when a search doesn't return what they're looking for — do they refine, give up, or search elsewhere?",
    "Do users try to search for photos based on remembered scenes or places?",
    "Do users search for document-like or purpose-driven photos (medicine, receipts, screenshots, notes) tied to a life event or time period?",
    "Do users struggle to find a specific photo among many similar ones from the same trip, event, or time period?",
    "Do users try to search for photos based on an object or appearance detail (an outfit, a specific item, how they looked)?",
    "Do users search for photos based on who was present, rather than where or when?",
    "Do users express frustration about paying for Google One storage while being unable to retrieve or organize their photos?",
    "Do users mention considering switching to another photo service due to retrieval or organization frustrations?",
    "Do users express distrust in Google Photos as a reliable place to store important documents or memories?",
]


def main():
    print("=" * 80)
    print("  GOOGLE PHOTOS DISCOVERY ENGINE — 16 VALIDATION QUESTIONS TEST")
    print("=" * 80 + "\n")

    for idx, q in enumerate(QUESTIONS, 1):
        res = generate_rag_response(q, top_k=5)
        citations = res.get("citations", [])
        top_score_str = "N/A"
        
        if citations and "distance" in citations[0]:
            dist = citations[0]["distance"]
            # Convert cosine distance to similarity score
            sim_score = round(1.0 - dist, 4)
            top_score_str = f"{sim_score} (dist: {round(dist, 4)})"

        print(f"[{idx}/16] QUESTION: {q}")
        print(f"TOP RESULT SIMILARITY SCORE: {top_score_str}")
        print("GENERATED ANSWER:")
        print(res.get("answer", "").strip())
        print("-" * 80 + "\n")
        time.sleep(2.0)


if __name__ == "__main__":
    main()
