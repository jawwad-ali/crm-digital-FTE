# Research: Customer Success Agent

**Feature Branch**: `001-customer-success-agent`
**Date**: 2026-02-22

## Decision 1: Agent Framework — OpenAI Agents SDK

**Decision**: Use `openai-agents` (PyPI) with `agents` import namespace.

**Rationale**: This is the SDK specified in the hackathon requirements. It provides `@function_tool` decorator, `Agent` class with system prompt (`instructions`), `Runner.run()` for async execution, and `RunContextWrapper` for injecting shared state (like a DB pool) into tools without exposing it to the LLM.

**Alternatives considered**:
- LangChain/LangGraph — heavier dependency, more abstraction layers than needed
- Raw OpenAI API with function calling — no agent loop, would need manual tool dispatch
- CrewAI — multi-agent focused, overkill for single-agent use case

**Key patterns**:
- `@function_tool` on async functions with typed parameters
- `RunContextWrapper[AppContext]` as first param injects context (DB pool, config) — NOT sent to LLM
- `Runner.run(agent, input, context=ctx)` for async execution
- `Agent(name=, instructions=, tools=[], model=)` for definition
- Pydantic `Field` or `Annotated` for tool parameter validation

## Decision 2: Async Database Driver — asyncpg

**Decision**: Use `asyncpg` with connection pooling via `asyncpg.create_pool()`.

**Rationale**: asyncpg is the fastest async PostgreSQL driver for Python. It supports parameterized queries natively (using `$1, $2` syntax), connection pooling, and custom type codecs needed for pgvector.

**Alternatives considered**:
- psycopg3 (async mode) — newer, good alternative, but asyncpg has better performance benchmarks
- SQLAlchemy async — adds ORM overhead we don't need; our tools run raw SQL
- databases library — thin wrapper, less control over pool management

**Key patterns**:
- `pool = await asyncpg.create_pool(dsn, min_size=5, max_size=20)`
- `async with pool.acquire() as conn:` for connection checkout
- `await conn.fetch("SELECT ... WHERE embedding <=> $1 < $2", vector, threshold)` for pgvector queries
- Register pgvector codec: `await conn.set_type_codec('vector', encoder=..., decoder=..., schema='public')`

## Decision 3: pgvector Integration

**Decision**: Use pgvector extension with IVFFlat index for cosine similarity search.

**Rationale**: IVFFlat is the recommended index type for datasets under 1M rows. HNSW is faster for recall but uses more memory and is slower to build. With 15-100 KB articles, IVFFlat is sufficient.

**Alternatives considered**:
- HNSW index — better recall at scale, but overkill for <1000 articles
- No index (brute force) — acceptable for <100 articles, but adding IVFFlat costs nothing and future-proofs
- External vector DB (Pinecone, Weaviate) — violates "PostgreSQL IS the CRM" constitution principle

**Key patterns**:
- `CREATE EXTENSION IF NOT EXISTS vector;`
- Column: `embedding vector(1536)` for OpenAI text-embedding-3-small
- Index: `CREATE INDEX ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);`
- Query: `SELECT *, 1 - (embedding <=> $1) AS similarity FROM knowledge_base WHERE 1 - (embedding <=> $1) >= 0.7 ORDER BY embedding <=> $1 LIMIT 3;`

## Decision 4: Embedding Generation

**Decision**: Use OpenAI `text-embedding-3-small` (1536 dimensions) via the `openai` Python client.

**Rationale**: Same provider as the Agents SDK, simplifies API key management. text-embedding-3-small balances cost and quality for a support knowledge base. Seed data embeddings are pre-computed at migration time; live query embeddings are generated on-the-fly during `search_knowledge_base`.

**Alternatives considered**:
- text-embedding-3-large (3072 dims) — better quality but doubles storage and index size
- text-embedding-ada-002 (1536 dims) — older model, similar cost, lower quality
- Local model (sentence-transformers) — avoids API dependency but adds GPU/CPU requirements

## Decision 5: Shared Context Pattern

**Decision**: Use a `@dataclass` context object injected via `RunContextWrapper` to share the DB pool and config across all tools.

**Rationale**: The OpenAI Agents SDK supports typed context injection. A single `AppContext` dataclass holding the asyncpg pool and OpenAI client avoids global state and enables testing with mock contexts.

**Pattern**:
```python
@dataclass
class AgentContext:
    db_pool: asyncpg.Pool
    openai_client: AsyncOpenAI

agent = Agent[AgentContext](name="...", instructions="...", tools=[...])
result = await Runner.run(agent, input, context=ctx)
```

## Decision 6: Project Structure

**Decision**: Single-project layout with `agent/`, `database/`, `api/` top-level directories.

**Rationale**: This feature covers schema + agent + tools. The API layer (FastAPI) is a future feature but we lay out the directory now. No frontend code in this feature.

```
agent/
├── __init__.py
├── customer_success_agent.py   # Agent definition + system prompt
├── tools/                      # All @function_tool functions
│   ├── __init__.py
│   ├── customer.py             # find_or_create_customer, get_customer_history
│   ├── ticket.py               # create_ticket, update_ticket, get_ticket
│   ├── knowledge.py            # search_knowledge_base
│   ├── conversation.py         # save_message, get_conversation_messages
│   ├── escalation.py           # escalate_to_human
│   ├── response.py             # send_response
│   └── metrics.py              # log_metric
├── prompts.py                  # System prompt text
└── context.py                  # AgentContext dataclass

database/
├── schema.sql                  # Full schema (reference)
├── migrations/
│   ├── 001_initial_schema.sql
│   └── 002_seed_knowledge_base.sql
├── pool.py                     # asyncpg pool setup + pgvector codec
└── queries.py                  # Shared query helpers (optional)

tests/
├── conftest.py                 # Fixtures: test DB, pool, agent context
├── test_tools/
│   ├── test_customer.py
│   ├── test_ticket.py
│   ├── test_knowledge.py
│   ├── test_conversation.py
│   ├── test_escalation.py
│   └── test_metrics.py
└── test_agent.py               # End-to-end agent tests
```
