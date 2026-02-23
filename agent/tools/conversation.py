"""Conversation tools — save_message, get_conversation_messages."""

from __future__ import annotations

import json
import logging

from agents import RunContextWrapper, function_tool

from agent.context import AgentContext

logger = logging.getLogger(__name__)


def _clamp_sentiment(value: float | None) -> float | None:
    """Clamp sentiment to [0.0, 1.0] per spec FR-019."""
    if value is None:
        return None
    return max(0.0, min(1.0, value))


@function_tool
async def save_message(
    ctx: RunContextWrapper[AgentContext],
    conversation_id: str,
    direction: str,
    channel: str,
    content: str,
    sentiment: float | None = None,
) -> str:
    """Save an inbound or outbound message to a conversation.

    Args:
        conversation_id: UUID of the conversation.
        direction: "inbound" or "outbound".
        channel: "web", "gmail", or "whatsapp".
        content: The message text.
        sentiment: Agent-estimated sentiment score (0.0–1.0). Clamped if out of range.
    """
    pool = ctx.context.db_pool
    sentiment = _clamp_sentiment(sentiment)

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO messages (conversation_id, direction, channel, content, sentiment) "
                "VALUES ($1, $2, $3, $4, $5) RETURNING id, created_at",
                conversation_id,
                direction,
                channel,
                content,
                sentiment,
            )

        logger.info("Saved %s message %s in conversation %s", direction, row["id"], conversation_id)

        return json.dumps(
            {
                "message_id": str(row["id"]),
                "created_at": str(row["created_at"]),
            },
            default=str,
        )
    except Exception:
        logger.exception("Failed to save message in conversation %s", conversation_id)
        return json.dumps({"error": "message save failed — please try again"})


@function_tool
async def get_conversation_messages(
    ctx: RunContextWrapper[AgentContext],
    conversation_id: str,
) -> str:
    """Fetch all messages in a conversation in chronological order.

    Args:
        conversation_id: UUID of the conversation.
    """
    pool = ctx.context.db_pool

    try:
        async with pool.acquire() as conn:
            # Verify conversation exists
            exists = await conn.fetchval(
                "SELECT 1 FROM conversations WHERE id = $1",
                conversation_id,
            )
            if not exists:
                return json.dumps({"error": "conversation not found"})

            rows = await conn.fetch(
                "SELECT id, direction, channel, content, sentiment, created_at "
                "FROM messages WHERE conversation_id = $1 ORDER BY created_at",
                conversation_id,
            )

        return json.dumps(
            {"messages": [dict(r) for r in rows]},
            default=str,
        )
    except Exception:
        logger.exception("Failed to fetch messages for conversation %s", conversation_id)
        return json.dumps({"error": "conversation messages unavailable — please try again"})
