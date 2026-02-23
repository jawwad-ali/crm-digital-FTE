"""Tests for agent.tools.metrics — log_metric."""

from __future__ import annotations

import json
import uuid

import pytest

from agent.tools.metrics import log_metric


async def test_log_metric_happy_path(tool_ctx, mock_conn, sample_uuid):
    """Metric logged successfully with required fields."""
    mock_conn.fetchrow.return_value = {
        "id": sample_uuid,
        "created_at": "2024-01-01T00:00:00",
    }

    result = json.loads(
        await log_metric.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "channel": "web",
                "response_time_ms": 1500,
                "resolution_type": "auto_resolved",
            }),
        )
    )

    assert result["metric_id"] == str(sample_uuid)
    assert "created_at" in result


async def test_log_metric_with_all_optional_params(tool_ctx, mock_conn, sample_uuid):
    """Metric logged with all optional parameters."""
    mock_conn.fetchrow.return_value = {
        "id": sample_uuid,
        "created_at": "2024-01-01T00:00:00",
    }

    result = json.loads(
        await log_metric.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "channel": "gmail",
                "response_time_ms": 2000,
                "resolution_type": "escalated",
                "customer_id": str(uuid.uuid4()),
                "ticket_id": str(uuid.uuid4()),
                "sentiment": 0.2,
                "escalation_reason": "refund request",
            }),
        )
    )

    assert result["metric_id"] == str(sample_uuid)


async def test_log_metric_db_error_nonfatal(tool_ctx, mock_conn):
    """DB exception → non-fatal: returns metric_id=None + error message."""
    mock_conn.fetchrow.side_effect = RuntimeError("insert failed")

    result = json.loads(
        await log_metric.on_invoke_tool(
            tool_ctx,
            json.dumps({
                "channel": "whatsapp",
                "response_time_ms": 500,
                "resolution_type": "error",
            }),
        )
    )

    assert result["metric_id"] is None
    assert "error" in result
    assert "non-fatal" in result["error"]
