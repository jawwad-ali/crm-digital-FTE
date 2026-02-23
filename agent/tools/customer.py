"""Customer management tools — find_or_create_customer, get_customer_history."""

from __future__ import annotations

import json
import logging

from agents import RunContextWrapper, function_tool

from agent.context import AgentContext

logger = logging.getLogger(__name__)


@function_tool
async def find_or_create_customer(
    ctx: RunContextWrapper[AgentContext],
    identifier_type: str,
    identifier_value: str,
    name: str | None = None,
    link_to_identifier_value: str | None = None,
) -> str:
    """Look up a customer by email or phone. Creates one if not found.

    Args:
        identifier_type: "email" or "phone".
        identifier_value: The email address or phone number.
        name: Optional customer display name.
        link_to_identifier_value: If provided, link this new identifier to
            the customer found by this existing value (cross-channel linking).
    """
    pool = ctx.context.db_pool

    if not identifier_value:
        return json.dumps({"error": "identifier_value must not be empty"})

    try:
        async with pool.acquire() as conn:
            # 1. Check if this identifier already exists
            row = await conn.fetchrow(
                "SELECT customer_id FROM customer_identifiers "
                "WHERE identifier_type = $1 AND identifier_value = $2",
                identifier_type,
                identifier_value,
            )

            if row:
                customer_id = row["customer_id"]
                logger.info("Found existing customer %s via %s", customer_id, identifier_value)
            elif link_to_identifier_value:
                # 2. Cross-channel link: find customer by the existing identifier
                link_row = await conn.fetchrow(
                    "SELECT customer_id FROM customer_identifiers "
                    "WHERE identifier_value = $1",
                    link_to_identifier_value,
                )
                if not link_row:
                    return json.dumps({"error": "no customer found to link"})

                customer_id = link_row["customer_id"]
                # Attach new identifier to existing customer
                await conn.execute(
                    "INSERT INTO customer_identifiers "
                    "(customer_id, identifier_type, identifier_value, channel) "
                    "VALUES ($1, $2, $3, $4)",
                    customer_id,
                    identifier_type,
                    identifier_value,
                    _channel_from_type(identifier_type),
                )
                logger.info("Linked %s to existing customer %s", identifier_value, customer_id)
            else:
                # 3. Brand new customer
                customer_id = await conn.fetchval(
                    "INSERT INTO customers (name) VALUES ($1) RETURNING id",
                    name,
                )
                await conn.execute(
                    "INSERT INTO customer_identifiers "
                    "(customer_id, identifier_type, identifier_value, channel) "
                    "VALUES ($1, $2, $3, $4)",
                    customer_id,
                    identifier_type,
                    identifier_value,
                    _channel_from_type(identifier_type),
                )
                logger.info("Created new customer %s for %s", customer_id, identifier_value)

            # Fetch all identifiers for response
            idents = await conn.fetch(
                "SELECT identifier_type, identifier_value, channel "
                "FROM customer_identifiers WHERE customer_id = $1",
                customer_id,
            )

            return json.dumps(
                {
                    "customer_id": str(customer_id),
                    "is_new": row is None and link_to_identifier_value is None,
                    "identifiers": [dict(r) for r in idents],
                },
                default=str,
            )
    except Exception:
        logger.exception("Failed to find or create customer for %s", identifier_value)
        return json.dumps({"error": "customer lookup failed — please try again"})


@function_tool
async def get_customer_history(
    ctx: RunContextWrapper[AgentContext],
    customer_id: str,
) -> str:
    """Fetch a customer's profile, identifiers, recent conversations and tickets.

    Args:
        customer_id: UUID of the customer.
    """
    pool = ctx.context.db_pool

    try:
        async with pool.acquire() as conn:
            customer = await conn.fetchrow(
                "SELECT id, name, created_at FROM customers WHERE id = $1",
                customer_id,
            )
            if not customer:
                return json.dumps({"error": "customer not found"})

            identifiers = await conn.fetch(
                "SELECT identifier_type, identifier_value, channel "
                "FROM customer_identifiers WHERE customer_id = $1",
                customer_id,
            )

            conversations = await conn.fetch(
                "SELECT c.id, c.channel, c.created_at, "
                "  (SELECT count(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count "
                "FROM conversations c "
                "WHERE c.customer_id = $1 "
                "ORDER BY c.created_at DESC LIMIT 10",
                customer_id,
            )

            tickets = await conn.fetch(
                "SELECT id, status, category, channel, priority, created_at "
                "FROM tickets WHERE customer_id = $1 "
                "ORDER BY created_at DESC LIMIT 10",
                customer_id,
            )

            # Group conversations by channel for cross-channel visibility
            conversations_list = [
                {**dict(r), "id": str(r["id"]), "created_at": str(r["created_at"])}
                for r in conversations
            ]
            by_channel: dict[str, list] = {}
            for conv in conversations_list:
                by_channel.setdefault(conv["channel"], []).append(conv)

            return json.dumps(
                {
                    "customer": {
                        "id": str(customer["id"]),
                        "name": customer["name"],
                        "created_at": str(customer["created_at"]),
                    },
                    "identifiers": [dict(r) for r in identifiers],
                    "conversations": conversations_list,
                    "conversations_by_channel": by_channel,
                    "tickets": [
                        {**dict(r), "id": str(r["id"]), "created_at": str(r["created_at"])}
                        for r in tickets
                    ],
                },
                default=str,
            )
    except Exception:
        logger.exception("Failed to fetch customer history for %s", customer_id)
        return json.dumps({"error": "customer history unavailable — please try again"})


def _channel_from_type(identifier_type: str) -> str:
    """Infer default channel from identifier type."""
    return "gmail" if identifier_type == "email" else "whatsapp"
