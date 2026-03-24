"""Questionnaire and answer models."""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, Boolean, JSON,
    Enum, ForeignKey, Float
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.session import Base

class Questionnaire(Base):
    """问卷模板"""
    __tablename__ = "questionnaires"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    category = Column(
        Enum("onboarding", "personality", "values", "lifestyle", "social", "communication", name="questionnaire_category"),
        nullable=False,
    )
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    order_index = Column(Integer, default=0, comment="问卷展示顺序")
    
    # ---- 扩展字段 ----
    tags = Column(JSON, default=list, comment="问卷分类标签")
    meta_data = Column(JSON, default=dict, comment="逻辑流配置、A/B测试组等")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    questions = relationship(
        "Question", back_populates="questionnaire",
        order_by="Question.order_index", lazy="joined", cascade="all, delete-orphan"
    )

    def to_dict(self, include_questions=False):
        result = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "is_active": self.is_active,
            "order_index": self.order_index,
            "tags": self.tags or [],
            "meta_data": self.meta_data or {},
            "question_count": len(self.questions) if self.questions else 0,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }
        if include_questions:
            result["questions"] = [q.to_dict() for q in self.questions]
        return result


class Question(Base):
    """问卷题目"""
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    questionnaire_id = Column(String(36), ForeignKey("questionnaires.id"), nullable=False)
    content = Column(Text, nullable=False, comment="题目内容")
    question_type = Column(
        Enum("scale", "text", "choice", "multi_choice", name="question_type"),
        nullable=False,
    )
    
    # Scale 配置
    scale_min = Column(Integer, default=1)
    scale_max = Column(Integer, default=7)
    scale_min_label = Column(String(50), default="完全不同意")
    scale_max_label = Column(String(50), default="完全同意")
    
    # Choice 配置 JSON 
    # 原本是 Column(Text) 为了向后兼容如果直接改类型可能有坑，我们换成 JSON 但保证兼容
    choices = Column(JSON, default=list, comment="选项列表 JSON")
    
    # 元数据
    order_index = Column(Integer, default=0)
    dimension = Column(String(100), default="", comment="所属维度")
    is_required = Column(Boolean, default=True)
    placeholder = Column(String(200), default="", comment="占位提示")
    
    # ---- 扩展字段 ----
    logic_jump = Column(JSON, default=dict, comment="基于答案的跳题逻辑")
    meta_data = Column(JSON, default=dict, comment="提示词或其他自定义字段")
    
    # Relationships
    questionnaire = relationship("Questionnaire", back_populates="questions")
    answers = relationship("Answer", back_populates="question", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        result = {
            "id": self.id,
            "questionnaire_id": self.questionnaire_id,
            "content": self.content,
            "question_type": self.question_type,
            "order_index": self.order_index,
            "dimension": self.dimension,
            "is_required": self.is_required,
            "logic_jump": self.logic_jump or {},
            "meta_data": self.meta_data or {},
        }
        if self.question_type == "scale":
            result.update({
                "scale_min": self.scale_min,
                "scale_max": self.scale_max,
                "scale_min_label": self.scale_min_label,
                "scale_max_label": self.scale_max_label,
            })
        elif self.question_type in ("choice", "multi_choice"):
            result["choices"] = self.choices or []
        elif self.question_type == "text":
            result["placeholder"] = self.placeholder
        return result


class Answer(Base):
    """用户回答"""
    __tablename__ = "answers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    question_id = Column(String(36), ForeignKey("questions.id"), nullable=False)
    questionnaire_id = Column(String(36), ForeignKey("questionnaires.id"), nullable=False)
    
    # 回答值
    scale_value = Column(Float, nullable=True, comment="数值量表答案")
    text_value = Column(Text, nullable=True, comment="文字描述答案")
    choice_value = Column(JSON, nullable=True, comment="选择题答案 JSON")
    
    # ---- 扩展字段 ----
    meta_data = Column(JSON, default=dict, comment="回答所用时长或客户端环境")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="answers")
    question = relationship("Question", back_populates="answers")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "question_id": self.question_id,
            "questionnaire_id": self.questionnaire_id,
            "scale_value": self.scale_value,
            "text_value": self.text_value,
            "choice_value": self.choice_value,
            "meta_data": self.meta_data or {},
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }