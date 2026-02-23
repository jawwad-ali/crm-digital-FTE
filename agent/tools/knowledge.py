"""Knowledge base tool — search_knowledge_base."""

from __future__ import annotations

import json
import logging

from agents import RunContextWrapper, function_tool

from agent.context import AgentContext

logger = logging.getLogger(__name__)

_SIMILARITY_THRESHOLD = 0.4
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
    # Build vector literal inline (safe — values are floats from OpenAI, not user input)
    vec_literal = "'[" + ",".join(str(float(v)) for v in query_embedding) + "]'"
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT id, title, content, category, "
                f"  1 - (embedding <=> {vec_literal}::vector) AS similarity "
                f"FROM knowledge_base "
                f"WHERE embedding IS NOT NULL "
                f"  AND 1 - (embedding <=> {vec_literal}::vector) >= $1 "
                f"ORDER BY embedding <=> {vec_literal}::vector "
                f"LIMIT $2",
                _SIMILARITY_THRESHOLD,
                top_k,
            )
    except Exception:
        logger.exception("KB similarity query failed")
        return json.dumps({"error": "knowledge base search unavailable"})

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
