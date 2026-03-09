"""Knowledge base tool — search_knowledge_base."""

from __future__ import annotations

import json
import logging

from agents import RunContextWrapper, function_tool

from agent.cache import TTL_KB_SEARCH, get_cached, make_kb_cache_key, set_cached
from agent.context import AgentContext

logger = logging.getLogger(__name__)

_SIMILARITY_THRESHOLD = 0.25
_EMBEDDING_MODEL = "text-embedding-3-small"


@function_tool
async def search_knowledge_base(
    ctx: RunContextWrapper[AgentContext],
    query: str,
    top_k: int = 3,
) -> str:
    """Find matching knowledge base articles for a customer question.

    Returns a list of verified, relevant articles. If the list is non-empty,
    you MUST use these articles to answer the customer. Only escalate if
    the returned list is empty.

    Args:
        query: A short search phrase derived from the customer's question.
        top_k: Maximum number of articles to return (default 3).
    """
    pool = ctx.context.db_pool
    openai = ctx.context.openai_client
    redis_client = ctx.context.redis_client

    # ── Cache check ─────────────────────────────────────────────────
    cache_key = make_kb_cache_key(query, top_k)
    cached = await get_cached(redis_client, cache_key)
    if cached is not None:
        logger.info("KB cache HIT for %r", query)
        return json.dumps(cached, default=str)

    # ── Cache MISS — full semantic search pipeline ──────────────────

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
            # Search ALL IVFFlat lists — default nprobe=1 misses most articles
            await conn.execute("SET LOCAL ivfflat.probes = 10")
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
        logger.exception("KB query failed")
        return json.dumps({"error": "knowledge base search unavailable"})

    articles = [
        {
            "title": r["title"],
            "content": r["content"],
            "category": r["category"],
        }
        for r in rows
    ]

    # Log similarity scores for debugging, but don't expose to the LLM
    for r in rows:
        logger.info(
            "KB match: %r — similarity=%.4f", r["title"], r["similarity"]
        )
    logger.info("KB search for %r returned %d articles", query, len(articles))

    if articles:
        result = {
            "status": "found",
            "message": f"Found {len(articles)} matching article(s). Use the content below to answer the customer.",
            "articles": articles,
        }
    else:
        result = {
            "status": "no_match",
            "message": "No articles found. You must escalate to a human agent.",
            "articles": [],
        }

    # ── Cache store (both "found" and "no_match") ──────────────────
    await set_cached(redis_client, cache_key, result, TTL_KB_SEARCH)

    return json.dumps(result, default=str)
