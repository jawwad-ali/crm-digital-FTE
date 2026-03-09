![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)
![Next.js 16](https://img.shields.io/badge/Next.js-16-000000.svg?logo=next.js&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI_Agents_SDK-0.0.16+-412991.svg?logo=openai&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1.svg?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-caching-DC382D.svg?logo=redis&logoColor=white)
![Tests](https://img.shields.io/badge/tests-258%20passing-brightgreen.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

# CRM Digital FTE — AI Customer Success Agent

> A 24/7 **AI customer support agent** that handles **Gmail**, **WhatsApp**, and **Web Form** inquiries using the **OpenAI Agents SDK**, **FastAPI**, **PostgreSQL + pgvector** for semantic search, **Redis** for caching and async job management, and a **Next.js** web interface — all in one monorepo.

---

## What is this?

CRM Digital FTE is a full-stack **AI-powered customer success platform** that automates multi-channel support. When a customer sends a message through the web form, Gmail, or WhatsApp, the AI agent:

1. **Identifies the customer** — finds or creates a customer record
2. **Creates a support ticket** — categorizes and prioritizes automatically
3. **Searches the knowledge base** — uses OpenAI embeddings + pgvector cosine similarity for semantic search
4. **Responds intelligently** — adapts tone per channel (formal for email, conversational for WhatsApp)
5. **Escalates when needed** — routes to humans for out-of-scope requests or low-sentiment interactions

The system processes requests **asynchronously** via background tasks with Redis job polling, falling back to synchronous mode gracefully when Redis is unavailable.

<p align="center">
  <img src="image.png" alt="Support Center Landing Page" width="700">
</p>

---

## Architecture

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Web Form   │   │    Gmail    │   │  WhatsApp   │
│  (Next.js)  │   │  (Webhook)  │   │  (Webhook)  │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │
       └────────────┬────┴────┬────────────┘
                    ▼         ▼
              ┌──────────────────┐
              │   FastAPI Layer  │  POST /api/chat → 202 + job_id
              │   (api/main.py)  │  GET  /api/jobs/{id} → result
              └────────┬─────────┘
                       │
              ┌────────▼─────────┐
              │  Background Task │  Redis job store
              │  (async runner)  │  5-min timeout
              └────────┬─────────┘
                       │
              ┌────────▼─────────┐
              │  AI Agent Engine │  OpenAI Agents SDK
              │  (agent/)        │  System prompt + tools
              └────────┬─────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌───────────┐ ┌───────────┐
│  PostgreSQL  │ │   Redis   │ │  OpenAI   │
│  + pgvector  │ │  (cache)  │ │   API     │
│  (CRM + KB)  │ │           │ │           │
└──────────────┘ └───────────┘ └───────────┘
```

---

## Features

- **Multi-Channel Support** — unified agent handles Web, Gmail, and WhatsApp through a single pipeline
- **Semantic Knowledge Base Search** — OpenAI `text-embedding-3-small` + pgvector cosine similarity finds relevant articles
- **Async Background Processing** — HTTP 202 + job polling pattern with Redis, graceful sync fallback
- **Redis Caching Layer** — caches KB search results (1h), channel configs (24h), customer lookups (1h)
- **Smart Escalation** — auto-escalates refund requests, low-sentiment interactions, and no-match queries to humans
- **Conversation Threading** — multi-turn follow-up support with conversation history
- **WCAG 2.1 AA Accessible** — axe-core audited, keyboard navigable, screen reader compatible
- **Responsive Web Form** — mobile-first design (320px–1920px), embeddable widget via `/embed`
- **Input Validation** — real-time character counter, email format checks, 10-second cooldown throttle
- **Structured Ticket Lifecycle** — open → in_progress → resolved/escalated, with sentiment tracking
- **Channel-Aware Responses** — formal for Gmail, semi-formal for Web, conversational for WhatsApp
- **258 Automated Tests** — 177 backend (pytest) + 81 frontend (Vitest + React Testing Library)

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **AI Agent** | [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) | Agent orchestration, function tools, guardrails |
| **LLM** | GPT-4o | Reasoning and response generation |
| **Embeddings** | text-embedding-3-small | Semantic search vectors (1536 dimensions) |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/) | Async HTTP layer, Pydantic validation |
| **Database** | [PostgreSQL](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector) | CRM data + vector similarity search |
| **Cache** | [Redis](https://redis.io/) | Job store, KB cache, config cache |
| **Frontend** | [Next.js 16](https://nextjs.org/) + React 19 | Web support form with App Router |
| **Styling** | [Tailwind CSS v4](https://tailwindcss.com/) | Utility-first responsive design |
| **Testing** | pytest + Vitest + React Testing Library | Full-stack test coverage |
| **Language** | Python 3.12 / TypeScript | Async/await throughout |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 16+ with [pgvector extension](https://github.com/pgvector/pgvector)
- Redis 7+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/jawwad-ali/crm-digital-FTE.git
cd crm-digital-FTE

# Set up Python environment
uv venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows
uv pip install -e ".[dev]"

# Set up the web frontend
cd web && npm install && cd ..

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL, OPENAI_API_KEY, REDIS_URL

# Initialize the database
psql $DATABASE_URL < database/migrations/001_initial_schema.sql
python -m database.migrations.002_seed_knowledge_base

# Start Redis
redis-server                     # Linux/Mac
# wsl sudo service redis-server start  # Windows

# Start the backend
uvicorn api.main:app --reload

# Start the frontend (new terminal)
cd web && npm run dev
```

Open `http://localhost:3000` — the support form is ready.

---

## Project Structure

```
crm-digital-FTE/
├── agent/                    # AI agent engine
│   ├── customer_success_agent.py   # Agent definition + runner
│   ├── prompts.py                  # System prompt
│   ├── context.py                  # AgentContext (DB + OpenAI + Redis)
│   ├── cache.py                    # Redis caching + job store
│   └── tools/                      # Function tools
│       ├── customer.py             #   find/create/link customers
│       ├── ticket.py               #   create/update/get tickets
│       ├── conversation.py         #   save/get messages
│       ├── knowledge.py            #   semantic KB search
│       └── response.py             #   channel-aware responses
├── api/
│   └── main.py               # FastAPI endpoints, background tasks
├── web/                       # Next.js 16 frontend
│   └── src/
│       ├── app/               # App Router pages
│       ├── components/        # React components
│       ├── hooks/             # Custom hooks (polling, cooldown, etc.)
│       └── lib/               # API client, types
├── database/
│   └── migrations/            # Schema + KB seed data
├── tests/                     # 177 backend tests
├── specs/                     # Feature specifications (001–005)
└── docs/                      # Architecture docs
```

---

## Testing

```bash
# Run all backend tests (177 tests)
pytest tests/ -v

# Run all frontend tests (81 tests)
cd web && npm test

# Run with coverage
pytest tests/ --cov=agent --cov=api
```

All tests use mocks (no real database, Redis, or OpenAI calls required):
- **Backend**: `fakeredis`, `AsyncMock` for DB pool and OpenAI client
- **Frontend**: `vi.fn()` mocked `fetch`, `vitest-axe` for accessibility audits

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Submit a support message (202 async / 200 sync) |
| `GET` | `/api/jobs/{job_id}` | Poll for async job result |
| `POST` | `/api/webhooks/gmail` | Gmail inbound webhook |
| `POST` | `/api/webhooks/whatsapp` | WhatsApp inbound webhook |
| `GET` | `/api/tickets/{id}` | Get ticket details |
| `GET` | `/api/customers/{id}/history` | Get customer history |
| `GET` | `/health` | Health check |

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style guidelines, and the PR process.

If this project helps you, consider giving it a star — it helps others discover it too.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
