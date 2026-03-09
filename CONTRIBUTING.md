# Contributing to CRM Digital FTE

Thank you for your interest in contributing! This guide will help you get set up and submit your first pull request.

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+ with [pgvector](https://github.com/pgvector/pgvector)
- Redis 7+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Installation

```bash
git clone https://github.com/jawwad-ali/crm-digital-FTE.git
cd crm-digital-FTE

# Python backend
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Next.js frontend
cd web && npm install && cd ..

# Environment
cp .env.example .env
# Fill in DATABASE_URL, OPENAI_API_KEY, REDIS_URL
```

### Running Tests

```bash
# Backend (177 tests — no real DB/Redis/OpenAI needed)
pytest tests/ -v

# Frontend (81 tests)
cd web && npm test
```

## Code Style

- **Python**: async/await throughout, Pydantic for validation, structured logging (no `print()`)
- **TypeScript**: React hooks, `'use client'` for interactive components
- **General**: no hardcoded secrets, environment variables for all config

## Finding Your First Contribution

Look for issues labeled [`good first issue`](https://github.com/jawwad-ali/crm-digital-FTE/labels/good%20first%20issue) — these are scoped, well-documented tasks ideal for new contributors.

## Branch Naming

Feature branches follow the pattern: `NNN-feature-name` (e.g., `005-web-support-form`).

## Pull Request Process

1. Fork the repo and create your branch from `main`
2. Write or update tests for your changes
3. Ensure all tests pass (`pytest tests/ -v` and `cd web && npm test`)
4. Submit a PR with a clear description of what changed and why

## Commit Messages

We use descriptive commit messages with emoji prefixes:

```
🚀 feat: New feature
🐛 fix:  Bug fix
✅ test: Tests
📝 docs: Documentation
♻️ refactor: Code refactoring
```

## Questions?

Open an [issue](https://github.com/jawwad-ali/crm-digital-FTE/issues) or start a discussion — we're happy to help.
