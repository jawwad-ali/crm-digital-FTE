"""Shared pytest fixtures for the CRM Digital FTE test suite."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.context import AgentContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _ACM:
    """Minimal async context manager mock."""

    def __init__(self, return_value):
        self._rv = return_value

    async def __aenter__(self):
        return self._rv

    async def __aexit__(self, *args):
        return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_conn():
    """Mock asyncpg.Connection with common query methods."""
    conn = AsyncMock()
    # transaction() is a regular method returning an async context manager
    conn.transaction = MagicMock(return_value=_ACM(None))
    return conn


@pytest.fixture
def mock_pool(mock_conn):
    """Mock asyncpg.Pool whose acquire() yields mock_conn."""
    pool = MagicMock()
    pool.acquire.return_value = _ACM(mock_conn)
    return pool


@pytest.fixture
def mock_openai():
    """Mock AsyncOpenAI client with default embedding response."""
    client = MagicMock()
    embedding = MagicMock()
    embedding.embedding = [0.01] * 1536
    resp = MagicMock()
    resp.data = [embedding]
    client.embeddings = MagicMock()
    client.embeddings.create = AsyncMock(return_value=resp)
    return client


@pytest.fixture
def agent_context(mock_pool, mock_openai):
    """AgentContext wired to mock pool + mock OpenAI."""
    return AgentContext(db_pool=mock_pool, openai_client=mock_openai)


@pytest.fixture
def tool_ctx(agent_context):
    """RunContextWrapper suitable for on_invoke_tool calls."""
    from agents import RunContextWrapper

    return RunContextWrapper(context=agent_context)


@pytest.fixture
def sample_uuid():
    """A deterministic UUID for assertions."""
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


# ---------------------------------------------------------------------------
# Redis / cache fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def mock_redis():
    """In-memory Redis via fakeredis — async, decode_responses=True."""
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def agent_context_with_cache(mock_pool, mock_openai, mock_redis):
    """AgentContext wired to mock pool + mock OpenAI + fakeredis."""
    return AgentContext(
        db_pool=mock_pool, openai_client=mock_openai, redis_client=mock_redis
    )


@pytest.fixture
def tool_ctx_with_cache(agent_context_with_cache):
    """RunContextWrapper with cache-enabled AgentContext."""
    from agents import RunContextWrapper

    return RunContextWrapper(context=agent_context_with_cache)
