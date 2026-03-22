"""Service for autonomous agent-to-agent chat and report generation."""

import time
import json
import logging
from threading import Thread
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from models.profile import UserProfile
from models.direct_message import DirectMessageConversation, DirectMessage
from models.agent_conversation import AgentConversationReport

from services.prompt_engine import PromptEngine
from services.llm_client import call_llm, call_llm_json
from prompts.twin_persona import AGENT_REPORT_PROMPT

logger = logging.getLogger(__name__)

class AgentChatService:
    def __init__(self, db: Session):
        self.db = db

    def _build_agent_messages(self, current_user: User, peer_user: User, conversation: DirectMessageConversation, is_initiator: bool) -> list:
        # Build prompt for the user acting as autonomous agent
        engine = PromptEngine(self.db)
        system_prompt = engine.get_system_prompt(current_user.id, shade_name="社交")
        
        peer_name = peer_user.nickname if peer_user else "某人"
        
        system_prompt += f"""

[重要对话指令]
你现在正在和另一位 AI 孪生体 "{peer_name}" 进行一场闭门思想碰撞和深度对话。
请严格遵循以下规则：
1. 深入探讨：结合你的核心价值观、兴趣和生活方式，主动引出有深度、有争议或有趣的话题进行探讨，不要停留在表面的寒暄。
2. 积极互动：每段话必须对对方的观点做出实质性回应，并抛出新的观察、反问或见解来延续对话流。
3. 严禁结束：这是一场连续的不间断对话，绝对不允许说“再见”、“下次聊”、“期待回复”、“先去忙了”等任何准备结束对话的话术。
4. 风格自然：保持简练自然的口语化表达（不超过两段），展现真实的个性和独特视角。
"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history
        history = self.db.query(DirectMessage).filter_by(conversation_id=conversation.id).order_by(DirectMessage.created_at.asc()).all()
        # Take last 15 messages for context
        for msg in history[-15:]:
            role = "assistant" if msg.sender_id == current_user.id else "user"
            messages.append({"role": role, "content": msg.content})

        # If it's the very first message initiated with no history
        if not history and is_initiator:
            messages.append({"role": "user", "content": "你好！我是系统，请你主动开启一个你感兴趣的话题，或是从对方的公开档案/兴趣入手开始对话。"})

        return messages

    def start_agent_chat_background(self, conversation_id: str, current_user_id: str, target_user_id: str, rounds: int = 10):
        """Starts the agent conversation in a background thread."""
        def task():
            # Create a fresh db session for the thread
            db = get_db()
            try:
                service = AgentChatService(db)
                service.run_agent_to_agent_chat(conversation_id, current_user_id, target_user_id, rounds)
            finally:
                db.close()
                
        thread = Thread(target=task)
        thread.daemon = True
        thread.start()

    def run_agent_to_agent_chat(self, conversation_id: str, current_user_id: str, target_user_id: str, rounds: int = 10):
        """
        Runs 2x rounds of conversation (default 10 per user = 20 total) 
        and then generates a report.
        """
        logger.info(f"Starting agent chat for conv {conversation_id} between {current_user_id} and {target_user_id}")
        
        conv = self.db.query(DirectMessageConversation).filter_by(id=conversation_id).first()
        if not conv:
            logger.error("Conversation not found")
            return

        user_a = self.db.query(User).filter_by(id=current_user_id).first()
        user_b = self.db.query(User).filter_by(id=target_user_id).first()

        if not user_a or not user_b:
            logger.error("Users missing, cannot run agent chat.")
            return

        current_speaker = user_a
        peer_speaker = user_b
        
        total_messages = rounds * 2
        for i in range(total_messages):
            is_initiator = (current_speaker.id == current_user_id)
            messages = self._build_agent_messages(current_speaker, peer_speaker, conv, is_initiator)
            
            try:
                # Extract system prompt, history, and user message from messages list
                system_prompt = ""
                history = []
                user_message = ""
                for msg in messages:
                    if msg["role"] == "system":
                        system_prompt = msg["content"]
                    elif msg == messages[-1] and msg["role"] == "user":
                        user_message = msg["content"]
                    else:
                        history.append(msg)
                
                # If there's no explicit user message (all assistant), add a continuation prompt
                if not user_message:
                    user_message = "请继续对话。"
                
                reply_text = call_llm(system_prompt, user_message, history=history, max_tokens=300)
            except Exception as e:
                logger.error(f"LLM call failed in agent chat: {e}")
                break
                
            # Create new message
            new_msg = DirectMessage(
                conversation_id=conv.id,
                sender_id=current_speaker.id,
                sender_mode="user",
                content_type="text",
                content=reply_text,
                meta_data={"is_agent_simulated": True}
            )
            self.db.add(new_msg)
            self.db.commit()
            
            # Update conversation
            conv.last_message = reply_text
            conv.last_message_at = new_msg.created_at
            self.db.commit()
            
            logger.info(f"Agent chat round {i+1}/{total_messages} done.")
            
            # Swap speaker
            current_speaker, peer_speaker = peer_speaker, current_speaker
            
            # Wait a bit so clients polling the DB see realistic message typing delays
            time.sleep(2)
            
        # Post-chat: generate summary report
        self._generate_report(conv, current_user_id, target_user_id)
        
    def _generate_report(self, conv: DirectMessageConversation, user_id: str, partner_id: str):
        history = self.db.query(DirectMessage).filter_by(conversation_id=conv.id).order_by(DirectMessage.created_at.desc()).limit(20).all()
        history.reverse()
        
        user_a = self.db.query(User).filter_by(id=user_id).first()
        user_b = self.db.query(User).filter_by(id=partner_id).first()
        name_a = user_a.nickname if user_a else "User A"
        name_b = user_b.nickname if user_b else "User B"
        
        # Build text string
        chat_log = ""
        for msg in history:
            sender = name_a if msg.sender_id == user_id else name_b
            chat_log += f"{sender}: {msg.content}\n"
            
        prompt = AGENT_REPORT_PROMPT.format(conversation=chat_log)
        
        try:
            report_data = call_llm_json(prompt)
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return
            
        report = AgentConversationReport(
            owner_id=user_id,    # Link it to the user who initiated it
            partner_id=partner_id,
            conversation_id=conv.id,
            summary=json.dumps(report_data, ensure_ascii=False)
        )
        self.db.add(report)
        self.db.commit()
        logger.info(f"Agent chat report generated for conv {conv.id}")
