# Data Model: Redis Caching Layer

## Entities

### Cache Entry

A key-value pair stored in Redis with a time-to-live (TTL).

| Attribute | Type | Description |
|-----------|------|-------------|
| key | string | Namespaced key (e.g., `crm:kb:search:{hash}`) |
| value | JSON string | Serialized tool result matching original return format |
| ttl | integer (seconds) | Time until automatic expiration |

**No new database tables.** Redis is the only new storage. PostgreSQL schema is unchanged.

### Cache Key Patterns

| Domain | Key Pattern | Value Shape | TTL |
|--------|------------|-------------|-----|
| KB Search | `crm:kb:search:{sha256[:16]}` | `{"status": "found\|no_match", "message": "...", "articles": [...]}` | 3600s |
| Channel Config | `crm:channel_config:{channel}` | `{"max_length": int, "response_style": "..."}` | 86400s |
| Customer Lookup | `crm:customer:lookup:{type}:{value}` | `{"customer_id": "uuid", "instruction": "...", "is_new": bool, "identifiers": [...]}` | 3600s |

### Cache Client

Added to the existing `AgentContext` dataclass.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| db_pool | asyncpg.Pool | (required) | Existing — database connection pool |
| openai_client | AsyncOpenAI | (required) | Existing — OpenAI API client |
| redis_client | redis.asyncio.Redis \| None | None | **New** — Redis cache client, None when unavailable |

### Invalidation Rules

| Trigger | Keys Invalidated | Method |
|---------|-----------------|--------|
| Customer cross-channel link | `crm:customer:lookup:{new_type}:{new_value}` | Explicit DELETE after write |
| KB article update (manual) | `crm:kb:search:*` | Pattern-based SCAN + DELETE |
| TTL expiration | (automatic) | Redis handles internally |
