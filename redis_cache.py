"""
redis_cache.py
Thin wrapper around Redis for URL caching.

All operations are wrapped in try/except so that a Redis outage
degrades gracefully (cache miss) rather than crashing the request.
"""
import redis
from config import settings

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    """Lazy singleton – avoids crashing at import time if Redis is down."""
    global _client
    if _client is None:
        _client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )
    return _client


def get_url(code: str) -> str | None:
    """Return the cached original URL for *code*, or None on miss/error."""
    try:
        return _get_client().get(code)
    except redis.RedisError:
        return None


def set_url(code: str, url: str, ttl: int | None = None) -> None:
    """Cache *url* under *code* with an optional TTL (seconds)."""
    try:
        r = _get_client()
        if ttl and ttl > 0:
            r.setex(code, ttl, url)
        else:
            r.set(code, url)
    except redis.RedisError:
        pass   # best-effort cache write; DB is the source of truth


def delete_url(code: str) -> None:
    """Remove *code* from the cache."""
    try:
        _get_client().delete(code)
    except redis.RedisError:
        pass


def ping() -> bool:
    """Return True if Redis is reachable (used by /health)."""
    try:
        return _get_client().ping()
    except redis.RedisError:
        return False


def get_stats() -> dict:
    """Get useful analytics from Redis for the UI."""
    try:
        r = _get_client()
        info = r.info()
        return {
            "status": "connected",
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human"),
            "total_keys": info.get("db0", {}).get("keys", 0) if isinstance(info.get("db0"), dict) else 0
        }
    except redis.RedisError as e:
        return {"status": "unreachable", "error": str(e)}


def get_all_data() -> dict:
    """Dump all keys and values from Redis for debugging/UI inspection."""
    try:
        r = _get_client()
        keys = r.keys("*")
        data = {}
        for k in keys:
            data[k] = r.get(k)
        return {"status": "success", "data": data}
    except redis.RedisError as e:
        return {"status": "error", "message": str(e)}