# Feature Specification: Redis Caching Layer

**Feature Branch**: `003-redis-caching-layer`
**Created**: 2026-03-01
**Status**: Draft
**Depends On**: `001-customer-success-agent` (complete), `002-fastapi-backend` (complete)
**Input**: User description: "Add a Redis caching layer to the CRM Digital FTE project that caches frequently accessed, rarely changing data to eliminate redundant OpenAI API calls and database queries. The caching targets three hot paths: (1) Knowledge base search results — cache the full search result keyed by normalized query hash, TTL 1 hour; (2) Channel configuration — cache the 3 static channel configs, TTL 24 hours; (3) Customer identifier lookup — cache the email/phone-to-customer_id mapping for returning customers, TTL 1 hour, with write-through invalidation on new customer creation or cross-channel linking. Graceful fallback to database when Redis is unavailable."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Faster Repeated Questions (Priority: P1)

A customer asks a common question like "How do I reset my password?" The system answers using a cached knowledge base result instead of re-computing the embedding and running a vector search. The customer receives the same accurate answer but noticeably faster, and the system avoids a costly external API call.

**Why this priority**: Knowledge base search is the most expensive operation per request — it requires an external embedding API call plus a database vector search. Caching this path delivers the highest cost savings and latency reduction. Most customers ask the same 10-15 common questions.

**Independent Test**: Send the same question to the chat endpoint twice. The first request performs the full search. The second request returns the same result from cache without calling the embedding API or database.

**Acceptance Scenarios**:

1. **Given** a customer asks a question for the first time, **When** the knowledge base is searched, **Then** the result is stored in cache with a 1-hour expiration and the customer receives the answer.
2. **Given** the same question was asked within the last hour, **When** another customer asks it, **Then** the cached result is returned without calling the embedding API or running a database vector search.
3. **Given** a question was cached more than 1 hour ago, **When** a customer asks it again, **Then** the cache entry has expired and a fresh search is performed.
4. **Given** the cache is normalized (case-insensitive, whitespace-trimmed), **When** a customer asks "HOW DO I RESET MY PASSWORD?" and another asks "how do i reset my password?", **Then** both resolve to the same cache entry.

---

### User Story 2 - Graceful Operation Without Cache (Priority: P1)

The system starts and operates normally even when the cache service is unavailable. All features work identically to the pre-caching behavior — the cache is purely an optimization layer, never a hard dependency.

**Why this priority**: Equal to P1 because reliability is non-negotiable. A cache failure must never cause user-visible errors or system downtime. The system must degrade gracefully.

**Independent Test**: Stop the cache service, restart the application, and send a chat request. The request succeeds with the same response as before caching was introduced. Application logs indicate the cache is unavailable but no errors are raised.

**Acceptance Scenarios**:

1. **Given** the cache service is not running, **When** the application starts, **Then** it starts successfully with a log message indicating caching is disabled.
2. **Given** the cache service goes down while the application is running, **When** a request is processed, **Then** the request succeeds by falling back to the database and a warning is logged.
3. **Given** the cache service was unavailable and comes back online, **When** a new cache connection is attempted, **Then** caching resumes automatically on the next applicable request.
4. **Given** a cache read or write fails, **When** any tool function executes, **Then** the function completes normally using the database path — no exceptions propagate to the user.

---

### User Story 3 - Cached Channel Configuration (Priority: P2)

When the system formats a response for a specific channel (web, Gmail, WhatsApp), it retrieves the channel's formatting rules (max length, response style) from cache instead of querying the database. Since there are only 3 channel configurations and they almost never change, this is a simple and highly effective cache target.

**Why this priority**: Low implementation complexity with a 100% cache hit rate after warmup. Eliminates a database query on every response sent.

**Independent Test**: Send a chat request and verify the channel configuration is fetched from cache on subsequent requests. The database query for channel config should only execute once per channel per 24 hours.

**Acceptance Scenarios**:

1. **Given** a response is sent on the "web" channel for the first time, **When** the channel config is fetched, **Then** the config is cached with a 24-hour expiration.
2. **Given** the "web" channel config is already cached, **When** another response is sent on the "web" channel, **Then** the cached config is used without a database query.
3. **Given** all 3 channels have been used, **When** checking the cache, **Then** exactly 3 channel config entries exist.

---

### User Story 4 - Cached Customer Lookup (Priority: P2)

When a returning customer contacts support, their customer record is found in cache instead of querying the database. This speeds up the most frequent lookup operation since most support requests come from existing customers.

**Why this priority**: High cache hit rate for returning customers. Eliminates 2-3 database queries per returning customer interaction.

**Independent Test**: Send two chat requests with the same email address. The first creates/finds the customer via database. The second finds the customer from cache without a database query.

**Acceptance Scenarios**:

