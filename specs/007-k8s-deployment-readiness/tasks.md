# Tasks: K8s Deployment & 24/7 Readiness

**Input**: Design documents from `/specs/007-k8s-deployment-readiness/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/health-endpoints.md, quickstart.md

**Tests**: Not requested — no test tasks included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. User stories are reordered from spec priority to respect implementation dependencies (US4/US5 must complete before US2's K8s manifests can reference health probes and ConfigMaps).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Container ignore files to keep images lean

- [x] T001 Create .dockerignore at repo root (exclude .venv, node_modules, .git, __pycache__, .env)
- [x] T002 [P] Create web/.dockerignore (exclude node_modules, .next, .env.local)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Container images and database initialization — MUST complete before any user story

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create Dockerfile at repo root — multi-stage Python 3.12-slim build, install deps with uv, copy source, run uvicorn on port 8000
- [x] T004 [P] Create web/Dockerfile — multi-stage node:22-alpine build, npm ci, next build, next start on port 3000
- [x] T005 [P] Create database/migrations/init.sh — run 001_initial_schema.sql via psql, then optionally run 002_seed_knowledge_base.py if OPENAI_API_KEY is set

**Checkpoint**: All 3 container images buildable — `docker build` succeeds for API and web

---

## Phase 3: User Story 1 — One-Command Local Startup (Priority: P1) MVP

**Goal**: A developer runs one command and the entire platform (API, frontend, PostgreSQL, Redis) starts locally with correct networking, dependency ordering, and auto-initialization.

**Independent Test**: Run `docker compose up --build` on a fresh clone, open http://localhost:3000, submit a support request, receive an AI response.

### Implementation for User Story 1

- [x] T006 [US1] Create docker-compose.yml with 4 services (api, web, postgres, redis) — health checks, depends_on conditions, volumes, port mappings (3000, 8000, 5432, 6379)
- [x] T007 [US1] Verify: `docker compose up --build` starts all services within 120s, web form at localhost:3000 works end-to-end

**Checkpoint**: MVP complete — single-command local startup with auto DB initialization

---

## Phase 4: User Story 4 — Health Monitoring & Liveness (Priority: P2)

**Goal**: The API exposes liveness and readiness probes so the orchestrator can detect failures and route traffic away from unhealthy instances.

**Independent Test**: `curl localhost:8000/health/live` returns 200 `{"status":"alive"}`; `curl localhost:8000/health/ready` returns 200 with DB+Redis status or 503 when a dependency is down.

**Dependency**: Completes before US2 (K8s manifests reference these endpoints in probe config).

### Implementation for User Story 4

- [x] T008 [US4] Add GET /health/live endpoint in api/main.py — returns `{"status": "alive"}`, no dependency checks
- [x] T009 [US4] Add GET /health/ready endpoint in api/main.py — checks asyncpg pool + Redis ping, returns 200 `{"status":"ready","database":"connected","redis":"connected"}` or 503 `{"status":"not_ready",...}` per contracts/health-endpoints.md

**Checkpoint**: Health probes functional — existing GET /health unchanged (backward compatible)

---

## Phase 5: User Story 5 — Configuration & Secrets Management (Priority: P3)

**Goal**: All configuration and secrets are externalized into K8s-native resources so the same container images work without rebuilds.

**Independent Test**: Verify ConfigMap and Secret manifests apply cleanly (`kubectl apply`) and contain all required keys per data-model.md.

**Dependency**: Completes before US2 (K8s deployments mount these resources as envFrom).

### Implementation for User Story 5

- [x] T010 [US5] Create k8s/namespace.yml — define `crm` namespace
- [x] T011 [P] [US5] Create k8s/configmap.yml — crm-config with keys: OPENAI_MODEL, REDIS_URL, NEXT_PUBLIC_API_URL per data-model.md
- [x] T012 [P] [US5] Create k8s/secret.yml — crm-secrets placeholder with keys: OPENAI_API_KEY, POSTGRES_PASSWORD (base64 encoded placeholders, real values created via kubectl)

**Checkpoint**: K8s namespace + config resources ready for deployment manifests

---

## Phase 6: User Story 2 — Survive Service Restarts (Priority: P1)

**Goal**: Any killed service auto-recovers within 30s. Database and Redis data persist across restarts via PVCs. The orchestrator uses health probes to detect failures and restart pods.

**Independent Test**: `kubectl apply -f k8s/`, wait for all pods Ready, then `kubectl delete pod -l app=api` — pod restarts within 30s, data in postgres/redis survives.

**Dependency**: Requires Phase 4 (health endpoints) and Phase 5 (ConfigMap/Secret/namespace).

### Implementation for User Story 2

- [x] T013 [P] [US2] Create k8s/postgres-pvc.yml (1Gi), k8s/postgres-deployment.yml (postgres:16, pgvector init, resource limits 100m-500m CPU / 256Mi-512Mi RAM), k8s/postgres-service.yml (ClusterIP :5432)
- [x] T014 [P] [US2] Create k8s/redis-pvc.yml (512Mi), k8s/redis-deployment.yml (redis:7-alpine with AOF persistence, resource limits 50m-200m CPU / 128Mi-256Mi RAM), k8s/redis-service.yml (ClusterIP :6379)
- [x] T015 [P] [US2] Create k8s/api-deployment.yml — init container runs database/migrations/init.sh, liveness probe /health/live (period 10s, failure 3), readiness probe /health/ready (period 5s, failure 2), resource limits 100m-500m CPU / 256Mi-512Mi RAM, envFrom crm-config + crm-secrets
- [x] T016 [P] [US2] Create k8s/api-service.yml — ClusterIP on port 8000
- [x] T017 [P] [US2] Create k8s/web-deployment.yml (resource limits 50m-200m CPU / 128Mi-256Mi RAM) and k8s/web-service.yml (NodePort on port 3000 for external access)
- [x] T018 [US2] Verify: `kubectl apply -f k8s/` deploys all resources, all pods reach Ready within 120s
- [x] T019 [US2] Verify: kill an API pod → auto-restarts within 30s, serves requests again
- [x] T020 [US2] Verify: restart postgres pod → customer data persists (PVC intact)

**Checkpoint**: Full K8s deployment operational with self-healing and persistent storage

---

## Phase 7: User Story 3 — Horizontal Scaling (Priority: P2)

**Goal**: The API scales from 1 to 5 replicas via HPA based on CPU utilization, distributing traffic across all healthy instances.

**Independent Test**: `kubectl -n crm scale deployment/api --replicas=3`, send concurrent requests, verify all 3 pods serve traffic. Then check HPA auto-scales under load.

**Dependency**: Requires Phase 6 (API deployment must exist for HPA to target it).

### Implementation for User Story 3

- [x] T021 [US3] Create k8s/api-hpa.yml — HorizontalPodAutoscaler targeting api deployment, 70% CPU threshold, min 1 / max 5 replicas
- [x] T022 [US3] Verify: manually scale API to 3 replicas → all serve traffic, requests distributed
- [x] T023 [US3] Verify: HPA scales up when CPU load increases above 70%

**Checkpoint**: Auto-scaling operational — API handles variable load without manual intervention

---

## Phase 7.5: Ingress — Single Entry Point (Enhancement)

**Goal**: Route all traffic through a single `localhost:80` entry point using nginx-ingress. The frontend calls the API via relative paths (`/api/chat`) — no CORS, no port-forwarding, no `NEXT_PUBLIC_API_URL` headaches.

**Independent Test**: Open `http://localhost`, submit a support request, verify it reaches the API and returns a response. Confirm `http://localhost/health/live` returns `{"status":"alive"}`.

