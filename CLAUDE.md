# CRM Digital FTE Factory

## Quick Reference

- **What:** 24/7 AI Customer Success agent handling Gmail, WhatsApp, and Web Form support
- **Full Spec:** [docs/hackathon-spec.md](docs/hackathon-spec.md) — all requirements, architecture, exercises, scoring, and deliverables live there. Read it before starting any work.

## Mandatory Skills

- **FastAPI**: When reading, reviewing, editing, or creating ANY `.py` file that involves FastAPI (routes, middleware, lifespan, dependencies, Pydantic request/response models, or anything under `api/`), you MUST load the `fastapi` skill BEFORE doing any work. This is NON-NEGOTIABLE — never write or modify FastAPI code without the skill loaded. Skill location: [`~/.claude/skills/fastapi/SKILL.md`](file:///C:/Users/Ali/.claude/skills/fastapi/SKILL.md)
- **OpenAI Agents SDK**: When reading, reviewing, editing, or creating ANY `.py` file that involves the OpenAI Agents SDK (`@function_tool`, `Agent`, `Runner`, `RunContextWrapper`, guardrails, handoffs, or anything under `agent/`), you MUST load the `openai-agents-sdk` skill BEFORE doing any work. This is NON-NEGOTIABLE — never write or modify agent code without the skill loaded. Skill location: [`~/.claude/skills/openai-agents-sdk/SKILL.md`](file:///C:/Users/Ali/.claude/skills/openai-agents-sdk/SKILL.md)
- **Multiple skills**: If a `.py` file involves BOTH FastAPI and OpenAI Agents SDK (e.g., `api/main.py` that defines endpoints and calls `run_agent`), you MUST load BOTH skills before doing any work. Skills are independent conditions — if a file matches multiple skills, load ALL of them.

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
