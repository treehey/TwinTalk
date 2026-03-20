"""Social Service — discover, follow, match, and interact with other twins."""

import hashlib
import random
import uuid
import logging
from sqlalchemy.orm import Session

from models.user import User
from models.profile import UserProfile
from models.social import TwinConnection

logger = logging.getLogger(__name__)


class SocialService:
    """Manages social features for digital twins."""

    def __init__(self, db: Session):
        self.db = db

    def follow(self, follower_id: str, following_id: str) -> dict:
        """Follow another user's twin."""
        # Check if already following
        existing = (
            self.db.query(TwinConnection)
            .filter_by(follower_id=follower_id, following_id=following_id)
            .first()
        )
        if existing:
            if existing.status == "blocked":
                raise ValueError("Cannot follow this user")
            return existing.to_dict()

        connection = TwinConnection(
            id=str(uuid.uuid4()),
            follower_id=follower_id,
            following_id=following_id,
            status="accepted",  # Auto-accept for now
        )
        self.db.add(connection)
        self.db.commit()
        return connection.to_dict()

    def unfollow(self, follower_id: str, following_id: str):
        """Unfollow a user."""
        self.db.query(TwinConnection).filter_by(
            follower_id=follower_id, following_id=following_id
        ).delete()
        self.db.commit()

    def get_following_ids(self, user_id: str) -> list:
        """Return list of user IDs that user_id is following."""
        rows = (
            self.db.query(TwinConnection.following_id)
            .filter_by(follower_id=user_id, status="accepted")
            .all()
        )
        return [r[0] for r in rows]

    def find_matches(self, user_id: str, limit: int = 10, refresh_token: str = "") -> list:
        """Find twins using multi-dimension profile similarity."""
        my_profile = (
            self.db.query(UserProfile)
            .filter_by(user_id=user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )

        if not my_profile:
            return []

        my_interests = my_profile.interests or []

        # Only keep latest profile per user.
        candidate_users = self.db.query(User).filter(User.id != user_id).all()

        matches = []
        for user in candidate_users:
            profile = (
                self.db.query(UserProfile)
                .filter_by(user_id=user.id)
                .order_by(UserProfile.version.desc())
                .first()
            )
            if not profile:
                continue

            common = self._find_common(my_interests, profile.interests or [])
            interest_score = self._jaccard(my_interests, profile.interests or [])
            trait_score = self._dict_similarity(
                my_profile.personality_traits or {},
                profile.personality_traits or {},
            )
            value_score = self._dict_similarity(
                my_profile.values_profile or {},
                profile.values_profile or {},
            )
            style_score = self._style_similarity(
                my_profile.communication_style or {},
                profile.communication_style or {},
            )

            total_score = (
                0.45 * interest_score
                + 0.25 * trait_score
                + 0.20 * value_score
                + 0.10 * style_score
            )

            matches.append({
                "user": user.to_dict(),
                "score": round(total_score, 4),
                "common_count": len(common),
                "bio_third_view": profile.bio_third_view or "",
                "common_interests": common,
                "score_breakdown": {
                    "interest": round(interest_score, 4),
                    "trait": round(trait_score, 4),
                    "value": round(value_score, 4),
                    "style": round(style_score, 4),
                },
            })

        matches.sort(key=lambda x: (x["score"], x["common_count"]), reverse=True)
        if refresh_token:
            top = matches[: max(limit * 3, limit)]
            seed_int = int(hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()[:8], 16)
            random.Random(seed_int).shuffle(top)
            top.sort(key=lambda x: x["score"], reverse=True)
            head = top[: max(limit // 2, 1)]
            tail = top[max(limit // 2, 1):]
            random.Random(seed_int + 7).shuffle(tail)
            matches = head + tail + matches[max(limit * 3, limit):]

        return matches[:limit]

    def _is_following(self, follower_id: str, following_id: str) -> bool:
        return (
            self.db.query(TwinConnection)
            .filter_by(follower_id=follower_id, following_id=following_id, status="accepted")
            .first()
        ) is not None

    @staticmethod
    def _find_common(a: list, b: list) -> list:
        """Find common elements between two lists."""
        return list(set(a) & set(b))

    @staticmethod
    def _jaccard(a: list, b: list) -> float:
        a_set = {str(item).strip().lower() for item in (a or []) if str(item).strip()}
        b_set = {str(item).strip().lower() for item in (b or []) if str(item).strip()}
        if not a_set and not b_set:
            return 0.0
        inter = len(a_set & b_set)
        union = len(a_set | b_set)
        return float(inter) / float(union or 1)

    @staticmethod
    def _dict_similarity(a: dict, b: dict) -> float:
        if not a or not b:
            return 0.0
        keys = set(a.keys()) & set(b.keys())
        if not keys:
            return 0.0

        diffs = []
        for k in keys:
            try:
                av = float(a.get(k, 0.0))
                bv = float(b.get(k, 0.0))
                diffs.append(min(abs(av - bv), 1.0))
            except (TypeError, ValueError):
                continue

        if not diffs:
            return 0.0
        return max(0.0, 1.0 - (sum(diffs) / len(diffs)))

    @staticmethod
    def _style_similarity(a: dict, b: dict) -> float:
        if not a or not b:
            return 0.0
        a_tokens = set(str(v).strip().lower() for v in a.values() if str(v).strip())
        b_tokens = set(str(v).strip().lower() for v in b.values() if str(v).strip())
        if not a_tokens or not b_tokens:
            return 0.0
        inter = len(a_tokens & b_tokens)
        union = len(a_tokens | b_tokens)
        return float(inter) / float(union or 1)
