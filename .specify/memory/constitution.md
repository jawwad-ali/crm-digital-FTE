<!--
  Sync Impact Report
  ===================
  Version change: 0.0.0 → 1.0.0 (MAJOR — initial ratification)
  Added principles:
    - I. Agent-First Architecture
    - II. PostgreSQL as CRM
    - III. Channel-Agnostic Core
    - IV. Async-First
    - V. Secrets-Free Codebase
    - VI. Structured Observability
    - VII. Graceful Degradation & Escalation
  Added sections:
    - Technology Stack & Constraints
    - Development Workflow
    - Governance
  Removed sections: (none — initial version)
  Templates requiring updates:
    - .specify/templates/plan-template.md — ⚠ pending (Constitution Check
      section needs gate definitions based on these principles)
    - .specify/templates/spec-template.md — ✅ no changes needed
    - .specify/templates/tasks-template.md — ✅ no changes needed
  Follow-up TODOs: none
-->

# CRM Digital FTE Factory Constitution

## Core Principles

### I. Agent-First Architecture

The AI agent (OpenAI Agents SDK) MUST autonomously decide which
`@function_tool` functions to call and in what order. We do NOT
hardcode control flow between tools.

- Every capability exposed to the agent MUST be a `@function_tool`
  decorated Python function with a Pydantic input model.
- The agent's system prompt defines guardrails and priorities;
  orchestration logic lives in the LLM, not in application code.
- Tool descriptions MUST be precise enough for the agent to select
  the correct tool without ambiguity.
- If the agent cannot resolve a request with available tools, it
  MUST call `escalate_to_human`.

### II. PostgreSQL as CRM

PostgreSQL (hosted on Neon) IS the CRM. No external CRM platform
(Salesforce, HubSpot, etc.) is permitted.

- All customer data, tickets, conversations, knowledge base
  articles, and metrics MUST reside in PostgreSQL.
- Semantic search MUST use pgvector for knowledge base retrieval.
- Schema changes MUST go through versioned SQL migrations.
- Every `@function_tool` that touches data MUST run a PostgreSQL
  query internally — no in-memory-only state for persistent data.

### III. Channel-Agnostic Core

The agent core MUST be channel-independent. Channel-specific
concerns live at the edges only.

- Inbound messages from Gmail, WhatsApp, and Web Form MUST be
  normalised into a unified internal format before reaching the
  agent.
- Outbound responses MUST be formatted per-channel only at the
  `send_response` boundary (tone, length, structure).
- Channel metadata (source, identifier type) MUST be stored with
  every message but MUST NOT alter core agent logic.
- Cross-channel customer identity MUST be resolved via
  `find_or_create_customer` using email/phone matching.

### IV. Async-First

All I/O-bound operations MUST use `async`/`await`. No synchronous
blocking calls in the request path.

- FastAPI endpoints MUST be `async def`.
- Database queries MUST use an async driver (e.g., `asyncpg`).
- External API calls (Gmail, WhatsApp/Twilio) MUST be async.
- CPU-bound work (if any) MUST be offloaded to a thread/process
  pool, never blocking the event loop.

### V. Secrets-Free Codebase

Zero secrets in source code. All credentials and configuration
MUST come from environment variables.

- API keys, database URLs, and tokens MUST be read from `os.environ`
  or a `.env` file loaded at startup.
- `.env` MUST be in `.gitignore` — never committed.
- Documentation MUST include a `.env.example` listing every
  required variable with placeholder values.
- No hardcoded URLs for production services; use env vars for all
  external endpoints.

### VI. Structured Observability

Every operation MUST produce structured, machine-parseable logs.
No `print()` statements in production code.

- Use Python `logging` with JSON-structured output.
- Every `@function_tool` invocation MUST log: tool name, input
  summary, outcome (success/failure), and duration.
- The `log_metric` tool MUST record response time, sentiment
  score, channel, and resolution type for every interaction.
- Error logs MUST include correlation IDs traceable to the
  originating request.

### VII. Graceful Degradation & Escalation

Every tool MUST handle errors with graceful fallbacks. The system
MUST never silently drop a customer request.

- If a tool raises an unrecoverable error, the agent MUST call
  `escalate_to_human` with the failure reason.
- A ticket MUST always be created before responding
  (`create_ticket` before `send_response`).
- Sentiment MUST always be checked before closing a ticket
  (sentiment < 0.3 triggers escalation).
- If the knowledge base returns no results, the agent MUST
  acknowledge the gap and escalate rather than fabricate an answer.

