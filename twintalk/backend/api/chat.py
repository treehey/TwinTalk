"""Chat API — conversation with digital twin."""

import uuid
import bleach
from flask import Blueprint, request, jsonify, Response, stream_with_context
from database import get_db
from services.chat_service import ChatService

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


def get_safe_message(data):
    """安全读取和清理前端发来的 message。防止 XSS 和提示词洪泛攻击。"""
    raw_message = data.get("message", "")
    if not isinstance(raw_message, str):
        return None
    raw_message = raw_message.strip()
    # 限制单次文本长度
    if len(raw_message) > 2000:
        raise ValueError("Message payload too large (exceeds 2000 characters).")
    # bleach 过滤掉一切 HTML
    return bleach.clean(raw_message)


@chat_bp.route("/message", methods=["POST"])
def send_message():
    """与自己的数字孪生对话。
    
    Body: {
        "message": "...",
        "session_id": "..." (optional, creates new session if absent),
        "shade": "职场" (optional, shade name for persona switching)
    }
    """
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    data = request.get_json()
    try:
        message = get_safe_message(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 413
    if not message:
        return jsonify({"error": "message is required"}), 400

    session_id = data.get("session_id", str(uuid.uuid4()))
    shade = data.get("shade")

    db = get_db()
    try:
        service = ChatService(db)
        reply = service.chat_with_twin(
            user_id=user_id,
            message=message,
            session_id=session_id,
            shade_name=shade,
        )
        return jsonify({
            "success": True,
            "session_id": session_id,
            "reply": reply,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@chat_bp.route("/mirror_greeting", methods=["POST"])
def get_mirror_greeting():
    """获取镜像聊天（深层自我对谈）的开场引导话题。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    data = request.get_json()
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    db = get_db()
    try:
        service = ChatService(db)
        result = service.generate_mirror_greeting(user_id=user_id, session_id=session_id)
        return jsonify({
            "success": True,
            "session_id": session_id,
            "reply": result.get("greeting", "你好，我是你的数字孪生。"),
            "suggestions": result.get("suggestions", []),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@chat_bp.route("/message/stream", methods=["POST"])
def stream_message():
    """SSE 流式对话接口。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    data = request.get_json()
    try:
        message = get_safe_message(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 413
    if not message:
        return jsonify({"error": "message is required"}), 400

    session_id = data.get("session_id", str(uuid.uuid4()))
    shade = data.get("shade")

    db = get_db()

    def generate():
        try:
            service = ChatService(db)
            for chunk in service.chat_with_twin_stream(
                user_id=user_id,
                message=message,
                session_id=session_id,
                shade_name=shade,
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
        finally:
            db.close()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@chat_bp.route("/message/<target_twin_id>", methods=["POST"])
def chat_with_other_twin(target_twin_id):
    """与他人的数字孪生对话。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    data = request.get_json()
    try:
        message = get_safe_message(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 413
    if not message:
        return jsonify({"error": "message is required"}), 400

    session_id = data.get("session_id", str(uuid.uuid4()))

    db = get_db()
    try:
        service = ChatService(db)
        reply = service.chat_with_twin(
            user_id=target_twin_id,  # 用目标用户的画像
            message=message,
            session_id=session_id,
            initiator_id=user_id,
        )
        return jsonify({
            "success": True,
            "session_id": session_id,
            "reply": reply,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@chat_bp.route("/sessions", methods=["GET"])
def get_sessions():
    """获取对话历史列表。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        service = ChatService(db)
        sessions = service.get_user_sessions(user_id)
        return jsonify({
            "success": True,
            "sessions": sessions,
        })
    finally:
        db.close()


@chat_bp.route("/sessions/<session_id>/messages", methods=["GET"])
def get_session_messages(session_id):
    """获取指定会话的消息列表。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        service = ChatService(db)
        messages = service.get_session_messages(user_id, session_id)
        return jsonify({
            "success": True,
            "messages": messages,
        })
    finally:
        db.close()
