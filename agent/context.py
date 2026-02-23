"""Shared agent context injected into every @function_tool via RunContextWrapper."""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg
from openai import AsyncOpenAI

from database.pool import create_pool


@dataclass
class AgentContext:
    """Holds the DB pool and OpenAI client shared across all agent tools.

    Passed to tools via ``RunContextWrapper[AgentContext]`` — the SDK
    injects it automatically; it is never sent to the LLM.
    """

    db_pool: asyncpg.Pool
    openai_client: AsyncOpenAI


async def build_context(
    *,
    dsn: str | None = None,
    openai_api_key: str | None = None,
) -> AgentContext:
    """Create an AgentContext from environment variables (or explicit args).

    Parameters
    ----------
    dsn:
        PostgreSQL DSN.  Falls back to ``DATABASE_URL`` env var.
    openai_api_key:
        OpenAI API key.  Falls back to ``OPENAI_API_KEY`` env var.
    """
    pool = await create_pool(dsn=dsn)
    client = AsyncOpenAI(api_key=openai_api_key)  # reads OPENAI_API_KEY if None
    return AgentContext(db_pool=pool, openai_client=client)
