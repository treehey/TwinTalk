"""Authentication API — username/password registration and login."""

import uuid
import random
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
from models.user import User
from services.sms_service import send_verification_code, SmsSendError

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

SMS_CODE_TTL_SECONDS = 300
SMS_CODE_MAX_ATTEMPTS = 5
SMS_SEND_COOLDOWN_SECONDS = 60
_sms_code_store = {}


def _cleanup_sms_store(now: datetime):
    expired_tokens = [
        token
        for token, payload in _sms_code_store.items()
        if payload["expires_at"] <= now or payload.get("attempts_left", 0) <= 0
    ]
    for token in expired_tokens:
        _sms_code_store.pop(token, None)


def _build_sms_key(phone_number: str, purpose: str):
    return f"{purpose}:{phone_number}"


def _verify_sms_code(phone_number: str, purpose: str, code: str):
    now = datetime.utcnow()
    _cleanup_sms_store(now)

    key = _build_sms_key(phone_number, purpose)
    payload = _sms_code_store.get(key)
    if not payload:
        return False, "验证码已过期或无效，请重新发送"

    if payload["code"] != code.strip():
        payload["attempts_left"] = payload.get("attempts_left", SMS_CODE_MAX_ATTEMPTS) - 1
        if payload["attempts_left"] <= 0:
            _sms_code_store.pop(key, None)
            return False, "验证码错误次数过多，请重新发送"
        return False, "验证码错误"

    _sms_code_store.pop(key, None)
    return True, ""


@auth_bp.route("/send-sms-code", methods=["POST"])
def send_sms_code():
    """发送短信验证码。Body: { phone_number, purpose }"""
    data = request.get_json(silent=True) or {}
    phone_number = (data.get("phone_number") or "").strip()
    purpose = (data.get("purpose") or "login").strip().lower()

    if not phone_number:
        return jsonify({"error": "手机号不能为空"}), 400
    if purpose not in {"login", "register"}:
        return jsonify({"error": "验证码用途不合法"}), 400

    now = datetime.utcnow()
    _cleanup_sms_store(now)
    key = _build_sms_key(phone_number, purpose)
    existing = _sms_code_store.get(key)

    if existing and existing.get("next_send_at") and existing["next_send_at"] > now:
        retry_after = int((existing["next_send_at"] - now).total_seconds())
        return jsonify({"error": "发送过于频繁，请稍后再试", "retry_after": max(retry_after, 1)}), 429

    code = f"{random.randint(0, 999999):06d}"
    try:
        send_result = send_verification_code(phone_number, code)
    except SmsSendError as e:
        return jsonify({"error": str(e)}), 503

    _sms_code_store[key] = {
        "code": code,
        "expires_at": now + timedelta(seconds=SMS_CODE_TTL_SECONDS),
        "attempts_left": SMS_CODE_MAX_ATTEMPTS,
        "next_send_at": now + timedelta(seconds=SMS_SEND_COOLDOWN_SECONDS),
    }

    payload = {
        "success": True,
        "ttl_seconds": SMS_CODE_TTL_SECONDS,
        "retry_after": SMS_SEND_COOLDOWN_SECONDS,
    }
    if send_result.get("mock") and current_app.config.get("DEBUG"):
        payload["debug_code"] = code

    return jsonify(payload)

@auth_bp.route("/register", methods=["POST"])
def register():
    """注册新账户。Body: { phone_number, password }"""
    data = request.get_json(silent=True) or {}
    phone_number = (data.get("phone_number") or "").strip()
    password = data.get("password") or ""
    sms_code = (data.get("sms_code") or "").strip()
    sms_purpose = (data.get("sms_purpose") or "register").strip().lower()

    if not phone_number:
        return jsonify({"error": "手机号不能为空"}), 400
    if len(password) < 6:
        return jsonify({"error": "密码不能少于 6 位"}), 400
    if not sms_code:
        return jsonify({"error": "请先完成验证码校验"}), 400
    if sms_purpose != "register":
        return jsonify({"error": "验证码用途不合法"}), 400

    passed, message = _verify_sms_code(phone_number, sms_purpose, sms_code)
    if not passed:
        return jsonify({"error": message}), 400

    db = get_db()
    try:
        if db.query(User).filter_by(phone_number=phone_number).first():
            return jsonify({"error": "该手机号已注册"}), 409

        user = User(
            id=str(uuid.uuid4()),
            openid=f"local_{phone_number}",
            phone_number=phone_number,
            password_hash=generate_password_hash(password),
            nickname="", # Nickname will be collected during onboarding
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return jsonify({"success": True, "user": user.to_dict(), "is_new": True}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    """登录。Body: { phone_number, password }"""
    data = request.get_json(silent=True) or {}
    phone_number = (data.get("phone_number") or "").strip()
    password = data.get("password") or ""
    sms_code = (data.get("sms_code") or "").strip()
    sms_purpose = (data.get("sms_purpose") or "login").strip().lower()

    if not phone_number or not password:
        return jsonify({"error": "手机号和密码不能为空"}), 400
    if not sms_code:
        return jsonify({"error": "请先完成验证码校验"}), 400
    if sms_purpose != "login":
        return jsonify({"error": "验证码用途不合法"}), 400

    passed, message = _verify_sms_code(phone_number, sms_purpose, sms_code)
    if not passed:
        return jsonify({"error": message}), 400

    db = get_db()
    try:
        user = db.query(User).filter_by(phone_number=phone_number).first()
        if not user or not user.password_hash:
            return jsonify({"error": "手机号或密码错误"}), 401
        if not check_password_hash(user.password_hash, password):
            return jsonify({"error": "手机号或密码错误"}), 401

        return jsonify({"success": True, "user": user.to_dict(), "is_new": False})
    finally:
        db.close()


@auth_bp.route("/me", methods=["GET"])
def get_current_user():
    """获取当前用户信息。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"success": True, "user": user.to_dict()})
    finally:
        db.close()


@auth_bp.route("/complete-onboarding", methods=["POST"])
def complete_onboarding():
    """标记用户已完成引导问卷。"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header required"}), 401

    db = get_db()
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        user.onboarding_completed = True
        db.commit()
        return jsonify({"success": True, "user": user.to_dict()})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
