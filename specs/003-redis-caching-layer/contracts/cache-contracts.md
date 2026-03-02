# Cache Utility API Contracts

## Module: `agent/cache.py`

### `create_redis_client(*, url: str | None = None) -> Redis | None`

Creates an async Redis connection. Returns `None` if connection fails.

**Parameters**:
- `url` — Redis connection URL. Falls back to `REDIS_URL` env var, then `redis://localhost:6379`

**Returns**: `redis.asyncio.Redis` on success, `None` on failure

**Behavior**:
- Calls `ping()` to verify connectivity
- Logs "Redis connected" on success
- Logs "Redis unavailable — caching disabled" on failure
- Never raises exceptions

---

### `get_cached(redis_client: Redis | None, key: str) -> dict | list | None`

Fetches a cached value by key.

**Parameters**:
- `redis_client` — Redis client or `None` (no-op)
- `key` — Cache key without prefix (prefix added internally)

**Returns**: Deserialized JSON object on hit, `None` on miss or failure

**Behavior**:
- Returns `None` immediately if `redis_client is None`
- Prepends `crm:` prefix to key
- Deserializes JSON string to dict/list
- Logs "Cache HIT" or "Cache MISS" at debug level
- Catches all exceptions, logs warning, returns `None`

---

### `set_cached(redis_client: Redis | None, key: str, value: dict | list, ttl: int) -> None`

Stores a value in cache with TTL.

**Parameters**:
- `redis_client` — Redis client or `None` (no-op)
- `key` — Cache key without prefix
- `value` — JSON-serializable dict or list
- `ttl` — Expiration in seconds

**Behavior**:
- No-ops if `redis_client is None`
- Serializes value via `json.dumps(value, default=str)`
- Uses Redis `SET` with `EX` parameter for TTL
- Logs "Cache SET" at debug level
- Catches all exceptions, logs warning, does not raise

---

### `invalidate(redis_client: Redis | None, *keys: str) -> None`

Deletes one or more cache keys.

**Parameters**:
- `redis_client` — Redis client or `None` (no-op)
- `*keys` — One or more cache keys without prefix

**Behavior**:
- No-ops if `redis_client is None`
- Prepends `crm:` prefix to each key
- Calls Redis `DELETE`
- Catches all exceptions, logs warning

---

### `invalidate_pattern(redis_client: Redis | None, pattern: str) -> None`

Deletes all keys matching a glob pattern. Uses `SCAN` (not `KEYS`) for production safety.

**Parameters**:
- `redis_client` — Redis client or `None` (no-op)
- `pattern` — Glob pattern without prefix (e.g., `kb:search:*`)

**Behavior**:
- No-ops if `redis_client is None`
- Uses cursor-based `SCAN` with `count=100` per batch
- Deletes matched keys in batches
- Catches all exceptions, logs warning

---

### Key Helper Functions

#### `make_kb_cache_key(query: str, top_k: int = 3) -> str`

Returns `kb:search:{sha256[:16]}` from normalized (lowercase, trimmed) query + top_k.

#### `make_channel_config_key(channel: str) -> str`

Returns `channel_config:{channel}`.

#### `make_customer_lookup_key(identifier_type: str, identifier_value: str) -> str`

Returns `customer:lookup:{identifier_type}:{identifier_value}`.

---

## TTL Constants

| Constant | Value | Used By |
|----------|-------|---------|
| `TTL_KB_SEARCH` | 3600 (1 hour) | KB search results |
| `TTL_CHANNEL_CONFIG` | 86400 (24 hours) | Channel configurations |
| `TTL_CUSTOMER_LOOKUP` | 3600 (1 hour) | Customer identifier lookups |
