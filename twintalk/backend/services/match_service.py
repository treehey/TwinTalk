"""Match Service — 混合推荐匹配算法（图谱规则召回 + LLM 语义精排）。

实现两阶段推荐：
  Stage 1 (Recall):  基于兴趣标签、MBTI 适配度、社交行为图谱等维度快速过滤候选人。
  Stage 2 (Rerank):  调用 LLM 对 Top-N 候选人进行深度语义精排，输出匹配理由。
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models.profile import UserProfile
from models.social import TwinConnection, TwinInteraction
from models.user import User
from services.llm_client import call_llm_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MBTI 适配度静态映射表
# 基于认知功能理论的互补/共鸣关系给出 0.0–1.0 的基础权重
# ---------------------------------------------------------------------------
_MBTI_COMPATIBILITY: Dict[str, Dict[str, float]] = {
    "INTJ": {"ENFP": 1.0, "ENTP": 0.9, "INFJ": 0.85, "INFP": 0.8,  "INTJ": 0.7,  "ENTJ": 0.75, "INTP": 0.7,  "ENFJ": 0.65},
    "INTP": {"ENTJ": 1.0, "ENFJ": 0.9, "INFJ": 0.8,  "INFP": 0.75, "INTJ": 0.7,  "ENTP": 0.7,  "INTP": 0.65, "ENFP": 0.7},
    "ENTJ": {"INTP": 1.0, "INFP": 0.9, "ISTP": 0.85, "INFJ": 0.8,  "INTJ": 0.75, "ENTP": 0.7,  "ENFJ": 0.7,  "ENFP": 0.65},
    "ENTP": {"INTJ": 1.0, "INFJ": 0.9, "INTP": 0.8,  "ENTJ": 0.7,  "INFP": 0.7,  "ENFP": 0.65, "ENFJ": 0.6,  "ENTP": 0.55},
    "INFJ": {"ENTP": 1.0, "ENFP": 0.9, "INTJ": 0.85, "INFP": 0.8,  "ENTJ": 0.8,  "INTP": 0.75, "ENFJ": 0.7,  "INFJ": 0.65},
    "INFP": {"ENFJ": 1.0, "ENTJ": 0.9, "INFJ": 0.85, "INTJ": 0.8,  "ENFP": 0.75, "INFP": 0.7,  "ENTP": 0.7,  "ENTP": 0.65},
    "ENFJ": {"INTP": 1.0, "INFP": 0.9, "ISFP": 0.85, "INFJ": 0.8,  "ENFP": 0.75, "ENTJ": 0.7,  "ENFJ": 0.65, "INTJ": 0.65},
    "ENFP": {"INTJ": 1.0, "INFJ": 0.9, "ENFJ": 0.8,  "INFP": 0.75, "ENTP": 0.7,  "ENFP": 0.65, "ENTJ": 0.65, "INTP": 0.65},
    "ISTJ": {"ESFP": 1.0, "ESTP": 0.9, "ISFJ": 0.85, "ESTJ": 0.8,  "ISTP": 0.75, "ISTJ": 0.7,  "ISFP": 0.65, "ESFJ": 0.65},
    "ISFJ": {"ESTP": 1.0, "ESFP": 0.9, "ISTJ": 0.85, "ESFJ": 0.8,  "ISFP": 0.75, "ISFJ": 0.7,  "ESTJ": 0.65, "ISTP": 0.65},
    "ESTJ": {"ISFP": 1.0, "ISTP": 0.9, "ESFJ": 0.85, "ISTJ": 0.8,  "ESTP": 0.75, "ESTJ": 0.7,  "ISFJ": 0.65, "ESFP": 0.65},
    "ESFJ": {"ISTP": 1.0, "ISFP": 0.9, "ESTJ": 0.85, "ESFJ": 0.7,  "ISFJ": 0.75, "ISTJ": 0.65, "ESTP": 0.65, "ESFP": 0.65},
    "ISTP": {"ESFJ": 1.0, "ESTJ": 0.9, "ESTP": 0.8,  "ISTJ": 0.75, "ISTP": 0.7,  "ISFJ": 0.65, "ISFP": 0.65, "ESFJ": 0.65},
    "ISFP": {"ESTJ": 1.0, "ESFJ": 0.9, "ISTP": 0.8,  "ESFP": 0.75, "ISFJ": 0.7,  "ISFP": 0.65, "ISTJ": 0.65, "ESTP": 0.65},
    "ESTP": {"ISFJ": 1.0, "ISTJ": 0.9, "ISTP": 0.85, "ESFP": 0.8,  "ESTJ": 0.75, "ESTP": 0.7,  "ESFJ": 0.65, "ISFP": 0.65},
    "ESFP": {"ISTJ": 1.0, "ISFJ": 0.9, "ESTP": 0.8,  "ESFP": 0.7,  "ISFP": 0.75, "ESTJ": 0.65, "ISTP": 0.65, "ESFJ": 0.65},
}

# 同类型自匹配默认权重（未在上表中定义的情况）
_MBTI_SAME_TYPE_WEIGHT: float = 0.6
# 无 MBTI 数据时的默认中性权重
_MBTI_NEUTRAL_WEIGHT: float = 0.5

# 批处理时每批最多多少个候选人发送给 LLM
_LLM_BATCH_SIZE: int = 8


# ---------------------------------------------------------------------------
# Pydantic 风格的返回数据模型（使用 dataclass 保持轻量级，无额外依赖）
# ---------------------------------------------------------------------------
@dataclass
class MatchResult:
    """单个匹配结果。"""
    candidate_id: str
    candidate_name: str
    final_score: float
    match_reason: str
    recall_score: float = 0.0
    score_breakdown: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate_name,
            "final_score": round(self.final_score, 4),
            "match_reason": self.match_reason,
            "recall_score": round(self.recall_score, 4),
            "score_breakdown": {k: round(v, 4) for k, v in self.score_breakdown.items()},
        }


# ---------------------------------------------------------------------------
# 辅助工具函数
# ---------------------------------------------------------------------------
def _jaccard(a: List[Any], b: List[Any]) -> float:
    """计算两个列表的 Jaccard 相似度（忽略大小写、空格）。"""
    a_set = {str(item).strip().lower() for item in (a or []) if str(item).strip()}
    b_set = {str(item).strip().lower() for item in (b or []) if str(item).strip()}
    if not a_set and not b_set:
        return 0.0
    return len(a_set & b_set) / len(a_set | b_set)


def _intersection_count(a: List[Any], b: List[Any]) -> int:
    """计算两个列表的交集元素个数。"""
    a_set = {str(item).strip().lower() for item in (a or []) if str(item).strip()}
    b_set = {str(item).strip().lower() for item in (b or []) if str(item).strip()}
    return len(a_set & b_set)


def _get_mbti(profile: UserProfile) -> Optional[str]:
    """从 extra_info 或 personality_traits 中提取 MBTI 字符串。"""
    if profile.extra_info and isinstance(profile.extra_info, dict):
        mbti = profile.extra_info.get("mbti") or profile.extra_info.get("MBTI") or ""
        mbti = str(mbti).upper().strip()
        if mbti in _MBTI_COMPATIBILITY:
            return mbti

    if profile.personality_traits and isinstance(profile.personality_traits, dict):
        mbti = profile.personality_traits.get("mbti") or profile.personality_traits.get("MBTI") or ""
        mbti = str(mbti).upper().strip()
        if mbti in _MBTI_COMPATIBILITY:
            return mbti

    return None


def _mbti_score(my_mbti: Optional[str], other_mbti: Optional[str]) -> float:
    """根据 MBTI 映射表计算两人之间的性格适配度。"""
    if not my_mbti or not other_mbti:
        return _MBTI_NEUTRAL_WEIGHT
    if my_mbti == other_mbti:
        return _MBTI_SAME_TYPE_WEIGHT
    return _MBTI_COMPATIBILITY.get(my_mbti, {}).get(other_mbti, _MBTI_NEUTRAL_WEIGHT)


def _build_candidate_profile_text(user: User, profile: UserProfile) -> str:
    """将候选人的关键画像信息压缩为紧凑的文本，用于 LLM Prompt 组装。"""
    interests = profile.interests or []
    mbti = _get_mbti(profile) or "未知"
    bio = (profile.bio_summary or user.bio or "").strip()[:200]
    values = profile.values_profile or {}
    knowledge = (profile.knowledge_base or [])[:5]

    parts = [
        f"ID: {user.id}",
        f"昵称: {user.nickname or '匿名'}",
        f"MBTI: {mbti}",
        f"兴趣: {', '.join(str(i) for i in interests[:10])}",
        f"价值观: {json.dumps(values, ensure_ascii=False)[:150]}",
        f"专业知识: {', '.join(str(k) for k in knowledge)}",
        f"简介: {bio}",
    ]
    return " | ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# 核心服务类
# ---------------------------------------------------------------------------
class MatchService:
    """提供混合推荐匹配能力的服务类。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -----------------------------------------------------------------------
    # 公开主函数
    # -----------------------------------------------------------------------
    def get_recommended_twins(
        self,
        user_id: str,
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        两阶段混合推荐：召回 → LLM 精排。

        Args:
            user_id: 当前用户的 UUID 字符串。
            top_n:   最终返回的推荐数量，默认 5。

        Returns:
            MatchResult.to_dict() 的列表，按 final_score 降序排列。
        """
        # --- Stage 1: 召回层 ---
        my_user, my_profile, recall_pool = self._recall_candidates(user_id, limit=20)

        if not recall_pool:
            logger.info("user %s: recall pool is empty, returning []", user_id)
            return []

        # 若没有 LLM 可用，退化为仅使用召回层分数
        try:
            results = self._rerank_with_llm(my_user, my_profile, recall_pool)
        except Exception as exc:
            logger.warning(
                "LLM reranking failed for user %s, falling back to recall scores. Error: %s",
                user_id,
                exc,
            )
            results = self._fallback_results(recall_pool)

        # 按最终得分降序，取 top_n
        results.sort(key=lambda r: r.final_score, reverse=True)
        return [r.to_dict() for r in results[:top_n]]

    # -----------------------------------------------------------------------
    # Stage 1: 召回层
    # -----------------------------------------------------------------------
    def _recall_candidates(
        self,
        user_id: str,
        limit: int = 20,
    ) -> Tuple[User, UserProfile, List[Tuple[User, UserProfile, float, Dict[str, float]]]]:
        """
        图谱规则召回：从数据库快速筛选最相关的候选人列表。

        Returns:
            (my_user, my_profile, candidates)
            candidates 中每项为 (candidate_user, candidate_profile, base_score, breakdown)
        """
        # 1️⃣ 查询当前用户及其最新画像
        my_user: Optional[User] = (
            self.db.query(User).filter(User.id == user_id).first()
        )
        if not my_user:
            raise ValueError(f"User {user_id} not found")

        my_profile: Optional[UserProfile] = (
            self.db.query(UserProfile)
            .filter(UserProfile.user_id == user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )
        if not my_profile:
            logger.warning("user %s has no profile, recall returns empty", user_id)
            return my_user, None, []

        my_interests: List[Any] = my_profile.interests or []
        my_mbti: Optional[str] = _get_mbti(my_profile)

        # 2️⃣ 查询行为图谱权重
        #    (a) 当前用户已有的社交连接 following 列表
        following_ids: set = {
            row.following_id
            for row in self.db.query(TwinConnection.following_id)
            .filter(TwinConnection.follower_id == user_id, TwinConnection.status == "accepted")
            .all()
        }
        #    (b) 与我互动过的用户（交互记录 initiator/target）
        interacted_ids: set = set()
        for row in (
            self.db.query(TwinInteraction.target_id)
            .filter(TwinInteraction.initiator_id == user_id)
            .all()
        ):
            interacted_ids.add(row.target_id)
        for row in (
            self.db.query(TwinInteraction.initiator_id)
            .filter(TwinInteraction.target_id == user_id)
            .all()
        ):
            interacted_ids.add(row.initiator_id)

        #    (c) 与我有共同关注的用户（二阶好友）
        common_friend_ids: set = set()
        if following_ids:
            for row in (
                self.db.query(TwinConnection.following_id)
                .filter(
                    TwinConnection.follower_id.in_(following_ids),
                    TwinConnection.status == "accepted",
                )
                .all()
            ):
                if row.following_id != user_id:
                    common_friend_ids.add(row.following_id)

        # 3️⃣ 拉取所有有画像且不是自己/已关注的候选人画像（子查询方式避免 N+1）
        #    先拉 subquery：每个 user 的最新 profile id
        from sqlalchemy import func as sa_func

        latest_profile_subq = (
            self.db.query(
                UserProfile.user_id,
                sa_func.max(UserProfile.version).label("max_ver"),
            )
            .group_by(UserProfile.user_id)
            .subquery()
        )

        candidate_profiles: List[UserProfile] = (
            self.db.query(UserProfile)
            .join(
                latest_profile_subq,
                (UserProfile.user_id == latest_profile_subq.c.user_id)
                & (UserProfile.version == latest_profile_subq.c.max_ver),
            )
            .filter(UserProfile.user_id != user_id)
            .all()
        )

        # 构建 user_id -> User 的快速查找缓存（仅查一次）
        profile_user_ids = [p.user_id for p in candidate_profiles]
        if not profile_user_ids:
            return my_user, my_profile, []

        candidate_users_map: Dict[str, User] = {
            u.id: u
            for u in self.db.query(User)
            .filter(User.id.in_(profile_user_ids), User.status == "active")
            .all()
        }

        # 4️⃣ 对每个候选人计算 recall 基础分
        scored: List[Tuple[User, UserProfile, float, Dict[str, float]]] = []

        for profile in candidate_profiles:
            cand_user = candidate_users_map.get(profile.user_id)
            if not cand_user:
                continue  # 用户不存在或非 active 状态

            cand_interests: List[Any] = profile.interests or []
            cand_mbti: Optional[str] = _get_mbti(profile)

            # --- 维度1：兴趣标签 Jaccard 相似度 (权重 0.45) ---
            tag_sim = _jaccard(my_interests, cand_interests)

            # --- 维度2：MBTI 性格适配度 (权重 0.30) ---
            mbti_sim = _mbti_score(my_mbti, cand_mbti)

            # --- 维度3：行为图谱权重 (权重 0.25) ---
            behavior_bonus = 0.0
            cid = profile.user_id
            if cid in interacted_ids:
                behavior_bonus += 0.6   # 已有直接互动
            if cid in common_friend_ids:
                behavior_bonus += 0.3   # 共同好友/关注
            behavior_bonus = min(behavior_bonus, 1.0)  # 钳位到 [0,1]

            # --- 综合召回得分 ---
            base_score = (
                0.45 * tag_sim
                + 0.30 * mbti_sim
                + 0.25 * behavior_bonus
            )

            breakdown: Dict[str, float] = {
                "tag_jaccard": tag_sim,
                "mbti_compatibility": mbti_sim,
                "behavior_graph": behavior_bonus,
            }
            scored.append((cand_user, profile, base_score, breakdown))

        # 5️⃣ 按基础得分降序取 Top-limit
        scored.sort(key=lambda x: x[2], reverse=True)
        return my_user, my_profile, scored[:limit]

    # -----------------------------------------------------------------------
    # Stage 2: LLM 精排层
    # -----------------------------------------------------------------------
    def _rerank_with_llm(
        self,
        my_user: User,
        my_profile: UserProfile,
        candidates: List[Tuple[User, UserProfile, float, Dict[str, float]]],
    ) -> List[MatchResult]:
        """
        LLM 语义精排：将候选人分批提交给 LLM，获取深度匹配评分与理由。

        Args:
            my_user:    当前用户对象。
            my_profile: 当前用户最新画像。
            candidates: 召回层输出的候选列表。

        Returns:
            MatchResult 列表（已注入 LLM 评分和理由）。
        """
        # 目标用户的压缩画像文本
        my_profile_text = _build_candidate_profile_text(my_user, my_profile)

        # 系统提示词（固定）
        system_prompt = (
            "你是一位社交心理学与用户匹配算法专家，精通 MBTI 认知功能理论、价值观契合度分析以及兴趣互补原则。"
            "你的任务是为目标用户评估一批候选人的契合度，从以下三个维度进行深度评估：\n"
            "1. 【价值观契合】双方的核心价值观是否对齐或有良好互补；\n"
            "2. 【兴趣互补】双方兴趣的交叉与互补程度，能否激发高质量的交流；\n"
            "3. 【性格动力学】基于 MBTI 或性格描述，双方的认知与互动模式是否相互促进；\n"
            "请对每位候选人给出 0–100 的整数匹配分，以及一段中文的匹配理由（50–120字，第一人称口吻，直接、温暖、有说服力）。\n"
            "必须严格返回 JSON 格式如下（不要包含任何额外文本或 Markdown）：\n"
            '{"results": [{"candidate_id": "<id>", "match_score": <int>, "match_reason": "<str>"}]}'
        )

        # 将候选人按批次处理
        batches: List[List[Tuple[User, UserProfile, float, Dict[str, float]]]] = []
        for i in range(0, len(candidates), _LLM_BATCH_SIZE):
            batches.append(candidates[i: i + _LLM_BATCH_SIZE])

        # 并发调用 LLM（使用线程池适配同步 LLM 客户端）
        llm_scores: Dict[str, Tuple[float, str]] = {}  # id -> (score, reason)

        def _process_batch(
            batch: List[Tuple[User, UserProfile, float, Dict[str, float]]]
        ) -> Dict[str, Tuple[float, str]]:
            """处理单批候选人，返回 {candidate_id: (score, reason)}。"""
            candidates_json = []
            for cand_user, cand_profile, _, _ in batch:
                candidates_json.append(_build_candidate_profile_text(cand_user, cand_profile))

            user_prompt = (
                f"目标用户画像：\n{my_profile_text}\n\n"
                f"候选人列表（共 {len(batch)} 人）：\n"
                + "\n---\n".join(candidates_json)
            )

            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            result = call_llm_json(
                prompt=full_prompt,
                temperature=0.3,
                max_tokens=2000,
            )
            batch_scores: Dict[str, Tuple[float, str]] = {}
            if result and isinstance(result.get("results"), list):
                for item in result["results"]:
                    cid = str(item.get("candidate_id", "")).strip()
                    score = float(item.get("match_score", 0)) / 100.0  # 归一化到 0-1
                    reason = str(item.get("match_reason", "")).strip()
                    if cid:
                        batch_scores[cid] = (score, reason)
            return batch_scores

        with ThreadPoolExecutor(max_workers=min(len(batches), 4)) as executor:
            future_map = {
                executor.submit(_process_batch, batch): batch
                for batch in batches
            }
            for future in as_completed(future_map):
                try:
                    batch_scores = future.result(timeout=60)
                    llm_scores.update(batch_scores)
                except Exception as exc:
                    logger.warning("LLM batch failed: %s", exc)

        # 融合召回分 + LLM 分，构建最终 MatchResult
        results: List[MatchResult] = []
        for cand_user, cand_profile, recall_score, breakdown in candidates:
            cid = cand_user.id
            llm_score, reason = llm_scores.get(cid, (None, None))

            if llm_score is not None:
                # 最终分 = 70% LLM 分 + 30% 召回基础分
                final_score = 0.70 * llm_score + 0.30 * recall_score
                match_reason = reason or "基于综合画像分析，双方具有较高契合度。"
            else:
                # LLM 未返回该候选人得分，退化到召回分
                final_score = recall_score
                match_reason = "基于兴趣标签与性格匹配的综合推荐。"

            results.append(
                MatchResult(
                    candidate_id=cid,
                    candidate_name=cand_user.nickname or "匿名用户",
                    final_score=final_score,
                    match_reason=match_reason,
                    recall_score=recall_score,
                    score_breakdown={
                        **breakdown,
                        "llm_score": llm_score if llm_score is not None else -1.0,
                    },
                )
            )

        return results

    # -----------------------------------------------------------------------
    # 退化策略：LLM 不可用时仅使用召回层分数
    # -----------------------------------------------------------------------
    @staticmethod
    def _fallback_results(
        candidates: List[Tuple[User, UserProfile, float, Dict[str, float]]]
    ) -> List[MatchResult]:
        """LLM 失败时将召回层结果包装为 MatchResult。"""
        results: List[MatchResult] = []
        for cand_user, cand_profile, recall_score, breakdown in candidates:
            results.append(
                MatchResult(
                    candidate_id=cand_user.id,
                    candidate_name=cand_user.nickname or "匿名用户",
                    final_score=recall_score,
                    match_reason="基于兴趣标签、性格特征与社交行为的综合分析，系统认为你们之间有较高契合度。",
                    recall_score=recall_score,
                    score_breakdown=breakdown,
                )
            )
        return results
