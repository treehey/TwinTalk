"""Social relationship and interaction models."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Enum, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.session import Base

class TwinConnection(Base):
    """孪生体之间的社交关系。极具扩展性的配置。"""
    __tablename__ = "twin_connections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    follower_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    following_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(
        Enum("pending", "accepted", "blocked", "ignored", name="connection_status"),
        default="pending",
    )
    
    match_score = Column(Float, default=0.0, comment="系统计算的匹配度 0-1")
    
    # ---- 扩展字段 ----
    relationship_label = Column(String(100), default="stranger", comment="关系标签：朋友/仇敌/同事/恋人等")
    affinity_score = Column(Float, default=0.5, comment="动态亲密度/好感度(根据互动增长或衰减)")
    interaction_frequency = Column(Integer, default=0, comment="此关系的交互活跃度频次统计")
    meta_data = Column(JSON, default=dict, comment="其他关系配置，例如单向屏蔽、特殊备注名")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "follower_id": self.follower_id,
            "following_id": self.following_id,
            "status": self.status,
            "match_score": self.match_score,
            "relationship_label": self.relationship_label,
            "affinity_score": self.affinity_score,
            "interaction_frequency": self.interaction_frequency,
            "meta_data": self.meta_data or {},
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }



class CommunityMembership(Base):
    """用户加入兴趣社区的记录。极具扩展性的配置。"""
    __tablename__ = "community_memberships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # ... (rest of community membership is likely omitted in my read) ...
    # Wait, I didn't read the whole file, so I don't know the exact content of CommunityMembership.
    # I should read the end of the file first to append correctly.

    __tablename__ = "community_memberships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    community_id = Column(String(100), nullable=True, comment="未来指向具体的社区实体的外键 ID")
    community_name = Column(String(100), nullable=False)
    
    # ---- 扩展字段 ----
    role = Column(String(50), default="member", comment="member/admin/creator")
    reputation_score = Column(Integer, default=0, comment="该用户在社区中的积分或声望")
    preferences = Column(JSON, default=dict, comment="在该社区的具体设置(如免打扰、特定标识)")
    
    last_active_at = Column(DateTime, nullable=True, comment="最近一次在该社区的活跃时间")
    joined_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "community_id": self.community_id,
            "community_name": self.community_name,
            "role": self.role,
            "reputation_score": self.reputation_score,
            "preferences": self.preferences or {},
            "last_active_at": self.last_active_at.isoformat() + "Z" if self.last_active_at else None,
            "joined_at": self.joined_at.isoformat() + "Z" if self.joined_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }


class TwinInteraction(Base):
    """孪生体交互记录。用于捕捉深度的社交行为信息。"""
    __tablename__ = "twin_interactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    initiator_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    target_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    interaction_type = Column(
        Enum("chat", "match", "collab", "poke", "share", name="interaction_type"),
        nullable=False,
    )
    
    session_id = Column(String(36), comment="关联的对话会话 ID")
    session_data = Column(JSON, default=dict, comment="交互会话元数据")
    
    # ---- 扩展字段 ----
    duration_seconds = Column(Integer, default=0, comment="本次互动的持时")
    interaction_summary = Column(Text, default="", comment="这段交互的AI总结，用以更新画像")
    impact_score = Column(Float, default=0.0, comment="本次交互对亲密度的影响分数 (影响 affinity_score)")
    meta_data = Column(JSON, default=dict, comment="支持未来扩展：如在什么场景下发生、触发原因等")

    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "initiator_id": self.initiator_id,
            "target_id": self.target_id,
            "interaction_type": self.interaction_type,
            "session_id": self.session_id,
            "session_data": self.session_data or {},
            "duration_seconds": self.duration_seconds,
            "interaction_summary": self.interaction_summary,
            "impact_score": self.impact_score,
            "meta_data": self.meta_data or {},
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }


class DailyMatch(Base):
    """Daily cache for user matches strategies."""
    __tablename__ = "daily_matches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    candidate_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    score = Column(Float, default=0.0)
    match_reason = Column(Text, default="")
    score_breakdown = Column(JSON, default=dict)
    
    # Store computed tags to speed up display
    profile_tags = Column(JSON, default=list)
    common_interests = Column(JSON, default=list)
    bio_third_view = Column(Text, default="")
    
    created_at = Column(DateTime, server_default=func.now())  # Daily update logic uses this

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "candidate_id": self.candidate_id,
            "score": self.score,
            "match_reason": self.match_reason,
            "score_breakdown": self.score_breakdown or {},
            "profile_tags": self.profile_tags or [],
            "common_interests": self.common_interests or [],
            "bio_third_view": self.bio_third_view or "",
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }
