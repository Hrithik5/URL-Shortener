"""
app.py
FastAPI application – URL Shortener.

Endpoints:
  POST /shorten          – create a short URL
  GET  /{code}           – redirect to original URL (with Redis cache)
  GET  /stats/{code}     – analytics for a short code
  GET  /health           – service health check
"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from config import settings
from database import SessionLocal, init_db
from models import URL
from redis_cache import delete_url, get_url, ping as redis_ping, set_url, get_stats as get_redis_stats, get_all_data as get_redis_data
from schemas import HealthResponse, ShortenRequest, ShortenResponse, StatsResponse, SystemStatsResponse, SystemDataResponse
from utils import encode
from zookeeper_client import get_next_id, zk, get_stats as get_zk_stats, get_all_data as get_zk_data


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup; stop ZooKeeper client on shutdown."""
    init_db()
    yield
    if zk is not None:
        zk.stop()


app = FastAPI(
    title="URL Shortener",
    description="A small-scale URL Shortener using FastAPI, Redis, and ZooKeeper.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /shorten
# ---------------------------------------------------------------------------

@app.post("/shorten", response_model=ShortenResponse, status_code=201)
def shorten_url(body: ShortenRequest):
    """
    Accept a long URL and return a unique short code.

    ID generation strategy
    ----------------------
    1. ZooKeeper atomically increments a global counter and returns the next ID.
    2. The integer ID is Base-62–encoded into a short alphabetic code (e.g. 1 → "b").
    3. The mapping is persisted to SQLite and also cached in Redis.
    """
    unique_id = get_next_id()
    short_code = encode(unique_id)

    expiry_hours = body.expiry_hours or settings.default_expiry_hours
    expire_time = datetime.utcnow() + timedelta(hours=expiry_hours)

    db = SessionLocal()
    try:
        db_url = URL(
            short_code=short_code,
            original_url=str(body.original_url),
            expire_at=expire_time,
        )
        db.add(db_url)
        db.commit()
        db.refresh(db_url)
    finally:
        db.close()

    ttl = int((expire_time - datetime.utcnow()).total_seconds())
    set_url(short_code, str(body.original_url), ttl)

    return ShortenResponse(
        short_code=short_code,
        short_url=f"{settings.base_url}/{short_code}",
        original_url=str(body.original_url),
        expires_at=expire_time,
    )


# ---------------------------------------------------------------------------
# GET /stats/{code}  – must be declared BEFORE /{code} to avoid shadowing
# ---------------------------------------------------------------------------

@app.get("/stats/{code}", response_model=StatsResponse)
def get_stats(code: str):
    """Return analytics (click count, creation time, expiry) for a short code."""
    db = SessionLocal()
    try:
        url = db.query(URL).filter(URL.short_code == code).first()
    finally:
        db.close()

    if not url:
        raise HTTPException(status_code=404, detail=f"Short code '{code}' not found.")

    return StatsResponse(
        short_code=url.short_code,
        original_url=url.original_url,
        click_count=url.click_count,
        created_at=url.created_at,
        expires_at=url.expire_at,
    )


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health_check():
    """
    Report the connectivity status of all backing services.
    Returns HTTP 200 regardless – the caller should inspect the JSON payload.
    """
    # Database check
    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
    except Exception:
        db_status = "unreachable"

    # Redis check
    redis_status = "ok" if redis_ping() else "unreachable"

    # ZooKeeper check
    zk_status = "ok" if zk.connected else "unreachable"

    overall = "ok" if all(
        s == "ok" for s in (db_status, redis_status, zk_status)
    ) else "degraded"

    return HealthResponse(
        status=overall,
        database=db_status,
        redis=redis_status,
        zookeeper=zk_status,
    )


# ---------------------------------------------------------------------------
# GET /system/stats
# ---------------------------------------------------------------------------

@app.get("/system/stats", response_model=SystemStatsResponse)
def system_stats():
    """Return live system analytics from Redis and ZooKeeper."""
    return SystemStatsResponse(
        redis=get_redis_stats(),
        zookeeper=get_zk_stats()
    )


# ---------------------------------------------------------------------------
# GET /system/data
# ---------------------------------------------------------------------------

@app.get("/system/data", response_model=SystemDataResponse)
def system_data():
    """Return all raw keys and values directly from Redis and ZooKeeper."""
    return SystemDataResponse(
        redis_keys=get_redis_data(),
        zookeeper_data=get_zk_data()
    )


# ---------------------------------------------------------------------------
# GET /{code}  – redirect (declared last so /stats/ is checked first)
# ---------------------------------------------------------------------------

@app.get("/{code}")
def redirect_url(code: str):
    """
    Redirect the caller to the original URL.

    Cache-aside strategy
    --------------------
    1. Check Redis first (fast path, O(1) network hop).
    2. On cache miss, query SQLite (slow path).
    3. Re-populate Redis for subsequent requests.
    4. Increment click_count in the DB (best-effort; does not block redirect).
    """
    # --- Fast path: Redis cache hit ---
    cached = get_url(code)
    if cached:
        _increment_clicks(code)
        return RedirectResponse(url=cached, status_code=302)

    # --- Slow path: DB lookup ---
    db = SessionLocal()
    try:
        url = db.query(URL).filter(URL.short_code == code).first()

        if not url:
            raise HTTPException(status_code=404, detail=f"Short code '{code}' not found.")

        if url.expire_at and url.expire_at < datetime.utcnow():
            delete_url(code)
            raise HTTPException(status_code=410, detail="This short URL has expired.")

        # Re-populate cache
        ttl = int((url.expire_at - datetime.utcnow()).total_seconds()) if url.expire_at else None
        set_url(code, url.original_url, ttl)

        original = url.original_url

        # Increment click count inside same DB session
        url.click_count += 1
        db.commit()
    finally:
        db.close()

    return RedirectResponse(url=original, status_code=302)


def _increment_clicks(code: str) -> None:
    """Increment click_count for *code* in the database (best-effort)."""
    try:
        db = SessionLocal()
        db.query(URL).filter(URL.short_code == code).update(
            {URL.click_count: URL.click_count + 1}
        )
        db.commit()
        db.close()
    except Exception:
        pass
