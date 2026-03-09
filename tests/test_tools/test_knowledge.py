"""Tests for agent.tools.knowledge — search_knowledge_base."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock

import pytest

from agent.tools.knowledge import (
    _EMBEDDING_MODEL,
    _SIMILARITY_THRESHOLD,
    search_knowledge_base,
)


# ── Constants ───────────────────────────────────────────────────────────


def test_similarity_threshold():
    assert _SIMILARITY_THRESHOLD == 0.25


def test_embedding_model():
    assert _EMBEDDING_MODEL == "text-embedding-3-small"


# ── search_knowledge_base ───────────────────────────────────────────────


async def test_search_happy_path(tool_ctx, mock_conn, mock_openai, sample_uuid):
    """Returns matching articles when found."""
    mock_conn.fetch.return_value = [
        {
            "id": sample_uuid,
            "title": "How to Reset Your Password",
            "content": "Go to Settings > Security > Reset Password.",
            "category": "account-management",
            "similarity": 0.82,
        },
    ]

    result = json.loads(
        await search_knowledge_base.on_invoke_tool(
            tool_ctx,
            json.dumps({"query": "password reset"}),
        )
    )

    assert result["status"] == "found"
    assert len(result["articles"]) == 1
    assert result["articles"][0]["title"] == "How to Reset Your Password"
    # Similarity scores are NOT exposed to the LLM — only in debug logs
    assert "similarity" not in result["articles"][0]


async def test_search_no_results(tool_ctx, mock_conn, mock_openai):
    """No matching articles → no_match status with empty articles list."""
    mock_conn.fetch.return_value = []

    result = json.loads(
        await search_knowledge_base.on_invoke_tool(
            tool_ctx,
            json.dumps({"query": "quantum computing"}),
        )
    )

    assert result["status"] == "no_match"
    assert result["articles"] == []


async def test_search_custom_top_k(tool_ctx, mock_conn, mock_openai, sample_uuid):
    """Respects custom top_k parameter."""
    mock_conn.fetch.return_value = [
        {
            "id": sample_uuid, "title": "Article 1", "content": "...",
            "category": "general", "similarity": 0.9,
        },
    ]

    result = json.loads(
        await search_knowledge_base.on_invoke_tool(
            tool_ctx,
            json.dumps({"query": "test", "top_k": 5}),
        )
    )

    assert "articles" in result


async def test_search_embedding_error(tool_ctx, mock_openai):
    """OpenAI embedding failure → error JSON."""
    mock_openai.embeddings.create.side_effect = RuntimeError("API error")

    result = json.loads(
        await search_knowledge_base.on_invoke_tool(
            tool_ctx,
            json.dumps({"query": "test"}),
        )
    )

    assert "error" in result
    assert "unavailable" in result["error"]


async def test_search_db_error(tool_ctx, mock_conn, mock_openai):
    """DB query failure → error JSON."""
    mock_conn.fetch.side_effect = RuntimeError("query failed")

    result = json.loads(
        await search_knowledge_base.on_invoke_tool(
            tool_ctx,
            json.dumps({"query": "test"}),
        )
    )

    assert "error" in result


# ── Cache integration ────────────────────────────────────────────────


async def test_cache_hit_skips_openai_and_db(
    tool_ctx_with_cache, mock_conn, mock_openai, sample_uuid
):
    """Second identical query returns cached result — OpenAI and DB not called again."""
    # First call: cache MISS — full pipeline runs
    mock_conn.fetch.return_value = [
        {
            "id": sample_uuid,
            "title": "Reset Password",
            "content": "Go to Settings > Security.",
            "category": "account-management",
            "similarity": 0.85,
        },
    ]

    first = json.loads(
        await search_knowledge_base.on_invoke_tool(
            tool_ctx_with_cache,
            json.dumps({"query": "password reset"}),
        )
    )
    assert first["status"] == "found"
    assert len(first["articles"]) == 1

    # Record call counts after first invocation
    embedding_calls_after_first = mock_openai.embeddings.create.call_count
    db_calls_after_first = mock_conn.fetch.call_count

    # Second call: same query — cache HIT
    second = json.loads(
        await search_knowledge_base.on_invoke_tool(
            tool_ctx_with_cache,
            json.dumps({"query": "password reset"}),
        )
    )

    # Same result returned
    assert second == first

    # OpenAI and DB were NOT called again
    assert mock_openai.embeddings.create.call_count == embedding_calls_after_first
    assert mock_conn.fetch.call_count == db_calls_after_first


async def test_cache_miss_no_redis(tool_ctx, mock_conn, mock_openai, sample_uuid):
    """When redis_client is None, search still works (full pipeline, no cache)."""
    mock_conn.fetch.return_value = [
        {
            "id": sample_uuid,
            "title": "Upgrade Plan",
            "content": "Go to Billing > Upgrade.",
            "category": "billing",
            "similarity": 0.90,
        },
    ]

    result = json.loads(
        await search_knowledge_base.on_invoke_tool(
            tool_ctx,
            json.dumps({"query": "upgrade subscription"}),
        )
    )

    assert result["status"] == "found"
    assert len(result["articles"]) == 1
