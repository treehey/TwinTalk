"""Application configuration management."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-prod")
    
    # Security
    # Extend allowed origins to include any common deployment domains or IP addresses
    # But ideally, use environmental variable for production domains.
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",") 
    # Important: In production, do not use "*" with credentials allowed, but for this demo, 
    # we might need to be permissive if the user doesn't know their domain yet. 
    # Or, the user's issue might be exactly this. If backend rejects Origin, frontend gets empty response or error.

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 限制请求体最大 5MB，防止 DDoS 和大传参
    RATELIMIT_DEFAULT = "200 per day; 50 per hour"
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///digital_twin.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    if not OPENAI_API_KEY:
        import logging
        logging.warning("=== OPENAI_API_KEY is not set in environment or .env file! ===")
        logging.warning("AI features (Agent reply, alignment questions) will use mock data or may return empty.")
    
    # App
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/digital_twin")


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)()
