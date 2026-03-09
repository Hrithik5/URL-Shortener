"""
zookeeper_client.py
Atomic distributed counter using ZooKeeper.

Falls back to a local in-process counter (threading.Lock) when ZooKeeper
is unreachable, so the app boots and works correctly in single-instance
local dev without any external services.

The retry loop around zk.set(..., version=stat.version) implements
optimistic locking: if another instance updates the node between our
read and write, the version check fails and we simply retry — the standard
pattern for distributed counters that avoids split-brain.
"""
import threading
import time
import logging

from config import settings

logger = logging.getLogger(__name__)

# Suppress Kazoo's connection-retry noise when ZK is not running
logging.getLogger("kazoo").setLevel(logging.CRITICAL)

# ---------------------------------------------------------------------------
# Try to connect to ZooKeeper; fall back to local counter if unavailable.
# ---------------------------------------------------------------------------

zk = None
_use_local_counter = False

try:
    from kazoo.client import KazooClient
    from kazoo.exceptions import BadVersionError

    zk = KazooClient(hosts=settings.zk_hosts)
    zk.start(timeout=5)          # fail fast — don't block startup for long

    COUNTER_PATH = "/url_counter"
    if not zk.exists(COUNTER_PATH):
        zk.create(COUNTER_PATH, b"1", makepath=True)

    logger.info("✅  ZooKeeper connected at %s", settings.zk_hosts)

except Exception as exc:
    logger.warning(
        "⚠️  ZooKeeper unavailable (%s). Using local in-process counter instead. "
        "This is fine for single-instance / local testing.",
        exc,
    )
    zk = None
    _use_local_counter = True


# ---------------------------------------------------------------------------
# Local fallback counter (thread-safe, single-process only)
# ---------------------------------------------------------------------------

_local_counter = 0
_local_lock = threading.Lock()


def _next_local_id() -> int:
    global _local_counter
    with _local_lock:
        _local_counter += 1
        return _local_counter


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_next_id() -> int:
    """
    Return an atomically incremented unique integer ID.
    Uses ZooKeeper when available, local counter otherwise.
    """
    if _use_local_counter:
        return _next_local_id()

    # ZooKeeper path — optimistic locking with retry
    from kazoo.exceptions import BadVersionError  # local import keeps top clean
    while True:
        data, stat = zk.get("/url_counter")
        current = int(data.decode())
        new_value = current + 1
        try:
            zk.set("/url_counter", str(new_value).encode(), version=stat.version)
            return new_value
        except BadVersionError:
            time.sleep(0.01)   # another instance won the race; retry


def get_stats() -> dict:
    """Get useful analytics from ZooKeeper (or local fallback) for the UI."""
    if _use_local_counter:
        return {
            "status": "local_fallback",
            "current_value": _local_counter
        }
    try:
        data, stat = zk.get("/url_counter")
        return {
            "status": "connected",
            "current_value": int(data.decode()),
            "version_updates": stat.version,
            "data_length": stat.dataLength
        }
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


def get_all_data() -> dict:
    """Dump the raw counter data from ZooKeeper for debugging/UI inspection."""
    if _use_local_counter:
        return {
            "status": "local_fallback",
            "data": {"/url_counter (local)": _local_counter}
        }
    try:
        data, _ = zk.get("/url_counter")
        return {
            "status": "success",
            "data": {"/url_counter": data.decode()}
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
