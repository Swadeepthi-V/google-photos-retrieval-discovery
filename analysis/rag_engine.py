"""
analysis/rag_engine.py — Google Photos Discovery Engine

Retrieval-Augmented Generation (RAG) pipeline:
  - Vector similarity search via BAAI/bge-large-en-v1.5 embeddings & ChromaDB
  - Top-k = 5 retrieval limit
  - Token conservation: context text truncated to 400 chars for LLM prompt,
    while full text is preserved for citation display
  - Concise generation (3-5 sentences) via Groq API
"""

import os
import sys
import logging
from typing import List, Dict, Any

# ── Add project root to path ──────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CHROMA_DB_DIR   = os.path.join("data", "chroma_db")
COLLECTION_NAME = "photos_retrieval"
MODEL_NAME      = "BAAI/bge-large-en-v1.5"
MAX_CONTEXT_CHARS_PER_CHUNK = 400
DEFAULT_TOP_K   = 5

_embed_model = None
_chroma_client = None
_collection = None
_groq_client = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        logger.info("Loading embedding model: %s", MODEL_NAME)
        _embed_model = SentenceTransformer(MODEL_NAME)
    return _embed_model


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY") or getattr(config, "GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in environment or config.py")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def retrieve_context(query: str, top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
    """
    Search ChromaDB vector store for top_k most relevant feedback entries.
    Returns list of dicts with both full_text and truncated_text (max 400 chars).
    """
    model = _get_embed_model()
    collection = _get_collection()

    query_embedding = model.encode([query], normalize_embeddings=True).tolist()
    
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    retrieved = []
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
        dists = results["distances"][0] if "distances" in results else [0.0] * len(docs)

        for i in range(len(docs)):
            full_text = docs[i]
            meta = metas[i] or {}
            
            # Truncate text to 400 characters for token conservation in LLM prompt
            truncated_text = full_text[:MAX_CONTEXT_CHARS_PER_CHUNK]
            if len(full_text) > MAX_CONTEXT_CHARS_PER_CHUNK:
                truncated_text += "..."

            retrieved.append({
                "full_text": full_text,
                "truncated_text": truncated_text,
                "source": meta.get("source", "Unknown"),
                "date": meta.get("date", ""),
                "rating": meta.get("rating", ""),
                "url": meta.get("url", ""),
                "distance": dists[i]
            })

    return retrieved


def generate_rag_response(query: str, top_k: int = DEFAULT_TOP_K) -> Dict[str, Any]:
    """
    Retrieve top_k chunks, construct token-conserving prompt, and generate
    concise 3-5 sentence answer via Groq LLM.
    """
    snippets = retrieve_context(query, top_k=top_k)
    
    # Format context blocks using truncated_text (max 400 chars per snippet)
    context_blocks = []
    for idx, s in enumerate(snippets, 1):
        src_info = f"[{idx}] Source: {s['source']}"
        if s['date']:
            src_info += f" ({s['date'][:10]})"
        context_blocks.append(f"{src_info}\nSnippet: {s['truncated_text']}")

    context_str = "\n\n".join(context_blocks)

    system_prompt = (
        "You are an AI assistant analyzing user feedback on Google Photos retrieval & search behavior. "
        "Keep your answers concise, clear, and focused (3-5 sentences maximum), referencing the provided "
        "context snippets where relevant."
    )

    user_prompt = (
        f"User Question: {query}\n\n"
        f"Retrieved Feedback Snippets (Truncated for token conservation):\n"
        f"{context_str}\n\n"
        f"Please provide a concise 3-5 sentence summary answering the user question based strictly on the feedback."
    )

    client = _get_groq_client()
    
    # Use model from config / env or default to available model
    groq_model = os.getenv("GROQ_MODEL") or getattr(config, "GROQ_MODEL", "openai/gpt-oss-120b")

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=groq_model,
            temperature=0.2,
            max_tokens=350,
        )
        answer = chat_completion.choices[0].message.content
    except Exception as e:
        logger.error("Groq API call failed: %s", e)
        # Fallback to secondary model if primary fails
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="openai/gpt-oss-20b",
                temperature=0.2,
                max_tokens=350,
            )
            answer = chat_completion.choices[0].message.content
        except Exception as fallback_err:
            answer = f"Error generating LLM response: {fallback_err}"

    return {
        "query": query,
        "answer": answer,
        "citations": snippets  # Full text retained for citation UI display
    }
