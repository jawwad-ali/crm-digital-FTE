"""Shared agent context injected into every @function_tool via RunContextWrapper."""

from __future__ import annotations

from dataclasses import dataclass, field

import asyncpg
import redis.asyncio as redis
from openai import AsyncOpenAI

from agent.cache import create_redis_client
from database.pool import create_pool


@dataclass
class AgentContext:
    """Holds the DB pool, OpenAI client, and Redis client shared across all agent tools.

    Passed to tools via ``RunContextWrapper[AgentContext]`` — the SDK
    injects it automatically; it is never sent to the LLM.
    """

    db_pool: asyncpg.Pool
    openai_client: AsyncOpenAI
    redis_client: redis.Redis | None = field(default=None)


async def build_context(
    *,
    dsn: str | None = None,
    openai_api_key: str | None = None,
    redis_url: str | None = None,
) -> AgentContext:
    """Create an AgentContext from environment variables (or explicit args).

    Parameters
    ----------
    dsn:
        PostgreSQL DSN.  Falls back to ``DATABASE_URL`` env var.
    openai_api_key:
        OpenAI API key.  Falls back to ``OPENAI_API_KEY`` env var.
    redis_url:
        Redis connection URL.  Falls back to ``REDIS_URL`` env var,
        then ``redis://localhost:6379``.
    """
    pool = await create_pool(dsn=dsn)
    client = AsyncOpenAI(api_key=openai_api_key)  # reads OPENAI_API_KEY if None
    rclient = await create_redis_client(url=redis_url)
    return AgentContext(db_pool=pool, openai_client=client, redis_client=rclient)
