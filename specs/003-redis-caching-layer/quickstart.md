# Quickstart: Redis Caching Layer

## Prerequisites

- Python 3.12+ with venv activated
- PostgreSQL (Neon) running with existing schema from 001
- Redis 7+ running locally (optional — system works without it)

## 1. Install Redis Locally

```bash
# Docker (recommended)
docker run -d --name redis -p 6379:6379 redis:alpine

# Verify
docker exec redis redis-cli ping
# → PONG
```

## 2. Install Dependencies

```bash
uv pip install -e ".[dev]"
```

This installs `redis[hiredis]` (production) and `fakeredis[json]` (testing).

## 3. Configure Environment

Add to `.env`:

```
REDIS_URL=redis://localhost:6379
```

If omitted, defaults to `redis://localhost:6379`. If Redis is not running, the app starts normally with caching disabled.

## 4. Start the Server

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8001 --reload
```

Look for in logs:
```
Redis connected — localhost:6379
```

Or if Redis is not running:
```
Redis unavailable — caching disabled (falling back to DB)
```

## 5. Test Caching

Send the same question twice:

```bash
# First request — cache MISS (full agent workflow)
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I reset my password?", "email": "test@example.com", "channel": "web"}'

# Second request — cache HIT (no embedding API call)
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I reset my password?", "email": "test2@example.com", "channel": "web"}'
```

Check logs for `Cache HIT` / `Cache MISS` entries.

## 6. Run Tests

```bash
pytest tests/ -v
```

No running Redis required — tests use `fakeredis` (in-memory).

## 7. Verify Without Redis

```bash
# Stop Redis
docker stop redis

# Restart server — should see "Redis unavailable" in logs
# Send a request — should still work (falls back to DB)
```
