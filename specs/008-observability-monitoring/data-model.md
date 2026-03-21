# Data Model: Observability & Monitoring

## Metrics Schema

### API Metrics (auto-instrumented)

Exposed by `prometheus-fastapi-instrumentator` on `/metrics`:

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `http_requests_total` | Counter | method, handler, status | Total request count |
| `http_request_duration_seconds` | Histogram | method, handler | Request latency (p50/p95/p99) |
| `http_requests_in_progress` | Gauge | method, handler | Currently active requests |

### Agent Metrics (custom, from agent_metrics table)

Exposed as custom Prometheus metrics on the same `/metrics` endpoint:

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `crm_agent_requests_total` | Counter | channel, resolution_type | Total agent interactions |
| `crm_agent_escalation_total` | Counter | channel | Escalated requests count |
| `crm_agent_response_time_seconds` | Histogram | channel | Agent response time distribution |
| `crm_agent_sentiment_average` | Gauge | channel | Rolling average sentiment score |

### Source: agent_metrics table (existing)

```
agent_metrics
├── id (UUID)
├── customer_id (UUID, FK → customers)
├── ticket_id (UUID, FK → tickets)
├── channel (VARCHAR) — web, gmail, whatsapp
├── response_time_ms (INTEGER)
├── sentiment (FLOAT)
├── resolution_type (VARCHAR) — auto_resolved, escalated, error
├── escalation_reason (TEXT)
└── created_at (TIMESTAMPTZ)
```

No schema changes needed — read-only access.

## Prometheus Scrape Targets

| Target | Endpoint | Interval |
|--------|----------|----------|
| API | `api.crm.svc:8000/metrics` | 15s |

## Grafana Dashboard Panels

### Row 1: API Overview
- Request Rate (req/s) — timeseries
- P95 Latency — timeseries
- Error Rate (%) — stat panel
- Active Requests — gauge

### Row 2: Agent Performance
- Escalation Rate (%) — stat panel
- Avg Response Time — stat panel
- Resolution Breakdown (auto/escalated/error) — pie chart
- Sentiment Trend — timeseries

### Row 3: Infrastructure
- Pod CPU Usage — timeseries (from metrics-server via kube-state-metrics or cAdvisor)
- Pod Memory Usage — timeseries
- Pod Restart Count — stat panel
