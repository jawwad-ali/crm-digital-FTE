"""Tests for agent.tools.conversation — save_message, get_conversation_messages."""

from __future__ import annotations

import json
import uuid

import pytest

from agent.tools.conversation import (
    _clamp_sentiment,
    get_conversation_messages,
    save_message,
)


# ── _clamp_sentiment (pure function) ────────────────────────────────────


def test_clamp_sentiment_none():
    assert _clamp_sentiment(None) is None


def test_clamp_sentiment_in_range():
    assert _clamp_sentiment(0.5) == 0.5


def test_clamp_sentiment_below_zero():
    assert _clamp_sentiment(-0.3) == 0.0


def test_clamp_sentiment_above_one():
    assert _clamp_sentiment(1.5) == 1.0


def test_clamp_sentiment_boundary_low():
    assert _clamp_sentiment(0.0) == 0.0


def test_clamp_sentiment_boundary_high():
    assert _clamp_sentiment(1.0) == 1.0


# ── save_message ────────────────────────────────────────────────────────


async def test_save_message_happy_path(tool_ctx, mock_conn, sample_uuid):
    """Message saved with sentiment."""
    mock_conn.fetchrow.return_value = {
        "id": sample_uuid,
        "created_at": "2024-01-01T00:00:00",
    }

    result = json.loads(
        await save_message.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "conversation_id": str(uuid.uuid4()),
                "direction": "inbound",
                "channel": "web",
                "content": "How do I reset my password?",
                "sentiment": 0.7,
            }),
        )
    )

    assert result["message_id"] == str(sample_uuid)
    assert "created_at" in result


async def test_save_message_without_sentiment(tool_ctx, mock_conn, sample_uuid):
    """Message saved with None sentiment (optional param omitted)."""
    mock_conn.fetchrow.return_value = {
        "id": sample_uuid,
        "created_at": "2024-01-01T00:00:00",
    }

    result = json.loads(
        await save_message.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "conversation_id": str(uuid.uuid4()),
                "direction": "outbound",
                "channel": "gmail",
                "content": "Here is how to reset your password.",
            }),
        )
    )

    assert result["message_id"] == str(sample_uuid)


async def test_save_message_clamps_high_sentiment(tool_ctx, mock_conn, sample_uuid):
    """Sentiment > 1.0 is clamped to 1.0."""
    mock_conn.fetchrow.return_value = {
        "id": sample_uuid,
        "created_at": "2024-01-01T00:00:00",
    }

    await save_message.on_invoke_tool(
        tool_ctx,
        json.dumps({
            "conversation_id": str(uuid.uuid4()),
            "direction": "inbound",
            "channel": "web",
            "content": "Great!",
            "sentiment": 1.5,
        }),
    )

    # Verify the clamped value was passed to the DB
    call_args = mock_conn.fetchrow.call_args
    assert call_args[0][5] == 1.0  # 6th positional arg = sentiment


async def test_save_message_db_error(tool_ctx, mock_conn):
    """DB exception → graceful error."""
    mock_conn.fetchrow.side_effect = RuntimeError("insert failed")

    result = json.loads(
        await save_message.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "conversation_id": str(uuid.uuid4()),
                "direction": "inbound",
                "channel": "web",
                "content": "test",
            }),
        )
    )

    assert "error" in result


# ── get_conversation_messages ───────────────────────────────────────────


async def test_get_messages_happy_path(tool_ctx, mock_conn, sample_uuid):
    """Returns messages in chronological order."""
    mock_conn.fetchval.return_value = 1  # conversation exists
    mock_conn.fetch.return_value = [
        {
            "id": sample_uuid, "direction": "inbound", "channel": "web",
            "content": "Hi", "sentiment": 0.8, "created_at": "2024-01-01",
        },
        {
            "id": uuid.uuid4(), "direction": "outbound", "channel": "web",
            "content": "Hello!", "sentiment": None, "created_at": "2024-01-01",
        },
    ]

    result = json.loads(
        await get_conversation_messages.on_invoke_tool(
            tool_ctx,
            json.dumps({"conversation_id": str(uuid.uuid4())}),
        )
    )

    assert len(result["messages"]) == 2


async def test_get_messages_conversation_not_found(tool_ctx, mock_conn):
    """Conversation doesn't exist → error."""
    mock_conn.fetchval.return_value = None

    result = json.loads(
        await get_conversation_messages.on_invoke_tool(
            tool_ctx,
            json.dumps({"conversation_id": str(uuid.uuid4())}),
        )
    )

    assert result["error"] == "conversation not found"


async def test_get_messages_db_error(tool_ctx, mock_conn):
    """DB exception → graceful error."""
    mock_conn.fetchval.side_effect = RuntimeError("timeout")

    result = json.loads(
        await get_conversation_messages.on_invoke_tool(
            tool_ctx,
            json.dumps({"conversation_id": str(uuid.uuid4())}),
        )
    )

    assert "error" in result
