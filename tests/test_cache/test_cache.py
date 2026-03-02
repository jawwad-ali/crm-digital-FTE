"""Unit tests for agent/cache.py — key helpers, get/set, invalidation, graceful failure."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.cache import (
    TTL_KB_SEARCH,
    _PREFIX,
    get_cached,
    invalidate,
    invalidate_pattern,
    make_channel_config_key,
    make_customer_lookup_key,
    make_kb_cache_key,
    set_cached,
)


# ── Key generation ──────────────────────────────────────────────────────


class TestMakeKbCacheKey:
    def test_deterministic(self):
        """Same query always produces the same key."""
        k1 = make_kb_cache_key("How do I reset my password?")
        k2 = make_kb_cache_key("How do I reset my password?")
        assert k1 == k2

    def test_normalized(self):
        """Leading/trailing whitespace and case are ignored."""
        k1 = make_kb_cache_key("reset password")
        k2 = make_kb_cache_key("  RESET PASSWORD  ")
        assert k1 == k2

    def test_different_top_k(self):
        """Different top_k produces different key."""
        k1 = make_kb_cache_key("reset password", top_k=3)
        k2 = make_kb_cache_key("reset password", top_k=5)
        assert k1 != k2

    def test_prefix_format(self):
        """Key starts with 'kb:search:' and has 16-char hex digest."""
        key = make_kb_cache_key("test query")
        assert key.startswith("kb:search:")
        digest = key.split(":")[-1]
        assert len(digest) == 16
        int(digest, 16)  # must be valid hex

    def test_different_queries(self):
        """Different queries produce different keys."""
        k1 = make_kb_cache_key("reset password")
        k2 = make_kb_cache_key("upgrade subscription")
        assert k1 != k2


class TestMakeChannelConfigKey:
    def test_format(self):
        assert make_channel_config_key("gmail") == "channel_config:gmail"

    def test_different_channels(self):
        assert make_channel_config_key("gmail") != make_channel_config_key("whatsapp")


class TestMakeCustomerLookupKey:
    def test_format(self):
        key = make_customer_lookup_key("email", "ali@test.com")
        assert key == "customer:lookup:email:ali@test.com"

    def test_different_types(self):
        k1 = make_customer_lookup_key("email", "ali@test.com")
        k2 = make_customer_lookup_key("phone", "ali@test.com")
        assert k1 != k2


# ── get_cached / set_cached ─────────────────────────────────────────────


class TestGetSetCached:
    async def test_set_then_get_hit(self, mock_redis):
        """set_cached stores a value; get_cached retrieves it."""
        data = {"articles": [{"title": "Reset Password"}]}
        await set_cached(mock_redis, "test:key", data, ttl=60)
        result = await get_cached(mock_redis, "test:key")
        assert result == data

    async def test_get_miss(self, mock_redis):
        """get_cached returns None on cache miss."""
        result = await get_cached(mock_redis, "nonexistent:key")
        assert result is None

    async def test_get_none_client(self):
        """get_cached returns None when redis_client is None."""
        result = await get_cached(None, "any:key")
        assert result is None

    async def test_set_none_client(self):
        """set_cached no-ops when redis_client is None (no error)."""
        await set_cached(None, "any:key", {"data": 1}, ttl=60)
        # No exception = success

    async def test_prefix_applied(self, mock_redis):
        """Values are stored with the crm: prefix."""
        await set_cached(mock_redis, "my:key", {"v": 1}, ttl=60)
        raw = await mock_redis.get(f"{_PREFIX}my:key")
        assert raw is not None
        assert json.loads(raw) == {"v": 1}

    async def test_ttl_set(self, mock_redis):
        """TTL is applied to the stored key."""
        await set_cached(mock_redis, "ttl:key", {"v": 1}, ttl=3600)
        ttl = await mock_redis.ttl(f"{_PREFIX}ttl:key")
        assert ttl > 0
        assert ttl <= 3600

    async def test_list_value(self, mock_redis):
        """Lists are serialized and deserialized correctly."""
        data = [{"id": 1}, {"id": 2}]
        await set_cached(mock_redis, "list:key", data, ttl=60)
        result = await get_cached(mock_redis, "list:key")
        assert result == data


# ── invalidate ──────────────────────────────────────────────────────────


class TestInvalidate:
    async def test_single_key(self, mock_redis):
        """invalidate() deletes a single key."""
        await set_cached(mock_redis, "del:one", {"v": 1}, ttl=60)
        await invalidate(mock_redis, "del:one")
        assert await get_cached(mock_redis, "del:one") is None

    async def test_multiple_keys(self, mock_redis):
        """invalidate() deletes multiple keys in one call."""
        await set_cached(mock_redis, "del:a", {"v": 1}, ttl=60)
        await set_cached(mock_redis, "del:b", {"v": 2}, ttl=60)
        await invalidate(mock_redis, "del:a", "del:b")
        assert await get_cached(mock_redis, "del:a") is None
        assert await get_cached(mock_redis, "del:b") is None

    async def test_none_client(self):
        """invalidate() no-ops when redis_client is None."""
        await invalidate(None, "any:key")
        # No exception = success

    async def test_no_keys(self, mock_redis):
        """invalidate() no-ops when no keys provided."""
        await invalidate(mock_redis)
        # No exception = success


class TestInvalidatePattern:
    async def test_pattern_delete(self, mock_redis):
        """invalidate_pattern() deletes keys matching a glob."""
        await set_cached(mock_redis, "kb:search:aaa", {"v": 1}, ttl=60)
        await set_cached(mock_redis, "kb:search:bbb", {"v": 2}, ttl=60)
        await set_cached(mock_redis, "other:key", {"v": 3}, ttl=60)

        await invalidate_pattern(mock_redis, "kb:search:*")

        assert await get_cached(mock_redis, "kb:search:aaa") is None
        assert await get_cached(mock_redis, "kb:search:bbb") is None
        assert await get_cached(mock_redis, "other:key") == {"v": 3}

    async def test_none_client(self):
        """invalidate_pattern() no-ops when redis_client is None."""
        await invalidate_pattern(None, "kb:search:*")
        # No exception = success


# ── Graceful failure ────────────────────────────────────────────────────


class TestGracefulFailure:
    async def test_get_broken_client(self):
        """get_cached returns None when Redis raises."""
        broken = AsyncMock()
        broken.get = AsyncMock(side_effect=ConnectionError("Redis down"))
        result = await get_cached(broken, "any:key")
        assert result is None

    async def test_set_broken_client(self):
        """set_cached doesn't raise when Redis is broken."""
        broken = AsyncMock()
        broken.set = AsyncMock(side_effect=ConnectionError("Redis down"))
        await set_cached(broken, "any:key", {"v": 1}, ttl=60)
        # No exception = success

    async def test_invalidate_broken_client(self):
        """invalidate doesn't raise when Redis is broken."""
        broken = AsyncMock()
        broken.delete = AsyncMock(side_effect=ConnectionError("Redis down"))
        await invalidate(broken, "any:key")
        # No exception = success

    async def test_invalidate_pattern_broken_client(self):
        """invalidate_pattern doesn't raise when Redis is broken."""
        broken = AsyncMock()
        broken.scan = AsyncMock(side_effect=ConnectionError("Redis down"))
        await invalidate_pattern(broken, "kb:*")
        # No exception = success

    async def test_get_closed_client(self, mock_redis):
        """get_cached returns None after Redis client is closed."""
        await mock_redis.aclose()
        result = await get_cached(mock_redis, "any:key")
        assert result is None

    async def test_set_closed_client(self, mock_redis):
        """set_cached no-ops after Redis client is closed."""
        await mock_redis.aclose()
        await set_cached(mock_redis, "any:key", {"v": 1}, ttl=60)
        # No exception = success

    async def test_invalidate_closed_client(self, mock_redis):
        """invalidate no-ops after Redis client is closed."""
        await mock_redis.aclose()
        await invalidate(mock_redis, "any:key")
        # No exception = success
