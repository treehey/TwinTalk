"""EmbeddingService — compute text embeddings and perform semantic search over KeyMemory.

Uses the OpenAI embeddings API (or compatible endpoint).  Embeddings are
stored as raw numpy float32 bytes in KeyMemory.embedding so that we can
perform cosine-similarity search entirely inside Python+SQLite without
needing an external vector DB.
"""

import json
import logging
import os
import struct
from typing import List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from models.profile import KeyMemory
from services.llm_client import get_client, _get_api_key

logger = logging.getLogger(__name__)

# ---- configuration -------------------------------------------------------

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))


# ---- helpers --------------------------------------------------------------

def _bytes_to_vector(raw: bytes) -> np.ndarray:
    """Deserialise bytes → float32 numpy array."""
    return np.frombuffer(raw, dtype=np.float32)


def _vector_to_bytes(vec: np.ndarray) -> bytes:
    """Serialise float32 numpy array → bytes."""
    return vec.astype(np.float32).tobytes()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ---- public API -----------------------------------------------------------

class EmbeddingService:
    """Light-weight wrapper around the OpenAI embeddings endpoint."""

    def __init__(self, db: Session):
        self.db = db

    # -- embedding generation -----------------------------------------------

    @staticmethod
    def embed_text(text: str) -> Optional[np.ndarray]:
        """Call the embeddings API and return a float32 numpy vector.

        Returns None when the API key is missing (offline mode).
        """
        if not _get_api_key():
            logger.warning("EmbeddingService: no API key, returning None")
            return None

        client = get_client()
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text[:8000],  # truncate to stay within limits
            )
            vec = np.array(response.data[0].embedding, dtype=np.float32)
            return vec
        except Exception as e:
            logger.error("EmbeddingService.embed_text failed: %s", e)
            return None

    # -- persistence helpers ------------------------------------------------

    @staticmethod
    def store_embedding(memory: KeyMemory, vec: np.ndarray) -> None:
        """Attach an embedding vector to a KeyMemory row (in-place)."""
        memory.embedding = _vector_to_bytes(vec)

    @staticmethod
    def get_embedding(memory: KeyMemory) -> Optional[np.ndarray]:
        """Retrieve the embedding vector from a KeyMemory row."""
        if memory.embedding is None:
            return None
        return _bytes_to_vector(memory.embedding)

    # -- semantic search ----------------------------------------------------

    def search_key_memories(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> List[Tuple[KeyMemory, float]]:
        """Return the top-k most semantically similar KeyMemory rows.

        Returns a list of ``(KeyMemory, similarity_score)`` tuples sorted
        by descending similarity.
        """
        query_vec = self.embed_text(query)
        if query_vec is None:
            # Fallback: return most-recent important memories
            return self._fallback_recent(user_id, top_k)

        memories = (
            self.db.query(KeyMemory)
            .filter(KeyMemory.user_id == user_id)
            .filter(KeyMemory.embedding.isnot(None))
            .all()
        )

        scored: List[Tuple[KeyMemory, float]] = []
        for mem in memories:
            mem_vec = _bytes_to_vector(mem.embedding)
            sim = cosine_similarity(query_vec, mem_vec)
            if sim >= min_similarity:
                scored.append((mem, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    # -- deduplication check ------------------------------------------------

    def find_duplicate(
        self,
        user_id: str,
        vec: np.ndarray,
        threshold: float = 0.90,
    ) -> Optional[KeyMemory]:
        """Check if a semantically similar memory already exists.

        Returns the existing KeyMemory if similarity ≥ threshold, else None.
        """
        memories = (
            self.db.query(KeyMemory)
            .filter(KeyMemory.user_id == user_id)
            .filter(KeyMemory.embedding.isnot(None))
            .all()
        )

        best_mem = None
        best_sim = 0.0
        for mem in memories:
            mem_vec = _bytes_to_vector(mem.embedding)
            sim = cosine_similarity(vec, mem_vec)
            if sim >= threshold and sim > best_sim:
                best_sim = sim
                best_mem = mem

        return best_mem

    # -- fallback (when embeddings are unavailable) -------------------------

    def _fallback_recent(
        self, user_id: str, limit: int
    ) -> List[Tuple[KeyMemory, float]]:
        """Return the most-recent, highest-importance memories (no embeddings)."""
        memories = (
            self.db.query(KeyMemory)
            .filter(KeyMemory.user_id == user_id)
            .order_by(KeyMemory.importance_score.desc(), KeyMemory.created_at.desc())
            .limit(limit)
            .all()
        )
        return [(m, m.importance_score or 0.5) for m in memories]