1. **Given** a customer contacts support for the first time, **When** their record is created, **Then** the result is cached with a 1-hour expiration keyed by their identifier (email or phone).
2. **Given** a returning customer's record is cached, **When** they contact support again, **Then** their record is returned from cache without a database query.
3. **Given** a customer links a new identifier (e.g., adds phone number to email account), **When** the link is created, **Then** the new identifier's cache entry is set and any stale entries are invalidated.
4. **Given** a customer's cache entry expired (older than 1 hour), **When** they contact support, **Then** a fresh database lookup is performed and the result is re-cached.

---

### Edge Cases

- What happens when the cache service becomes unavailable mid-request (between cache check and cache store)? The store silently fails and the request completes normally.
- What happens when cached data becomes stale after a knowledge base article is updated? The cached result serves stale data until TTL expiry (max 1 hour). An optional manual cache flush mechanism can clear all KB cache entries.
- What happens when the same query is asked simultaneously by multiple users and it's a cache miss? Multiple database queries may execute (no thundering herd protection in v1). The last write wins in the cache — all results are identical so this is safe.
- What happens when the cache stores corrupted or unparseable data? The cache read fails, logs a warning, and falls through to the database.
- What happens when the customer lookup cache returns a stale result (e.g., customer was deleted from database)? The downstream tool call (create_ticket) will fail with a clear error. The cache entry expires within 1 hour.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST cache knowledge base search results keyed by a deterministic hash of the normalized query string (case-insensitive, whitespace-trimmed) and the top_k parameter.
- **FR-002**: System MUST cache channel configuration lookups keyed by channel name (web, gmail, whatsapp).
- **FR-003**: System MUST cache customer identifier lookups keyed by identifier type and value (e.g., email:alice@example.com).
- **FR-004**: Cached knowledge base results MUST expire after 1 hour.
- **FR-005**: Cached channel configurations MUST expire after 24 hours.
- **FR-006**: Cached customer lookups MUST expire after 1 hour.
- **FR-007**: System MUST invalidate the customer lookup cache when a new identifier is linked to an existing customer (cross-channel linking).
- **FR-008**: System MUST fall back to database queries when the cache is unavailable, without raising exceptions or degrading functionality.
- **FR-009**: System MUST log cache hits, misses, and failures at appropriate log levels (debug for hits/misses, warning for failures).
- **FR-010**: System MUST connect to the cache service on application startup and disconnect on shutdown.
- **FR-011**: Cache service connection details MUST be configurable via environment variable, with a sensible default for local development.
- **FR-012**: All cache operations MUST be non-blocking (async) and MUST NOT increase request latency when the cache is unavailable (timeout-bounded).
- **FR-013**: System MUST cache both "found" and "no match" knowledge base results to prevent repeated lookups for queries with no matching articles.
- **FR-014**: System MUST provide a mechanism to manually flush all knowledge base cache entries (for use after KB article updates).
- **FR-015**: All existing functionality MUST continue to work identically when the cache service is not configured or unavailable.
- **FR-016**: Unit tests MUST NOT require a running cache service — tests MUST use an in-memory substitute.

### Key Entities

- **Cache Entry**: A key-value pair with a time-to-live (TTL). Key follows a namespaced convention (e.g., `kb:search:{hash}`, `channel_config:{name}`, `customer:lookup:{type}:{value}`). Value is a JSON-serialized object matching the original tool return format.
- **Cache Client**: A shared async connection to the cache service, created on application startup and injected into the agent context alongside the database pool and API client.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Repeated knowledge base questions (same query within 1 hour) are answered without calling the external embedding API, reducing per-request cost for cached queries to near zero.
- **SC-002**: The system starts and serves requests successfully when the cache service is not running, with zero user-visible errors.
- **SC-003**: Channel configuration lookups hit the cache after the first request per channel, reducing database queries by 1 per response sent.
- **SC-004**: Returning customer lookups hit the cache on subsequent interactions within 1 hour, eliminating 2-3 database queries per cached interaction.
- **SC-005**: All existing tests continue to pass without modification (cache defaults to disabled when not configured).
- **SC-006**: Cache-specific tests achieve full coverage of cache utility functions (get, set, invalidate, key generation, graceful failure).

## Assumptions

- Knowledge base articles are updated infrequently (less than once per hour). A 1-hour TTL for KB search results is acceptable.
- Channel configurations are essentially static. A 24-hour TTL is conservative.
- Customer identifiers change rarely (new accounts or cross-channel linking). A 1-hour TTL with explicit invalidation on linking is sufficient.
- The cache service runs locally during development on the default port (6379). Production deployments will configure the connection URL via environment variable.
- Thundering herd protection is not required for v1 — concurrent cache misses for the same query may result in duplicate database queries, which is acceptable given the low probability and identical results.
