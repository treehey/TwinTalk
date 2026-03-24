"""Direct message service for user-to-user conversations."""

import uuid
import threading
from datetime import datetime, timedelta

from sqlalchemy import and_, or_, func as sqlfunc
from sqlalchemy.orm import Session

from models.direct_message import DirectMessageConversation, DirectMessage
from models.profile import KeyMemory, UserProfile
from models.user import User

from services.prompt_engine import PromptEngine
from services.llm_client import call_llm
from database.session import get_db


class DirectMessageService:
    """Provides a minimal DM workflow: start, list, read, and send."""

    def __init__(self, db: Session):
        self.db = db

    def start_conversation(
        self, user_id: str, target_user_id: str, source_community: str = ""
    ) -> dict:
        if user_id == target_user_id:
            raise ValueError("Cannot start direct message with yourself")

        target_user = self.db.query(User).filter_by(id=target_user_id).first()
        if not target_user:
            raise ValueError("Target user not found")

        existing = (
            self.db.query(DirectMessageConversation)
            .filter(
                or_(
                    and_(
                        DirectMessageConversation.participant_a_id == user_id,
                        DirectMessageConversation.participant_b_id == target_user_id,
                    ),
                    and_(
                        DirectMessageConversation.participant_a_id == target_user_id,
                        DirectMessageConversation.participant_b_id == user_id,
                    ),
                )
            )
            .first()
        )
        if existing:
            if source_community and not existing.source_community:
                existing.source_community = source_community
                self.db.commit()
            return self._conversation_to_dict(existing, user_id)

        conv = DirectMessageConversation(
            id=str(uuid.uuid4()),
            participant_a_id=user_id,
            participant_b_id=target_user_id,
            source_community=(source_community or "").strip(),
            last_message="",
            last_message_at=datetime.utcnow(),
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return self._conversation_to_dict(conv, user_id)

    def list_conversations(self, user_id: str) -> list:
        conversations = (
            self.db.query(DirectMessageConversation)
            .filter(
                or_(
                    DirectMessageConversation.participant_a_id == user_id,
                    DirectMessageConversation.participant_b_id == user_id,
                )
            )
            .order_by(DirectMessageConversation.last_message_at.desc())
            .all()
        )

        result = []
        for conv in conversations:
            if self._is_archived_for(conv, user_id):
                continue
            result.append(self._conversation_to_dict(conv, user_id))

        result.sort(
            key=lambda item: (
                item.get("last_message_at") or "",
            ),
            reverse=True,
        )
        return result

    def get_messages(self, user_id: str, conversation_id: str, limit: int = 200) -> list:
        conv = self._get_conversation_or_raise(user_id, conversation_id)
        messages = (
            self.db.query(DirectMessage)
            .filter_by(conversation_id=conv.id)
            .order_by(DirectMessage.created_at.asc())
            .limit(limit)
            .all()
        )
        return [m.to_dict() for m in messages]

    def send_message(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
        content_type: str = "text",
        agent_reply: bool = False,
    ) -> dict:
        conv = self._get_conversation_or_raise(user_id, conversation_id)

        if conv.blocked_by_id and conv.blocked_by_id != user_id:
            raise ValueError("You cannot send messages in this conversation")

        msg = DirectMessage(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            sender_id=user_id,
            sender_mode="user",
            content_type=content_type,
            content=content,
            meta_data={"agent_reply_enabled": bool(agent_reply)},
        )
        self.db.add(msg)

        conv.last_message = content[:200]
        conv.last_message_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(msg)
        sent_dict = msg.to_dict()

        if agent_reply:
            # Run LLM generation in background thread so the sender's message
            # is returned to the client immediately.
            target_user_id = conv.participant_b_id if conv.participant_a_id == user_id else conv.participant_a_id

            def _generate_reply(conv_id, sender_id, target_id, msg_content):
                import logging
                log = logging.getLogger(__name__)
                db = get_db()
                try:
                    sender_user = db.query(User).filter_by(id=sender_id).first()
                    sender_name = sender_user.nickname if sender_user else "对方"
                    target_user_obj = db.query(User).filter_by(id=target_id).first()
                    target_name = target_user_obj.nickname if target_user_obj else "我"

                    recent_msgs = (
                        db.query(DirectMessage)
                        .filter_by(conversation_id=conv_id)
                        .order_by(DirectMessage.created_at.desc())
                        .limit(10)
                        .all()
                    )
                    recent_msgs.reverse()
                    # Exclude the just-sent message from history to avoid duplication
                    # (msg_content is passed separately as user_message)
                    history = [
                        {"role": "user" if m.sender_id == sender_id else "assistant", "content": m.content}
                        for m in recent_msgs[:-1]
                    ]

                    prompt_engine = PromptEngine(db)
                    system_prompt = prompt_engine.get_system_prompt(target_id)
                    system_prompt += (
                        f"\n\n## 当前私信对话"
                        f"\n你（{target_name}）正在与 {sender_name} 进行一对一私信对话。"
                        f"\n请只生成你自己（{target_name}）的一条自然回复，不要生成 {sender_name} 的发言，"
                        f"不要生成多轮对话，不要在回复开头加任何角色名称或冒号标注，直接输出回复内容。"
                    )

                    reply_content = call_llm(system_prompt, msg_content, history)

                    reply_msg = DirectMessage(
                        id=str(uuid.uuid4()),
                        conversation_id=conv_id,
                        sender_id=target_id,
                        sender_mode="user",
                        content_type="text",
                        content=reply_content,
                        meta_data={"generated_by": "target_agent"},
                    )
                    db.add(reply_msg)
                    conv_row = db.query(DirectMessageConversation).filter_by(id=conv_id).first()
                    if conv_row:
                        conv_row.last_message = reply_content[:200]
                        conv_row.last_message_at = datetime.utcnow()
                    db.commit()
                except Exception as e:
                    log.error(f"Failed to generate agent reply: {e}")
                finally:
                    db.close()

            threading.Thread(
                target=_generate_reply,
                args=(conv.id, user_id, target_user_id, content),
                daemon=True,
            ).start()

        return sent_dict

    def suggest_message(self, user_id: str, conversation_id: str) -> dict:
        conv = self._get_conversation_or_raise(user_id, conversation_id)
        target_user_id = (
            conv.participant_b_id if conv.participant_a_id == user_id else conv.participant_a_id
        )

        me = self.db.query(User).filter_by(id=user_id).first()
        peer = self.db.query(User).filter_by(id=target_user_id).first()
        my_profile = (
            self.db.query(UserProfile)
            .filter_by(user_id=user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )
        peer_profile = (
            self.db.query(UserProfile)
            .filter_by(user_id=target_user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )

        recent_msgs = (
            self.db.query(DirectMessage)
            .filter_by(conversation_id=conv.id)
            .order_by(DirectMessage.created_at.desc())
            .limit(8)
            .all()
        )
        recent_msgs.reverse()

        # Build history from sender's perspective:
        # my past messages → "assistant", peer's messages → "user"
        all_msgs = list(recent_msgs)  # already in chronological order

        # Determine the trigger for the LLM
        if not all_msgs:
            # No history — this is the opening message
            history = []
            trigger = "这是与对方的第一次联系，请写一条简短自然的开场消息。"
            task_hint = "请写一条开场私信"
        elif all_msgs[-1].sender_id != user_id:
            # Last message was from peer — use it as the trigger (natural reply)
            trigger = all_msgs[-1].content
            history = [
                {"role": "assistant" if m.sender_id == user_id else "user", "content": m.content}
                for m in all_msgs[:-1]
            ]
            task_hint = "请根据对方刚才说的，写一条自然的回复"
        else:
            # Last message was from me — ask for a continuation
            history = [
                {"role": "assistant" if m.sender_id == user_id else "user", "content": m.content}
                for m in all_msgs
            ]
            trigger = "对话进行中，请根据聊天节奏继续写下一条合适的消息。"
            task_hint = "请继续这段对话"

        common_interests = self._common_interests(
            (my_profile.interests if my_profile else []) or [],
            (peer_profile.interests if peer_profile else []) or [],
        )

        # Use sender's own persona so the suggestion genuinely sounds like them
        prompt_engine = PromptEngine(self.db)
        my_system_prompt = prompt_engine.get_system_prompt(user_id)
        peer_brief = (peer_profile.bio_summary if peer_profile else "")[:80]
        common_str = "、".join(common_interests[:3]) if common_interests else "暂无明显重合"
        my_system_prompt += (
            f"\n\n## 当前私信对话：与 {peer.nickname if peer else '对方'} 的对话"
            f"\n对方简介：{peer_brief}"
            f"\n与对方的共同兴趣：{common_str}"
            f"\n任务：{task_hint}（20-60字）。"
            f"不要出现自己的名字、不要以'我是XXX'开头，直接切入话题，不要加任何额外说明。"
        )

        try:
            suggestion = call_llm(
                system_prompt=my_system_prompt,
                user_message=trigger,
                history=history,
                temperature=0.7,
                max_tokens=120,
            )
            text = (suggestion or "").strip()
            if not text:
                raise ValueError("empty suggestion")
        except Exception:
            text = self._fallback_suggestion(me, peer, common_interests)

        return {
            "text": text,
            "target_user_id": target_user_id,
            "common_interests": common_interests[:5],
        }

    def mark_read(self, user_id: str, conversation_id: str) -> int:
        conv = self._get_conversation_or_raise(user_id, conversation_id)
        updated = (
            self.db.query(DirectMessage)
            .filter(
                DirectMessage.conversation_id == conv.id,
                DirectMessage.sender_id != user_id,
                DirectMessage.read_at.is_(None),
            )
            .update({DirectMessage.read_at: datetime.utcnow()}, synchronize_session=False)
        )
        self.db.commit()
        return int(updated)

    def archive_conversation(self, user_id: str, conversation_id: str) -> dict:
        conv = self._get_conversation_or_raise(user_id, conversation_id)
        if conv.participant_a_id == user_id:
            conv.is_archived_a = True
        else:
            conv.is_archived_b = True
        self.db.commit()
        return {"conversation_id": conversation_id, "archived": True}

    def get_dm_stats(self, user_id: str) -> dict:
        since = datetime.utcnow() - timedelta(days=7)
        sent_messages_week = (
            self.db.query(sqlfunc.count(DirectMessage.id))
            .filter(
                DirectMessage.sender_id == user_id,
                DirectMessage.created_at >= since,
            )
            .scalar()
        )
        return {"sent_messages_week": int(sent_messages_week or 0)}

    def sync_dm_to_memories(self, user_id: str, limit: int = 30) -> dict:
        """Sync DM history into KeyMemory with LLM refinement and dedup.

        Instead of blindly copying raw messages, aggregates recent DMs,
        asks the LLM to extract key facts, and saves via KeyMemoryService.
        """
        rows = (
            self.db.query(DirectMessage)
            .filter_by(sender_id=user_id)
            .order_by(DirectMessage.created_at.desc())
            .limit(limit)
            .all()
        )

        if not rows:
            return {"synced": 0}

        # Aggregate DM content for LLM refinement
        dm_texts = []
        for msg in rows:
            text = (msg.content or "").strip()
            if text:
                dm_texts.append(text)

        if not dm_texts:
            return {"synced": 0}

        # Use LLM to extract key facts from DMs
        combined = "\n".join(dm_texts[:20])  # cap for token limits
        try:
            from services.llm_client import call_llm_json

            extract_prompt = f"""请从以下用户私信内容中提取 1-5 条关键个人信息、偏好或重要事实。
每条应简明扼要（一句话），只保留有意义的内容，忽略日常寒暄。

## 私信内容
{combined}

请以 JSON 格式输出：
{{
    "memories": ["关键事实1", "关键事实2"]
}}
如果没有有价值的信息，输出 {{"memories": []}}。"""

            result = call_llm_json(extract_prompt)
            memory_texts = (result or {}).get("memories", [])
        except Exception:
            # Fallback: just take first 5 messages
            memory_texts = [f"[私信] {t[:200]}" for t in dm_texts[:5]]

        # Save via KeyMemoryService (with dedup)
        synced = 0
        try:
            from services.key_memory_service import KeyMemoryService
            km_svc = KeyMemoryService(self.db)
            for text in memory_texts:
                if text.strip():
                    km_svc.add_memory(
                        user_id=user_id,
                        content=text.strip(),
                        memory_type="chat_extracted",
                        importance=0.5,
                        tags=["dm_sync"],
                    )
                    synced += 1
        except Exception:
            # Fallback: direct insert
            for text in memory_texts:
                if text.strip():
                    self.db.add(
                        KeyMemory(
                            id=str(uuid.uuid4()),
                            user_id=user_id,
                            content=f"[私信同步] {text.strip()[:300]}",
                            memory_type="chat_extracted",
                        )
                    )
                    synced += 1
            self.db.commit()

        return {"synced": synced}

    def get_common_communities(self, user_id: str, other_user_id: str) -> list:
        my_profile = (
            self.db.query(UserProfile)
            .filter_by(user_id=user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )
        other_profile = (
            self.db.query(UserProfile)
            .filter_by(user_id=other_user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )

        mine = (my_profile.interests if my_profile else []) or []
        other = (other_profile.interests if other_profile else []) or []
        return self._common_interests(mine, other)

    def _get_conversation_or_raise(
        self, user_id: str, conversation_id: str
    ) -> DirectMessageConversation:
        conv = self.db.query(DirectMessageConversation).filter_by(id=conversation_id).first()
        if not conv:
            raise ValueError("Conversation not found")

        if user_id not in (conv.participant_a_id, conv.participant_b_id):
            raise ValueError("Conversation access denied")

        return conv

    def _conversation_to_dict(self, conv: DirectMessageConversation, current_user_id: str) -> dict:
        partner_id = (
            conv.participant_b_id
            if conv.participant_a_id == current_user_id
            else conv.participant_a_id
        )
        partner = self.db.query(User).filter_by(id=partner_id).first()

        unread_count = (
            self.db.query(sqlfunc.count(DirectMessage.id))
            .filter(
                DirectMessage.conversation_id == conv.id,
                DirectMessage.sender_id != current_user_id,
                DirectMessage.read_at.is_(None),
            )
            .scalar()
        )

        return {
            "id": conv.id,
            "partner": partner.to_dict() if partner else {"id": partner_id, "nickname": "未知用户"},
            "source_community": conv.source_community or "",
            "last_message": conv.last_message or "",
            "last_message_at": conv.last_message_at.isoformat() + "Z" if conv.last_message_at else None,
            "unread_count": int(unread_count or 0),
            "created_at": conv.created_at.isoformat() + "Z" if conv.created_at else None,
        }

    @staticmethod
    def _is_archived_for(conv: DirectMessageConversation, user_id: str) -> bool:
        return (conv.participant_a_id == user_id and conv.is_archived_a) or (
            conv.participant_b_id == user_id and conv.is_archived_b
        )

    @staticmethod
    def _common_interests(a: list, b: list) -> list:
        a_set = {str(i).strip() for i in (a or []) if str(i).strip()}
        b_set = {str(i).strip() for i in (b or []) if str(i).strip()}
        return sorted(list(a_set & b_set))

    @staticmethod
    def _fallback_suggestion(me: User, peer: User, common_interests: list) -> str:
        peer_name = peer.nickname if peer and peer.nickname else "你"
        if common_interests:
            return f"你好，看到我们都对“{common_interests[0]}”感兴趣，想听听你最近在这方面的一个新发现。"
        return f"你好 {peer_name}，我看了你的主页挺有意思，想和你聊聊你最近最投入的一件事。"
