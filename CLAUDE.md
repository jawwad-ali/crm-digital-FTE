# CRM Digital FTE Factory

## Mandatory Skills

- **FastAPI**: When reading, reviewing, editing, or creating ANY `.py` file that involves FastAPI (routes, middleware, lifespan, dependencies, Pydantic request/response models, or anything under `api/`), you MUST load the `fastapi` skill BEFORE doing any work. This is NON-NEGOTIABLE — never write or modify FastAPI code without the skill loaded. Skill location: [`~/.claude/skills/fastapi/SKILL.md`](file:///C:/Users/Ali/.claude/skills/fastapi/SKILL.md)
- **OpenAI Agents SDK**: When reading, reviewing, editing, or creating ANY `.py` file that involves the OpenAI Agents SDK (`@function_tool`, `Agent`, `Runner`, `RunContextWrapper`, guardrails, handoffs, or anything under `agent/`), you MUST load the `openai-agents-sdk` skill BEFORE doing any work. This is NON-NEGOTIABLE — never write or modify agent code without the skill loaded. Skill location: [`~/.claude/skills/openai-agents-sdk/SKILL.md`](file:///C:/Users/Ali/.claude/skills/openai-agents-sdk/SKILL.md)
- **Next.js App Router**: When reading, reviewing, editing, or creating ANY `.tsx` or `.ts` file under `web/src/` (components, hooks, pages, layouts, routes, or anything in the `web/` directory), you MUST load the `nextjs-app-router` skill BEFORE doing any work. This is NON-NEGOTIABLE — never write or modify Next.js/React code without the skill loaded. Skill location: [`~/.claude/skills/nextjs-app-router/SKILL.md`](file:///C:/Users/Ali/.claude/skills/nextjs-app-router/SKILL.md)
- **Multiple skills**: If a file involves multiple technologies (e.g., `api/main.py` with FastAPI + OpenAI Agents SDK, or a `.tsx` file in a Next.js route that also calls agent APIs), you MUST load ALL matching skills before doing any work. Skills are independent conditions — if a file matches multiple skills, load ALL of them.

## Quick Reference

- **What:** 24/7 AI Customer Success agent handling Gmail, WhatsApp, and Web Form support
- **Tech Stack:** Python 3.12, FastAPI, OpenAI Agents SDK, PostgreSQL + pgvector, Redis
- **Full Spec:** [docs/hackathon-spec.md](docs/hackathon-spec.md) — all requirements, architecture, exercises, scoring, and deliverables live there. Read it before starting any work.

## Architecture

```
Request Flow:
  Client → POST /api/chat → 202 + job_id (instant)
                           → BackgroundTask: run_agent() → set_job() in Redis
  Client → GET /api/jobs/{id} → reads result from Redis

Sync Fallback:
  POST /api/chat?sync=true → 200 + response (blocks ~30s)
  Redis unavailable         → auto-falls back to sync mode

System Layers:
  api/main.py          → FastAPI HTTP layer (endpoints, Pydantic models)
  agent/               → AI agent (OpenAI Agents SDK, tools, context)
  agent/cache.py       → Redis caching + job store (get/set with graceful fallback)
  agent/tools/         → Function tools (customer, ticket, conversation, knowledge, response)
  database/            → PostgreSQL schema, migrations, seed data
  tests/               → pytest with fakeredis, async fixtures
```

## Key Files

| File | Purpose |
|------|---------|
| `api/main.py` | All endpoints, Pydantic models, background task helpers |
| `agent/cache.py` | Redis cache (KB search, channel config, customer lookup) + job store |
| `agent/context.py` | `AgentContext` dataclass (db_pool, openai_client, redis_client) |
| `agent/customer_success_agent.py` | Agent definition, system prompt, `run_agent()` |
| `agent/__init__.py` | Correlation ID (contextvars), JSON log formatter |
| `agent/tools/customer.py` | find_or_create_customer, get_customer_history, cross_channel_link |
| `agent/tools/ticket.py` | create_ticket, update_ticket, get_ticket |
| `agent/tools/conversation.py` | save_message, get_conversation_messages |
| `agent/tools/knowledge.py` | search_knowledge_base (OpenAI embedding + pgvector) |
| `agent/tools/response.py` | send_response (channel-aware, config-cached) |
| `tests/conftest.py` | Shared fixtures (mock_redis via fakeredis) |
| `tests/test_api/test_main.py` | API endpoint tests (28 tests) |
| `tests/test_cache/test_cache.py` | Cache + job store tests (42 tests) |

## Async Pattern (Background Tasks)

All three channels (web, Gmail, WhatsApp) use the same pattern:
1. Endpoint receives request, generates correlation ID
2. Stores `{"status": "processing"}` in Redis via `set_job()`
3. Dispatches `_process_chat` or `_process_webhook` to `BackgroundTasks`
4. Returns HTTP 202 with `JobAccepted(job_id, status, retry_after)`
5. Background task runs agent, stores result via `set_job()` as completed/failed
6. Client polls `GET /api/jobs/{job_id}` to retrieve result

**Fallbacks:**
- `?sync=true` on `/api/chat` → skips background task, returns 200 with direct response
- `redis_client is None` → all endpoints auto-fall back to sync mode with warning log

## Caching Strategy

| What | Key Pattern | TTL | Why |
|------|-------------|-----|-----|
| KB search results | `kb:search:{hash}` | 1 hour | Saves OpenAI embedding + pgvector query |
| Channel config | `channel_config:{channel}` | 24 hours | Static config (style, max_length) |
| Customer lookup | `customer:lookup:{type}:{value}` | 1 hour | Email/phone → customer_id mapping |
| Job state | `job:{job_id}` | 1 hour | Background task results |

All keys prefixed with `crm:`. All functions accept `redis_client: Redis | None` and no-op gracefully when None.

## Conventions

- Python 3.12+, async/await throughout
- Pydantic BaseModel for all input validation
- Structured logging (no print statements)
- Environment variables for all config (no hardcoded secrets)
- All tools must have error handling with graceful fallbacks
- PostgreSQL IS the CRM — no external CRM integration needed
- Every Redis function must handle `None` client (graceful no-op)
- Job timeout: processing jobs older than 5 minutes auto-marked "failed" at read time

## Testing Patterns

- **Framework:** pytest + pytest-asyncio (mode=auto), all tests are async
- **Redis mock:** `mock_redis` fixture in `tests/conftest.py` uses `fakeredis.aioredis.FakeRedis`
- **API tests:** `_mock_lifespan` fixture injects fake `AgentContext` into `app.state`
- **Agent mocking:** `@patch("api.main.run_agent", new_callable=AsyncMock)`
- **Job store mocking:** `@patch("api.main.set_job", new_callable=AsyncMock)` for endpoint tests
- **Job polling mocking:** `@patch("api.main.get_job", new_callable=AsyncMock)` returns different states
- **Package manager:** `uv` (not pip) — use `uv pip install -e ".[dev]"`

## Commands

- `uvicorn api.main:app --reload` — run FastAPI dev server
- `pytest tests/ -v` — run full test suite (177 tests)
- `docker compose up` — start local dev environment
- `wsl sudo service redis-server start` — start Redis (from Windows)

## Do NOT

- Don't cache agent responses — customer data changes constantly, stale answers are dangerous
- Don't use `print()` — use `logger` from the logging module
- Don't hardcode connection strings — use env vars (`DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`)
- Don't skip graceful fallback — every Redis call must handle `None` client
- Don't add external CRM integrations — PostgreSQL IS the CRM
- Don't use pip — use `uv` as the package manager
