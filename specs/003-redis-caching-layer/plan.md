# Implementation Plan: Redis Caching Layer

**Branch**: `003-redis-caching-layer` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-redis-caching-layer/spec.md`

## Summary

Add a Redis caching layer that eliminates redundant OpenAI embedding API calls and database queries for three hot paths: KB search results (highest cost savings), channel configuration (simplest win), and customer identifier lookups (highest hit rate). The cache module is a thin async utility with graceful fallback — when Redis is unavailable, the system works identically to today.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: redis[hiredis]>=5.0.0 (production), fakeredis[json]>=2.21.0 (dev)
**Existing Dependencies**: openai-agents, asyncpg, openai, pydantic, python-dotenv, fastapi, uvicorn
**Storage**: PostgreSQL 16 + pgvector (Neon) — existing; Redis 7+ — new (local Docker or managed)
**Testing**: pytest + pytest-asyncio + fakeredis (in-memory Redis substitute, no real Redis needed)
**Target Platform**: Linux server / Docker container
**Performance Goals**: Cache hit eliminates OpenAI embedding call (50-200ms) + vector search (5-50ms); cache operations < 2ms
**Constraints**: Cache is additive (never a hard dependency); all existing 119 tests must pass unchanged

## Constitution Check

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | Agent-First Architecture | PASS | Cache is inside tool functions — agent still decides tool order autonomously |
| II | PostgreSQL as CRM | PASS | PostgreSQL remains the source of truth; Redis is a read-through cache only |
| III | Channel-Agnostic Core | PASS | Cache is channel-independent — channel config cache serves all channels equally |
| IV | Async-First | PASS | redis.asyncio client; all cache operations are async/await |
| V | Secrets-Free Codebase | PASS | REDIS_URL from environment variable with localhost default |
| VI | Structured Observability | PASS | Cache hits/misses logged at debug; failures at warning with key context |
| VII | Graceful Degradation | PASS | Every cache function accepts `Redis | None`; `None` = no-op fallback to DB |

**Result**: All gates PASS. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/003-redis-caching-layer/
├── plan.md                      # This file
├── spec.md                      # Feature specification
├── research.md                  # Technology decisions
├── data-model.md                # Cache entity model
├── contracts/
│   └── cache-contracts.md       # Cache utility API contracts
├── quickstart.md                # Setup instructions
└── tasks.md                     # Task breakdown (via /sp.tasks)
```

### Source Code (repository root)

```text
agent/
├── cache.py                     # NEW — Cache utility module (get/set/invalidate/key helpers)
├── context.py                   # MODIFY — Add redis_client to AgentContext
├── tools/
│   ├── knowledge.py             # MODIFY — Add KB search caching
│   ├── response.py              # MODIFY — Add channel config caching
│   └── customer.py              # MODIFY — Add customer lookup caching

api/
└── main.py                      # MODIFY — Redis shutdown in lifespan

tests/
├── test_cache/
│   ├── __init__.py              # NEW — empty
│   └── test_cache.py            # NEW — Cache utility unit tests
├── test_tools/
│   ├── test_knowledge.py        # MODIFY — Add cache-hit tests
│   ├── test_response.py         # MODIFY — Add cache-hit tests
│   └── test_customer.py         # MODIFY — Add cache-hit tests
└── conftest.py                  # MODIFY — Add fakeredis fixtures
```

**Structure Decision**: No new directories beyond `tests/test_cache/`. The cache module lives in `agent/cache.py` alongside the existing context and tools — it's part of the agent infrastructure, not a separate service.

## Implementation Phases

### Phase 1: Foundation (cache utility + context integration)

1. Add `redis[hiredis]` and `fakeredis` dependencies to `pyproject.toml`
2. Install via `uv pip install -e ".[dev]"`
3. Create `agent/cache.py` with: `create_redis_client()`, `get_cached()`, `set_cached()`, `invalidate()`, `invalidate_pattern()`, key helper functions
4. Add `redis_client: Redis | None = None` to `AgentContext` dataclass in `agent/context.py`
5. Call `create_redis_client()` in `build_context()`
6. Add Redis `aclose()` to FastAPI lifespan shutdown in `api/main.py`
7. Add `REDIS_URL` to `.env.example`

### Phase 2: Cache integration (tool modifications)

8. Add KB search caching to `agent/tools/knowledge.py` (cache check before embedding, cache store after DB query)
9. Add channel config caching to `agent/tools/response.py`
10. Add customer lookup caching to `agent/tools/customer.py` (with write-through invalidation on linking)

### Phase 3: Testing

11. Add `mock_redis` and `tool_ctx_with_cache` fixtures to `tests/conftest.py`
12. Create `tests/test_cache/test_cache.py` — unit tests for cache module (key gen, get/set, invalidate, TTL, graceful failure)
13. Add cache-hit/miss tests to existing tool test files
14. Run full test suite — verify all existing 119 tests still pass + new cache tests pass
