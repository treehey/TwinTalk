"""Database session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()
_engine = None
_SessionLocal = None


def init_db(database_url: str):
    """Initialize the database engine and create tables."""
    global _engine, _SessionLocal
    _engine = create_engine(database_url, echo=False, pool_pre_ping=True, pool_recycle=1800)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(bind=_engine)


def get_session():
    """Get a database session."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_db():
    """Get a database session (non-generator version for direct use)."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _SessionLocal()
