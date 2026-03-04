# Quickstart: FastAPI Background Tasks

**Feature**: 004-fastapi-background-tasks
**Date**: 2026-03-04

## Prerequisites

- Python 3.12+ with `.venv` activated
- PostgreSQL running with schema migrated
- Redis running (WSL: `wsl sudo service redis-server start`)
- `.env` with `DATABASE_URL`, `OPENAI_API_KEY`, `REDIS_URL`

## Start the Server

```bash
uvicorn api.main:app --reload
```

## Test Async Flow (Default)

### 1. Submit a chat request

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "message": "How do I reset my password?"}'
```

**Expected**: HTTP 202 — instant response (~1 second):

```json
{
  "job_id": "a65c5987...",
  "status": "processing",
  "retry_after": 5
}
```

### 2. Poll for result

Wait 5 seconds, then:

```bash
curl http://localhost:8000/api/jobs/a65c5987...
```

**Expected** (if still processing):

```json
{
  "job_id": "a65c5987...",
  "status": "processing",
  "retry_after": 5
}
```

**Expected** (when done — after ~30 seconds):

```json
{
  "job_id": "a65c5987...",
  "status": "completed",
  "response": "To reset your password...",
  "retry_after": null
}
```

### 3. Verify server logs

Look for these log entries:

```
{"level": "INFO", "msg": "Job a65c5987... started — background processing"}
{"level": "INFO", "msg": "Job a65c5987... completed — response stored"}
```

## Test Sync Mode (Escape Hatch)

```bash
curl -X POST "http://localhost:8000/api/chat?sync=true" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "message": "How do I reset my password?"}'
```

**Expected**: HTTP 200 — blocks until agent finishes (~30-40 seconds):

```json
{
  "response": "To reset your password...",
  "correlation_id": "b72d1234..."
}
```

## Test Graceful Fallback (No Redis)

1. Stop Redis: `wsl sudo service redis-server stop`
2. Restart the server (will log "Redis unavailable — caching disabled")
3. Send a chat request — should automatically fall back to synchronous behavior
4. Restart Redis: `wsl sudo service redis-server start`

## Run Tests

```bash
pytest tests/ -v
```

All existing tests should pass, plus new tests for:
- HTTP 202 responses from chat/webhook endpoints
- Job polling (processing → completed → expired)
- Sync mode (`?sync=true`)
- Background task error handling
- Timeout-based expiry for stuck jobs
