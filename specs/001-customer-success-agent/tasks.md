# Tasks: Customer Success Agent

**Input**: Design documents from `/specs/001-customer-success-agent/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/tool-contracts.md

**Tests**: Not explicitly requested in the feature specification. Test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `agent/`, `database/`, `tests/` at repository root (per plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and directory structure

- [X] T001 Create project directory structure per plan.md: `agent/`, `agent/tools/`, `database/`, `database/migrations/`, `tests/`, `tests/test_tools/`
- [X] T002 Initialize Python project with pyproject.toml — dependencies: openai-agents, asyncpg, openai, pydantic, python-dotenv, pytest, pytest-asyncio
- [X] T003 [P] Create .env.example with DATABASE_URL and OPENAI_API_KEY placeholders and inline comments

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema, connection pool, agent context, and system prompt — MUST be complete before ANY user story

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Write 001_initial_schema.sql in database/migrations/ — all 8 tables (customers, customer_identifiers, conversations, messages, tickets, knowledge_base, channel_configs, agent_metrics), pgvector extension, all indexes, CHECK constraints, foreign keys, and channel_configs seed data per data-model.md
- [X] T005 [P] Implement asyncpg connection pool with pgvector vector codec registration in database/pool.py — create_pool() from DATABASE_URL env var, min_size=5, max_size=20, init callback for vector codec
- [X] T006 [P] Create AgentContext dataclass in agent/context.py — holds asyncpg.Pool and openai.AsyncOpenAI client, loaded from environment variables
- [X] T007 [P] Write production system prompt with all guardrails in agent/prompts.py — rules: always create ticket before responding, check sentiment < 0.3 for escalation, never discuss competitors, never promise undocumented features, use channel-appropriate tone, escalate when KB has no match
- [X] T008 [P] Configure structured JSON logging in agent/__init__.py — Python logging with JSON formatter, correlation ID support, no print() statements
- [X] T009 Write 002_seed_knowledge_base.py in database/migrations/ — Python script that generates embeddings via OpenAI text-embedding-3-small and inserts 15+ articles covering: getting-started, account management, billing FAQ, troubleshooting, feature how-tos, notification settings, password reset, integrations, API docs, security, data export

**Checkpoint**: Foundation ready — database schema deployed, pool configured, agent context and prompt defined. User story implementation can begin.

---

## Phase 3: User Story 1 — Web Form Customer Gets an Accurate Answer (Priority: P1) MVP

**Goal**: Agent receives a product question, identifies/creates the customer, creates a ticket + conversation, searches the knowledge base, saves messages, sends an accurate response, and resolves the ticket — all autonomously.

**Independent Test**: Submit "How do I reset my password?" with email "alice@example.com". Verify: customer created, ticket opened, KB article found, accurate response sent, ticket resolved.

### Implementation for User Story 1

- [X] T010 [P] [US1] Implement find_or_create_customer (basic: lookup by email/phone, create if new) and get_customer_history in agent/tools/customer.py — per tool-contracts.md, use RunContextWrapper[AgentContext] for DB pool access
- [X] T011 [P] [US1] Implement create_ticket (inserts ticket + conversation in single transaction), update_ticket (with forward-only transition validation: open→in_progress→resolved, any→escalated), and get_ticket in agent/tools/ticket.py — per tool-contracts.md
- [X] T012 [P] [US1] Implement search_knowledge_base in agent/tools/knowledge.py — generate query embedding via OpenAI API, cosine similarity query with threshold >= 0.7, return top_k=3 results, empty list if no match — per tool-contracts.md
- [X] T013 [P] [US1] Implement save_message and get_conversation_messages in agent/tools/conversation.py — per tool-contracts.md, clamp sentiment to [0.0, 1.0]
- [X] T014 [P] [US1] Implement send_response in agent/tools/response.py — verify ticket exists (safety net), fetch channel_configs for max_length/response_style, truncate if needed, save as outbound message, return delivered=true for web (gmail/whatsapp return delivered=false for now) — per tool-contracts.md
- [X] T015 [US1] Create agent/tools/__init__.py exporting all US1 tools as a list for agent registration (depends on T010–T014)
- [X] T016 [US1] Wire Customer Success Agent definition in agent/customer_success_agent.py — Agent[AgentContext] with name, instructions from prompts.py, all tools from T015, model="gpt-4o", helper function to run agent via Runner.run() (depends on T006, T007, T015)
- [X] T017 [US1] Add __main__.py entry point in agent/ for smoke testing — accept a message string + email, create AgentContext, run agent, print result (depends on T016)

**Checkpoint**: US1 complete. Agent handles a happy-path product question end-to-end. Validates SC-001, SC-009, SC-010.

---

## Phase 4: User Story 2 — Agent Escalates When It Cannot Help (Priority: P1)

**Goal**: Agent detects out-of-scope requests (refunds, legal), low sentiment (< 0.3), and no KB match — escalates instead of answering.

**Independent Test**: Submit "I want a full refund" — verify ticket created with status=escalated, reason recorded, customer gets acknowledgement.

### Implementation for User Story 2

- [X] T018 [P] [US2] Implement escalate_to_human in agent/tools/escalation.py — updates ticket status to "escalated" with reason, returns escalation confirmation — per tool-contracts.md
- [X] T019 [US2] Register escalation tool in agent/tools/__init__.py and agent/customer_success_agent.py — verify system prompt guardrails enforce: escalate on refund/legal requests, sentiment < 0.3, no KB match (depends on T018)
- [X] T020 [US2] Validate escalation scenarios: (1) refund request → escalated, (2) sentiment < 0.3 → escalated, (3) no KB match → escalated rather than fabricated answer (depends on T019)

**Checkpoint**: US2 complete. Agent safely escalates all out-of-scope requests. Validates SC-004, SC-008.

---

## Phase 5: User Story 3 — Cross-Channel Customer Continuity (Priority: P2)

**Goal**: A customer who contacts via web (email) and later via WhatsApp (phone) is recognized as the same person. The agent retrieves unified history across channels.

**Independent Test**: Create customer via email, link phone via agent-prompted flow, verify get_customer_history returns conversations from both channels.

### Implementation for User Story 3

- [X] T021 [US3] Enhance find_or_create_customer with identity linking — add link_to_identifier_value parameter: when provided, find existing customer by that value and attach the new identifier to their record in agent/tools/customer.py (depends on T010)
- [X] T022 [US3] Enhance get_customer_history to include cross-channel conversation details — return conversations grouped by channel with message counts in agent/tools/customer.py (depends on T010)
- [X] T023 [US3] Validate cross-channel: create customer via email on web, link phone number, query history — both channel conversations appear under one customer record (depends on T021, T022)

**Checkpoint**: US3 complete. Cross-channel identity works. Validates SC-002.

---

## Phase 6: User Story 4 — Knowledge Base Powers Agent Answers (Priority: P2)

**Goal**: Seeded knowledge base returns relevant articles for product questions. Similarity threshold 0.7 filters out irrelevant matches.

**Independent Test**: Run 10 diverse questions against seeded KB, verify top-result relevance >= 85%.

### Implementation for User Story 4

- [X] T024 [US4] Review and expand KB seed data in database/migrations/002_seed_knowledge_base.py — ensure 15+ articles cover all product areas, each with clear distinct content for semantic differentiation (depends on T009)
- [X] T025 [US4] Validate KB search quality: run 10 test queries (password reset, notification settings, billing, API usage, data export, account deletion, integrations, troubleshooting, security, getting started), verify >= 85% return the correct article in top 3 results. Tune article content if needed (depends on T024)

**Checkpoint**: US4 complete. KB semantic search is accurate. Validates SC-003, SC-010.

---

## Phase 7: User Story 5 — Agent Logs Metrics for Every Interaction (Priority: P3)

**Goal**: Every agent interaction (resolved or escalated) produces a metric row with response time, sentiment, channel, and resolution type.

**Independent Test**: Process 5 interactions, query agent_metrics by channel, verify all 5 entries exist with correct fields.

### Implementation for User Story 5

- [ ] T026 [P] [US5] Implement log_metric in agent/tools/metrics.py — best-effort insert into agent_metrics table, never fails fatally — per tool-contracts.md
- [ ] T027 [US5] Register log_metric tool in agent/tools/__init__.py and agent/customer_success_agent.py, verify the agent calls it after every interaction (resolved and escalated paths) (depends on T026)

**Checkpoint**: US5 complete. Metrics logged for every interaction. Validates SC-007.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Error handling audit, documentation, and full validation

- [ ] T028 [P] Audit error handling across all 11 tools — verify every tool has try/except with structured logging, graceful fallback message, and correlation IDs
- [ ] T029 [P] Verify .env.example is complete with all required variables (DATABASE_URL, OPENAI_API_KEY) and inline documentation for each
- [ ] T030 Validate quickstart.md end-to-end — fresh setup: install deps, run migrations, seed KB, execute smoke test via agent/__main__.py
- [ ] T031 Run full acceptance validation against all 10 success criteria (SC-001 through SC-010) — document pass/fail for each

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — the core MVP
- **US2 (Phase 4)**: Depends on Phase 2 — can run in parallel with US1 (different files) but logically builds on US1's agent definition
- **US3 (Phase 5)**: Depends on US1 (enhances customer.py from T010)
- **US4 (Phase 6)**: Depends on Phase 2 (seed data from T009) — can run in parallel with US1
- **US5 (Phase 7)**: Depends on Phase 2 — can run in parallel with US1 (different file)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational only — no dependencies on other stories
- **US2 (P1)**: Depends on Foundational only — new file (escalation.py), but T019 updates agent definition from T016
- **US3 (P2)**: Depends on US1 (T010) — enhances existing customer.py
- **US4 (P2)**: Depends on Foundational (T009) — validates/tunes seed data
- **US5 (P3)**: Depends on Foundational only — new file (metrics.py), but T027 updates agent definition

### Within Each User Story

- Tools in different files (marked [P]) can be built in parallel
- Tools in the same file must be sequential
- Agent wiring (customer_success_agent.py) depends on all tools for that story
- Validation depends on agent wiring

### Parallel Opportunities

- **Phase 2**: T005, T006, T007, T008 can all run in parallel (different files)
- **Phase 3**: T010, T011, T012, T013, T014 can all run in parallel (different files)
- **Phase 4 + Phase 7**: T018 (escalation.py) and T026 (metrics.py) can run in parallel
- **Phase 8**: T028 and T029 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tools in parallel (different files):
Task: "T010 [P] [US1] Implement customer tools in agent/tools/customer.py"
Task: "T011 [P] [US1] Implement ticket tools in agent/tools/ticket.py"
Task: "T012 [P] [US1] Implement KB search in agent/tools/knowledge.py"
Task: "T013 [P] [US1] Implement conversation tools in agent/tools/conversation.py"
Task: "T014 [P] [US1] Implement send_response in agent/tools/response.py"

# Then sequentially:
Task: "T015 [US1] Export all tools from agent/tools/__init__.py"
Task: "T016 [US1] Wire agent definition in agent/customer_success_agent.py"
Task: "T017 [US1] Add __main__.py smoke test entry point"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run agent with a product question end-to-end
5. Demo-ready: agent answers product questions from the knowledge base

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Agent answers questions → **MVP!**
3. Add US2 → Agent escalates safely → **Production guardrails**
4. Add US3 → Cross-channel identity → **Multi-channel ready**
5. Add US4 → KB quality validated → **Answer quality confirmed**
6. Add US5 → Metrics logged → **Observability complete**
7. Polish → Error audit + validation → **Feature complete**

### Suggested MVP Scope

Complete Phases 1–3 (Setup + Foundational + US1). This gives you a working agent that answers product questions end-to-end. Total: 17 tasks.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All tool implementations follow contracts in specs/001-customer-success-agent/contracts/tool-contracts.md
- All data model details in specs/001-customer-success-agent/data-model.md
