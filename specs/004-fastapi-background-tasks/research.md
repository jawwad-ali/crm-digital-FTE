# Research: FastAPI Background Tasks

**Feature**: 004-fastapi-background-tasks
**Date**: 2026-03-04

## R1: FastAPI BackgroundTasks — How It Works

**Decision**: Use FastAPI's built-in `BackgroundTasks` dependency for deferring agent work.

**Rationale**: BackgroundTasks runs tasks in the same async event loop (for `async def` tasks) or in a thread pool (for `def` tasks). Since `run_agent()` is already `async def`, it will share the event loop — no thread overhead, no external dependencies.

**How it works**:
```python
from fastapi import BackgroundTasks

@app.post("/api/chat", status_code=202)
async def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    job_id = set_correlation_id()
    await set_job(redis, job_id, {"status": "processing"})
    background_tasks.add_task(process_chat, job_id, req, app.state.agent_ctx)
    return {"job_id": job_id, "status": "processing"}
```

**Alternatives considered**:
- **Redis Streams + worker process**: Survives restarts, multi-server capable, but overkill for MVP. Adds a separate worker process to manage.
- **Celery**: Heavy dependency, requires message broker config, complex setup. Far beyond MVP needs.
- **asyncio.create_task()**: Lower-level, no integration with FastAPI's request lifecycle, harder to test.

## R2: Job State Storage in Redis

**Decision**: Store job state as JSON in Redis with a `crm:job:{correlation_id}` key and 1-hour TTL.

**Rationale**: Redis is already wired into `AgentContext` from feature 003. Job data is ephemeral (only needed until the client retrieves the result) — perfect for Redis with TTL-based auto-cleanup. No database schema changes needed.

**Job JSON structure**:
```json
{
  "status": "processing | completed | failed",
  "response": "Agent's final answer (when completed)",
  "error": "Error message (when failed)",
  "created_at": "2026-03-04T12:00:00Z"
}
```

**Key design**:
- Key: `crm:job:{correlation_id}` — uses existing `crm:` prefix convention
- TTL: 3600 seconds (1 hour) — applied at creation, reset on completion
- Timeout check: If `status == "processing"` and `created_at` is older than 5 minutes, the status endpoint returns "failed" with a timeout message

**Alternatives considered**:
- **PostgreSQL table**: Persistent but unnecessary — jobs are ephemeral. Would add a migration and ongoing storage growth.
- **In-memory dict**: Simplest but lost on restart with no TTL management. Redis already handles both.

## R3: Correlation ID as Job Tracking ID

**Decision**: Reuse the existing `set_correlation_id()` / `get_correlation_id()` mechanism as the job tracking ID.

**Rationale**: The correlation ID is already a UUID4 hex string generated per-request, propagated via `contextvars`, and included in all log entries. Using it as the job ID means:
- Zero new ID generation logic
- All logs for a background task are automatically traceable via the same ID
- The client receives the same ID they'd use for both polling and log correlation

**Alternatives considered**:
- **Separate job UUID**: Would require maintaining two IDs (correlation + job) and mapping between them. No benefit.

## R4: contextvars Propagation in BackgroundTasks

**Decision**: Manually set the correlation ID at the start of the background task function.

**Rationale**: FastAPI's `BackgroundTasks` copies the context from the calling coroutine, but `contextvars` behavior can be unreliable across task boundaries. To guarantee the correlation ID is available in all log messages within the background task, we explicitly call `set_correlation_id(job_id)` as the first line of the background processing function.

**Pattern**:
```python
async def _process_chat(job_id: str, req: ChatRequest, ctx: AgentContext):
    set_correlation_id(job_id)  # Ensure logs are tagged
    try:
        response = await run_agent(ctx, message)
        await set_job(redis, job_id, {"status": "completed", "response": response})
    except Exception as e:
        await set_job(redis, job_id, {"status": "failed", "error": str(e)})
```

## R5: Graceful Fallback When Redis Is Unavailable

**Decision**: If Redis is `None`, all endpoints fall back to synchronous behavior (equivalent to `?sync=true`).

**Rationale**: Background tasks require Redis to store results. Without Redis, there's nowhere to put the result for later polling. Falling back to sync mode means the system still works — just slower. This aligns with Constitution VII (Graceful Degradation).

**Logic**:
```python
if sync or ctx.redis_client is None:
    # Synchronous path — wait for result
    response = await run_agent(ctx, message)
    return ChatResponse(response=response, correlation_id=cid)
else:
    # Async path — background task
    background_tasks.add_task(...)
    return JobAccepted(job_id=cid, status="processing")
```

## R6: Test Strategy

**Decision**: Use fakeredis (already in dev dependencies) for job store tests. Use `httpx.AsyncClient` for endpoint integration tests.

**Rationale**: Existing test infrastructure is sufficient. No new test dependencies needed.

**Test categories**:
1. **Job store unit tests** (`test_cache.py`): `set_job`, `get_job`, TTL verification, timeout detection
2. **Endpoint integration tests** (`test_main.py`): 202 response, job polling, sync mode, error handling
3. **Background task tests** (`test_main.py`): Verify background function writes correct job state