## Technology Stack & Constraints

| Layer              | Technology                                   |
|--------------------|----------------------------------------------|
| Frontend           | Next.js (Web Support Form only)              |
| API                | FastAPI (Python 3.12+)                        |
| Agent Runtime      | OpenAI Agents SDK (`@function_tool`)          |
| Database / CRM     | PostgreSQL 16 + pgvector (Neon)               |
| Validation         | Pydantic BaseModel for all request/response   |
| Email Channel      | Gmail API (MCP tool — not through REST API)   |
| WhatsApp Channel   | WhatsApp MCP tool (not through REST API)      |
| Web Form Channel   | Next.js → FastAPI REST endpoints              |
| Containerisation   | Docker + docker-compose for local dev         |

### REST API Surface (FastAPI)

- `POST /support/submit` — web form submissions
- `GET /support/ticket/{id}` — ticket status lookup
- `GET /health` — health check
- `GET /metrics/channels` — channel metrics

### Agent Tool Inventory

| Category            | Tool                         | Purpose                                        |
|---------------------|------------------------------|------------------------------------------------|
| Customer Management | `find_or_create_customer`    | Lookup/create customer, merge cross-channel IDs |
| Customer Management | `get_customer_history`       | Fetch all past conversations across channels    |
| Ticket Lifecycle    | `create_ticket`              | Log new interaction with channel/category/priority |
| Ticket Lifecycle    | `update_ticket`              | Change status, add resolution notes             |
| Ticket Lifecycle    | `get_ticket`                 | Fetch ticket details and thread                 |
| Knowledge Base      | `search_knowledge_base`      | Semantic search (pgvector) on product docs      |
| Conversation        | `save_message`               | Store message with channel metadata, sentiment  |
| Conversation        | `get_conversation_messages`  | Load conversation history for context           |
| Escalation          | `escalate_to_human`          | Mark ticket escalated, notify human queue       |
| Response            | `send_response`              | Reply via correct channel (WhatsApp/Gmail/Web)  |
| Metrics             | `log_metric`                 | Record response time, sentiment, resolution     |

### Constraints

- Web Form is the required channel; Gmail and WhatsApp are
  stretch goals with documented limitations acceptable.
- No external CRM integrations permitted.
- Agent MUST NOT discuss competitor products.
- Agent MUST NOT promise features not present in knowledge base.
- Performance targets: P95 latency < 3 s, escalation rate < 25%,
  cross-channel identification > 95%.

## Development Workflow

### Stage Context

This project starts from **Stage 2 (Specialization)**. The
incubation/prototyping phase is complete. All work follows the
production architecture:

```
Next.js Web Form → FastAPI (REST API) → OpenAI Agents SDK → PostgreSQL (Neon)
                                               ↓
                                     @function_tool functions
                                     (DB queries, MCP calls)
```

### Build Order

1. **Schema first** — PostgreSQL schema with all tables and
   pgvector indexes.
2. **Tools second** — `@function_tool` functions, each backed by
   async PostgreSQL queries.
3. **Agent third** — OpenAI Agents SDK agent wired to tools with
   production system prompt.
4. **API fourth** — FastAPI endpoints calling the agent.
5. **Channels fifth** — Web Form (required), then Gmail/WhatsApp.

### Code Quality Gates

- All input validation via Pydantic BaseModel.
- Structured logging only (no `print()`).
- `async`/`await` for all I/O.
- Error handling with graceful fallbacks on every tool.
- Environment variables for all config — no hardcoded secrets.
- Commits after each logical unit of work.

### Testing Strategy

- `pytest` for all test suites.
- Contract tests for API endpoints.
- Integration tests for agent tool → database round-trips.
- E2E tests for multi-channel message flows.

## Governance

This constitution is the highest-authority document for the CRM
Digital FTE Factory project. It supersedes all other practices
and ad-hoc decisions.

- **Amendments** require explicit documentation of the change,
  rationale, and impact on existing code. Version MUST be bumped
  per semantic versioning rules below.
- **Version bumps**: MAJOR for principle removals or redefinitions;
  MINOR for new principles or material expansions; PATCH for
  wording clarifications.
- **Compliance**: Every PR and code review MUST verify adherence
  to these principles. Violations MUST be justified in writing
  (see Complexity Tracking in plan template).
- **Runtime guidance**: See `CLAUDE.md` for day-to-day development
  conventions and commands.

**Version**: 1.0.0 | **Ratified**: 2026-02-22 | **Last Amended**: 2026-02-22
