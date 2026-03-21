# Implementation Plan: Observability & Monitoring Dashboard

**Branch**: `008-observability-monitoring` | **Date**: 2026-03-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-observability-monitoring/spec.md`

## Summary

Add Prometheus metrics collection and Grafana dashboards to the CRM platform running on K8s. The API exposes a `/metrics` endpoint with request counts, latency histograms, and error rates. A custom metrics exporter queries the `agent_metrics` table to expose agent-level metrics (escalation rate, response time, sentiment). Grafana ships with a pre-provisioned dashboard showing API performance, agent health, and pod resource usage — all accessible at `localhost/grafana` via the existing Ingress.

## Technical Context

**Language/Version**: Python 3.12+ (API instrumentation), YAML (K8s manifests, Grafana provisioning)
**Primary Dependencies**: prometheus-fastapi-instrumentator (API metrics), prometheus-client (custom metrics), Prometheus server, Grafana
**Storage**: Prometheus TSDB (in-pod, ephemeral — metrics are transient), PostgreSQL (agent_metrics source)
**Testing**: Manual validation via dashboard + `curl localhost/metrics`
**Target Platform**: Local K8s cluster (Docker Desktop)
**Project Type**: Infrastructure addition — no new application code beyond metrics instrumentation
**Performance Goals**: `/metrics` endpoint < 200ms, dashboard refresh < 30s, < 10% CPU overhead
**Constraints**: Local-only, no cloud services, no alerting, no tracing, no log aggregation
**Scale/Scope**: 1 Prometheus pod, 1 Grafana pod, 1 dashboard with 3 panel groups

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Agent-First Architecture | PASS | No agent changes — monitoring only observes |
| II. PostgreSQL as CRM | PASS | agent_metrics table read-only, no schema changes |
| III. Channel-Agnostic Core | PASS | Metrics labeled by channel but no core logic changes |
| IV. Async-First | PASS | Metrics instrumentation is non-blocking middleware |
| V. Secrets-Free Codebase | PASS | No secrets needed — Prometheus/Grafana use K8s service discovery |
| VI. Structured Observability | PASS | This feature directly implements Principle VI at the infrastructure level |
| VII. Graceful Degradation | PASS | FR-008: API works normally when monitoring stack is down |

**Post-Phase 1 re-check**: All gates still pass. Metrics collection is passive middleware — no impact on request handling.

## Project Structure

### Documentation (this feature)

```text
specs/008-observability-monitoring/
├── plan.md              # This file
├── research.md          # Phase 0 output — technology decisions
├── data-model.md        # Phase 1 output — metrics schema
├── quickstart.md        # Phase 1 output — deploy + access instructions
├── contracts/
│   └── metrics-endpoint.md  # Phase 1 output — /metrics contract
└── tasks.md             # Phase 2 output (/sp.tasks command)
```

### Source Code (repository root)

```text
api/main.py                          # Add metrics middleware (2-3 lines)
k8s/prometheus-deployment.yml        # Prometheus server + config
k8s/prometheus-service.yml           # ClusterIP service for Prometheus
k8s/grafana-deployment.yml           # Grafana with provisioned dashboard
k8s/grafana-service.yml              # ClusterIP service for Grafana
k8s/ingress.yml                      # Update: add /grafana and /prometheus paths
k8s/grafana-dashboard-configmap.yml  # Pre-built dashboard JSON
k8s/grafana-datasource-configmap.yml # Prometheus datasource config
```

**Structure Decision**: Infrastructure-only addition. Two new pods (Prometheus, Grafana) with ConfigMaps for auto-provisioning. Only change to existing code is 2-3 lines in `api/main.py` for metrics middleware.

## Implementation Steps

1. Add `prometheus-fastapi-instrumentator` to API dependencies
2. Add metrics middleware to `api/main.py` (exposes `/metrics`)
3. Create Prometheus K8s manifests (Deployment, Service, ConfigMap with scrape config)
4. Create Grafana K8s manifests (Deployment, Service, datasource ConfigMap, dashboard ConfigMap)
5. Update Ingress to route `/grafana` and `/prometheus`
6. Rebuild API image with new dependency
7. Apply all manifests and verify dashboard loads

## Complexity Tracking

No constitution violations. No complexity justification needed.
