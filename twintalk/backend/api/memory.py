"""Memory API — CRUD + search for key memories (v2).

v2 changes:
  - POST uses KeyMemoryService for auto-dedup.
  - GET supports ?search= query for semantic search.
  - Added PATCH /<id> for editing memories.
"""

from flask import Blueprint, request, jsonify
from database import get_db
from models.profile import KeyMemory, UserProfile

memory_bp = Blueprint("memory", __name__, url_prefix="/api/memories")


def _invalidate_prompt_cache(db, user_id):
    """Invalidate system prompt cache so next chat includes updated memory."""
    profile = (
        db.query(UserProfile)
        .filter_by(user_id=user_id)
        .order_by(UserProfile.version.desc())
        .first()
    )
    if profile:
        profile.system_prompt_cache = ""


@memory_bp.route("/", methods=["GET"])
def list_memories():
    """获取当前用户的关键记忆。支持 ?search= 语义搜索 和 ?limit= 分页。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    search_query = request.args.get("search", "").strip()
    limit = request.args.get("limit", 50, type=int)

    db = get_db()
    try:
        if search_query:
            from services.key_memory_service import KeyMemoryService
            svc = KeyMemoryService(db)
            results = svc.search_memories(user_id, search_query, top_k=limit)
            return jsonify({"success": True, "memories": results})
        else:
            memories = (
                db.query(KeyMemory)
                .filter_by(user_id=user_id)
                .order_by(KeyMemory.importance_score.desc(), KeyMemory.created_at.desc())
                .limit(limit)
                .all()
            )
            return jsonify({
                "success": True,
                "memories": [m.to_dict() for m in memories],
            })
    finally:
        db.close()


@memory_bp.route("/", methods=["POST"])
def add_memory():
    """添加一条关键记忆（自动去重）。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    data = request.get_json() or {}
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "content is required"}), 400

    db = get_db()
    try:
        from services.key_memory_service import KeyMemoryService
        svc = KeyMemoryService(db)
        mem = svc.add_memory(
            user_id=user_id,
            content=content,
            memory_type=data.get("memory_type", "user_added"),
            importance=float(data.get("importance", 0.5)),
            tags=data.get("tags"),
        )

        _invalidate_prompt_cache(db, user_id)
        db.commit()

        return jsonify({
            "success": True,
            "memory": mem.to_dict(),
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@memory_bp.route("/<memory_id>", methods=["PATCH"])
def edit_memory(memory_id):
    """编辑一条关键记忆。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    data = request.get_json() or {}

    db = get_db()
    try:
        from services.key_memory_service import KeyMemoryService
        svc = KeyMemoryService(db)
        mem = svc.update_memory(
            memory_id=memory_id,
            user_id=user_id,
            content=data.get("content"),
            importance=data.get("importance"),
            tags=data.get("tags"),
        )
        if mem is None:
            return jsonify({"error": "Memory not found"}), 404

        _invalidate_prompt_cache(db, user_id)
        db.commit()

        return jsonify({"success": True, "memory": mem.to_dict()})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@memory_bp.route("/<memory_id>", methods=["DELETE"])
def delete_memory(memory_id):
    """删除一条关键记忆。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        memory = (
            db.query(KeyMemory)
            .filter_by(id=memory_id, user_id=user_id)
            .first()
        )
        if not memory:
            return jsonify({"error": "Memory not found"}), 404

        db.delete(memory)
        _invalidate_prompt_cache(db, user_id)
        db.commit()

        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
