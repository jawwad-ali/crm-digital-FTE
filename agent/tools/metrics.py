"""Metrics tool — log_metric."""

from __future__ import annotations

import json
import logging

from agents import RunContextWrapper, function_tool

from agent.context import AgentContext

logger = logging.getLogger(__name__)


@function_tool
async def log_metric(
    ctx: RunContextWrapper[AgentContext],
    channel: str,
    response_time_ms: int,
    resolution_type: str,
    customer_id: str | None = None,
    ticket_id: str | None = None,
    sentiment: float | None = None,
    escalation_reason: str | None = None,
) -> str:
    """Log an interaction metric. Best-effort — never fails fatally.

    Call this after every interaction (resolved or escalated) to record
    response time, sentiment, channel, and resolution type.

    Args:
        channel: "web", "gmail", or "whatsapp".
        response_time_ms: Agent processing time in milliseconds.
        resolution_type: "auto_resolved", "escalated", or "error".
        customer_id: UUID of the customer (if identified).
        ticket_id: UUID of the ticket (if exists).
        sentiment: Final sentiment score (0.0–1.0).
        escalation_reason: Reason if escalated.
    """
    pool = ctx.context.db_pool

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO agent_metrics "
                "(customer_id, ticket_id, channel, response_time_ms, "
                " sentiment, resolution_type, escalation_reason) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7) "
                "RETURNING id, created_at",
                customer_id,
                ticket_id,
                channel,
                response_time_ms,
                sentiment,
                resolution_type,
                escalation_reason,
            )

        logger.info(
            "Metric %s logged — channel=%s resolution=%s",
            row["id"],
            channel,
            resolution_type,
        )

        return json.dumps(
            {
                "metric_id": str(row["id"]),
                "created_at": str(row["created_at"]),
            },
            default=str,
        )
    except Exception:
        logger.exception("Failed to log metric (best-effort, non-fatal)")
        return json.dumps({"metric_id": None, "error": "metric logging failed (non-fatal)"})
