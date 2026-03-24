"""KeyMemoryService — deduplication, importance scoring, and CRUD for KeyMemory.

Provides a single entry-point ``add_memory()`` that:
  1. Computes an embedding for the new content.
  2. Checks for semantic duplicates (cosine similarity ≥ 0.90).
  3. If duplicate found → merges content, bumps importance_score.
  4. Otherwise → creates a new KeyMemory row with embedding.
"""

import logging
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from models.profile import KeyMemory
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# Maximum number of KeyMemory entries per user (oldest low-importance pruned first)
MAX_MEMORIES_PER_USER = 200


class KeyMemoryService:
    """High-level memory management with dedup and importance ranking."""

    def __init__(self, db: Session):
        self.db = db
        self.embedding_svc = EmbeddingService(db)

    # ---- public API -------------------------------------------------------

    def add_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str = "user_added",
        importance: float = 0.5,
        tags: list = None,
    ) -> KeyMemory:
        """Add a memory with automatic deduplication.

        Returns the new or updated KeyMemory row.
        """
        content = content.strip()
        if not content:
            raise ValueError("Memory content must not be empty")

        vec = self.embedding_svc.embed_text(content)

        # --- deduplication ---
        if vec is not None:
            existing = self.embedding_svc.find_duplicate(user_id, vec, threshold=0.90)
            if existing:
                return self._merge_into(existing, content, importance, tags)

        # --- create new ---
        mem = KeyMemory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            importance_score=importance,
            tags=tags or [],
        )
        if vec is not None:
            EmbeddingService.store_embedding(mem, vec)
        self.db.add(mem)
        self.db.commit()

        # enforce per-user cap
        self._prune_if_needed(user_id)

        logger.info("KeyMemoryService: created memory %s for user %s", mem.id, user_id)
        return mem

    def update_memory(
        self,
        memory_id: str,
        user_id: str,
        content: str = None,
        importance: float = None,
        tags: list = None,
    ) -> Optional[KeyMemory]:
        """Edit an existing memory. Re-computes embedding if content changed."""
        mem = (
            self.db.query(KeyMemory)
            .filter(KeyMemory.id == memory_id, KeyMemory.user_id == user_id)
            .first()
        )
        if mem is None:
            return None

        if content is not None and content.strip():
            mem.content = content.strip()
            # recompute embedding
            vec = self.embedding_svc.embed_text(mem.content)
            if vec is not None:
                EmbeddingService.store_embedding(mem, vec)
        if importance is not None:
            mem.importance_score = max(0.0, min(1.0, importance))
        if tags is not None:
            mem.tags = tags

        self.db.commit()
        return mem

    def search_memories(
        self,
        user_id: str,
        query: str,
        top_k: int = 10,
    ) -> List[dict]:
        """Semantic search over a user's memories. Returns dicts with score."""
        results = self.embedding_svc.search_key_memories(user_id, query, top_k=top_k)
        return [
            {**mem.to_dict(), "similarity": round(score, 4)}
            for mem, score in results
        ]

    def get_top_memories(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[KeyMemory]:
        """Return the most important memories (no embedding query)."""
        return (
            self.db.query(KeyMemory)
            .filter(KeyMemory.user_id == user_id)
            .order_by(KeyMemory.importance_score.desc(), KeyMemory.created_at.desc())
            .limit(limit)
            .all()
        )

    # ---- internal helpers -------------------------------------------------

    def _merge_into(
        self,
        existing: KeyMemory,
        new_content: str,
        importance: float,
        tags: list = None,
    ) -> KeyMemory:
        """Merge semantically duplicate memory: combine tags, bump importance."""
        # bump importance (diminishing returns)
        existing.importance_score = min(
            1.0,
            existing.importance_score + importance * 0.3,
        )
        # append any new info snippet if materially different
        if new_content not in (existing.content or ""):
            existing.content = f"{existing.content}\n---\n{new_content}"
        # merge tags
        if tags:
            old_tags = set(existing.tags or [])
            existing.tags = list(old_tags | set(tags))

        self.db.commit()
        logger.info(
            "KeyMemoryService: merged duplicate into %s (score=%.2f)",
            existing.id, existing.importance_score,
        )
        return existing

    def _prune_if_needed(self, user_id: str) -> None:
        """If user exceeds MAX_MEMORIES, delete the least important old ones."""
        total = (
            self.db.query(KeyMemory)
            .filter(KeyMemory.user_id == user_id)
            .count()
        )
        if total <= MAX_MEMORIES_PER_USER:
            return

        excess = total - MAX_MEMORIES_PER_USER
        to_delete = (
            self.db.query(KeyMemory)
            .filter(KeyMemory.user_id == user_id)
            .order_by(KeyMemory.importance_score.asc(), KeyMemory.created_at.asc())
            .limit(excess)
            .all()
        )
        for mem in to_delete:
            self.db.delete(mem)
        self.db.commit()
        logger.info("KeyMemoryService: pruned %d old memories for user %s", excess, user_id)
