"""Tests for agent.tools.ticket — create_ticket, update_ticket, get_ticket."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import pytest

from agent.tools.ticket import (
    _VALID_TRANSITIONS,
    create_ticket,
    get_ticket,
    update_ticket,
)


# ── _VALID_TRANSITIONS constant ─────────────────────────────────────────


def test_valid_transitions_structure():
    assert _VALID_TRANSITIONS["open"] == {"in_progress", "escalated"}
    assert _VALID_TRANSITIONS["in_progress"] == {"resolved", "escalated"}
    assert _VALID_TRANSITIONS["resolved"] == {"escalated"}
    assert _VALID_TRANSITIONS["escalated"] == set()


# ── create_ticket ───────────────────────────────────────────────────────


async def test_create_ticket_happy_path(tool_ctx, mock_conn, sample_uuid):
    """Creates ticket + conversation in a single transaction."""
    conv_uuid = uuid.uuid4()
    # 1st fetchval: customer existence check, 2nd: ticket INSERT, 3rd: conversation INSERT
    mock_conn.fetchval.side_effect = [True, sample_uuid, conv_uuid]

    result = json.loads(
        await create_ticket.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "customer_id": str(sample_uuid),
                "channel": "web",
                "category": "how-to",
                "priority": "low",
            }),
        )
    )

    assert result["ticket_id"] == str(sample_uuid)
    assert result["conversation_id"] == str(conv_uuid)
    assert result["status"] == "open"


async def test_create_ticket_customer_not_found(tool_ctx, mock_conn, sample_uuid):
    """Fake customer_id → clear error telling LLM to use find_or_create_customer."""
    mock_conn.fetchval.return_value = None  # customer doesn't exist

    result = json.loads(
        await create_ticket.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "customer_id": str(sample_uuid),
                "channel": "web",
                "category": "how-to",
                "priority": "low",
            }),
        )
    )

    assert "error" in result
    assert "find_or_create_customer" in result["error"]


async def test_create_ticket_db_error(tool_ctx, mock_conn, sample_uuid):
    """DB exception → graceful error."""
    mock_conn.fetchval.side_effect = RuntimeError("insert failed")

    result = json.loads(
        await create_ticket.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "customer_id": str(sample_uuid),
                "channel": "web",
                "category": "bug-report",
                "priority": "high",
            }),
        )
    )

    assert "error" in result


# ── update_ticket — valid transitions (parametrized) ────────────────────


@pytest.mark.parametrize("old_status,new_status", [
    ("open", "in_progress"),
    ("open", "escalated"),
    ("in_progress", "resolved"),
    ("in_progress", "escalated"),
    ("resolved", "escalated"),
])
async def test_update_ticket_valid_transition(
    tool_ctx, mock_conn, sample_uuid, old_status, new_status,
):
    mock_conn.fetchrow.return_value = {"status": old_status}
    mock_conn.fetchval.return_value = datetime(2024, 1, 1)

    result = json.loads(
        await update_ticket.on_invoke_tool(
            tool_ctx,
            json.dumps({"ticket_id": str(sample_uuid), "status": new_status}),
        )
    )

    assert result["old_status"] == old_status
    assert result["new_status"] == new_status
    assert "updated_at" in result


# ── update_ticket — invalid transitions (parametrized) ──────────────────


@pytest.mark.parametrize("old_status,new_status", [
    ("open", "resolved"),
    ("in_progress", "open"),
    ("resolved", "open"),
    ("resolved", "in_progress"),
    ("escalated", "open"),
    ("escalated", "in_progress"),
    ("escalated", "resolved"),
])
async def test_update_ticket_invalid_transition(
    tool_ctx, mock_conn, sample_uuid, old_status, new_status,
):
    mock_conn.fetchrow.return_value = {"status": old_status}

    result = json.loads(
        await update_ticket.on_invoke_tool(
            tool_ctx,
            json.dumps({"ticket_id": str(sample_uuid), "status": new_status}),
        )
    )

    assert result["error"] == "invalid status transition"
    assert old_status in result["detail"]
    assert new_status in result["detail"]


async def test_update_ticket_with_resolution_notes(tool_ctx, mock_conn, sample_uuid):
    """Resolving ticket includes resolution_notes."""
    mock_conn.fetchrow.return_value = {"status": "in_progress"}
    mock_conn.fetchval.return_value = datetime(2024, 1, 1)

    result = json.loads(
        await update_ticket.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "ticket_id": str(sample_uuid),
                "status": "resolved",
                "resolution_notes": "Answered via KB article",
            }),
        )
    )

    assert result["new_status"] == "resolved"


async def test_update_ticket_not_found(tool_ctx, mock_conn, sample_uuid):
    """Ticket ID doesn't exist → error."""
    mock_conn.fetchrow.return_value = None

    result = json.loads(
        await update_ticket.on_invoke_tool(
            tool_ctx,
            json.dumps({"ticket_id": str(sample_uuid), "status": "in_progress"}),
        )
    )

    assert result["error"] == "ticket not found"


