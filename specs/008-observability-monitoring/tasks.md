# Tasks: Observability & Monitoring Dashboard

**Input**: Design documents from `/specs/008-observability-monitoring/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/metrics-endpoint.md, quickstart.md

**Tests**: Not requested — no test tasks included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. US1 (API metrics + dashboard) is the MVP — delivers visible value immediately.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Dependencies)

**Purpose**: Add the metrics library to the API

- [ ] T001 Add `prometheus-fastapi-instrumentator` and `prometheus-client` to pyproject.toml dependencies
- [ ] T002 Rebuild crm-api:latest image with new dependencies — `docker build -t crm-api:latest .`

**Checkpoint**: API image includes metrics libraries

---

## Phase 2: Foundational (Metrics Endpoint)

**Purpose**: Expose `/metrics` on the API — MUST complete before Prometheus can scrape

**CRITICAL**: No monitoring stack work can begin until this phase is complete

- [ ] T003 Add Prometheus metrics middleware to api/main.py — instrument the FastAPI app with `prometheus-fastapi-instrumentator` (exposes `/metrics` endpoint automatically)
- [ ] T004 Verify: `curl http://localhost/metrics` returns Prometheus text exposition format with `http_requests_total` and `http_request_duration_seconds`

**Checkpoint**: `/metrics` endpoint live — Prometheus can scrape it

---

## Phase 3: User Story 1 — Live API Metrics Dashboard (Priority: P1) MVP

**Goal**: Operators open a Grafana dashboard and see real-time API request rate, latency, and error rate.

**Independent Test**: Open `http://localhost/grafana`, see charts updating as requests flow through the API.

### Implementation for User Story 1

- [ ] T005 [P] [US1] Create k8s/prometheus-configmap.yml — Prometheus scrape config targeting `api.crm.svc:8000/metrics` with 15s interval
- [ ] T006 [P] [US1] Create k8s/prometheus-deployment.yml — Prometheus server (prom/prometheus:latest, 100m-500m CPU / 256Mi-512Mi RAM) mounting config via ConfigMap, with k8s/prometheus-service.yml (ClusterIP :9090)
- [ ] T007 [P] [US1] Create k8s/grafana-datasource-configmap.yml — Grafana provisioning config pointing to Prometheus at http://prometheus:9090
- [ ] T008 [P] [US1] Create k8s/grafana-dashboard-configmap.yml — pre-built dashboard JSON with panels: Request Rate, P95 Latency, Error Rate, Active Requests
- [ ] T009 [US1] Create k8s/grafana-deployment.yml — Grafana (grafana/grafana:latest, 100m-300m CPU / 128Mi-256Mi RAM) with provisioning ConfigMaps mounted, GF_SERVER_ROOT_URL and GF_SERVER_SERVE_FROM_SUB_PATH=true, with k8s/grafana-service.yml (ClusterIP :3000)
- [ ] T010 [US1] Update k8s/ingress.yml — add paths `/grafana` → grafana:3000 and `/prometheus` → prometheus:9090
- [ ] T011 [US1] Apply all manifests, rebuild API image, restart api deployment
- [ ] T012 [US1] Verify: `http://localhost/grafana` loads dashboard, charts show live API metrics after sending test requests

**Checkpoint**: MVP complete — live API metrics dashboard visible at localhost/grafana

---

## Phase 4: User Story 2 — Agent Performance Metrics (Priority: P2)

**Goal**: Dashboard shows agent-specific metrics: escalation rate, response time, sentiment trends.

**Independent Test**: Send a mix of easy and out-of-scope requests, verify escalation rate and resolution breakdown update on dashboard.

**Dependency**: Requires Phase 3 (Prometheus + Grafana running).

### Implementation for User Story 2

