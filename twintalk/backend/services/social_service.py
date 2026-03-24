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
        """Find twins using the two-stage hybrid matching algorithm (recall + LLM rerank).

        Delegates to MatchService and converts MatchResult to the legacy response format
        so existing API callers remain unaffected.
        """
        from services.match_service import MatchService

        svc = MatchService(self.db)
        # Retrieve more candidates than needed so refresh_token shuffle has room
        fetch_limit = max(limit * 3, 20)
        raw_results = svc.get_recommended_twins(user_id, top_n=fetch_limit)

        if not raw_results:
            return []

        # Convert MatchResult dicts → legacy response format
        matches = []
        # Query current user's profile once (not inside the loop)
        my_profile = (
            self.db.query(UserProfile)
            .filter_by(user_id=user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )
        my_interests = (my_profile.interests or []) if my_profile else []

        for r in raw_results:
            # Retrieve the candidate's profile for bio_third_view / common_interests
            candidate_profile = (
                self.db.query(UserProfile)
                .filter_by(user_id=r["candidate_id"])
                .order_by(UserProfile.version.desc())
                .first()
            )
            candidate_user = (
                self.db.query(User)
                .filter_by(id=r["candidate_id"])
                .first()
            )
            if not candidate_user or not candidate_profile:
                continue

            cand_interests = candidate_profile.interests or []
            common_interests = list(
                {str(i).strip().lower() for i in my_interests if str(i).strip()}
                & {str(i).strip().lower() for i in cand_interests if str(i).strip()}
            )
            if not candidate_user or not candidate_profile:
                continue

            # Build profile tags like Ego page does
            extra = candidate_profile.extra_info or {}
            profile_tags = []
            if extra.get('mbti'):
                profile_tags.append(extra['mbti'])
            for kw in (extra.get('personality_keywords') or []):
                profile_tags.append(kw)
            for interest in (candidate_profile.interests or [])[:8]:
                profile_tags.append(interest)
            vals = candidate_profile.values_profile or {}
            for v in (vals.get('核心价值') or [])[:3]:
                profile_tags.append(v)
            cstyle = candidate_profile.communication_style or {}
            if cstyle.get('风格'):
                profile_tags.append(cstyle['风格'])
            
            # Deduplicate and limit
            seen = set()
            unique_tags = []
            for t in profile_tags:
                if t not in seen:
                    seen.add(t)
                    unique_tags.append(t)
            profile_tags = unique_tags[:12]

            matches.append({
                "user": candidate_user.to_dict(),
                "score": r["final_score"],
                "common_count": len(common_interests),
                "bio_third_view": candidate_profile.bio_third_view or "",
                "common_interests": common_interests,
                "profile_tags": profile_tags,
                "match_reason": r["match_reason"],
                "score_breakdown": r["score_breakdown"],
            })

        # Optional: shuffle with refresh_token for diversity
        if refresh_token:
            seed_int = int(hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()[:8], 16)
            top = matches[: max(limit * 3, limit)]
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
