# CRM Digital FTE Factory

## Quick Reference

- **What:** 24/7 AI Customer Success agent handling Gmail, WhatsApp, and Web Form support
- **Full Spec:** [docs/hackathon-spec.md](docs/hackathon-spec.md) — all requirements, architecture, exercises, scoring, and deliverables live there. Read it before starting any work.

## Conventions

- Python 3.12+, async/await throughout
- Pydantic BaseModel for all input validation
- Structured logging (no print statements)
- Environment variables for all config (no hardcoded secrets)
- All tools must have error handling with graceful fallbacks
- PostgreSQL IS the CRM — no external CRM integration needed

## Commands

- `docker compose up` — start local dev environment
- `pytest tests/` — run test suite
- `uvicorn api.main:app --reload` — run FastAPI dev server
