"""Tests for agent.tools.customer — find_or_create_customer, get_customer_history."""

from __future__ import annotations

import json
import uuid

import pytest

from agent.tools.customer import (
    _channel_from_type,
    find_or_create_customer,
    get_customer_history,
)


# ── _channel_from_type (pure function) ──────────────────────────────────


def test_channel_from_type_email():
    assert _channel_from_type("email") == "gmail"


def test_channel_from_type_phone():
    assert _channel_from_type("phone") == "whatsapp"


def test_channel_from_type_other():
    assert _channel_from_type("unknown") == "whatsapp"


# ── find_or_create_customer ─────────────────────────────────────────────


async def test_find_existing_customer(tool_ctx, mock_conn, sample_uuid):
    """Existing identifier → returns customer_id, is_new=False."""
    mock_conn.fetchrow.return_value = {"customer_id": sample_uuid}
    mock_conn.fetch.return_value = [
        {"identifier_type": "email", "identifier_value": "a@b.com", "channel": "gmail"}
    ]

    result = json.loads(
        await find_or_create_customer.on_invoke_tool(
            tool_ctx,
            json.dumps({"identifier_type": "email", "identifier_value": "a@b.com"}),
        )
    )

    assert result["customer_id"] == str(sample_uuid)
    assert result["is_new"] is False
    assert len(result["identifiers"]) == 1


async def test_create_new_customer(tool_ctx, mock_conn, sample_uuid):
    """No existing identifier, no link → creates brand-new customer."""
    mock_conn.fetchrow.return_value = None
    mock_conn.fetchval.return_value = sample_uuid
    mock_conn.fetch.return_value = [
        {"identifier_type": "email", "identifier_value": "new@b.com", "channel": "gmail"}
    ]

    result = json.loads(
        await find_or_create_customer.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "identifier_type": "email",
                "identifier_value": "new@b.com",
                "name": "Alice",
            }),
        )
    )

    assert result["customer_id"] == str(sample_uuid)
    assert result["is_new"] is True


async def test_create_new_customer_without_name(tool_ctx, mock_conn, sample_uuid):
    """New customer with no name provided."""
    mock_conn.fetchrow.return_value = None
    mock_conn.fetchval.return_value = sample_uuid
    mock_conn.fetch.return_value = [
        {"identifier_type": "email", "identifier_value": "anon@b.com", "channel": "gmail"}
    ]

    result = json.loads(
        await find_or_create_customer.on_invoke_tool(
            tool_ctx,
            json.dumps({"identifier_type": "email", "identifier_value": "anon@b.com"}),
        )
    )

    assert result["is_new"] is True


async def test_cross_channel_link_success(tool_ctx, mock_conn, sample_uuid):
    """Link new phone identifier to customer found by email."""
    mock_conn.fetchrow.side_effect = [
        None,                          # new identifier not found
        {"customer_id": sample_uuid},  # found via link_to_identifier_value
    ]
    mock_conn.fetch.return_value = [
        {"identifier_type": "email", "identifier_value": "a@b.com", "channel": "gmail"},
        {"identifier_type": "phone", "identifier_value": "+1234", "channel": "whatsapp"},
    ]

    result = json.loads(
        await find_or_create_customer.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "identifier_type": "phone",
                "identifier_value": "+1234",
                "link_to_identifier_value": "a@b.com",
            }),
        )
    )

    assert result["customer_id"] == str(sample_uuid)
    assert result["is_new"] is False
    assert len(result["identifiers"]) == 2


async def test_cross_channel_link_not_found(tool_ctx, mock_conn):
    """Link target doesn't exist → error."""
    mock_conn.fetchrow.side_effect = [None, None]

    result = json.loads(
        await find_or_create_customer.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "identifier_type": "phone",
                "identifier_value": "+999",
                "link_to_identifier_value": "nobody@example.com",
            }),
        )
    )

    assert result["error"] == "no customer found to link"


async def test_empty_identifier_value(tool_ctx):
    """Empty identifier → immediate error."""
    result = json.loads(
        await find_or_create_customer.on_invoke_tool(
            tool_ctx,
            json.dumps({"identifier_type": "email", "identifier_value": ""}),
        )
    )

    assert "error" in result
    assert "empty" in result["error"]


async def test_find_or_create_db_error(tool_ctx, mock_conn):
    """DB exception → graceful error JSON."""
    mock_conn.fetchrow.side_effect = RuntimeError("connection lost")

    result = json.loads(
        await find_or_create_customer.on_invoke_tool(
            tool_ctx,
            json.dumps({"identifier_type": "email", "identifier_value": "fail@b.com"}),
        )
    )

    assert "error" in result


# ── get_customer_history ────────────────────────────────────────────────


async def test_get_history_happy_path(tool_ctx, mock_conn, sample_uuid):
    """Customer exists → returns profile + tickets + conversations by channel."""
    conv_uuid = uuid.uuid4()
    mock_conn.fetchrow.return_value = {
        "id": sample_uuid,
        "name": "Alice",
        "created_at": "2024-01-01T00:00:00",
    }
    mock_conn.fetch.side_effect = [
        # identifiers
        [{"identifier_type": "email", "identifier_value": "a@b.com", "channel": "gmail"}],
        # conversations
        [
            {"id": sample_uuid, "channel": "web", "created_at": "2024-01-01", "message_count": 3},
            {"id": conv_uuid, "channel": "gmail", "created_at": "2024-01-02", "message_count": 1},
        ],
        # tickets
        [
            {
                "id": sample_uuid, "status": "resolved", "category": "how-to",
                "channel": "web", "priority": "low", "created_at": "2024-01-01",
            }
        ],
    ]

    result = json.loads(
        await get_customer_history.on_invoke_tool(
            tool_ctx,
            json.dumps({"customer_id": str(sample_uuid)}),
        )
    )

    assert result["customer"]["name"] == "Alice"
    assert len(result["identifiers"]) == 1
    assert len(result["conversations"]) == 2
    assert "web" in result["conversations_by_channel"]
    assert "gmail" in result["conversations_by_channel"]
    assert len(result["tickets"]) == 1


async def test_get_history_customer_not_found(tool_ctx, mock_conn, sample_uuid):
    """Customer doesn't exist → error."""
    mock_conn.fetchrow.return_value = None

    result = json.loads(
        await get_customer_history.on_invoke_tool(
            tool_ctx,
            json.dumps({"customer_id": str(sample_uuid)}),
        )
    )

    assert result["error"] == "customer not found"


async def test_get_history_db_error(tool_ctx, mock_conn, sample_uuid):
    """DB exception → graceful error."""
    mock_conn.fetchrow.side_effect = RuntimeError("timeout")

    result = json.loads(
        await get_customer_history.on_invoke_tool(
            tool_ctx,
            json.dumps({"customer_id": str(sample_uuid)}),
        )
    )

    assert "error" in result
