"""
schemas.py
Pydantic models for request validation and response serialisation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl


class ShortenRequest(BaseModel):
    original_url: HttpUrl
    expiry_hours: Optional[int] = None   # falls back to DEFAULT_EXPIRY_HOURS


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    expires_at: datetime


class StatsResponse(BaseModel):
    short_code: str
    original_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime]


class HealthResponse(BaseModel):
    status: str          # "ok" | "degraded"
    database: str
    redis: str
    zookeeper: str


class SystemStatsResponse(BaseModel):
    redis: dict
    zookeeper: dict


class SystemDataResponse(BaseModel):
    redis_keys: dict
    zookeeper_data: dict
