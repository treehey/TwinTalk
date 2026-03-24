"""Social API — discover, follow, match, and interact with other twins."""

import bleach
from flask import Blueprint, request, jsonify
from database import get_db
from services.social_service import SocialService
from services.direct_message_service import DirectMessageService

social_bp = Blueprint("social", __name__, url_prefix="/api/social")


def _safe_dm_message(data):
    raw_message = data.get("message", "")
    if not isinstance(raw_message, str):
        return None
    message = raw_message.strip()
    if len(message) > 2000:
        raise ValueError("Message payload too large (exceeds 2000 characters).")
    return bleach.clean(message)


@social_bp.route("/follow/<target_user_id>", methods=["POST"])
def follow_user(target_user_id):
    """关注用户的孪生体。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    if user_id == target_user_id:
        return jsonify({"error": "Cannot follow yourself"}), 400

    db = get_db()
    try:
        service = SocialService(db)
        connection = service.follow(user_id, target_user_id)
        return jsonify({
            "success": True,
            "connection": connection,
        })
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@social_bp.route("/unfollow/<target_user_id>", methods=["POST"])
def unfollow_user(target_user_id):
    """取消关注。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        service = SocialService(db)
        service.unfollow(user_id, target_user_id)
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@social_bp.route("/match", methods=["GET"])
def match_twins():
    """基于个性相似度匹配孪生体。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    limit = request.args.get("limit", 10, type=int)
    refresh_token = (request.args.get("refresh_token") or "").strip()

    db = get_db()
    try:
        service = SocialService(db)
        matches = service.find_matches(user_id, limit=limit, refresh_token=refresh_token)
        return jsonify({
            "success": True,
            "matches": matches,
        })
    finally:
        db.close()


@social_bp.route("/following", methods=["GET"])
def get_following():
    """获取当前用户关注的用户 ID 列表。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        service = SocialService(db)
        ids = service.get_following_ids(user_id)
        return jsonify({"success": True, "following_ids": ids})
    finally:
        db.close()








@social_bp.route("/common-communities/<target_user_id>", methods=["GET"])
def get_common_communities(target_user_id):
    """Get common communities between current user and target user."""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        service = DirectMessageService(db)
        common = service.get_common_communities(user_id, target_user_id)
        return jsonify({"success": True, "communities": common})
    finally:
        db.close()


@social_bp.route("/dm/conversations", methods=["GET"])
def list_dm_conversations():
    """List current user's direct message conversations."""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        service = DirectMessageService(db)
        conversations = service.list_conversations(user_id)
        return jsonify({"success": True, "conversations": conversations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@social_bp.route("/dm/conversations/start", methods=["POST"])
def start_dm_conversation():
    """Start or reuse a direct message conversation with target user."""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    data = request.get_json() or {}
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        return jsonify({"error": "target_user_id is required"}), 400

    db = get_db()
    try:
        service = DirectMessageService(db)
        conv = service.start_conversation(
            user_id=user_id,
            target_user_id=target_user_id,
            source_community=(data.get("source_community") or "").strip(),
        )
        return jsonify({"success": True, "conversation": conv})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@social_bp.route("/dm/conversations/<conversation_id>/messages", methods=["GET"])
def get_dm_messages(conversation_id):
    """Get direct messages of one conversation."""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        service = DirectMessageService(db)
        messages = service.get_messages(user_id, conversation_id)
        return jsonify({"success": True, "messages": messages})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@social_bp.route("/dm/conversations/<conversation_id>/messages", methods=["POST"])
def send_dm_message(conversation_id):
    """Send direct message in one conversation."""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    data = request.get_json() or {}
    try:
        message = _safe_dm_message(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 413

    if not message:
        return jsonify({"error": "message is required"}), 400

    db = get_db()
    try:
        service = DirectMessageService(db)
        created = service.send_message(
            user_id=user_id,
            conversation_id=conversation_id,
            content=message,
            content_type=data.get("content_type", "text"),
            agent_reply=data.get("agent_reply", False),
        )
        return jsonify({"success": True, "message": created})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@social_bp.route("/dm/conversations/<conversation_id>/suggestion", methods=["POST"])
def suggest_dm_message(conversation_id):
    """Generate one suggested message based on both users' profiles and context."""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        service = DirectMessageService(db)
        suggestion = service.suggest_message(user_id=user_id, conversation_id=conversation_id)
        return jsonify({"success": True, "suggestion": suggestion})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@social_bp.route("/dm/conversations/<conversation_id>/read", methods=["POST"])
def mark_dm_read(conversation_id):
    """Mark unread direct messages as read."""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        service = DirectMessageService(db)
        updated = service.mark_read(user_id, conversation_id)
        return jsonify({"success": True, "updated": updated})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@social_bp.route("/dm/conversations/<conversation_id>", methods=["DELETE"])
def archive_dm_conversation(conversation_id):
    """Archive one direct message conversation for current user."""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        service = DirectMessageService(db)
        result = service.archive_conversation(user_id, conversation_id)
        return jsonify({"success": True, **result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@social_bp.route("/dm/stats", methods=["GET"])
def get_dm_stats():
    """Get demo DM stats used by Ego page."""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        service = DirectMessageService(db)
        stats = service.get_dm_stats(user_id)
        return jsonify({"success": True, **stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@social_bp.route("/dm/sync-memory", methods=["POST"])
def sync_dm_memory():
    """Scan all explicit DM messages and extract possible key memories."""
    current_user_id = request.headers.get("X-User-Id")
    if not current_user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    db = get_db()
    try:
        service = DirectMessageService(db)
        result = service.sync_dm_to_memories(current_user_id)
        synced_count = result.get("synced", 0) if isinstance(result, dict) else 0
        return jsonify({"success": True, "synced": synced_count})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()


@social_bp.route("/dm/conversations/<conversation_id>/agent-chat", methods=["POST"])
def start_agent_chat(conversation_id: str):
    """Starts autonomous agent-to-agent chatting and report generation."""
    current_user_id = request.headers.get("X-User-Id")
    if not current_user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    db = get_db()
    try:
        service = DirectMessageService(db)
        conv = service._get_conversation_or_raise(current_user_id, conversation_id)
        target_user_id = conv.participant_b_id if conv.participant_a_id == current_user_id else conv.participant_a_id

        from services.agent_chat_service import AgentChatService
        agent_svc = AgentChatService(db)
        agent_svc.start_agent_chat_background(conversation_id, current_user_id, target_user_id, rounds=10)
        
        return jsonify({"success": True, "message": "Agent chat started in background"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()

