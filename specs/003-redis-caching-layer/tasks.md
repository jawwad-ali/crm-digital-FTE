# Tasks: Redis Caching Layer

**Input**: Design documents from `/specs/003-redis-caching-layer/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/cache-contracts.md

**Tests**: Included — spec FR-016 requires tests using in-memory cache substitute.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3, US4)
- Exact file paths included in descriptions

---

## Phase 1: Setup

**Purpose**: Add Redis dependencies and install

- [x] T001 Add `redis[hiredis]>=5.0.0` to dependencies and `fakeredis[json]>=2.21.0` to dev dependencies in `pyproject.toml`
- [x] T002 Install dependencies via `uv pip install -e ".[dev]"`
- [x] T003 [P] Add `REDIS_URL=redis://localhost:6379` to `.env.example`

---

## Phase 2: Foundational (Cache Utility Module)

**Purpose**: Core cache infrastructure that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create `agent/cache.py` with TTL constants (`TTL_KB_SEARCH=3600`, `TTL_CHANNEL_CONFIG=86400`, `TTL_CUSTOMER_LOOKUP=3600`), key prefix `_PREFIX="crm:"`, and `create_redis_client()` function per `contracts/cache-contracts.md`
- [x] T005 Add `get_cached()` and `set_cached()` functions to `agent/cache.py` with JSON serialization, prefix handling, and graceful exception handling per contracts
- [x] T006 Add `invalidate()` and `invalidate_pattern()` functions to `agent/cache.py` with SCAN-based pattern delete per contracts
- [ ] T007 Add key helper functions to `agent/cache.py`: `make_kb_cache_key()` (SHA-256 hash of normalized query), `make_channel_config_key()`, `make_customer_lookup_key()` per contracts
- [ ] T008 Add `redis_client: redis.asyncio.Redis | None = None` field to `AgentContext` dataclass and call `create_redis_client()` in `build_context()` in `agent/context.py`
- [ ] T009 Add Redis `aclose()` to FastAPI lifespan shutdown (guarded by `if is not None`) in `api/main.py`
- [ ] T010 Add `mock_redis` fixture (fakeredis), `agent_context_with_cache` fixture, and `tool_ctx_with_cache` fixture to `tests/conftest.py`
- [ ] T011 Create `tests/test_cache/__init__.py` (empty) and `tests/test_cache/test_cache.py` with unit tests: key generation (deterministic, normalized, different top_k), get/set (hit, miss, None client, TTL), invalidate (single, multiple, pattern, None client), graceful failure (broken client)

**Checkpoint**: Cache utility module complete, tested in isolation, existing 119 tests still pass

---

## Phase 3: User Story 1 — Faster Repeated Questions (Priority: P1)

**Goal**: Cache KB search results to eliminate redundant OpenAI embedding calls and vector searches

**Independent Test**: Send same question to `/api/chat` twice — second request returns cached result without OpenAI/DB calls

### Implementation

- [ ] T012 [US1] Add cache check (before embedding call) and cache store (after DB query, for both "found" and "no_match") to `search_knowledge_base()` in `agent/tools/knowledge.py` using `make_kb_cache_key()`, `get_cached()`, `set_cached()` with `TTL_KB_SEARCH`
- [ ] T013 [US1] Add cache-hit test to `tests/test_tools/test_knowledge.py`: verify second call with same query uses cache (mock OpenAI and DB not called on cache hit)

**Checkpoint**: KB search caching works — repeated questions skip embedding API + vector search

---

## Phase 4: User Story 2 — Graceful Operation Without Cache (Priority: P1)

**Goal**: System works identically when Redis is unavailable — zero crashes, zero degraded functionality

**Independent Test**: Set `redis_client=None`, run all existing tool tests — everything passes unchanged

### Implementation

- [ ] T014 [US2] Verify all existing tests pass with `redis_client=None` (default) — no code changes expected, just run `pytest tests/` and confirm 119+ tests pass
- [ ] T015 [US2] Add graceful fallback test to `tests/test_cache/test_cache.py`: verify `get_cached()` returns None and `set_cached()` no-ops when client is closed/broken — no exceptions raised

**Checkpoint**: Graceful degradation confirmed — cache unavailability causes zero failures

---

