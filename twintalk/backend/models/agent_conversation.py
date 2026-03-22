"""Model for saving agent-to-agent conversation reports."""

import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.session import Base


class AgentConversationReport(Base):
    """Stores the summarization report of an agent-to-agent conversation."""

    __tablename__ = "agent_conversation_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    partner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    conversation_id = Column(String(36), ForeignKey("direct_message_conversations.id"), nullable=False)
    
    summary = Column(Text, nullable=False)
    meta_data = Column(JSON, default=dict)
    
    created_at = Column(DateTime, server_default=func.now())

    owner = relationship("User", foreign_keys=[owner_id])
    partner = relationship("User", foreign_keys=[partner_id])
    conversation = relationship("DirectMessageConversation")

    def to_dict(self):
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "partner_id": self.partner_id,
            "conversation_id": self.conversation_id,
            "summary": self.summary,
            "meta_data": self.meta_data or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "owner_nickname": self.owner.nickname if self.owner else None,
            "partner_nickname": self.partner.nickname if self.partner else None,
        }
