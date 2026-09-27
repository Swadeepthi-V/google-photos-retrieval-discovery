"""
scripts/index_data.py — Google Photos Discovery Engine

Loads data/processed/all_reviews.csv, computes BAAI/bge-large-en-v1.5 embeddings,
and stores vectors with metadata in persistent ChromaDB collection 'photos_retrieval'.
Idempotent: document IDs are generated via SHA256(source||text).
"""

import os
import sys
import csv
import hashlib
import logging
from datetime import datetime, timezone

# ── Add project root to path ──────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_CSV = os.path.join("data", "processed", "all_reviews.csv")
CHROMA_DB_DIR = os.path.join("data", "chroma_db")
COLLECTION_NAME = "photos_retrieval"
MODEL_NAME = "BAAI/bge-large-en-v1.5"


def generate_doc_id(source: str, text: str) -> str:
    """Generate stable document ID by hashing source||text."""
    raw_key = f"{source.strip()}||{text.strip()}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def main():
    if not os.path.exists(PROCESSED_CSV):
        logger.error(f"Input file not found: {PROCESSED_CSV}")
        sys.exit(1)

    logger.info("Initializing SentenceTransformer model: %s", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)
    
    # Patch / use get_embedding_dimension() explicitly to avoid FutureWarning
    if hasattr(model, "get_embedding_dimension"):
        emb_dim = model.get_embedding_dimension()
    else:
        emb_dim = model.get_sentence_embedding_dimension()
    logger.info("Embedding dimension: %d", emb_dim)

    os.makedirs(CHROMA_DB_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    # Fetch existing IDs in collection to ensure idempotency
    existing_items = collection.get(include=[])
    existing_ids = set(existing_items["ids"]) if existing_items and "ids" in existing_items else set()
    logger.info("Found %d existing records in ChromaDB collection '%s'", len(existing_ids), COLLECTION_NAME)

    records_to_index = []
    with open(PROCESSED_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = row.get("source", "").strip()
            txt = row.get("text", "").strip()
            if not txt:
                continue
            doc_id = generate_doc_id(src, txt)
            if doc_id in existing_ids:
                continue
            
            records_to_index.append({
                "id": doc_id,
                "source": src,
                "date": row.get("date", "").strip(),
                "text": txt,
                "rating": row.get("rating", "").strip(),
                "url": row.get("url", "").strip(),
            })

    if not records_to_index:
        logger.info("No new records to index. Database is up to date!")
    else:
        logger.info("Encoding and inserting %d new records into ChromaDB...", len(records_to_index))
        texts = [r["text"] for r in records_to_index]
        ids = [r["id"] for r in records_to_index]
        metadatas = [{
            "source": r["source"],
            "date": r["date"],
            "rating": r["rating"],
            "url": r["url"]
        } for r in records_to_index]

        # Compute normalized embeddings
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True).tolist()

        # Batch add to ChromaDB
        batch_size = 200
        for i in range(0, len(records_to_index), batch_size):
            collection.add(
                ids=ids[i:i+batch_size],
                embeddings=embeddings[i:i+batch_size],
                documents=texts[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size]
            )

    # Calculate final stats
    all_data = collection.get(include=["metadatas"])
    total_count = len(all_data["ids"])
    
    breakdown = {}
    if all_data.get("metadatas"):
        for meta in all_data["metadatas"]:
            if meta and "source" in meta:
                s = meta["source"]
                breakdown[s] = breakdown.get(s, 0) + 1

    last_indexed_ts = datetime.now(timezone.utc).isoformat()

    print("\n=======================================================")
    print("  CHROMADB INDEXING PIPELINE — SUMMARY")
    print("=======================================================")
    print(f"  Collection Name    : {COLLECTION_NAME}")
    print(f"  Newly Indexed      : {len(records_to_index)} records")
    print(f"  Total Collection   : {total_count} records")
    print(f"  Breakdown by Source:")
    for src, count in breakdown.items():
        print(f"    - {src:<15}: {count:>5} records")
    print(f"  Last-Indexed Time  : {last_indexed_ts}")
    print(f"  Chroma DB Path     : {os.path.abspath(CHROMA_DB_DIR)}")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
