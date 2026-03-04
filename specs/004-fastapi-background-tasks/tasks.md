# Tasks: FastAPI Background Tasks

**Input**: Design documents from `specs/004-fastapi-background-tasks/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/job-endpoints.md

**Organization**: Tasks are grouped by user story. US1+US2 are combined (both P1, tightly coupled — submitting jobs is useless without polling, and vice versa).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

---

## Phase 1: Foundational — Job Store Helpers

**Purpose**: Add Redis-based job storage functions that all endpoints will use. Must complete before any user story work.

- [x] T001 Add `TTL_JOB = 3600`, `JOB_TIMEOUT = 300` constants and `make_job_key(job_id)` helper returning `job:{job_id}` in `agent/cache.py`
- [x] T002 Add `set_job(redis_client, job_id, data, ttl=TTL_JOB)` function in `agent/cache.py` — serialize `data` dict as JSON, store with `crm:` prefix and TTL. Auto-inject `created_at` ISO timestamp if not present. Graceful no-op when `redis_client is None`.
- [x] T003 Add `get_job(redis_client, job_id)` function in `agent/cache.py` — fetch and deserialize job JSON. If `status == "processing"` and `created_at` is older than `JOB_TIMEOUT` seconds, return `{"status": "failed", "error": "Request timed out. Please try again.", "response": null}`. Return `None` for missing keys or `None` client.
- [x] T004 [P] Add `JobAccepted` and `JobStatus` Pydantic response models in `api/main.py` — `JobAccepted(job_id: str, status: str = "processing", retry_after: int = 5)`, `JobStatus(job_id: str, status: str, response: str | None = None, error: str | None = None, retry_after: int | None = None)`
- [x] T005 Add job store unit tests in `tests/test_cache/test_cache.py` — test `make_job_key` format, `set_job` + `get_job` round-trip, `get_job` returns `None` for missing key, `get_job` timeout detection (mock `created_at` to 6 minutes ago), `set_job`/`get_job` no-op with `None` client, `set_job` graceful failure with broken client

**Checkpoint**: Job store helpers ready — all 3 functions tested, all user stories can now use `set_job`/`get_job`.

---

## Phase 2: US1 + US2 — Chat Background Processing & Job Polling (Priority: P1) 🎯 MVP

**Goal**: `/api/chat` returns HTTP 202 instantly with a job ID. Agent runs in background. Client polls `/api/jobs/{job_id}` to get the result.

**Independent Test**: POST to `/api/chat`, get 202 with `job_id` in < 2s. Poll `GET /api/jobs/{job_id}` — see "processing" then "completed".

### Implementation

- [ ] T006 [US1] Create `_process_chat(job_id, req, ctx)` async background task function in `api/main.py` — call `set_correlation_id(job_id)`, then `run_agent()`, then `set_job()` with `status=completed` and the response. Wrap in try/except: on failure, `set_job()` with `status=failed` and error message. Log start and completion/failure.
- [ ] T007 [US1] Refactor `POST /api/chat` endpoint in `api/main.py` — inject `BackgroundTasks` dependency, generate correlation ID, call `set_job()` with `status=processing`, add `_process_chat` to background tasks, return `JobAccepted` with HTTP 202.
- [ ] T008 [US2] Implement `GET /api/jobs/{job_id}` endpoint in `api/main.py` — call `get_job()`, return 404 if `None`, otherwise return `JobStatus` with `retry_after=5` when processing, `retry_after=None` when completed/failed.
- [ ] T009 [US1] Update existing `TestChat` tests in `tests/test_api/test_main.py` — change expected status code from 200 to 202, update expected response shape to `JobAccepted` (`job_id`, `status`, `retry_after`). Mock `run_agent` must still be called (via background task). Update validation error tests (those should still return 422).
- [ ] T010 [US2] Add `TestJobPolling` tests in `tests/test_api/test_main.py` — test job processing status (set a "processing" job, poll, verify response), job completed status, job failed status, job timed out (set `created_at` 6 min ago), job not found (invalid ID returns 404), job expired (no key in Redis returns 404).

**Checkpoint**: Core async flow works — chat returns instantly, agent runs in background, results retrievable via polling.

---

## Phase 3: US3 — Webhook Background Processing (Priority: P2)

**Goal**: Gmail and WhatsApp webhook endpoints return HTTP 202 instantly instead of blocking for ~40s.

**Independent Test**: POST to `/api/webhooks/gmail`, get 202 with `job_id`. Poll `/api/jobs/{job_id}` — see "processing" then "completed".

### Implementation

- [ ] T011 [US3] Create `_process_webhook(job_id, channel, from_address, body, ctx)` async background task function in `api/main.py` — same pattern as `_process_chat`: set correlation ID, run agent, set job result. Log start and completion/failure with channel name.
- [ ] T012 [US3] Refactor `POST /api/webhooks/gmail` endpoint in `api/main.py` — inject `BackgroundTasks`, generate correlation ID, store "processing" job, dispatch `_process_webhook(channel="gmail")`, return `JobAccepted` with HTTP 202.
- [ ] T013 [US3] Refactor `POST /api/webhooks/whatsapp` endpoint in `api/main.py` — same pattern as T012 with `channel="whatsapp"`.
- [ ] T014 [US3] Update existing `TestGmailWebhook` and `TestWhatsAppWebhook` tests in `tests/test_api/test_main.py` — change expected status from 200 to 202, update response shape to `JobAccepted`. Validation error tests (missing fields) should still return 422.

**Checkpoint**: All 3 channels (web, Gmail, WhatsApp) return instantly. Background processing works identically across channels.

---

## Phase 4: US4 — Synchronous Escape Hatch & Graceful Fallback (Priority: P3)

**Goal**: `?sync=true` preserves the old blocking behavior for Swagger/testing. If Redis is down, system auto-falls back to sync.

**Independent Test**: POST to `/api/chat?sync=true`, get HTTP 200 with full response (old behavior). Stop Redis, POST to `/api/chat`, get HTTP 200 (graceful fallback).

### Implementation

- [ ] T015 [US4] Add `sync: bool = Query(False)` parameter to `POST /api/chat` endpoint in `api/main.py` — when `True`, skip background task: await `run_agent()` directly and return `ChatResponse` with HTTP 200.
- [ ] T016 [US4] Add graceful fallback logic in `api/main.py` — if `ctx.redis_client is None`, force sync mode regardless of `sync` parameter. Log a warning when falling back. Apply same fallback to webhook endpoints (always sync when no Redis).
- [ ] T017 [US4] Add sync mode and fallback tests in `tests/test_api/test_main.py` — test `?sync=true` returns HTTP 200 with `ChatResponse`, test Redis-None fallback returns HTTP 200 with `ChatResponse`, test default (no `?sync`) returns HTTP 202 with `JobAccepted`.

**Checkpoint**: Developer escape hatch works. System degrades gracefully without Redis.

---

## Phase 5: Polish & Verification

**Purpose**: Full suite regression and manual validation

- [ ] T018 Run full test suite (`pytest tests/ -v`) — verify ALL existing tests pass + ALL new tests pass
- [ ] T019 Run quickstart.md manual validation — test async flow (POST chat → poll job), sync mode (`?sync=true`), and graceful fallback (stop Redis → verify sync fallback)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Foundational)**: No dependencies — start immediately
- **Phase 2 (US1+US2)**: Depends on Phase 1 (needs `set_job`/`get_job` + Pydantic models)
- **Phase 3 (US3)**: Depends on Phase 2 (reuses `_process_chat` pattern, needs `/api/jobs` endpoint)
- **Phase 4 (US4)**: Depends on Phase 2 (adds sync parameter to existing async endpoint)
- **Phase 5 (Polish)**: Depends on all phases complete

### Within Each Phase

- T001 → T002 → T003 (sequential — each builds on previous in same file)
- T004 is parallel with T001–T003 (different file)
- T005 depends on T001–T003 (tests need the functions)
- T006 → T007 (background function before endpoint refactor)
- T008 can start after T003 (needs `get_job`)
- T009 depends on T007 (tests updated endpoint)
- T010 depends on T008 (tests the polling endpoint)
- T011 → T012+T013 (background function before endpoint refactors)
- T012 and T013 are parallel (independent endpoints)
- T015 → T016 (sync param before fallback logic)

### Parallel Opportunities

```text
# Phase 1 — parallel across files:
T001–T003 (agent/cache.py)  ||  T004 (api/main.py)

# Phase 2 — after T006+T007:
T008 (job endpoint)  ||  T009 (chat test updates)

# Phase 3 — after T011:
T012 (gmail refactor)  ||  T013 (whatsapp refactor)
```

---

## Implementation Strategy

### MVP First (Phase 1 + Phase 2)

1. Complete Phase 1: Job store helpers + Pydantic models
2. Complete Phase 2: Chat endpoint → async, job polling endpoint
3. **STOP and VALIDATE**: POST chat → get 202 → poll → get result
4. This alone delivers the core value (instant responses)

### Incremental Delivery

1. Phase 1 + Phase 2 → MVP (chat works async) → Commit
2. Add Phase 3 → Webhooks work async too → Commit
3. Add Phase 4 → Sync escape hatch for Swagger → Commit
4. Phase 5 → Full regression + manual validation → Final commit + PR

---

## Notes

- Only 2 production files modified: `api/main.py` and `agent/cache.py`
- No database migrations — job state lives entirely in Redis
- All existing tests updated (not deleted) — response shape changes from `ChatResponse` to `JobAccepted`
- Commit after each phase
- Total: 19 tasks across 5 phases
