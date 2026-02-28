# Tasks: FastAPI Backend

**Input**: Design documents from `/specs/002-fastapi-backend/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, contracts/endpoint-contracts.md

**Organization**: Tasks are grouped by phase. The API is small enough that most tasks are sequential.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `api/`, `tests/test_api/` at repository root (per plan.md)

---

## Phase 1: Setup

**Purpose**: Add dependencies and create directory structure

- [X] T001 [P] Update pyproject.toml — add `fastapi>=0.115.0` and `uvicorn[standard]>=0.34.0` to dependencies, `httpx>=0.28.0` to dev dependencies, add `"api*"` to `[tool.setuptools.packages.find] include`
- [X] T002 [P] Create directory structure: `api/__init__.py`, `tests/test_api/__init__.py`
- [X] T003 Install new dependencies via `uv pip install -e ".[dev]"`

---

## Phase 2: Core Application

**Purpose**: FastAPI app with lifespan, health check, CORS, and error handling — MUST be complete before endpoint implementation

- [X] T004 [US4] Create `api/main.py` with FastAPI app, lifespan context manager (`build_context()` on startup, `db_pool.close()` on shutdown), CORS middleware (allow all origins), and global exception handler returning JSON errors
- [X] T005 [US4] Add `GET /health` endpoint returning `{"status": "ok"}` — verify server starts with `uvicorn api.main:app --reload`

**Checkpoint**: Server starts, health check works, CORS headers present.

---

## Phase 3: Chat Endpoint (User Story 1 — P1)

**Purpose**: The primary endpoint connecting the frontend to the agent

- [X] T006 [US1] Define Pydantic models in `api/main.py`: `ChatRequest` (message, email, channel, name), `ChatResponse` (response, correlation_id)
- [X] T007 [US1] Implement `POST /api/chat` — set correlation_id, prepend `[Customer: {email}, Channel: {channel}]` to message, call `run_agent()`, return ChatResponse (depends on T004, T006)
- [X] T008 [US1] Smoke test: POST a product question to `/api/chat`, verify the agent processes it end-to-end and returns a response

**Checkpoint**: Chat endpoint works — frontend can send messages and receive agent responses.

---

## Phase 4: Read Endpoints (User Story 2 — P2)

**Purpose**: Ticket and customer lookup for the frontend

- [X] T009 [P] [US2] Implement `GET /api/tickets/{ticket_id}` — reuse `get_ticket` tool via `on_invoke_tool()`, return 404 if not found
- [X] T010 [P] [US2] Implement `GET /api/customers/{customer_id}/history` — reuse `get_customer_history` tool via `on_invoke_tool()`, return 404 if not found

**Checkpoint**: Frontend can look up tickets and customer history.

---

## Phase 5: Webhook Endpoints (User Story 3 — P3)

**Purpose**: Stub endpoints for Gmail and WhatsApp channel integration

- [X] T011 [P] [US3] Define `WebhookPayload` Pydantic model (from_address, body) and implement `POST /api/webhooks/gmail` — same pattern as chat but with channel="gmail" and email=from_address
- [X] T012 [P] [US3] Implement `POST /api/webhooks/whatsapp` — same pattern as chat but with channel="whatsapp" and phone=from_address

**Checkpoint**: Webhook stubs work — Gmail and WhatsApp messages process through the agent.

---

## Phase 6: Tests

**Purpose**: Comprehensive API tests with mocked agent

- [X] T013 Create `tests/test_api/test_main.py` — test all 6 endpoints using `httpx.AsyncClient` with `ASGITransport`. Mock `run_agent` to avoid real OpenAI calls. Test: health check, chat happy path, chat validation error, ticket lookup, ticket not found, customer history, customer not found, gmail webhook, whatsapp webhook, CORS headers, error handling.
- [X] T014 Run full test suite (`pytest tests/ -v`) and verify coverage remains >= 80%

**Checkpoint**: All tests pass, coverage >= 80%.

---

## Phase 7: Validation

**Purpose**: End-to-end validation against success criteria

- [X] T015 Validate all 10 success criteria (SC-001 through SC-010) — start server, test each endpoint manually or programmatically, document pass/fail

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Core App)**: Depends on Phase 1
- **Phase 3 (Chat)**: Depends on Phase 2
- **Phase 4 (Read)**: Depends on Phase 2 — can run in parallel with Phase 3
- **Phase 5 (Webhooks)**: Depends on Phase 2 — can run in parallel with Phase 3 and 4
- **Phase 6 (Tests)**: Depends on all endpoints being implemented (Phase 3-5)
- **Phase 7 (Validation)**: Depends on Phase 6

### Parallel Opportunities

- **Phase 1**: T001 and T002 can run in parallel
- **Phase 4**: T009 and T010 can run in parallel
- **Phase 5**: T011 and T012 can run in parallel
- **Phase 3 + 4 + 5**: All depend only on Phase 2 — can run in parallel

---

## Implementation Strategy

### MVP First (Chat Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Core Application
3. Complete Phase 3: Chat Endpoint
4. **STOP and VALIDATE**: POST a question, verify agent responds
5. Demo-ready: frontend can talk to the agent

### Incremental Delivery

1. Setup + Core → Server starts, health works
2. Add Chat → Frontend can send messages → **MVP!**
3. Add Read Endpoints → Frontend shows tickets/history
4. Add Webhooks → Gmail/WhatsApp stubs ready
5. Tests + Validation → **Feature complete**
