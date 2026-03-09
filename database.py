"""
database.py
SQLAlchemy engine, session factory, and declarative base.
Tables are created on first import (create_all is idempotent).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

engine = create_engine(
    settings.database_url,
    # SQLite-specific: allow the same connection across threads
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


def init_db() -> None:
    """Create all tables. Safe to call multiple times (no-ops if tables exist)."""
    # Import models here so Base sees them before create_all
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)