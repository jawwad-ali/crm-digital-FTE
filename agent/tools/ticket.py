"""Ticket lifecycle tools — create_ticket, update_ticket, get_ticket."""

from __future__ import annotations

import json
import logging

from agents import RunContextWrapper, function_tool

from agent.context import AgentContext

logger = logging.getLogger(__name__)

# Forward-only transitions (spec FR-005)
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "escalated"},
    "in_progress": {"resolved", "escalated"},
    "resolved": {"escalated"},
    "escalated": set(),
}


@function_tool
async def create_ticket(
    ctx: RunContextWrapper[AgentContext],
    customer_id: str,
    channel: str,
    category: str,
    priority: str,
) -> str:
    """Create a new support ticket and its 1:1 conversation in a single transaction.

    Args:
        customer_id: UUID of the customer.
        channel: "web", "gmail", or "whatsapp".
        category: e.g. "how-to", "bug-report", "feedback", "billing", "general".
        priority: "low", "medium", "high", or "urgent".
    """
    pool = ctx.context.db_pool

    async with pool.acquire() as conn:
        async with conn.transaction():
            ticket_id = await conn.fetchval(
                "INSERT INTO tickets (customer_id, channel, category, priority) "
                "VALUES ($1, $2, $3, $4) RETURNING id",
                customer_id,
                channel,
                category,
                priority,
            )

            conversation_id = await conn.fetchval(
                "INSERT INTO conversations (ticket_id, customer_id, channel) "
                "VALUES ($1, $2, $3) RETURNING id",
                ticket_id,
                customer_id,
                channel,
            )

    logger.info("Created ticket %s with conversation %s", ticket_id, conversation_id)

    return json.dumps(
        {
            "ticket_id": str(ticket_id),
            "conversation_id": str(conversation_id),
            "status": "open",
        },
        default=str,
    )


@function_tool
async def update_ticket(
    ctx: RunContextWrapper[AgentContext],
    ticket_id: str,
    status: str,
    resolution_notes: str | None = None,
    escalation_reason: str | None = None,
) -> str:
    """Update a ticket's status with forward-only transition validation.

    Args:
        ticket_id: UUID of the ticket to update.
        status: Target status — "in_progress", "resolved", or "escalated".
        resolution_notes: Notes when resolving a ticket.
        escalation_reason: Reason when escalating a ticket.
    """
    pool = ctx.context.db_pool

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT status FROM tickets WHERE id = $1",
            ticket_id,
        )
        if not row:
            return json.dumps({"error": "ticket not found"})

        old_status: str = row["status"]

        if status not in _VALID_TRANSITIONS.get(old_status, set()):
            return json.dumps(
                {
                    "error": "invalid status transition",
                    "detail": f"cannot move from '{old_status}' to '{status}'",
                }
            )

        updated_at = await conn.fetchval(
            "UPDATE tickets "
            "SET status = $1, resolution_notes = $2, escalation_reason = $3, updated_at = now() "
            "WHERE id = $4 RETURNING updated_at",
            status,
            resolution_notes,
            escalation_reason,
            ticket_id,
        )

    logger.info("Ticket %s: %s -> %s", ticket_id, old_status, status)

    return json.dumps(
        {
            "ticket_id": str(ticket_id),
            "old_status": old_status,
            "new_status": status,
            "updated_at": str(updated_at),
        },
        default=str,
    )


@function_tool
async def get_ticket(
    ctx: RunContextWrapper[AgentContext],
    ticket_id: str,
) -> str:
    """Fetch a ticket with its linked conversation and all messages.

    Args:
        ticket_id: UUID of the ticket.
    """
    pool = ctx.context.db_pool

    async with pool.acquire() as conn:
        ticket = await conn.fetchrow(
            "SELECT id, customer_id, channel, category, priority, status, "
            "escalation_reason, resolution_notes, parent_ticket_id, created_at, updated_at "
            "FROM tickets WHERE id = $1",
            ticket_id,
        )
        if not ticket:
            return json.dumps({"error": "ticket not found"})

        conversation = await conn.fetchrow(
            "SELECT id, ticket_id, customer_id, channel, created_at "
            "FROM conversations WHERE ticket_id = $1",
            ticket_id,
        )

        messages: list[dict] = []
        if conversation:
            rows = await conn.fetch(
                "SELECT id, direction, channel, content, sentiment, created_at "
                "FROM messages WHERE conversation_id = $1 ORDER BY created_at",
                conversation["id"],
            )
            messages = [dict(r) for r in rows]

        return json.dumps(
            {
                "ticket": dict(ticket),
                "conversation": dict(conversation) if conversation else None,
                "messages": messages,
            },
            default=str,
        )
