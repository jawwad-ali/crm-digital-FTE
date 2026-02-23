"""Tests for agent.tools.escalation — escalate_to_human."""

from __future__ import annotations

import json
import uuid

import pytest

from agent.tools.escalation import escalate_to_human


async def test_escalate_happy_path(tool_ctx, mock_conn, sample_uuid):
    """Ticket escalated successfully."""
    mock_conn.fetchrow.return_value = {
        "id": sample_uuid,
        "status": "escalated",
        "escalation_reason": "refund request",
        "updated_at": "2024-01-01T12:00:00",
    }

    result = json.loads(
        await escalate_to_human.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "ticket_id": str(sample_uuid),
                "reason": "refund request",
            }),
        )
    )

    assert result["ticket_id"] == str(sample_uuid)
    assert result["status"] == "escalated"
    assert result["reason"] == "refund request"
    assert "escalated_at" in result


async def test_escalate_ticket_not_found(tool_ctx, mock_conn, sample_uuid):
    """Ticket doesn't exist → UPDATE returns no row."""
    mock_conn.fetchrow.return_value = None

    result = json.loads(
        await escalate_to_human.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "ticket_id": str(sample_uuid),
                "reason": "low sentiment",
            }),
        )
    )

    assert "error" in result
    assert str(sample_uuid) in result["error"]


async def test_escalate_db_error(tool_ctx, mock_conn, sample_uuid):
    """DB exception → graceful error."""
    mock_conn.fetchrow.side_effect = RuntimeError("connection lost")

    result = json.loads(
        await escalate_to_human.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "ticket_id": str(sample_uuid),
                "reason": "unrecoverable error",
            }),
        )
    )

    assert "error" in result
