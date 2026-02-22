"""Knowledge base tool — search_knowledge_base."""

from __future__ import annotations

import json
import logging

from agents import RunContextWrapper, function_tool

from agent.context import AgentContext

logger = logging.getLogger(__name__)

_SIMILARITY_THRESHOLD = 0.7
_EMBEDDING_MODEL = "text-embedding-3-small"


@function_tool
async def search_knowledge_base(
    ctx: RunContextWrapper[AgentContext],
    query: str,
    top_k: int = 3,
) -> str:
    """Search the knowledge base using semantic similarity.

    Args:
        query: The user's question (will be embedded for cosine similarity search).
        top_k: Maximum number of results to return (default 3).
    """
    pool = ctx.context.db_pool
    openai = ctx.context.openai_client

    # 1. Generate embedding for the query
    try:
        resp = await openai.embeddings.create(input=query, model=_EMBEDDING_MODEL)
        query_embedding = resp.data[0].embedding
    except Exception:
        logger.exception("Failed to generate query embedding")
        return json.dumps({"error": "knowledge base search unavailable"})

    # 2. Cosine similarity search — only results >= threshold
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, title, content, category, "
            "  1 - (embedding <=> $1) AS similarity "
            "FROM knowledge_base "
            "WHERE embedding IS NOT NULL "
            "  AND 1 - (embedding <=> $1) >= $2 "
            "ORDER BY embedding <=> $1 "
            "LIMIT $3",
            query_embedding,
            _SIMILARITY_THRESHOLD,
            top_k,
        )

    results = [
        {
            "id": str(r["id"]),
            "title": r["title"],
            "content": r["content"],
            "category": r["category"],
            "similarity": round(r["similarity"], 4),
        }
        for r in rows
    ]

    logger.info("KB search for %r returned %d results", query, len(results))

    return json.dumps({"results": results}, default=str)
