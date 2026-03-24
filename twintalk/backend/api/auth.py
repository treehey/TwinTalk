"""Authentication API — username/password registration and login."""

import uuid
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
from models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """注册新账户。Body: { phone_number, password }"""
    data = request.get_json()
    phone_number = (data.get("phone_number") or "").strip()
    password = data.get("password") or ""

    if not phone_number:
        return jsonify({"error": "手机号不能为空"}), 400
    if len(password) < 6:
        return jsonify({"error": "密码不能少于 6 位"}), 400

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
    data = request.get_json()
    phone_number = (data.get("phone_number") or "").strip()
    password = data.get("password") or ""

    if not phone_number or not password:
        return jsonify({"error": "手机号和密码不能为空"}), 400

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
