"""
models.py
SQLAlchemy ORM model for the urls table.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime

from database import Base


class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String, unique=True, index=True, nullable=False)
    original_url = Column(String, nullable=False)
    click_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expire_at = Column(DateTime, nullable=True)