"""API package — register all blueprints."""

from .auth import auth_bp
from .questionnaire import questionnaire_bp
from .profile import profile_bp
from .chat import chat_bp
from .social import social_bp
from .memory import memory_bp
from .report import report_bp


def register_blueprints(app):
    """Register all application blueprints."""
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(questionnaire_bp, url_prefix="/api/questionnaires")
    app.register_blueprint(profile_bp, url_prefix="/api/profiles")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(social_bp, url_prefix="/api/social")
    app.register_blueprint(memory_bp, url_prefix="/api/memories")
    app.register_blueprint(report_bp, url_prefix="/api/reports")


__all__ = [
    "auth_bp", "questionnaire_bp", "profile_bp", "chat_bp", "social_bp",
    "memory_bp", "report_bp", "register_blueprints",
]
