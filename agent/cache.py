"""Cache utility module — thin async wrapper around Redis with graceful fallback."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TTL constants (seconds)
# ---------------------------------------------------------------------------
TTL_KB_SEARCH: int = 3600  # 1 hour
TTL_CHANNEL_CONFIG: int = 86400  # 24 hours
TTL_CUSTOMER_LOOKUP: int = 3600  # 1 hour
TTL_JOB: int = 3600  # 1 hour — job results auto-expire
JOB_TIMEOUT: int = 300  # 5 minutes — processing jobs older than this are treated as failed

# ---------------------------------------------------------------------------
# Key prefix — all keys namespaced under "crm:"
# ---------------------------------------------------------------------------
_PREFIX: str = "crm:"


# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------
async def create_redis_client(*, url: str | None = None) -> redis.Redis | None:
    """Create an async Redis connection. Returns ``None`` if connection fails.

    Parameters
    ----------
    url:
        Redis connection URL.  Falls back to ``REDIS_URL`` env var,
        then ``redis://localhost:6379``.
    """
    url = url or os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        client = redis.from_url(url, decode_responses=True)
        await client.ping()
        logger.info("Redis connected — %s", url)
        return client
    except Exception:
        logger.warning("Redis unavailable — caching disabled")
        return None


# ---------------------------------------------------------------------------
# Get / Set
# ---------------------------------------------------------------------------
async def get_cached(
    redis_client: redis.Redis | None, key: str
) -> dict | list | None:
    """Fetch a cached value by key.

    Returns deserialized JSON on hit, ``None`` on miss or failure.
    """
    if redis_client is None:
        return None
    try:
        raw = await redis_client.get(f"{_PREFIX}{key}")
        if raw is None:
            logger.debug("Cache MISS — %s", key)
            return None
        logger.debug("Cache HIT — %s", key)
        return json.loads(raw)
    except Exception:
        logger.warning("Cache get failed — %s", key, exc_info=True)
        return None


async def set_cached(
    redis_client: redis.Redis | None,
    key: str,
    value: dict | list,
    ttl: int,
) -> None:
    """Store a value in cache with TTL.

    No-ops when ``redis_client`` is ``None``.
    """
    if redis_client is None:
        return
    try:
        await redis_client.set(
            f"{_PREFIX}{key}", json.dumps(value, default=str), ex=ttl
        )
        logger.debug("Cache SET — %s (ttl=%ds)", key, ttl)
    except Exception:
        logger.warning("Cache set failed — %s", key, exc_info=True)


# ---------------------------------------------------------------------------
# Job store
# ---------------------------------------------------------------------------
async def set_job(
    redis_client: redis.Redis | None,
    job_id: str,
    data: dict,
    ttl: int = TTL_JOB,
) -> None:
    """Store a background job's state in Redis.

    Auto-injects ``created_at`` ISO timestamp if not already present in *data*.
    No-ops when ``redis_client`` is ``None``.
    """
    if redis_client is None:
        return
    if "created_at" not in data:
        data["created_at"] = datetime.now(timezone.utc).isoformat()
    key = make_job_key(job_id)
    try:
        await redis_client.set(
            f"{_PREFIX}{key}", json.dumps(data, default=str), ex=ttl
        )
        logger.debug("Job SET — %s (ttl=%ds)", job_id, ttl)
    except Exception:
        logger.warning("Job set failed — %s", job_id, exc_info=True)


async def get_job(
    redis_client: redis.Redis | None, job_id: str
) -> dict | None:
    """Fetch a background job's state from Redis.

    Returns the deserialized job dict, or ``None`` if the key is missing or
    the client is ``None``.  If the job is still ``"processing"`` and
    ``created_at`` is older than :data:`JOB_TIMEOUT` seconds, returns a
    synthetic ``"failed"`` result with a timeout error message.
    """
    if redis_client is None:
        return None
    key = make_job_key(job_id)
    try:
        raw = await redis_client.get(f"{_PREFIX}{key}")
        if raw is None:
            return None
        data: dict = json.loads(raw)
        # Timeout detection — stale "processing" jobs become "failed"
        if data.get("status") == "processing" and "created_at" in data:
            created = datetime.fromisoformat(data["created_at"])
            age = (datetime.now(timezone.utc) - created).total_seconds()
            if age > JOB_TIMEOUT:
                logger.warning("Job %s timed out (%.0fs)", job_id, age)
                return {
                    "status": "failed",
                    "response": None,
                    "error": "Request timed out. Please try again.",
                    "created_at": data["created_at"],
                }
        return data
    except Exception:
        logger.warning("Job get failed — %s", job_id, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Invalidation
# ---------------------------------------------------------------------------
async def invalidate(redis_client: redis.Redis | None, *keys: str) -> None:
    """Delete one or more cache keys.

    Prepends the ``crm:`` prefix to each key.  No-ops when client is ``None``.
    """
    if redis_client is None or not keys:
        return
    try:
        prefixed = [f"{_PREFIX}{k}" for k in keys]
        await redis_client.delete(*prefixed)
        logger.debug("Cache DELETE — %s", ", ".join(keys))
    except Exception:
        logger.warning("Cache invalidate failed — %s", keys, exc_info=True)


async def invalidate_pattern(
    redis_client: redis.Redis | None, pattern: str
) -> None:
    """Delete all keys matching a glob pattern.

    Uses cursor-based ``SCAN`` (not ``KEYS``) for production safety.
    The *pattern* should NOT include the ``crm:`` prefix — it is added
    automatically.
    """
    if redis_client is None:
        return
    try:
        full_pattern = f"{_PREFIX}{pattern}"
        cursor = 0
        while True:
            cursor, batch = await redis_client.scan(
                cursor=cursor, match=full_pattern, count=100
            )
            if batch:
                await redis_client.delete(*batch)
            if cursor == 0:
                break
        logger.debug("Cache PATTERN DELETE — %s", pattern)
    except Exception:
        logger.warning(
            "Cache pattern invalidate failed — %s", pattern, exc_info=True
        )


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------
def make_kb_cache_key(query: str, top_k: int = 3) -> str:
    """Return ``kb:search:{sha256[:16]}`` from normalized query + top_k."""
    normalized = f"{query.strip().lower()}|{top_k}"
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"kb:search:{digest}"


def make_channel_config_key(channel: str) -> str:
    """Return ``channel_config:{channel}``."""
    return f"channel_config:{channel}"


def make_customer_lookup_key(identifier_type: str, identifier_value: str) -> str:
    """Return ``customer:lookup:{identifier_type}:{identifier_value}``."""
    return f"customer:lookup:{identifier_type}:{identifier_value}"


def make_job_key(job_id: str) -> str:
    """Return ``job:{job_id}``."""
    return f"job:{job_id}"
