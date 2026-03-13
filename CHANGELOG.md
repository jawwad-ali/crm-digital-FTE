# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Kubernetes namespace, ConfigMap, and Secret manifests
- Health probes: `/health/live` (liveness) and `/health/ready` (readiness)
- Docker Compose for one-command local startup (API + Frontend + PostgreSQL + Redis)
- Multi-stage Dockerfiles for API and web frontend
- `.dockerignore` files for optimized builds

## [0.1.0] - 2026-03-10

### Added

#### AI Agent (OpenAI Agents SDK)
- Customer success agent with system prompt and 9 function tools
- `find_or_create_customer` — automatic customer identification from email/phone
- `create_ticket` / `update_ticket` / `get_ticket` — structured ticket lifecycle with sentiment tracking
- `search_knowledge_base` — semantic search using OpenAI embeddings + pgvector cosine similarity
- `send_response` — channel-aware responses (formal for Gmail, conversational for WhatsApp)
- `save_message` / `get_conversation_messages` — multi-turn conversation threading
- `escalation` — auto-escalates refund requests, low-sentiment, and no-match queries
- `metrics` — interaction metrics logging

#### FastAPI Backend
- `POST /api/chat` — submit support message (202 async with job polling / 200 sync fallback)
- `GET /api/jobs/{job_id}` — poll for async job result
- `POST /api/webhooks/gmail` — Gmail inbound webhook
- `POST /api/webhooks/whatsapp` — WhatsApp inbound webhook
- `GET /api/tickets/{id}` — get ticket details
- `GET /api/customers/{id}/history` — get customer history
- `GET /health` — health check endpoint
- Pydantic request/response models with full input validation

#### Redis Caching Layer
- KB search result caching (1h TTL) — saves OpenAI embedding + pgvector queries
- Channel config caching (24h TTL) — static channel style/length config
- Customer lookup caching (1h TTL) — email/phone to customer_id mapping
- Job store for async background tasks (1h TTL, 5-min processing timeout)
- All cache functions handle `None` Redis client gracefully (no-op fallback)

#### Next.js Frontend
- Support form with real-time status polling and conversation threading
- Follow-up conversation mode with `CustomerHeader`
- Input validation with character counter, email format checks, 10-second cooldown
- Embeddable widget via `/embed` endpoint
- WCAG 2.1 AA accessible — axe-core audited, keyboard navigable, screen reader compatible
- Responsive design (320px–1920px)

#### Database
- PostgreSQL schema: customers, identifiers, messages, tickets, conversations, knowledge_base, channel_config
- pgvector extension for 1536-dimensional embeddings
- Seed script for knowledge base articles with pre-computed embeddings

#### Testing
- 177 backend tests (pytest + pytest-asyncio)
- 81 frontend tests (Vitest + React Testing Library + vitest-axe)
- `fakeredis` for Redis mocking, `AsyncMock` for DB and OpenAI
- GitHub Actions CI pipeline (backend + frontend)

#### Documentation
- README with architecture diagram, features, tech stack, getting started guide
- CONTRIBUTING.md with development setup and PR process
- CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- Full project specification (`docs/hackathon-spec.md`)
- Production scaling guide (`docs/scaling-notes.md`)
