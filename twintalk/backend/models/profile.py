"""User profile, conversation memory, and key memory models."""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, JSON,
    Enum, ForeignKey, Float, LargeBinary
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.session import Base

class UserProfile(Base):
    """用户个人画像 — 面向扩缩容全面加强版。"""
    __tablename__ = "user_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)

    # ---- 核心画像 ----
    bio_summary = Column(Text, default="", comment="第一人称自我简介")
    bio_third_view = Column(Text, default="", comment="第三人称视角简介")
    memory_summary = Column(Text, default="", comment="对于此分身的核心记忆提取摘要")

    # 特征集合 (结构化数据)
    personality_traits = Column(JSON, default=dict, comment="性格特征维度得分")
    values_profile = Column(JSON, default=dict, comment="价值观档案")
    interests = Column(JSON, default=list, comment="兴趣列表")
    knowledge_base = Column(JSON, default=list, comment="技能或专业知识库标签")
    communication_style = Column(JSON, default=dict, comment="沟通风格(语气, 常用词等)")
    social_graph_summary = Column(JSON, default=dict, comment="该用户在群体中的社交表现总结")
    
    # ---- 状态与表现设置 (未来扩展) ----
    dynamic_state = Column(JSON, default=dict, comment="当前情绪、近期注意力焦点等短期状态")
    voice_id = Column(String(100), default="", comment="TTS 声音预设 ID")
    avatar_config = Column(JSON, default=dict, comment="可视化 2D/3D Avatar 的外观组合参数")
    privacy_settings = Column(JSON, default=dict, comment="关于该分身的隐私选项设置")
    language = Column(String(50), default="zh-CN", comment="该分身偏好的语言与区域")

    # ---- 结构化基础信息 (来自引导问卷的直接字段) ----
    extra_info = Column(JSON, default=dict, comment="引导问卷或外部补充的其他结构化信息")

    # ---- Shade 角色系统 ----
    shades = Column(JSON, default=list, comment="多面人设、特定的角色表现修改器")

    # ---- 缓存与系统信息 ----
    system_prompt_cache = Column(Text, default="", comment="缓存的 system prompt")
    confidence_scores = Column(JSON, default=dict, comment="各维度置信度")
    source_summary = Column(Text, default="", comment="数据来源摘要")
    
    # 杂项元数据 (兜底扩展)
    meta_data = Column(JSON, default=dict, comment="可支持任意未预见的字段扩充")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="profiles")

    def to_dict(self, include_prompt=False):
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "version": self.version,
            "bio_summary": self.bio_summary,
            "bio_third_view": self.bio_third_view,
            "memory_summary": self.memory_summary,
            "personality_traits": self.personality_traits or {},
            "values_profile": self.values_profile or {},
            "interests": self.interests or [],
            "knowledge_base": self.knowledge_base or [],
            "communication_style": self.communication_style or {},
            "social_graph_summary": self.social_graph_summary or {},
            "dynamic_state": self.dynamic_state or {},
            "voice_id": self.voice_id,
            "avatar_config": self.avatar_config or {},
            "privacy_settings": self.privacy_settings or {},
            "language": self.language,
            "extra_info": self.extra_info or {},
            "shades": self.shades or [],
            "confidence_scores": self.confidence_scores or {},
            "meta_data": self.meta_data or {},
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }
        if include_prompt:
            result["system_prompt_cache"] = self.system_prompt_cache
        return result


class ConversationMemory(Base):
    """对话记忆 — 用于持续构建 / 修正个人档案。"""
    __tablename__ = "conversation_memories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    session_id = Column(String(36), nullable=False, comment="对话会话 ID")
    role = Column(
        Enum("user", "assistant", "system", name="message_role"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    
    # ---- 扩展字段 ----
    extracted_traits = Column(JSON, default=dict, comment="提取的新特征或事件")
    token_count = Column(Integer, default=0, comment="占用的 Token 数量(可选)")
    embedding_id = Column(String(100), nullable=True, comment="对应向量数据库中的向量ID(若有)")
    context_metadata = Column(JSON, default=dict, comment="其他上下文元数据(设备、地理位置等)")
    session_summary = Column(Text, default="", comment="LLM 生成的该会话摘要")
    
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="conversations")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "extracted_traits": self.extracted_traits or {},
            "token_count": self.token_count,
            "embedding_id": self.embedding_id,
            "context_metadata": self.context_metadata or {},
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }


class KeyMemory(Base):
    """关键记忆 — 用户主动添加或从对话中提取的重要信息片段。"""
    __tablename__ = "key_memories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False, comment="记忆内容")
    memory_type = Column(String(50), default="user_added", comment="user_added / chat_extracted / platform_generated")
    
    # ---- 扩展字段 ----
    importance_score = Column(Float, default=0.5, comment="记忆的重要性权重 0-1")
    tags = Column(JSON, default=list, comment="记忆标签(如 '情感', '经历')")
    embedding_id = Column(String(100), nullable=True, comment="对应向量数据库的向量 ID")
    embedding = Column(LargeBinary, nullable=True, comment="本地存储的文本向量嵌入 (numpy bytes)")
    meta_data = Column(JSON, default=dict, comment="时空或其他附加背景信息")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="key_memories")

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance_score": self.importance_score,
            "tags": self.tags or [],
            "embedding_id": self.embedding_id,
            "meta_data": self.meta_data or {},
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }