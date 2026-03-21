# Research: Observability & Monitoring Dashboard

## Decision 1: FastAPI Metrics Library

**Decision**: `prometheus-fastapi-instrumentator`
**Rationale**: Auto-instruments all FastAPI endpoints with request count, latency histogram, and error rate — zero manual per-endpoint code. Exposes `/metrics` endpoint automatically.
**Alternatives considered**:
- `prometheus-client` (manual instrumentation per endpoint — more work, same result)
- `starlette-exporter` (less maintained, fewer features)
- OpenTelemetry SDK (overkill — adds tracing complexity we don't need)

## Decision 2: Prometheus Deployment Strategy

**Decision**: Single Prometheus pod with ConfigMap-based scrape config
**Rationale**: Simplest approach for local K8s. ConfigMap holds `prometheus.yml` with scrape targets. No need for Prometheus Operator or ServiceMonitor CRDs for a single-cluster setup.
**Alternatives considered**:
- Prometheus Operator + ServiceMonitor (overkill for 1 target)
- Grafana Agent/Alloy (adds another tool when Prometheus is simpler)
- Victoria Metrics (unnecessary complexity for local dev)

## Decision 3: Grafana Dashboard Provisioning

**Decision**: ConfigMap-based provisioning (datasource + dashboard JSON mounted as files)
**Rationale**: Grafana supports file-based provisioning — mount ConfigMaps into `/etc/grafana/provisioning/`. Dashboard survives pod restarts without manual setup. No Grafana API calls needed.
**Alternatives considered**:
- Manual dashboard creation via UI (lost on restart)
- Grafana API sidecar (adds complexity)
- Grafana Operator (overkill for 1 dashboard)

## Decision 4: Agent Metrics Exposition

**Decision**: Custom Prometheus gauge/counter in the API process that queries `agent_metrics` table periodically
**Rationale**: The `agent_metrics` table already stores escalation rates, response times, and sentiment. A lightweight background task in the API can expose these as Prometheus metrics on the same `/metrics` endpoint. No separate exporter pod needed.
**Alternatives considered**:
- Separate exporter pod (adds a pod for a simple query)
- SQL exporter (generic tool, harder to customize)
- Skip agent metrics (misses key business metrics)

## Decision 5: Ingress Path for Grafana

**Decision**: Route `/grafana` via Ingress with sub-path rewrite
**Rationale**: Grafana supports `GF_SERVER_ROOT_URL` and `GF_SERVER_SERVE_FROM_SUB_PATH=true` for sub-path hosting. This keeps the single-entry-point pattern from feature 007.
**Alternatives considered**:
- Separate NodePort (breaks the single-entry-point pattern)
- Subdomain (requires DNS config, overkill for local)
