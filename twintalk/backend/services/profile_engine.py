"""Profile Engine — builds user profiles from questionnaire answers.

This replaces Second Me's L1 generation pipeline (bio.py, shade_generator.py)
with a prompt-engineering approach.
"""

import json
import uuid
import logging
from typing import Optional
from sqlalchemy.orm import Session

from models.user import User
from models.questionnaire import Answer, Question, Questionnaire
from models.profile import UserProfile
from prompts.twin_persona import PROFILE_BUILDER_PROMPT
from services.llm_client import call_llm_json

logger = logging.getLogger(__name__)


class ProfileEngine:
    """Builds and updates user profiles from questionnaire data."""

    def __init__(self, db: Session):
        self.db = db

    def build_profile(self, user_id: str) -> UserProfile:
        """Build a new profile from all questionnaire answers.

        Workflow:
        1. Gather all user answers
        2. Extract structured extra_info from onboarding questionnaire
        3. Call LLM to generate the core profile JSON
        4. Save profile to database
        """
        user = self.db.query(User).filter_by(id=user_id).first()
        if not user:
            raise ValueError(f"User not found: {user_id}")

        answers = (
            self.db.query(Answer, Question)
            .join(Question, Answer.question_id == Question.id)
            .filter(Answer.user_id == user_id)
            .order_by(Question.dimension, Question.order_index)
            .all()
        )

        if not answers:
            raise ValueError("请先完成至少一份问卷")

        # Extract structured extra_info from onboarding questionnaire and update User nickname
        extra_info = self._extract_onboarding_info(user, answers)

        # Format answers for the LLM prompt
        answers_text = self._format_answers(answers)
        prompt = PROFILE_BUILDER_PROMPT.format(questionnaire_answers=answers_text)

        profile_data = call_llm_json(prompt)
        if not profile_data:
            raise RuntimeError("LLM 画像生成失败，请重试")

        latest = (
            self.db.query(UserProfile)
            .filter_by(user_id=user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )
        new_version = (latest.version + 1) if latest else 1

        profile = UserProfile(
            id=str(uuid.uuid4()),
            user_id=user_id,
            version=new_version,
            bio_summary=profile_data.get("bio_summary", ""),
            bio_third_view=profile_data.get("bio_third_view", ""),
            personality_traits=profile_data.get("personality_traits", {}),
            values_profile=profile_data.get("values_profile", {}),
            interests=profile_data.get("interests", []),
            communication_style=profile_data.get("communication_style", {}),
            shades=profile_data.get("shades", []),
            extra_info=extra_info,
            source_summary=f"基于 {len(answers)} 条问卷回答构建",
        )

        self.db.add(profile)
        user.profile_version = new_version
        self.db.commit()
        self.db.refresh(profile)

        logger.info(f"Built profile v{new_version} for user {user_id}")
        return profile

    def _extract_onboarding_info(self, user: User, answers) -> dict:
        """Extract structured fields from the onboarding questionnaire answers."""
        # Find the onboarding questionnaire
        onboarding_q = (
            self.db.query(Questionnaire)
            .filter_by(category="onboarding")
            .first()
        )
        if not onboarding_q:
            return {}

        # Map question order → answer for onboarding questionnaire
        extra = {}
        for answer, question in answers:
            if question.questionnaire_id != onboarding_q.id:
                continue

            val = answer.text_value or answer.choice_value or ""
            order = question.order_index

            if order == 1:
                # Update the user's nickname directly from the first question
                if val:
                    user.nickname = val
                extra["twin_nickname"] = val
            elif order == 2:
                # Age / Gender
                extra["age_gender"] = val
            elif order == 3:
                # City
                extra["city"] = val
            elif order == 4:
                # Profession
                extra["profession"] = val
            elif order == 5:
                # "MBTI, 三个词" — try to split MBTI from keywords
                parts = val.replace("，", ",").split(",", 1)
                if len(parts) == 2:
                    mbti_part = parts[0].strip()
                    kw_part = parts[1].strip()
                    extra["mbti"] = mbti_part
                    keywords = [k.strip() for k in kw_part.replace("、", ",").split(",") if k.strip()]
                    extra["personality_keywords"] = keywords[:3]
                else:
                    extra["mbti"] = val
            elif order == 6:
                # Hobbies
                hobbies = [h.strip() for h in val.replace("、", ",").split(",") if h.strip()]
                extra["top_hobbies"] = hobbies[:3]
            elif order == 7:
                # Current Focus
                extra["current_focus"] = val
            elif order == 8:
                # Future Goals
                extra["future_goals"] = val
            elif order == 9:
                # Communication Preference
                extra["communication_preference"] = val
            elif order == 10:
                # Avoided Topics
                avoided = val.strip()
                if avoided and avoided not in ("没有", "没有雷点", "无"):
                    extra["avoided_topics"] = avoided
            elif order == 11:
                # Social Purpose
                extra["social_purpose"] = val

        return extra

    def _format_answers(self, answers) -> str:
        """Format answer rows into readable text for LLM."""
        current_dimension = ""
        lines = []

        for answer, question in answers:
            if question.dimension != current_dimension:
                current_dimension = question.dimension
                lines.append(f"\n### {current_dimension or '通用'}")

            line = f"Q: {question.content}"
            if answer.scale_value is not None:
                line += f"\n   量表评分: {answer.scale_value}/{question.scale_max}"
            if answer.text_value:
                line += f"\n   文字描述: {answer.text_value}"
            if answer.choice_value:
                line += f"\n   选择: {answer.choice_value}"
            lines.append(line)

        return "\n".join(lines)

    def update_profile_from_traits(
        self, user_id: str, extracted_traits: dict
    ) -> Optional[UserProfile]:
        """Incrementally update profile with newly extracted traits from conversations."""
        profile = (
            self.db.query(UserProfile)
            .filter_by(user_id=user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )

        if not profile or not extracted_traits:
            return profile

        updated = False

        new_interests = extracted_traits.get("new_interests", [])
        if new_interests:
            current = profile.interests or []
            profile.interests = list(dict.fromkeys(current + new_interests))
            updated = True

        confidence = extracted_traits.get("confidence", "LOW")
        if confidence in ("MEDIUM", "HIGH"):
            notes = extracted_traits.get("communication_notes", [])
            if notes:
                style = dict(profile.communication_style or {})
                existing_notes = style.get("对话观察", [])
                style["对话观察"] = (existing_notes + notes)[-10:]
                profile.communication_style = style
                updated = True

        if updated:
            profile.system_prompt_cache = ""
            self.db.commit()
            logger.info(f"Updated profile for user {user_id} with new traits")

        return profile
