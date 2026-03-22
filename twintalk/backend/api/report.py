from flask import Blueprint, jsonify, request
from functools import wraps
from typing import Callable

from database.session import get_db
from models.agent_conversation import AgentConversationReport

report_bp = Blueprint("report", __name__)


def require_user(f: Callable) -> Callable:
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.headers.get("X-User-Id")
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401
        return f(user_id, *args, **kwargs)

    return decorated_function


@report_bp.route("/", methods=["GET"])
@require_user
def list_reports(current_user_id: str):
    """Get all agent conversation reports for the current user."""
    db = get_db()
    try:
        # Reports where user is either the owner (initiator) or partner
        reports = (
            db.query(AgentConversationReport)
            .filter(
                (AgentConversationReport.owner_id == current_user_id) | 
                (AgentConversationReport.partner_id == current_user_id)
            )
            .order_by(AgentConversationReport.created_at.desc())
            .all()
        )
        return jsonify({
            "reports": [report.to_dict() for report in reports]
        })
    finally:
        db.close()


@report_bp.route("/<report_id>", methods=["GET"])
@require_user
def get_report(current_user_id: str, report_id: str):
    """Get a specific report details."""
    db = get_db()
    try:
        report = db.query(AgentConversationReport).filter_by(id=report_id).first()
        if not report:
            return jsonify({"error": "Report not found"}), 404
            
        if report.owner_id != current_user_id and report.partner_id != current_user_id:
            return jsonify({"error": "Unauthorized"}), 403
            
        return jsonify({"report": report.to_dict()})
    finally:
        db.close()

@report_bp.route("/<report_id>", methods=["DELETE"])
@require_user
def delete_report(current_user_id: str, report_id: str):
    """Delete a specific report."""
    db = get_db()
    try:
        report = db.query(AgentConversationReport).filter_by(id=report_id).first()
        if not report:
            return jsonify({"error": "Report not found"}), 404
            
        if report.owner_id != current_user_id and report.partner_id != current_user_id:
            return jsonify({"error": "Unauthorized"}), 403
            
        db.delete(report)
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
