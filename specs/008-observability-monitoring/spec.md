# Feature Specification: Observability & Monitoring Dashboard

**Feature Branch**: `008-observability-monitoring`
**Created**: 2026-03-21
**Status**: Draft
**Input**: User description: "Prometheus + Grafana observability stack for K8s deployment"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Live API Metrics Dashboard (Priority: P1)

As a developer or operator, I want to open a visual dashboard and see real-time API metrics (request rates, latency, error rates, channel breakdown) so I can understand how the CRM agent is performing at a glance.

**Why this priority**: Without visibility into what the system is doing, you're flying blind. This is the foundation — every other monitoring capability depends on metrics being collected and displayed.

**Independent Test**: Open `http://localhost/grafana`, see a dashboard with live charts updating as requests flow through the API. Submit a few chat requests and watch the numbers change.

**Acceptance Scenarios**:

1. **Given** the K8s cluster is running with Prometheus and Grafana deployed, **When** I open the Grafana dashboard URL, **Then** I see a pre-configured dashboard with API request rate, latency percentiles, and error rate panels.
2. **Given** the dashboard is open, **When** I submit 5 chat requests via the web form, **Then** the request count and latency charts update within 30 seconds.
3. **Given** the dashboard is open, **When** I filter by channel (web, gmail, whatsapp), **Then** I see metrics broken down per channel.

---

### User Story 2 - Monitor Agent Performance (Priority: P2)

As a developer, I want to see agent-specific metrics (escalation rate, average response time, sentiment trends, resolution types) so I can identify how well the AI agent is handling customer requests and where it struggles.

**Why this priority**: API metrics tell you the system is running. Agent metrics tell you the business is working — are customers being helped or escalated?

**Independent Test**: Open the Agent Performance panel in Grafana, send a mix of easy questions and out-of-scope requests, verify escalation rate and resolution type charts reflect the test.

**Acceptance Scenarios**:

1. **Given** the agent has processed 10+ requests, **When** I view the Agent Performance panel, **Then** I see escalation rate as a percentage, average response time, and a breakdown by resolution type (auto_resolved vs escalated).
2. **Given** the agent escalated 3 out of 10 requests, **When** I view the dashboard, **Then** the escalation rate shows 30%.

---

### User Story 3 - Kubernetes Pod Health Overview (Priority: P3)

As an operator, I want to see pod CPU/memory usage and restart counts so I can detect resource pressure or crashlooping pods before they impact users.

**Why this priority**: Pod-level metrics complete the picture — API metrics show the application, pod metrics show the infrastructure. Together they enable full incident diagnosis.

**Independent Test**: Kill a pod, watch the restart count increment on the dashboard. Scale to 3 replicas, see all 3 pods appear in the resource usage panel.

**Acceptance Scenarios**:

1. **Given** the cluster is running, **When** I view the K8s panel, **Then** I see CPU and memory usage per pod in the `crm` namespace.
2. **Given** an API pod is killed, **When** the new pod starts, **Then** the restart count increments on the dashboard within 60 seconds.

---

### Edge Cases

- What happens when Prometheus is down? The API must continue working normally — metrics collection failure must not impact request handling.
- What happens when Grafana is restarted? Dashboards must be pre-provisioned (not manually created) so they survive pod restarts without reconfiguration.
- What happens when the metrics endpoint is slow? The `/metrics` endpoint must respond in under 200ms and not block API request processing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The API must expose a `/metrics` endpoint that returns request counts, latency histograms, and error rates in a scrapeable format.
- **FR-002**: Metrics must include labels for HTTP method, endpoint path, response status code, and channel (web, gmail, whatsapp).
- **FR-003**: Agent-level metrics (escalation rate, response time, resolution type) must be queryable from the existing `agent_metrics` database table.
- **FR-004**: A metrics collector must expose agent metrics from the database in a scrapeable format alongside API metrics.
- **FR-005**: A pre-configured visual dashboard must display: request rate, P50/P95/P99 latency, error rate, channel breakdown, escalation rate, and pod resource usage.
- **FR-006**: The dashboard must be accessible via the existing Ingress at a `/grafana` path.
- **FR-007**: Dashboard configuration must be provisioned automatically (not manually created) so it survives pod restarts.
- **FR-008**: Metrics collection must not impact API performance — the API must function normally even if the monitoring stack is down.
- **FR-009**: Pod CPU and memory metrics must be available from the existing metrics-server already deployed in the cluster.

### Key Entities

- **API Metric**: Request count, latency histogram, error count — labeled by method, path, status, channel
- **Agent Metric**: Escalation rate, response time, sentiment, resolution type — sourced from `agent_metrics` table
- **Pod Metric**: CPU usage, memory usage, restart count — per pod in the `crm` namespace

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can view a live dashboard showing API and agent metrics within 5 seconds of opening the URL.
- **SC-002**: Dashboard charts update within 30 seconds of new requests being processed.
- **SC-003**: The monitoring stack adds less than 10% CPU overhead to the cluster under normal load.
- **SC-004**: The API continues serving requests with zero degradation when the monitoring stack is unavailable.
- **SC-005**: Dashboard survives pod restarts without manual reconfiguration — all panels and data sources are auto-provisioned.

## Scope

### In Scope

- Metrics collection from the FastAPI application
- Agent metrics exposition from the existing `agent_metrics` table
- Pre-built visual dashboard with API, agent, and pod panels
- Ingress routing for dashboard access
- Auto-provisioned dashboard configuration

### Out of Scope

- Distributed tracing (traces for individual request flows)
- Log aggregation (centralized log collection and search)
- Alerting rules and notification channels (Slack, email, PagerDuty)
- Custom metric instrumentation beyond what the API framework provides automatically
- Multi-cluster or cloud-based monitoring

## Assumptions

- The K8s cluster already has metrics-server deployed (from feature 007)
- The Ingress controller (nginx) is already running (from feature 007)
- The `agent_metrics` table exists in PostgreSQL with escalation, sentiment, and response time data
- The monitoring stack runs entirely within the local K8s cluster (no cloud services)
- Grafana does not require authentication for local development use

## Dependencies

- Feature 007 (K8s Deployment & 24/7 Readiness) — provides the cluster, Ingress, and metrics-server
- Existing `agent_metrics` table in PostgreSQL schema
