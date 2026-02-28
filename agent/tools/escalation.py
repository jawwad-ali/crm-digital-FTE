"""Escalation tool — escalate_to_human."""

from __future__ import annotations

import json
import logging

from agents import RunContextWrapper, function_tool

from agent.context import AgentContext

logger = logging.getLogger(__name__)


@function_tool
async def escalate_to_human(
    ctx: RunContextWrapper[AgentContext],
    ticket_id: str,
    reason: str,
) -> str:
    """Escalate a ticket to a human support agent.

    Use this ONLY when:
    - The customer requests a refund, legal action, or account deletion
    - Sentiment is below 0.3 (very negative)
    - search_knowledge_base returned ZERO articles (empty list)
    - The request is outside the agent's scope

    Do NOT escalate if search_knowledge_base returned any articles — use
    those articles to answer the customer instead.

    Args:
        ticket_id: UUID of the ticket to escalate.
        reason: Why escalation is needed (e.g. "refund request", "low sentiment").
    """
    pool = ctx.context.db_pool

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE tickets "
                "SET status = 'escalated', escalation_reason = $2, updated_at = now() "
                "WHERE id = $1 "
                "RETURNING id, status, escalation_reason, updated_at",
                ticket_id,
                reason,
            )

            if row is None:
                logger.warning("Escalation failed — ticket %s not found", ticket_id)
                return json.dumps({"error": f"Ticket {ticket_id} not found"})

        logger.info("Ticket %s escalated — reason: %s", ticket_id, reason)

        return json.dumps(
            {
                "ticket_id": str(row["id"]),
                "status": row["status"],
                "reason": row["escalation_reason"],
                "escalated_at": str(row["updated_at"]),
            },
            default=str,
        )
    except Exception:
        logger.exception("Failed to escalate ticket %s", ticket_id)
        return json.dumps({"error": "Escalation failed — please retry or contact support manually"})
