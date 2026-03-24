"""ConversationSummaryService — generate and store conversation summaries.

When a conversation session grows beyond a configurable threshold, this
service calls the LLM to produce a concise summary and stores it on the
*first* ConversationMemory row of that session (session_summary column).

Additionally provides ``generate_memory_summary()`` which aggregates
conversation summaries + top KeyMemory entries into a holistic
``UserProfile.memory_summary`` paragraph.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from models.profile import ConversationMemory, KeyMemory, UserProfile
from services.llm_client import call_llm

logger = logging.getLogger(__name__)

# Summarise when a session has more messages than this
SUMMARY_THRESHOLD = 30

# ---- Prompt templates (internal) -----------------------------------------

CONVERSATION_SUMMARY_PROMPT = """你是一个擅长信息提炼的AI助手。
请用中文对以下对话进行简明而准确的总结，保留关键事实、用户表达的偏好、观点和情感。
总结应控制在 200 字以内。

## 对话内容
{conversation}

请直接输出总结文本，不要加标题或标签。"""

MEMORY_SUMMARY_PROMPT = """你是一名数字孪生体的记忆管理员。
请根据以下核心记忆片段和对话摘要，为该用户生成一段 300 字以内的"核心记忆总结"。
这段总结将帮助数字孪生体快速回忆该用户的关键信息。

## 核心记忆片段
{key_memories}

## 近期对话摘要
{conversation_summaries}

请直接输出总结文本（第三人称描述该用户），不要加标题或标签。"""


class ConversationSummaryService:
    """Generate and manage conversation & profile memory summaries."""

    def __init__(self, db: Session):
        self.db = db

    # ---- conversation-level summary --------------------------------------

    def maybe_summarize_session(self, user_id: str, session_id: str) -> Optional[str]:
        """Check if the session needs summarization and do it.

        Returns the summary text if generated, else None.
        """
        messages = (
            self.db.query(ConversationMemory)
            .filter(
                ConversationMemory.user_id == user_id,
                ConversationMemory.session_id == session_id,
            )
            .order_by(ConversationMemory.created_at.asc())
            .all()
        )
        if len(messages) < SUMMARY_THRESHOLD:
            return None

        # Check if we already have a summary for this session
        first = messages[0]
        if first.session_summary:
            return first.session_summary  # already done

        # Build the conversation transcript
        transcript_lines = []
        for msg in messages:
            role_label = "用户" if msg.role == "user" else "AI"
            transcript_lines.append(f"{role_label}: {msg.content}")
        transcript = "\n".join(transcript_lines)

        # Call LLM
        try:
            summary = call_llm(
                system_prompt="你是一个擅长信息提炼的助手。",
                user_message=CONVERSATION_SUMMARY_PROMPT.format(conversation=transcript),
                temperature=0.3,
                max_tokens=500,
            )
            summary = (summary or "").strip()
        except Exception as e:
            logger.error("Failed to summarize session %s: %s", session_id, e)
            return None

        # Persist: store on the *first* message of the session
        first.session_summary = summary
        self.db.commit()

        logger.info(
            "ConversationSummaryService: summarized session %s (%d msgs → %d chars)",
            session_id, len(messages), len(summary),
        )
        return summary

    # ---- user-level memory summary ---------------------------------------

    def generate_memory_summary(self, user_id: str) -> str:
        """Build a holistic memory summary for the user's profile.

        Combines top KeyMemory entries + all session summaries into one
        paragraph and writes it to ``UserProfile.memory_summary``.
        """
        # Gather top key memories
        top_memories = (
            self.db.query(KeyMemory)
            .filter(KeyMemory.user_id == user_id)
            .order_by(KeyMemory.importance_score.desc())
            .limit(15)
            .all()
        )
        km_text = "\n".join(
            f"- [{m.memory_type}] {m.content}" for m in top_memories
        ) or "（暂无关键记忆）"

        # Gather session summaries
        summaries = (
            self.db.query(ConversationMemory.session_summary)
            .filter(
                ConversationMemory.user_id == user_id,
                ConversationMemory.session_summary.isnot(None),
                ConversationMemory.session_summary != "",
            )
            .distinct()
            .limit(10)
            .all()
        )
        cs_text = "\n".join(
            f"- {row[0]}" for row in summaries if row[0]
        ) or "（暂无对话摘要）"

        # Call LLM
        try:
            result = call_llm(
                system_prompt="你是一名数字孪生体的记忆管理员。",
                user_message=MEMORY_SUMMARY_PROMPT.format(
                    key_memories=km_text,
                    conversation_summaries=cs_text,
                ),
                temperature=0.3,
                max_tokens=600,
            )
            result = (result or "").strip()
        except Exception as e:
            logger.error("Failed to generate memory summary for user %s: %s", user_id, e)
            return ""

        # Persist
        profile = (
            self.db.query(UserProfile)
            .filter(UserProfile.user_id == user_id)
            .first()
        )
        if profile:
            profile.memory_summary = result
            profile.system_prompt_cache = ""  # invalidate cache
            self.db.commit()
            logger.info("ConversationSummaryService: updated memory_summary for user %s", user_id)

        return result
