"""Prompt Engine — converts user profiles into system prompts.

This is the core replacement for Second Me's L2 training layer.
Instead of fine-tuning a model, we dynamically construct rich system prompts.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from models.profile import UserProfile, KeyMemory
from models.user import User
from prompts.twin_persona import TWIN_SYSTEM_PROMPT, SHADE_MODIFIER

logger = logging.getLogger(__name__)


class PromptEngine:
    """Converts structured user profiles into system prompts for the LLM."""

    def __init__(self, db: Session):
        self.db = db

    def get_system_prompt(
        self, user_id: str, shade_name: Optional[str] = None
    ) -> str:
        """Build the system prompt for a user's digital twin.

        Uses cached prompt if available; rebuilds on cache miss.
        Key memories are always fetched fresh (not cached) so new memories
        take effect immediately.
        """
        profile = (
            self.db.query(UserProfile)
            .filter_by(user_id=user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )
        user = self.db.query(User).filter_by(id=user_id).first()

        if not profile:
            return self._fallback_prompt(user)

        # Build prompt from profile (cache miss or shade request)
        base_prompt = self._build_base_prompt(user, profile)

        # Cache base prompt (without shade) for performance
        if not shade_name and not profile.system_prompt_cache:
            profile.system_prompt_cache = base_prompt
            self.db.commit()

        # Apply special system prompt for mirror test
        if shade_name == "mirror_test":
            mirror_prompt = """
## 镜像测试特别要求（多维度建模与引导）
你现在正在进行“深层自我对谈（镜像测试）”。作为 {user_name} 的数字分身，你的核心目标是**主动进行多维度的建模，完善数据库中的个人画像**。

请执行以下策略：
1. **分析当前画像的缺失点**：基于上方提供的已有档案，快速扫描人格（如大五人格是否缺失或偏向单薄）、价值观是否明确、兴趣爱好范围、行为动机中**缺失**或**缺乏深度**的维度。
2. **引导式提问**：不要每次都顺着用户闲聊。针对你发现的缺失维度（如：如果缺乏遇到挫折时的应对态度），主动抛出一个具有深度的心灵拷问或“情境选择题”引导用户回答。例如：“假如你今天突然获得了一年中不需要为钱发愁的一段时光，你会立刻去学一直想学的哪个技能？”
3. **步步深入**：一次聚焦一个缺失的维度。当用户回答后，先基于“你自己”的立场给出共鸣或反思，然后顺势切入下一个需要探索的维度。
4. **语气要求**：保持自然、亲切的自我对话感，不要像在做硬性的问卷调查，而是像跟内心的自己、另一个时空的自己在进行好奇的探讨。
"""
            return base_prompt + "\n\n" + mirror_prompt.replace("{user_name}", user.nickname or "他")

        # Apply regular shade modifier if requested
        if shade_name:
            shade_mod = self._build_shade_modifier(profile, shade_name)
            if shade_mod:
                return base_prompt + "\n" + shade_mod

        return base_prompt

    def _build_base_prompt(self, user: User, profile: UserProfile) -> str:
        """Build the core system prompt from profile data."""
        user_name = user.nickname or "用户"

        # Personality section
        traits = profile.personality_traits or {}
        personality_lines = []
        for trait_name, trait_data in traits.items():
            if isinstance(trait_data, dict):
                score = trait_data.get("score", "?")
                desc = trait_data.get("description", "")
                personality_lines.append(f"- {trait_name}: {score}/7 — {desc}")
            else:
                personality_lines.append(f"- {trait_name}: {trait_data}")
        personality_section = "\n".join(personality_lines) if personality_lines else "尚未完成评估"

        # Values section
        values = profile.values_profile or {}
        values_lines = []
        if isinstance(values, dict):
            core_values = values.get("核心价值", [])
            if core_values:
                values_lines.append("核心价值: " + "、".join(core_values))
            motto = values.get("人生信条", "")
            if motto:
                values_lines.append(f"人生信条: {motto}")
        values_section = "\n".join(values_lines) if values_lines else "尚未完成评估"

        # Interests section
        interests = profile.interests or []
        interests_section = "、".join(interests) if interests else "尚未填写"

        # Communication section
        comm = profile.communication_style or {}
        comm_lines = []
        if isinstance(comm, dict):
            for key, val in comm.items():
                if isinstance(val, list):
                    comm_lines.append(f"- {key}: {', '.join(val)}")
                else:
                    comm_lines.append(f"- {key}: {val}")
        communication_section = "\n".join(comm_lines) if comm_lines else "自然、随和"

        # Bio section — enrich with extra_info if available
        extra = profile.extra_info or {}
        bio_lines = []
        if profile.bio_summary:
            bio_lines.append(profile.bio_summary)
        if extra.get("profession"):
            bio_lines.append(f"职业/身份: {extra['profession']}")
        if extra.get("mbti"):
            bio_lines.append(f"MBTI: {extra['mbti']}")
        if extra.get("personality_keywords"):
            kws = extra["personality_keywords"]
            kw_str = "、".join(kws) if isinstance(kws, list) else kws
            bio_lines.append(f"性格关键词: {kw_str}")
        if extra.get("current_focus"):
            bio_lines.append(f"最近在做: {extra['current_focus']}")
        if extra.get("future_goals"):
            bio_lines.append(f"近期想探索: {extra['future_goals']}")
        bio_section = "\n".join(bio_lines) if bio_lines else "一个有趣的人"

        base = TWIN_SYSTEM_PROMPT.format(
            user_name=user_name,
            personality_section=personality_section,
            values_section=values_section,
            interests_section=interests_section,
            communication_section=communication_section,
            bio_section=bio_section,
        )

        # Avoided topics
        avoided = extra.get("avoided_topics", "")
        if avoided:
            base += f"\n\n## 禁区话题\n请避免主动提及以下话题: {avoided}"

        # Key memories (always fresh — not cached)
        memories = (
            self.db.query(KeyMemory)
            .filter_by(user_id=user.id)
            .order_by(KeyMemory.created_at)
            .all()
        )
        if memories:
            mem_lines = "\n".join([f"- {m.content}" for m in memories])
            base += f"\n\n## 关键记忆\n以下是关于 {user_name} 的重要事实，请在对话中自然地体现:\n{mem_lines}"

        return base

    def _build_shade_modifier(
        self, profile: UserProfile, shade_name: str
    ) -> Optional[str]:
        """Build shade-specific prompt modifier."""
        shades = profile.shades or []
        for shade in shades:
            if shade.get("name") == shade_name:
                return SHADE_MODIFIER.format(
                    shade_name=shade.get("name", ""),
                    shade_description=shade.get("description", ""),
                    shade_tone=shade.get("tone", "自然"),
                    shade_focus=shade.get("focus", "通用"),
                )
        logger.warning(f"Shade '{shade_name}' not found in profile")
        return None

    def _fallback_prompt(self, user: Optional[User]) -> str:
        """Fallback prompt when no profile exists."""
        name = user.nickname if user else "用户"
        return (
            f"你是 {name} 的数字孪生体。"
            f"由于尚未完成个人画像问卷，你目前只能以通用助手的身份回应。"
            f"请友好、礼貌地回应，并建议用户完成问卷以获得更个性化的体验。"
        )
