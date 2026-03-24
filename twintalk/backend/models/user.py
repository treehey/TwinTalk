"""User model."""

import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.session import Base

class User(Base):
    """User account model, linked to WeChat OpenID."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    openid = Column(String(64), unique=True, nullable=False, comment="微信 OpenID / 内部账户标识")
    phone_number = Column(String(20), unique=True, nullable=False, comment="登录手机号")
    password_hash = Column(String(256), nullable=True, comment="密码哈希")
    
    # 基础信息
    nickname = Column(String(100), default="")
    avatar_url = Column(String(512), default="")
    gender = Column(String(10), default="")
    bio = Column(Text, default="")
    email = Column(String(100), unique=True, nullable=True)
    
    # 状态与权限
    status = Column(String(20), default="active", comment="active/suspended/deleted")
    role = Column(String(20), default="user", comment="user/admin/vip")
    
    # 行为数据与配置包 (极具扩展性)
    preferences = Column(JSON, default=dict, comment="UI配置、通知、隐私设置等")
    meta_data = Column(JSON, default=dict, comment="注册来源、设备信息、IP等杂项扩展")
    
    profile_version = Column(Integer, default=0, comment="档案版本号")
    onboarding_completed = Column(Boolean, default=False, comment="是否完成初始引导问卷")
    
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    answers = relationship("Answer", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    profiles = relationship("UserProfile", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    conversations = relationship("ConversationMemory", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    key_memories = relationship("KeyMemory", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "openid": self.openid,
            "phone_number": self.phone_number,
            "nickname": self.nickname,
            "avatar_url": self.avatar_url,
            "gender": self.gender,
            "bio": self.bio,
            "email": self.email,
            "status": self.status,
            "role": self.role,
            "preferences": self.preferences or {},
            "meta_data": self.meta_data or {},
            "profile_version": self.profile_version,
            "onboarding_completed": bool(self.onboarding_completed),
            "last_login": self.last_login.isoformat() + "Z" if self.last_login else None,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }