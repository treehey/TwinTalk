"""Chat Service — manages conversations with digital twins."""

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
# Extract traits from conversation every N user messages
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
        system_prompt = self.prompt_engine.get_system_prompt(user_id, shade_name)
        history = self._get_history(session_id, initiator_id or user_id)

        reply = call_llm(system_prompt, message, history)

        actual_user_id = initiator_id or user_id
        self._save_message(actual_user_id, session_id, "user", message)
        self._save_message(actual_user_id, session_id, "assistant", reply)

        # Trigger rolling profile update periodically
        self._maybe_update_profile(actual_user_id, session_id)

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
        system_prompt = self.prompt_engine.get_system_prompt(user_id, shade_name)
        history = self._get_history(session_id, user_id)

        self._save_message(user_id, session_id, "user", message)

        full_reply = []
        for chunk in call_llm_stream(system_prompt, message, history):
            full_reply.append(chunk)
            yield json.dumps({"content": chunk}, ensure_ascii=False)

        self._save_message(user_id, session_id, "assistant", "".join(full_reply))
        self._maybe_update_profile(user_id, session_id)

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

    def _maybe_update_profile(self, user_id: str, session_id: str):
        """Periodically extract traits from conversation and update profile.

        Runs every TRAIT_EXTRACTION_INTERVAL user messages to keep the profile
        evolving through natural conversation.
        """
        user_msg_count = (
            self.db.query(ConversationMemory)
            .filter_by(user_id=user_id, role="user")
            .count()
        )

        is_mirror = session_id.startswith("mirror_")
        interval = 2 if is_mirror else TRAIT_EXTRACTION_INTERVAL
        
        if user_msg_count % interval != 0:
            return

        try:
            # Get the most recent messages from this session for extraction
            recent = (
                self.db.query(ConversationMemory)
                .filter_by(user_id=user_id, session_id=session_id)
                .order_by(ConversationMemory.created_at.desc())
                .limit(TRAIT_EXTRACTION_INTERVAL * 2)
                .all()
            )
            recent.reverse()

            if len(recent) < 2:
                return

            # Get current profile summary
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

            logger.info(
                f"Rolling profile update applied for user {user_id} "
                f"(msg #{user_msg_count}, is_mirror={is_mirror})"
            )
        except Exception as e:
            logger.warning(f"Trait extraction failed (non-critical): {e}")

    def _save_mirror_insights(self, user_id: str, insights: list):
        """Save insights from mirror test as KeyMemory."""
        from models.profile import KeyMemory
        import uuid
        for text in insights:
            mem = KeyMemory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                content=f"在镜像测试中发现：{text}",
                memory_type="system_extracted",
                importance_score=0.7
            )
            self.db.add(mem)
        self.db.commit()

    def _apply_extracted_traits(self, profile: UserProfile, traits: dict):
        """Merge extracted traits into the existing profile."""
        updated = False

        new_interests = traits.get("new_interests", [])
        if new_interests:
            current = profile.interests or []
            profile.interests = list(dict.fromkeys(current + new_interests))
            updated = True

        comm_notes = traits.get("communication_notes", [])
        if comm_notes and traits.get("confidence") in ("MEDIUM", "HIGH"):
            style = dict(profile.communication_style or {})
            existing = style.get("对话观察", [])
            # Keep only last 10 observations to avoid prompt bloat
            style["对话观察"] = (existing + comm_notes)[-10:]
            profile.communication_style = style
            updated = True

        if updated:
            profile.system_prompt_cache = ""  # Invalidate cache
            self.db.commit()
