"""Response delivery tool — send_response."""

from __future__ import annotations

import json
import logging

from agents import RunContextWrapper, function_tool

from agent.cache import (
    TTL_CHANNEL_CONFIG,
    get_cached,
    make_channel_config_key,
    set_cached,
)
from agent.context import AgentContext

logger = logging.getLogger(__name__)


@function_tool
async def send_response(
    ctx: RunContextWrapper[AgentContext],
    conversation_id: str,
    channel: str,
    content: str,
    ticket_id: str | None = None,
) -> str:
    """Send a response to the customer via the appropriate channel.

    Verifies a ticket exists (safety net), fetches channel config for
    formatting, truncates if needed, and saves the outbound message.

    Args:
        conversation_id: UUID of the conversation.
        channel: "web", "gmail", or "whatsapp".
        content: The response text to send.
        ticket_id: Optional ticket ID for safety check. Looked up from
            conversation if not provided.
    """
    pool = ctx.context.db_pool
    redis_client = ctx.context.redis_client

    try:
        async with pool.acquire() as conn:
            # 1. Safety net — verify ticket exists for this conversation
            if ticket_id is None:
                ticket_id = await conn.fetchval(
                    "SELECT t.id FROM tickets t "
                    "JOIN conversations c ON c.ticket_id = t.id "
                    "WHERE c.id = $1",
                    conversation_id,
                )

            if ticket_id is None:
                # Guardrail violation fallback: create a ticket so we never
                # respond without one. Fetch customer_id from conversation.
                cust_id = await conn.fetchval(
                    "SELECT customer_id FROM conversations WHERE id = $1",
                    conversation_id,
                )
                if cust_id:
                    ticket_id = await conn.fetchval(
                        "INSERT INTO tickets (customer_id, channel, category, priority) "
                        "VALUES ($1, $2, 'general', 'medium') RETURNING id",
                        cust_id,
                        channel,
                    )
                    logger.warning(
                        "Safety-net ticket %s created for conversation %s",
                        ticket_id,
                        conversation_id,
                    )

            # 2. Fetch channel config for formatting (cache-aside)
            cache_key = make_channel_config_key(channel)
            config = await get_cached(redis_client, cache_key)
            if config is None:
                row = await conn.fetchrow(
                    "SELECT max_length, response_style FROM channel_configs WHERE channel = $1",
                    channel,
                )
                if row:
                    config = dict(row)
                    await set_cached(redis_client, cache_key, config, TTL_CHANNEL_CONFIG)

            # 3. Truncate content to max_length
            if config and len(content) > config["max_length"]:
                content = content[: config["max_length"]]
                logger.info("Truncated response to %d chars for %s", config["max_length"], channel)

            # 4. Save outbound message
            row = await conn.fetchrow(
                "INSERT INTO messages (conversation_id, direction, channel, content) "
                "VALUES ($1, 'outbound', $2, $3) RETURNING id, created_at",
                conversation_id,
                channel,
                content,
            )

        # 5. Delivery — web is synchronous (FastAPI serves it); gmail/whatsapp deferred
        delivered = channel == "web"

        logger.info(
            "Response %s sent on %s (delivered=%s)", row["id"], channel, delivered,
        )

        return json.dumps(
            {
                "message_id": str(row["id"]),
                "channel": channel,
                "delivered": delivered,
            },
            default=str,
        )
    except Exception:
        logger.exception("Failed to send response in conversation %s", conversation_id)
        return json.dumps({"error": "response delivery failed — please try again"})
