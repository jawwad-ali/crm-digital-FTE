# Data Model: FastAPI Background Tasks

**Feature**: 004-fastapi-background-tasks
**Date**: 2026-03-04

## Overview

No new database tables. Job state is ephemeral and stored in Redis only.

## Entities

### Job (Redis — ephemeral)

Represents a background processing request. Stored as a JSON string in Redis.

**Key pattern**: `crm:job:{correlation_id}`
**TTL**: 3600 seconds (1 hour)
**Timeout threshold**: 300 seconds (5 minutes) — jobs still "processing" after this are treated as "failed" at read time

| Field | Type | Description |
|-------|------|-------------|
| `status` | string (enum) | `processing`, `completed`, `failed` |
| `response` | string \| null | Agent's final text response (populated on completion) |
| `error` | string \| null | Error message (populated on failure or timeout) |
| `created_at` | ISO-8601 string | Timestamp when job was created |

**State transitions**:

```
[created] → processing → completed
                       → failed (error during processing)
                       → failed (timeout — 5 min expiry, detected at read time)
```

**Notes**:
- `processing → completed` and `processing → failed` are the only valid transitions
- Timeout is not written to Redis — it's computed when the status endpoint reads a "processing" job and compares `created_at` against the current time
- TTL applies to all states — completed and failed results are cleaned up after 1 hour regardless

## Existing Entities (unchanged)

No modifications to PostgreSQL schema. All existing tables (`customers`, `tickets`, `conversations`, `messages`, `channel_configs`, `knowledge_base_articles`, `agent_metrics`) remain unchanged.

## Pydantic Models

### Request Models

**ChatRequest** (modified — add `sync` query param):
```
ChatRequest:
  message: str (required)
  email: str (required)
  channel: str (default: "web")
  name: str | None (default: None)
```

### Response Models

**JobAccepted** (new — HTTP 202):
```
JobAccepted:
  job_id: str
  status: str = "processing"
  retry_after: int = 5
```

**JobStatus** (new — polling response):
```
JobStatus:
  job_id: str
  status: str  # "processing" | "completed" | "failed"
  response: str | None  # present when completed
  error: str | None  # present when failed
  retry_after: int | None  # present when processing (5 seconds)
```

**ChatResponse** (unchanged — used in sync mode):
```
ChatResponse:
  response: str
  correlation_id: str
```
