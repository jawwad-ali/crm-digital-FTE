# Scaling Notes

## Key Technologies

- **Redis** — An in-memory key-value store that holds frequently accessed data in RAM instead of querying the database. Returns results in under 1ms, making it ideal for caching shared data like KB articles and common search results that thousands of users request repeatedly.

- **PgBouncer** — A lightweight connection pooler that sits between your application and PostgreSQL. It funnels millions of incoming requests through a small pool of reusable database connections, with PostgreSQL supporting a maximum of approximately 500 concurrent connections. PgBouncer multiplexes requests across this limited pool, ensuring connections are efficiently recycled rather than exhausted.

- **Kafka** — A distributed message queue that decouples request acceptance from processing. Instead of making users wait while heavy operations complete, Kafka accepts the work instantly and lets background workers process it asynchronously, enabling near-instant API response times.

## When to Use What

Kafka is for async write/processing operations, not read. Here's the precise version:

- **Redis** — For massive reads of shared, rarely-changing data (KB articles, common answers). Avoids hitting the DB at all for repeated queries
- **Kafka** — For massive writes/processing (saving messages, running agent, creating tickets, logging metrics). Accepts the work instantly, processes it in the background so the user doesn't wait
- **Read Replicas + PgBouncer** — For massive reads of personal, dynamic data (chat history, ticket list). When 1M users load their own unique data, Redis can't help and Kafka isn't relevant. Replicas + connection pooling handle this

```
Shared static data    → Redis (cache)
Personal dynamic data → Read Replicas + PgBouncer (DB scaling)
Heavy processing      → Kafka (async queue)
```
