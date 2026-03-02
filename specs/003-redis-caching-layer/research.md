# Research: Redis Caching Layer

## Decision 1: Redis Client Library

**Decision**: `redis[hiredis]` (redis-py with hiredis C parser)

**Rationale**: The official Redis Python client (`redis-py` v5+) includes `redis.asyncio` module natively — no separate `aioredis` package needed. The `hiredis` extra provides a C-based response parser for ~10x faster deserialization. Version 5.0+ is mature, well-documented, and the standard choice for async Python + Redis.

**Alternatives considered**:
- `aioredis` — Merged into redis-py v4.2+; the standalone package is deprecated
- `coredis` — Less popular, smaller community, unnecessary for our use case
- `valkey-py` — Redis fork client; premature to adopt given Redis stability

## Decision 2: Test Strategy for Redis

**Decision**: `fakeredis[json]` — in-memory Redis implementation for testing

**Rationale**: fakeredis provides a full in-memory Redis server that behaves identically to real Redis. Tests run without Docker or a real Redis instance, keeping the CI pipeline simple. The `[json]` extra adds JSON module support. Used by major projects (celery, django-redis) for testing.

**Alternatives considered**:
- Mocking redis.asyncio.Redis — Fragile, requires mocking every method individually
- testcontainers-redis — Requires Docker in CI, adds test complexity and startup time
- Real Redis in CI — Infrastructure dependency, slower tests, flaky network issues

## Decision 3: Cache Key Strategy

**Decision**: Namespaced keys with `crm:` prefix and semantic segments

**Rationale**: Key naming convention `crm:{domain}:{identifier}` prevents collisions if Redis is shared, is human-readable for debugging, and supports pattern-based invalidation via `SCAN`. KB search keys use SHA-256 hash of normalized query (case-insensitive, trimmed) to keep key length bounded regardless of query content.

**Key patterns**:
- `crm:kb:search:{sha256_hash[:16]}` — KB search results
- `crm:channel_config:{channel}` — Channel configurations
- `crm:customer:lookup:{type}:{value}` — Customer identifier lookups

**Alternatives considered**:
- UUID-based keys — Not human-readable, harder to debug
- Raw query as key — Unbounded key length, case sensitivity issues
- MD5 hash — SHA-256 preferred for collision resistance (even though security isn't the concern)

## Decision 4: Cache Invalidation Strategy

**Decision**: TTL-based expiration with explicit invalidation on writes

**Rationale**: TTL handles the common case (data naturally expires). Explicit invalidation handles the critical case (customer cross-channel linking must immediately reflect). No event bus or pub/sub needed — direct `DELETE` calls in the write path are sufficient for a single-instance deployment.

**TTL values**:
- KB search results: 3600s (1 hour) — articles change rarely
- Channel config: 86400s (24 hours) — essentially static
- Customer lookup: 3600s (1 hour) — identifiers change rarely

**Alternatives considered**:
- Redis pub/sub for invalidation — Over-engineered for single-instance; useful only for multi-instance deployments
- Write-behind cache — Adds complexity with delayed consistency; not needed when writes are infrequent
- No TTL (infinite cache) — Risk of stale data with no automatic recovery

## Decision 5: Graceful Fallback Design

**Decision**: Every cache function accepts `redis_client: Redis | None` and no-ops when `None`

**Rationale**: This is the simplest possible fallback design. If Redis fails at startup, `create_redis_client()` returns `None`. All cache functions check for `None` first and immediately return `None` (for reads) or silently skip (for writes). No try/except needed at call sites — the cache module absorbs all failures internally.

**Alternatives considered**:
- Circuit breaker pattern — Over-engineered for v1; Redis failures are already handled by timeout + fallback
- Retry with exponential backoff — Adds latency on failure; better to just skip cache and hit DB
- Feature flag to disable caching — Unnecessary when `None` client achieves the same effect automatically

## Decision 6: Connection Configuration

**Decision**: `REDIS_URL` environment variable with `redis://localhost:6379` default

**Rationale**: Follows the project's convention (similar to `DATABASE_URL`). The URL format supports auth, TLS, and database selection for production: `rediss://user:pass@host:6379/0`. Local development uses the default with no configuration needed.

**Connection parameters**:
- `decode_responses=True` — Return strings, not bytes (matches JSON workflow)
- `socket_connect_timeout=5` — Fail fast on startup if Redis unreachable
- `socket_timeout=5` — Bound per-operation latency
- `retry_on_timeout=True` — Auto-retry transient timeouts
