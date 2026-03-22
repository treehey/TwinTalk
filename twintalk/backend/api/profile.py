"""Profile API — build, view, update user profiles."""

from flask import Blueprint, request, jsonify
import json
from database import get_db
from models.profile import UserProfile
from models.user import User
from services.profile_engine import ProfileEngine

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profiles")


@profile_bp.route("/build", methods=["POST"])
def build_profile():
    """构建 / 重建用户个人画像。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        engine = ProfileEngine(db)
        profile = engine.build_profile(user_id)
        return jsonify({
            "success": True,
            "profile": profile.to_dict(),
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@profile_bp.route("/me", methods=["GET"])
def get_my_profile():
    """获取当前用户的最新画像。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        profile = (
            db.query(UserProfile)
            .filter_by(user_id=user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )
        if not profile:
            return jsonify({
                "success": True,
                "profile": None,
                "message": "尚未构建画像，请先完成问卷",
            })
        # Calculate realistic fitness index
        from models.profile import KeyMemory
        memories_count = db.query(KeyMemory).filter_by(user_id=user_id).count()
        fitness = 20
        if profile.bio_summary:
            fitness += 5 if len(profile.bio_summary) > 20 else 2
        if profile.interests and len(profile.interests) > 0:
            fitness += min(15, len(profile.interests) * 2)
        if profile.personality_traits and len(profile.personality_traits) > 0:
            fitness += min(15, len(profile.personality_traits) * 2)
        if profile.extra_info:
            fitness += min(15, len(profile.extra_info.get("personality_keywords", [])) * 2)
            if profile.extra_info.get("mbti"):
                fitness += 5
        if profile.shades:
            fitness += min(10, len(profile.shades) * 3)
            
        fitness += min(20, int(memories_count * 1.5))
        fitness = min(99, int(fitness))

        return jsonify({
            "success": True,
            "profile": profile.to_dict(),
            "fitness_index": fitness,
        })
    finally:
        db.close()


@profile_bp.route("/me/shades", methods=["GET"])
def get_my_shades():
    """获取当前用户的角色切面列表。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        profile = (
            db.query(UserProfile)
            .filter_by(user_id=user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )
        if not profile:
            return jsonify({"success": True, "shades": []})
        return jsonify({
            "success": True,
            "shades": profile.shades or [],
        })
    finally:
        db.close()


@profile_bp.route("/me", methods=["PATCH"])
def update_my_profile():
    """手动微调画像字段。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    data = request.get_json()
    db = get_db()
    try:
        profile = (
            db.query(UserProfile)
            .filter_by(user_id=user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )
        if not profile:
            return jsonify({"error": "Profile not found, build it first"}), 404

        # Updatable fields
        for field in ["bio_summary", "interests", "communication_style", "shades"]:
            if field in data:
                setattr(profile, field, data[field])

        # Invalidate prompt cache when profile changes
        profile.system_prompt_cache = ""

        db.commit()
        return jsonify({
            "success": True,
            "profile": profile.to_dict(),
        })
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# NOTE: Memory CRUD endpoints are handled by api/memory.py (/api/memories/)
# Do NOT add duplicate memory routes here.

from prompts.twin_persona import ALIGNMENT_QUESTIONS_PROMPT
from services.llm_client import call_llm_json

@profile_bp.route("/alignment/questions", methods=["GET"])
def get_alignment_questions():
    """动态生成 3 道人格对齐问题"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401
    
    db = get_db()
    try:
        profile = (
            db.query(UserProfile)
            .filter_by(user_id=user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )
        if not profile:
            return jsonify({"error": "请先构建基础画像"}), 400
            
        profile_text = json.dumps(profile.to_dict(), ensure_ascii=False)
        prompt = ALIGNMENT_QUESTIONS_PROMPT.format(profile_text=profile_text)
        
        data = call_llm_json(prompt)
        if not data or "questions" not in data:
            # Fallback
            return jsonify({
                "success": True,
                "questions": [
                    { "id": "q1", "title": "朋友在圈子里向你借钱，你会？", "options": ["直接拉黑", "委婉拒绝", "问清缘由再决定"] },
                    { "id": "q2", "title": "收到冒犯性私信时，你更倾向？", "options": ["忽略", "礼貌回应后结束", "明确表达边界"] },
                    { "id": "q3", "title": "对方私信约线下见面，你会？", "options": ["直接拒绝", "先继续线上了解", "确认安全后再考虑"] }
                ]
            })
            
        return jsonify({
            "success": True, 
            "questions": data["questions"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@profile_bp.route("/alignment/submit", methods=["POST"])
def submit_alignment_answers():
    """保存用户作答为关键记忆"""
    import uuid
    from models.profile import KeyMemory
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401
        
    data = request.get_json()
    answers = data.get("answers", [])
    
    if not answers:
        return jsonify({"error": "No answers provided"}), 400
        
    db = get_db()
    try:
        content_lines = ["在人格对齐环节，我做出了以下选择表明我的态度："]
        for ans in answers:
            q_title = ans.get("title", "")
            q_choice = ans.get("choice", "")
            content_lines.append(f"- 面对【{q_title}】，我选择【{q_choice}】")
            
        mem_content = "\n".join(content_lines)
        
        mem = KeyMemory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            content=mem_content,
            memory_type="user_added",
            importance_score=0.8
        )
        db.add(mem)
        
        profile = (
            db.query(UserProfile)
            .filter_by(user_id=user_id)
            .order_by(UserProfile.version.desc())
            .first()
        )
        if profile:
            profile.system_prompt_cache = ""
            
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
