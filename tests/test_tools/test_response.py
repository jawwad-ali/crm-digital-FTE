"""Tests for agent.tools.response — send_response."""

from __future__ import annotations

import json
import uuid

import pytest

from agent.tools.response import send_response


# ── send_response ───────────────────────────────────────────────────────


async def test_send_with_explicit_ticket_id(tool_ctx, mock_conn, sample_uuid):
    """Explicit ticket_id skips lookup; channel config + message saved."""
    mock_conn.fetchrow.side_effect = [
        {"max_length": 5000, "response_style": "formal"},  # channel config
        {"id": sample_uuid, "created_at": "2024-01-01"},   # saved message
    ]

    result = json.loads(
        await send_response.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "conversation_id": str(uuid.uuid4()),
                "channel": "web",
                "content": "Here is your answer.",
                "ticket_id": str(sample_uuid),
            }),
        )
    )

    assert result["message_id"] == str(sample_uuid)
    assert result["channel"] == "web"
    assert result["delivered"] is True


async def test_send_lookup_ticket_from_conversation(tool_ctx, mock_conn, sample_uuid):
    """ticket_id=None → looks up from conversation join."""
    ticket_uuid = uuid.uuid4()
    mock_conn.fetchval.return_value = ticket_uuid  # ticket lookup
    mock_conn.fetchrow.side_effect = [
        None,                                                # no channel config
        {"id": sample_uuid, "created_at": "2024-01-01"},    # saved message
    ]

    result = json.loads(
        await send_response.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "conversation_id": str(uuid.uuid4()),
                "channel": "gmail",
                "content": "Your issue is resolved.",
            }),
        )
    )

    assert result["message_id"] == str(sample_uuid)
    assert result["delivered"] is False  # gmail is not synchronous


async def test_send_safety_net_ticket_creation(tool_ctx, mock_conn, sample_uuid):
    """No ticket found anywhere → creates a safety-net ticket."""
    cust_uuid = uuid.uuid4()
    new_ticket_uuid = uuid.uuid4()

    mock_conn.fetchval.side_effect = [
        None,             # no ticket from conversation
        cust_uuid,        # customer_id lookup
        new_ticket_uuid,  # new safety-net ticket
    ]
    mock_conn.fetchrow.side_effect = [
        None,                                                # no channel config
        {"id": sample_uuid, "created_at": "2024-01-01"},    # saved message
    ]

    result = json.loads(
        await send_response.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "conversation_id": str(uuid.uuid4()),
                "channel": "whatsapp",
                "content": "We are looking into it.",
            }),
        )
    )

    assert result["message_id"] == str(sample_uuid)
    assert result["delivered"] is False


async def test_send_content_truncation(tool_ctx, mock_conn, sample_uuid):
    """Content exceeding max_length is truncated."""
    mock_conn.fetchrow.side_effect = [
        {"max_length": 10, "response_style": "concise"},   # channel config (max 10 chars)
        {"id": sample_uuid, "created_at": "2024-01-01"},   # saved message
    ]

    await send_response.on_invoke_tool(
        tool_ctx,
        json.dumps({
            "conversation_id": str(uuid.uuid4()),
            "channel": "whatsapp",
            "content": "A" * 100,
            "ticket_id": str(sample_uuid),
        }),
    )

    # The truncated content (10 chars) should be passed to INSERT message
    save_call = mock_conn.fetchrow.call_args_list[-1]
    saved_content = save_call[0][3]  # 4th positional arg = content
    assert len(saved_content) == 10


async def test_send_web_delivered_true(tool_ctx, mock_conn, sample_uuid):
    """Web channel → delivered=True."""
    mock_conn.fetchrow.side_effect = [
        None,
        {"id": sample_uuid, "created_at": "2024-01-01"},
    ]

    result = json.loads(
        await send_response.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "conversation_id": str(uuid.uuid4()),
                "channel": "web",
                "content": "Hello",
                "ticket_id": str(sample_uuid),
            }),
        )
    )

    assert result["delivered"] is True


async def test_send_gmail_delivered_false(tool_ctx, mock_conn, sample_uuid):
    """Gmail channel → delivered=False (async delivery)."""
    mock_conn.fetchrow.side_effect = [
        None,
        {"id": sample_uuid, "created_at": "2024-01-01"},
    ]

    result = json.loads(
        await send_response.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "conversation_id": str(uuid.uuid4()),
                "channel": "gmail",
                "content": "Hello",
                "ticket_id": str(sample_uuid),
            }),
        )
    )

    assert result["delivered"] is False


async def test_send_db_error(tool_ctx, mock_conn):
    """DB exception → graceful error."""
    mock_conn.fetchrow.side_effect = RuntimeError("connection lost")

    result = json.loads(
        await send_response.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "conversation_id": str(uuid.uuid4()),
                "channel": "web",
                "content": "test",
                "ticket_id": str(uuid.uuid4()),
            }),
        )
    )

    assert "error" in result