**Dependency**: Requires Phase 6 (all services deployed) and Phase 7 (HPA targets API deployment).

### Implementation for Ingress

- [x] T026 [US2] Install ingress-nginx controller via official manifest
- [x] T027 [US2] Create k8s/ingress.yml — routes `/api/*` and `/health/*` to api:8000, `/*` to web:3000
- [x] T028 [US2] Rebuild crm-web:latest with `--build-arg NEXT_PUBLIC_API_URL=""` so frontend uses relative paths
- [x] T029 [US2] Verify: `http://localhost` loads frontend, API calls succeed via Ingress, health endpoints accessible

**Checkpoint**: Single entry point operational — browser hits `localhost`, all routing handled by Ingress

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation updates

- [x] T024 [P] Update specs/007-k8s-deployment-readiness/quickstart.md with final tested commands and any adjustments discovered during implementation
- [x] T025 Create k8s/verify-deployment.sh — 27-check verification suite covering resources, pods, health, data, ingress, self-healing, persistence, scaling, HPA, and end-to-end chat (all 27 passed)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
  └──▶ Phase 2 (Foundational: Dockerfiles + init script)
         └──▶ Phase 3: US1 (docker-compose.yml) ── MVP STOP POINT
               └──▶ Phase 4: US4 (Health endpoints in api/main.py)
                     └──▶ Phase 5: US5 (K8s namespace + ConfigMap + Secret)
                           └──▶ Phase 6: US2 (K8s deployments + PVCs + probes)
                                 └──▶ Phase 7: US3 (HPA auto-scaling)
                                       └──▶ Phase 8 (Polish + chaos test)
