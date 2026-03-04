# Implementation Plan: FastAPI Background Tasks

**Branch**: `004-fastapi-background-tasks` | **Date**: 2026-03-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/004-fastapi-background-tasks/spec.md`

## Summary

Convert all chat and webhook endpoints from synchronous (blocking ~40s while the AI agent runs) to asynchronous background processing using FastAPI's built-in `BackgroundTasks`. Requests return an HTTP 202 with a correlation ID instantly. Clients poll a new `/api/jobs/{job_id}` endpoint for results. Job state is stored in Redis (already wired from feature 003). A `?sync=true` query parameter preserves the old blocking behavior for developer/testing use.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI (BackgroundTasks), redis.asyncio (already installed), Pydantic
**Storage**: Redis (job results — ephemeral, 1h TTL), PostgreSQL (persistent CRM data — unchanged)
**Testing**: pytest + fakeredis (already configured), httpx AsyncClient
**Target Platform**: Linux server / Windows (WSL for Redis)
**Project Type**: Web API (single backend)
**Performance Goals**: Acknowledgment response < 2 seconds; 50+ concurrent requests accepted without rejection
**Constraints**: Jobs lost on server restart (acceptable — timeout-based expiry at 5 minutes marks stale jobs as failed); no external task queue
**Scale/Scope**: MVP — single server instance, single Redis instance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Agent-First Architecture | PASS | Agent tool-calling loop unchanged — just moved into a background task |
| II. PostgreSQL as CRM | PASS | No schema changes. All persistent data stays in PostgreSQL |
| III. Channel-Agnostic Core | PASS | All 3 channels (web, gmail, whatsapp) get identical background processing |
| IV. Async-First | PASS | `BackgroundTasks` uses `async def`. All I/O remains async. `run_agent()` is already async |
| V. Secrets-Free Codebase | PASS | No new secrets. Redis URL already in `.env.example` |
| VI. Structured Observability | PASS | FR-010 requires logging start/completion/failure with correlation ID |
| VII. Graceful Degradation | PASS | If Redis unavailable, `?sync=true` behavior is the fallback — jobs degrade to synchronous |

**Gate Result**: ALL PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/004-fastapi-background-tasks/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── job-endpoints.md
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
api/
├── main.py              # MODIFY — refactor chat/webhook endpoints to use BackgroundTasks
└── __init__.py

agent/
├── cache.py             # MODIFY — add job store helpers (set_job, get_job)
├── context.py           # NO CHANGE
├── customer_success_agent.py  # NO CHANGE
└── tools/               # NO CHANGE

tests/
├── test_api/
│   └── test_main.py     # MODIFY — update tests for 202 responses + add job polling tests
├── test_cache/
│   └── test_cache.py    # MODIFY — add job store tests
└── conftest.py          # POSSIBLY MODIFY — add job-related fixtures
```

**Structure Decision**: Minimal footprint — only 2 production files modified (`api/main.py`, `agent/cache.py`), plus test updates. No new modules or packages needed. Job storage reuses the existing Redis infrastructure from feature 003.

## Complexity Tracking

No constitution violations — table not needed.