- [ ] T013 [US2] Add custom Prometheus metrics in api/main.py — define counters/histograms (`crm_agent_requests_total`, `crm_agent_escalation_total`, `crm_agent_response_time_seconds`, `crm_agent_sentiment_average`) and a background task that periodically queries agent_metrics table to update them
- [ ] T014 [US2] Update k8s/grafana-dashboard-configmap.yml — add Agent Performance row: Escalation Rate (stat), Avg Response Time (stat), Resolution Breakdown (pie), Sentiment Trend (timeseries)
- [ ] T015 [US2] Apply updated manifests and restart grafana deployment
- [ ] T016 [US2] Verify: send 5+ chat requests, check Agent Performance panels show correct escalation rate and response times

**Checkpoint**: Agent business metrics visible — escalation rate, sentiment, resolution types

---

## Phase 5: User Story 3 — Pod Health Overview (Priority: P3)

**Goal**: Dashboard shows pod CPU/memory usage and restart counts for the crm namespace.

**Independent Test**: Kill a pod, see restart count increment on dashboard. Scale to 3 replicas, see all 3 in resource panel.

**Dependency**: Requires Phase 3 (Grafana running) and metrics-server (already deployed from feature 007).

### Implementation for User Story 3

- [ ] T017 [US3] Update k8s/prometheus-configmap.yml — add kubernetes-pods scrape job to discover pod metrics from cAdvisor/kubelet
- [ ] T018 [US3] Update k8s/grafana-dashboard-configmap.yml — add Infrastructure row: Pod CPU Usage (timeseries), Pod Memory Usage (timeseries), Pod Restart Count (stat)
- [ ] T019 [US3] Apply updated manifests, restart prometheus and grafana
- [ ] T020 [US3] Verify: pod metrics visible, kill a pod → restart count increments within 60s

**Checkpoint**: Full observability — API metrics, agent metrics, and infrastructure metrics in one dashboard

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [ ] T021 [P] Update specs/008-observability-monitoring/quickstart.md with final tested commands
- [ ] T022 Run k8s/verify-deployment.sh to ensure monitoring didn't break existing functionality

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup: add dependencies)
  └──▶ Phase 2 (Foundational: /metrics endpoint)
         └──▶ Phase 3: US1 (Prometheus + Grafana + API dashboard) ── MVP STOP POINT
               └──▶ Phase 4: US2 (Agent metrics panels)
                     └──▶ Phase 5: US3 (Pod health panels)
                           └──▶ Phase 6 (Polish)
```

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational only — delivers MVP dashboard
- **US2 (P2)**: Depends on US1 — adds agent panels to existing dashboard
- **US3 (P3)**: Depends on US1 — adds infrastructure panels to existing dashboard

### Within Each User Story

- K8s manifests (ConfigMaps) before deployments
- Deployments before Ingress updates
- All manifests applied before verification

### Parallel Opportunities

**Phase 3 (US1)**: T005, T006, T007, T008 all in parallel (different ConfigMap/manifest files)
**Phase 4 (US2)**: T013 and T014 in parallel (different files — api/main.py vs configmap)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Add metrics dependency
2. Complete Phase 2: Expose `/metrics` endpoint
3. Complete Phase 3: US1 (Prometheus + Grafana + dashboard)
4. **STOP and VALIDATE**: Open `localhost/grafana` — see live charts
5. Demo-ready with API metrics dashboard

### Incremental Delivery

1. Setup + Foundational → `/metrics` endpoint live
2. US1 (Prometheus + Grafana) → **MVP Demo** — API dashboard at localhost/grafana
3. US2 (Agent metrics) → escalation rate, sentiment, resolution breakdown
4. US3 (Pod health) → CPU, memory, restart counts
5. Polish → quickstart updated, verify-deployment passes

---

## Notes

- [P] tasks = different files, no dependencies between them
- [Story] label maps task to specific user story for traceability
- No schema changes needed — agent_metrics table already exists
- Only code change to existing app: 2-3 lines in api/main.py for metrics middleware
- All new infrastructure is K8s manifests (ConfigMaps + Deployments)
- Grafana dashboard is JSON provisioned via ConfigMap — survives pod restarts
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
