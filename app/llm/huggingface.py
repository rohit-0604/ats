"""
ATS v8 — HuggingFace local embeddings
Runs all-MiniLM-L6-v2 locally. No API calls, no rate limits, no keys needed.
~90MB model download on first call, cached at ~/.cache/huggingface/
"""

from __future__ import annotations
import logging
from typing import Optional
from sentence_transformers import SentenceTransformer

log = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        log.info(f"Loading embedding model {MODEL_NAME} (downloads ~90MB on first run)...")
        _model = SentenceTransformer(MODEL_NAME)
        log.info("Embedding model loaded.")
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """
    Returns 384-dimensional vectors for each input text.
    Batch-processed efficiently on CPU.
    """
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings.tolist()


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