```

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational only — no other story dependencies
- **US4 (P2)**: Depends on Foundational — delivers health endpoints needed by US2
- **US5 (P3)**: Depends on Foundational — delivers K8s config needed by US2
- **US2 (P1)**: Depends on US4 + US5 — K8s deployments reference health probes and ConfigMap/Secret
- **US3 (P2)**: Depends on US2 — HPA targets the API deployment created in US2

### Within Each User Story

- Infrastructure files (manifests) before verification tasks
- All manifests within a story marked [P] can be created in parallel
- Verification tasks run sequentially after all manifests are applied

### Parallel Opportunities

**Phase 1**: T001 and T002 in parallel (different files)
**Phase 2**: T003, T004, T005 all in parallel (different files)
**Phase 5**: T011 and T012 in parallel (different files, after T010 creates namespace)
**Phase 6**: T013, T014, T015, T016, T017 all in parallel (different K8s manifest files)
**Phase 8**: T024 can run while T025 is in progress

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Launch all three in parallel — different files, no dependencies:
Task T003: "Create Dockerfile at repo root"
Task T004: "Create web/Dockerfile"
Task T005: "Create database/migrations/init.sh"
```

## Parallel Example: Phase 6 (US2 — K8s Manifests)

```bash
# Launch all five manifest groups in parallel — different files:
Task T013: "Create k8s/postgres-pvc.yml + postgres-deployment.yml + postgres-service.yml"
Task T014: "Create k8s/redis-pvc.yml + redis-deployment.yml + redis-service.yml"
Task T015: "Create k8s/api-deployment.yml"
Task T016: "Create k8s/api-service.yml"
Task T017: "Create k8s/web-deployment.yml + web-service.yml"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (.dockerignore files)
2. Complete Phase 2: Foundational (Dockerfiles + init script)
3. Complete Phase 3: US1 (docker-compose.yml)
4. **STOP and VALIDATE**: `docker compose up --build` → web form works end-to-end
5. Demo-ready with single-command local startup

### Incremental Delivery

1. Setup + Foundational → container images buildable
2. US1 (docker-compose) → **MVP Demo** — single-command startup
3. US4 (health endpoints) → probes ready for K8s
4. US5 (ConfigMap/Secret) → K8s config externalized
5. US2 (K8s deployments) → self-healing, persistent storage, orchestrated deployment
6. US3 (HPA) → auto-scaling under load
7. Polish → chaos-tested, documentation finalized

### Single Developer Strategy

Execute phases sequentially (1 → 2 → 3 → 4 → 5 → 6 → 7 → 8). Within each phase, leverage parallel opportunities for [P] tasks where possible.

---

## Notes

- [P] tasks = different files, no dependencies between them
- [Story] label maps task to specific user story for traceability
- US4 and US5 are implemented before US2 despite lower priority — they are technical prerequisites
- Verification tasks (T007, T018-T020, T022-T023, T025) require a running environment
- No new test code — existing 177 tests remain unchanged
- Redis gets AOF persistence + PVC (user requirement: Redis failure is unacceptable)
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
