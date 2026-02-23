# Implementation Plan: Customer Success Agent

**Branch**: `001-customer-success-agent` | **Date**: 2026-02-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-customer-success-agent/spec.md`

## Summary

Build the core Customer Success AI agent backed by a PostgreSQL schema. The agent uses OpenAI Agents SDK with 11 `@function_tool` functions that autonomously handle customer identification, ticket lifecycle, knowledge base search (pgvector), conversation persistence, escalation, response delivery, and metrics. Each tool is an async Python function running PostgreSQL queries via asyncpg. The agent's system prompt enforces guardrails (no competitor discussion, no fabrication, ticket-before-response, sentiment-based escalation).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: openai-agents (OpenAI Agents SDK), asyncpg, openai (embeddings), pydantic, python-dotenv
**Storage**: PostgreSQL 16 + pgvector (Neon)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server / Docker container
**Project Type**: Single project (backend agent service)
**Performance Goals**: P95 response time < 3 seconds, semantic search relevance >= 85%
**Constraints**: P95 latency < 3s, escalation rate < 25%, cross-channel ID accuracy > 95%
**Scale/Scope**: 15+ KB articles, hundreds of customers, thousands of tickets

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | Agent-First Architecture | PASS | All 11 capabilities are `@function_tool` functions; agent decides ordering via system prompt; no hardcoded flow (FR-027) |
| II | PostgreSQL as CRM | PASS | All data in PostgreSQL (FR-001–FR-012); pgvector for KB search (FR-007); no external CRM |
| III | Channel-Agnostic Core | PASS | Agent core is channel-independent; channel formatting only in `send_response` (FR-033); unified message format |
| IV | Async-First | PASS | All tools are `async def`; asyncpg for DB (FR-025); no sync blocking calls |
| V | Secrets-Free Codebase | PASS | DATABASE_URL and OPENAI_API_KEY via env vars; `.env.example` included; no hardcoded secrets |
| VI | Structured Observability | PASS | Every tool logs via Python `logging` with JSON output (FR-026); `log_metric` records per-interaction data (FR-023); correlation IDs in error logs |
| VII | Graceful Degradation | PASS | Every tool has error handling + fallback (FR-026); unrecoverable errors → `escalate_to_human` (FR-032); ticket always created before response (FR-028) |

**Result**: All gates PASS. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-customer-success-agent/
├── plan.md              # This file
├── research.md          # Phase 0 output — technology decisions
├── data-model.md        # Phase 1 output — entity definitions
├── quickstart.md        # Phase 1 output — setup instructions
├── contracts/
│   └── tool-contracts.md # Phase 1 output — tool I/O specifications
└── tasks.md             # Phase 2 output (/sp.tasks command)
```

### Source Code (repository root)

```text
agent/
├── __init__.py
├── customer_success_agent.py    # Agent definition (OpenAI Agents SDK)
├── tools/                       # All @function_tool definitions
│   ├── __init__.py
│   ├── customer.py              # find_or_create_customer, get_customer_history
│   ├── ticket.py                # create_ticket, update_ticket, get_ticket
│   ├── knowledge.py             # search_knowledge_base
│   ├── conversation.py          # save_message, get_conversation_messages
│   ├── escalation.py            # escalate_to_human
│   ├── response.py              # send_response
│   └── metrics.py               # log_metric
├── prompts.py                   # System prompt text
└── context.py                   # AgentContext dataclass (db pool + openai client)

database/
├── migrations/
│   ├── 001_initial_schema.sql   # Tables, indexes, constraints, pgvector
│   └── 002_seed_knowledge_base.py # Seed 15+ KB articles with embeddings
└── pool.py                      # asyncpg pool creation + pgvector codec registration

tests/
├── conftest.py                  # Shared fixtures (test DB, pool, agent context)
├── test_tools/
│   ├── test_customer.py
│   ├── test_ticket.py
│   ├── test_knowledge.py
│   ├── test_conversation.py
│   ├── test_escalation.py
│   └── test_metrics.py
└── test_agent.py                # End-to-end agent tests
```

**Structure Decision**: Single-project layout chosen. No frontend in this feature (web form is a separate feature). The `agent/tools/` directory groups tools by domain for maintainability. The `database/` directory is separate from `agent/` because the schema and pool are shared infrastructure.

## Complexity Tracking

> No constitution violations detected. Table left empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none)    | —          | —                                   |