async def test_update_ticket_db_error(tool_ctx, mock_conn, sample_uuid):
    """DB exception → graceful error."""
    mock_conn.fetchrow.side_effect = RuntimeError("timeout")

    result = json.loads(
        await update_ticket.on_invoke_tool(
            tool_ctx,
            json.dumps({"ticket_id": str(sample_uuid), "status": "in_progress"}),
        )
    )

    assert "error" in result


# ── get_ticket ──────────────────────────────────────────────────────────


async def test_get_ticket_with_conversation_and_messages(
    tool_ctx, mock_conn, sample_uuid,
):
    """Full ticket with conversation + messages."""
    conv_uuid = uuid.uuid4()
    msg_uuid = uuid.uuid4()

    mock_conn.fetchrow.side_effect = [
        # ticket
        {
            "id": sample_uuid, "customer_id": uuid.uuid4(),
            "channel": "web", "category": "how-to", "priority": "low",
            "status": "resolved", "escalation_reason": None,
            "resolution_notes": "Done", "parent_ticket_id": None,
            "created_at": "2024-01-01", "updated_at": "2024-01-02",
        },
        # conversation
        {
            "id": conv_uuid, "ticket_id": sample_uuid,
            "customer_id": uuid.uuid4(), "channel": "web",
            "created_at": "2024-01-01",
        },
    ]
    mock_conn.fetch.return_value = [
        {
            "id": msg_uuid, "direction": "inbound", "channel": "web",
            "content": "Help!", "sentiment": 0.5, "created_at": "2024-01-01",
        },
    ]

    result = json.loads(
        await get_ticket.on_invoke_tool(
            tool_ctx,
            json.dumps({"ticket_id": str(sample_uuid)}),
        )
    )

    assert result["ticket"]["status"] == "resolved"
    assert result["conversation"] is not None
    assert len(result["messages"]) == 1


async def test_get_ticket_without_conversation(tool_ctx, mock_conn, sample_uuid):
    """Ticket exists but has no conversation."""
    mock_conn.fetchrow.side_effect = [
        {
            "id": sample_uuid, "customer_id": uuid.uuid4(),
            "channel": "web", "category": "general", "priority": "medium",
            "status": "open", "escalation_reason": None,
            "resolution_notes": None, "parent_ticket_id": None,
            "created_at": "2024-01-01", "updated_at": "2024-01-01",
        },
        None,  # no conversation
    ]

    result = json.loads(
        await get_ticket.on_invoke_tool(
            tool_ctx,
            json.dumps({"ticket_id": str(sample_uuid)}),
        )
    )

    assert result["ticket"] is not None
    assert result["conversation"] is None
    assert result["messages"] == []


async def test_get_ticket_not_found(tool_ctx, mock_conn, sample_uuid):
    """Ticket doesn't exist → error."""
    mock_conn.fetchrow.return_value = None

    result = json.loads(
        await get_ticket.on_invoke_tool(
            tool_ctx,
            json.dumps({"ticket_id": str(sample_uuid)}),
        )
    )

    assert result["error"] == "ticket not found"


async def test_get_ticket_db_error(tool_ctx, mock_conn, sample_uuid):
    """DB exception → graceful error."""
    mock_conn.fetchrow.side_effect = RuntimeError("connection lost")

    result = json.loads(
        await get_ticket.on_invoke_tool(
            tool_ctx,
            json.dumps({"ticket_id": str(sample_uuid)}),
        )
    )

    assert "error" in result
