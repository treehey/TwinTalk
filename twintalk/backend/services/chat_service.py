"""Chat Service — manages conversations with digital twins.

v2: Integrates with KeyMemoryService for deduplication-aware insight saving,
    ConversationSummaryService for session summarization, and passes
    context_hint to PromptEngine for semantic memory retrieval.
"""

import uuid
import json
import logging
from typing import Optional, Generator
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from models.profile import ConversationMemory, UserProfile
from services.prompt_engine import PromptEngine
from services.llm_client import call_llm, call_llm_stream, call_llm_json
from prompts.twin_persona import TRAIT_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

# Maximum number of recent messages to include as context
MAX_CONTEXT_MESSAGES = 20
# Extract traits from conversation every N user messages (per session)
TRAIT_EXTRACTION_INTERVAL = 8


class ChatService:
    """Handles chat conversations with digital twins."""

    def __init__(self, db: Session):
        self.db = db
        self.prompt_engine = PromptEngine(db)

    def chat_with_twin(
        self,
        user_id: str,
        message: str,
        session_id: str,
        shade_name: Optional[str] = None,
        initiator_id: Optional[str] = None,
    ) -> str:
        """Send a message to a digital twin and get a response."""
        actual_user_id = initiator_id or user_id

        # Build context hint from recent messages for semantic retrieval
        history = self._get_history(session_id, actual_user_id)
        context_hint = self._build_context_hint(history, message)

        system_prompt = self.prompt_engine.get_system_prompt(
            user_id, shade_name, context_hint=context_hint
        )

        reply = call_llm(system_prompt, message, history)

        self._save_message(actual_user_id, session_id, "user", message)
        self._save_message(actual_user_id, session_id, "assistant", reply)

        # Trigger rolling profile update periodically
        self._maybe_update_profile(actual_user_id, session_id)

        # Trigger session summarization if needed
        self._maybe_summarize_session(actual_user_id, session_id)

        return reply

    def generate_mirror_greeting(self, user_id: str, session_id: str) -> dict:
        """Generate a proactive guided question as the initial greeting and suggested responses for mirror tests."""
        shade_name = "mirror_test"
        system_prompt = self.prompt_engine.get_system_prompt(user_id, shade_name)
        
        json_prompt = f"""
{system_prompt}

【任务要求】
请针对当前用户的画像分析其缺失点或薄弱的部分，并生成一个镜像自我对话的开场白。同时，为了引导用户，请提供 3 个确切的引导式提问选项（比如关于音乐、游戏、日常习惯、情绪等非常具体的切入点），供用户直接选择来开启话题。

必须返回严格有效的 JSON 格式，包含以下字段：
{{
    "greeting": "一段自然亲切的开场白，直接抛出你想探讨的话题方向。",
    "suggestions": [
        "你平常喜欢听什么类型的歌？",
        "你一直想学但没去学的一项技能是什么？",
        "上一次让你感到完全放松是什么时候？"
    ]
}}
"""
        try:
            result = call_llm_json(json_prompt)
            greeting = result.get("greeting", "你好！我准备好进行对谈了，今天有什么想梳理的心绪吗？")
            suggestions = result.get("suggestions", ["我想聊聊最近的开心事", "谈谈工作/学习压力", "分享一个有趣的爱好"])
        except Exception:
            greeting = "嗨，我是你的数字孪生。今天有什么想梳理的心绪吗？"
            suggestions = ["我想聊聊最近的开心事", "谈谈工作/学习压力", "分享一个有趣的爱好"]
        
        # Save only the assistant's greeting, omit the dummy user prompt
        self._save_message(user_id, session_id, "assistant", greeting)
        
        return {
            "greeting": greeting,
            "suggestions": suggestions
        }

    def chat_with_twin_stream(
        self,
        user_id: str,
        message: str,
        session_id: str,
        shade_name: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Stream chat response via SSE."""
        history = self._get_history(session_id, user_id)
        context_hint = self._build_context_hint(history, message)

        system_prompt = self.prompt_engine.get_system_prompt(
            user_id, shade_name, context_hint=context_hint
        )

        self._save_message(user_id, session_id, "user", message)

        full_reply = []
        for chunk in call_llm_stream(system_prompt, message, history):
            full_reply.append(chunk)
            yield json.dumps({"content": chunk}, ensure_ascii=False)

        self._save_message(user_id, session_id, "assistant", "".join(full_reply))
        self._maybe_update_profile(user_id, session_id)
        self._maybe_summarize_session(user_id, session_id)

    def get_user_sessions(self, user_id: str) -> list:
        """Get all conversation sessions for a user."""
        sessions = (
            self.db.query(
                ConversationMemory.session_id,
                sqlfunc.min(ConversationMemory.created_at).label("started_at"),
                sqlfunc.max(ConversationMemory.created_at).label("last_message_at"),
                sqlfunc.count(ConversationMemory.id).label("message_count"),
            )
            .filter_by(user_id=user_id)
            .group_by(ConversationMemory.session_id)
            .order_by(sqlfunc.max(ConversationMemory.created_at).desc())
            .all()
        )

        result = []
        for s in sessions:
            first_msg = (
                self.db.query(ConversationMemory)
                .filter_by(session_id=s.session_id, role="user")
                .order_by(ConversationMemory.created_at)
                .first()
            )
            result.append({
                "session_id": s.session_id,
                "started_at": s.started_at.isoformat() + "Z" if s.started_at else None,
                "last_message_at": s.last_message_at.isoformat() + "Z" if s.last_message_at else None,
                "message_count": s.message_count,
                "preview": first_msg.content[:100] if first_msg else "",
            })
        return result

    def get_session_messages(self, user_id: str, session_id: str) -> list:
        """Get all messages in a session."""
        messages = (
            self.db.query(ConversationMemory)
            .filter_by(user_id=user_id, session_id=session_id)
            .order_by(ConversationMemory.created_at)
            .all()
        )
        return [m.to_dict() for m in messages]

    # ── private helpers ────────────────────────────────────────────

    def _build_context_hint(self, history: list, current_message: str) -> str:
        """Build a short text snippet for semantic memory retrieval.

        Takes the last few messages + current user message and joins them.
        """
        recent_texts = [m["content"] for m in history[-4:]]
        recent_texts.append(current_message)
        return " ".join(recent_texts)[-500:]  # cap at 500 chars

    def _get_history(self, session_id: str, user_id: str) -> list:
        """Get recent conversation history for context."""
        messages = (
            self.db.query(ConversationMemory)
            .filter_by(session_id=session_id, user_id=user_id)
            .order_by(ConversationMemory.created_at.desc())
            .limit(MAX_CONTEXT_MESSAGES)
            .all()
        )
        messages.reverse()
        return [{"role": m.role, "content": m.content} for m in messages]

    def _save_message(self, user_id: str, session_id: str, role: str, content: str):
        """Save a message to conversation memory."""
        memory = ConversationMemory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
        )
        self.db.add(memory)
        self.db.commit()

    def _maybe_summarize_session(self, user_id: str, session_id: str):
        """Trigger conversation summarization when session is long enough."""
        try:
            from services.conversation_summary_service import ConversationSummaryService
            svc = ConversationSummaryService(self.db)
            svc.maybe_summarize_session(user_id, session_id)
        except Exception as e:
            logger.warning("Session summarization failed (non-critical): %s", e)

    def _maybe_update_profile(self, user_id: str, session_id: str):
        """Periodically extract traits from conversation and update profile.

        v2 changes:
          - Uses *session-level* message count instead of global count.
          - Saves mirror insights via KeyMemoryService (with dedup).
          - Also applies personality_updates, values_updates, notable_quotes.
          - Triggers memory_summary regeneration after updates.
        """
        # Count messages in THIS session only
        session_user_msg_count = (
            self.db.query(ConversationMemory)
            .filter_by(user_id=user_id, session_id=session_id, role="user")
            .count()
        )

        is_mirror = session_id.startswith("mirror_")
        interval = 2 if is_mirror else TRAIT_EXTRACTION_INTERVAL

        if session_user_msg_count % interval != 0:
            return

        try:
            # Get recent messages from THIS session for extraction
            recent = (
                self.db.query(ConversationMemory)
                .filter_by(user_id=user_id, session_id=session_id)
                .order_by(ConversationMemory.created_at.desc())
                .limit(interval * 2)
                .all()
            )
            recent.reverse()

            if len(recent) < 2:
                return

            # Get current profile
            profile = (
                self.db.query(UserProfile)
                .filter_by(user_id=user_id)
                .order_by(UserProfile.version.desc())
                .first()
            )
            if not profile:
                return

            conv_text = "\n".join(
                [f"{m.role}: {m.content}" for m in recent]
            )
            profile_summary = (
                f"兴趣: {', '.join(profile.interests or [])}\n"
                f"性格: {json.dumps(profile.personality_traits or {}, ensure_ascii=False)}\n"
                f"价值观: {json.dumps(profile.values_profile or {}, ensure_ascii=False)}\n"
                f"沟通风格: {(profile.communication_style or {}).get('风格', '未知')}"
            )

            from prompts.twin_persona import MIRROR_INSIGHT_PROMPT

            if is_mirror:
                prompt = MIRROR_INSIGHT_PROMPT.format(conversation=conv_text)
                extracted = call_llm_json(prompt)
                if extracted:
                    if extracted.get("insights"):
                        self._save_mirror_insights(user_id, extracted["insights"])
                    if extracted.get("new_tags"):
                        self._apply_extracted_traits(profile, {"new_interests": extracted["new_tags"]})
            else:
                prompt = TRAIT_EXTRACTION_PROMPT.format(
                    conversation=conv_text,
                    current_profile=profile_summary,
                )
                extracted = call_llm_json(prompt)
                if extracted:
                    self._apply_extracted_traits(profile, extracted)

            # Regenerate memory summary after trait updates
            self._refresh_memory_summary(user_id)

            logger.info(
                "Rolling profile update applied for user %s "
                "(session %s, msg #%d, is_mirror=%s)",
                user_id, session_id, session_user_msg_count, is_mirror,
            )
        except Exception as e:
            logger.warning("Trait extraction failed (non-critical): %s", e)

    def _save_mirror_insights(self, user_id: str, insights: list):
        """Save insights from mirror test via KeyMemoryService (with dedup)."""
        try:
            from services.key_memory_service import KeyMemoryService
            km_svc = KeyMemoryService(self.db)
            for text in insights:
                km_svc.add_memory(
                    user_id=user_id,
                    content=f"在镜像测试中发现：{text}",
                    memory_type="system_extracted",
                    importance=0.7,
                    tags=["mirror_insight"],
                )
        except Exception as e:
            logger.warning("Failed to save mirror insights via KeyMemoryService: %s", e)
            # Fallback to direct insert
            from models.profile import KeyMemory
            for text in insights:
                mem = KeyMemory(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    content=f"在镜像测试中发现：{text}",
                    memory_type="system_extracted",
                    importance_score=0.7,
                )
                self.db.add(mem)
            self.db.commit()

    def _apply_extracted_traits(self, profile: UserProfile, traits: dict):
        """Merge extracted traits into the existing profile.

        v2: Also handles personality_updates, values_updates, notable_quotes.
        """
        updated = False

        # New interests
        new_interests = traits.get("new_interests", [])
        if new_interests:
            current = profile.interests or []
            profile.interests = list(dict.fromkeys(current + new_interests))
            updated = True

        # Communication notes
        comm_notes = traits.get("communication_notes", [])
        if comm_notes and traits.get("confidence") in ("MEDIUM", "HIGH"):
            style = dict(profile.communication_style or {})
            existing = style.get("对话观察", [])
            style["对话观察"] = (existing + comm_notes)[-10:]
            profile.communication_style = style
            updated = True

        # Personality updates (NEW in v2)
        personality_updates = traits.get("personality_updates", {})
        if personality_updates and traits.get("confidence") in ("MEDIUM", "HIGH"):
            current_traits = dict(profile.personality_traits or {})
            for dim, observation in personality_updates.items():
                if dim in current_traits and isinstance(current_traits[dim], dict):
                    current_traits[dim]["description"] = observation
                else:
                    current_traits[dim] = observation
            profile.personality_traits = current_traits
            updated = True

        # Values updates (NEW in v2)
        values_updates = traits.get("values_updates", [])
        if values_updates and traits.get("confidence") in ("MEDIUM", "HIGH"):
            current_values = dict(profile.values_profile or {})
            core = list(current_values.get("核心价值", []))
            for v in values_updates:
                if v not in core:
                    core.append(v)
            current_values["核心价值"] = core[-8:]  # keep top 8
            profile.values_profile = current_values
            updated = True

        # Notable quotes → save as key memories (NEW in v2)
        notable_quotes = traits.get("notable_quotes", [])
        if notable_quotes:
            try:
                from services.key_memory_service import KeyMemoryService
                km_svc = KeyMemoryService(self.db)
                for q in notable_quotes[:3]:  # max 3 per extraction
                    km_svc.add_memory(
                        user_id=profile.user_id,
                        content="用户原话：" + q,
                        memory_type="chat_extracted",
                        importance=0.6,
                        tags=["notable_quote"],
                    )
            except Exception as e:
                logger.warning("Failed to save notable quotes: %s", e)

        if updated:
            profile.system_prompt_cache = ""  # Invalidate cache
            self.db.commit()

    def _refresh_memory_summary(self, user_id: str):
        """Trigger regeneration of the holistic memory summary."""
        try:
            from services.conversation_summary_service import ConversationSummaryService
            svc = ConversationSummaryService(self.db)
            svc.generate_memory_summary(user_id)
        except Exception as e:
            logger.warning("Memory summary refresh failed (non-critical): %s", e)
