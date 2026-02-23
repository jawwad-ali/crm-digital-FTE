"""Asyncpg connection pool with pgvector codec registration."""

from __future__ import annotations

import json
import os

import asyncpg


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Register pgvector codec on every new connection.

    The codec converts between Python ``list[float]`` and PostgreSQL
    ``vector`` text representation (e.g. ``"[0.1,0.2,0.3]"``).
    """
    await conn.set_type_codec(
        "vector",
        encoder=_encode_vector,
        decoder=_decode_vector,
        schema="public",
        format="text",
    )


def _encode_vector(value: list[float]) -> str:
    """list[float] → pgvector text literal."""
    return json.dumps(value)


def _decode_vector(value: str) -> list[float]:
    """pgvector text literal → list[float]."""
    return json.loads(value)


async def create_pool(
    *,
    dsn: str | None = None,
    min_size: int = 5,
    max_size: int = 20,
) -> asyncpg.Pool:
    """Create an asyncpg connection pool with pgvector support.

    Parameters
    ----------
    dsn:
        PostgreSQL connection string.  Falls back to the ``DATABASE_URL``
        environment variable when *None*.
    min_size:
        Minimum number of connections kept open in the pool.
    max_size:
        Maximum number of connections the pool will create.

    Returns
    -------
    asyncpg.Pool
        A ready-to-use connection pool.
    """
    if dsn is None:
        dsn = os.environ["DATABASE_URL"]

    return await asyncpg.create_pool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        init=_init_connection,
    )