## Phase 5: User Story 3 — Cached Channel Configuration (Priority: P2)

**Goal**: Cache the 3 static channel configs to eliminate a DB query per response sent

**Independent Test**: Send chat request, verify channel config DB query only runs once per channel — subsequent requests use cache

### Implementation

- [ ] T016 [US3] Add cache check and cache store for channel config lookup in `send_response()` in `agent/tools/response.py` using `make_channel_config_key()`, `get_cached()`, `set_cached()` with `TTL_CHANNEL_CONFIG`
- [ ] T017 [US3] Add cache-hit test to `tests/test_tools/test_response.py`: verify second call with same channel uses cached config (DB fetchrow not called on cache hit)

**Checkpoint**: Channel config caching works — only 3 DB queries total (one per channel) per 24 hours

---

## Phase 6: User Story 4 — Cached Customer Lookup (Priority: P2)

**Goal**: Cache customer identifier lookups with write-through invalidation on cross-channel linking

**Independent Test**: Send two chat requests with same email — second finds customer from cache without DB query

### Implementation

- [ ] T018 [US4] Add cache check (before DB query, skip for linking requests) and cache store (after DB result) to `find_or_create_customer()` in `agent/tools/customer.py` using `make_customer_lookup_key()`, `get_cached()`, `set_cached()` with `TTL_CUSTOMER_LOOKUP`
- [ ] T019 [US4] Add cache invalidation on cross-channel linking path in `find_or_create_customer()` in `agent/tools/customer.py` — set cache for new identifier after link
- [ ] T020 [US4] Add cache-hit test and cache-invalidation test to `tests/test_tools/test_customer.py`: verify returning customer uses cache, verify linking invalidates stale entry

**Checkpoint**: Customer lookup caching works — returning customers skip 2-3 DB queries per interaction

---

## Phase 7: Polish & Verification

**Purpose**: Full suite validation and cross-story verification

- [ ] T021 Run full test suite (`pytest tests/ -v`) — verify ALL existing tests pass + ALL new cache tests pass
- [ ] T022 Run quickstart.md validation: start Redis via Docker, start server, send duplicate question, verify "Cache HIT" in logs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1 - KB caching)**: Depends on Phase 2
- **Phase 4 (US2 - Graceful fallback)**: Depends on Phase 2 — can run in parallel with Phase 3
- **Phase 5 (US3 - Channel config)**: Depends on Phase 2 — can run in parallel with Phase 3/4
- **Phase 6 (US4 - Customer lookup)**: Depends on Phase 2 — can run in parallel with Phase 3/4/5
- **Phase 7 (Polish)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (KB caching)**: Independent — only needs foundational cache module
- **US2 (Graceful fallback)**: Independent — tests existing behavior with `None` client
- **US3 (Channel config)**: Independent — different tool file (`response.py`)
- **US4 (Customer lookup)**: Independent — different tool file (`customer.py`)

### Parallel Opportunities

After Phase 2 completes, ALL four user stories can execute in parallel:
- US1 modifies `agent/tools/knowledge.py` + `tests/test_tools/test_knowledge.py`
- US2 adds tests to `tests/test_cache/test_cache.py` (no tool changes)
- US3 modifies `agent/tools/response.py` + `tests/test_tools/test_response.py`
- US4 modifies `agent/tools/customer.py` + `tests/test_tools/test_customer.py`

No file conflicts between user stories.

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T011)
3. Complete Phase 3: US1 — KB caching (T012-T013)
4. **STOP and VALIDATE**: Send duplicate question, verify cache hit in logs
5. This alone delivers the highest value — eliminates OpenAI API cost for repeated queries

### Incremental Delivery

1. Setup + Foundational → Cache module ready
2. Add US1 (KB caching) → Highest cost savings
3. Add US2 (Graceful fallback) → Reliability confirmed
4. Add US3 (Channel config) → Easiest win, 100% hit rate
5. Add US4 (Customer lookup) → Highest hit rate for returning customers
6. Polish → Full verification

---

## Notes

- [P] tasks = different files, no dependencies
- [USn] label maps task to specific user story
- `redis_client` defaults to `None` — existing tests never break
- All cache tests use `fakeredis` — no running Redis needed
- Commit after each phase completion
