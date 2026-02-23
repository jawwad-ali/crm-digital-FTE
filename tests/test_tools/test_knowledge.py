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
    assert _SIMILARITY_THRESHOLD == 0.4


def test_embedding_model():
    assert _EMBEDDING_MODEL == "text-embedding-3-small"


# ── search_knowledge_base ───────────────────────────────────────────────


async def test_search_happy_path(tool_ctx, mock_conn, mock_openai, sample_uuid):
    """Returns matching articles with similarity scores."""
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

    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "How to Reset Your Password"
    assert result["results"][0]["similarity"] == 0.82


async def test_search_no_results(tool_ctx, mock_conn, mock_openai):
    """No matching articles → empty results list."""
    mock_conn.fetch.return_value = []

    result = json.loads(
        await search_knowledge_base.on_invoke_tool(
            tool_ctx,
            json.dumps({"query": "quantum computing"}),
        )
    )

    assert result["results"] == []


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

    assert "results" in result


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
