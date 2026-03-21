# Quickstart: K8s Deployment & 24/7 Readiness

**Feature**: 007-k8s-deployment-readiness

## Prerequisites

- Docker Desktop (with Kubernetes enabled) or Minikube
- `kubectl` CLI
- An OpenAI API key

## Option A: Docker Compose (Development)

```bash
# 1. Clone and configure
git clone https://github.com/jawwad-ali/crm-digital-FTE.git
cd crm-digital-FTE
cp .env.example .env
# Edit .env — set OPENAI_API_KEY (required)

# 2. Start everything
docker compose up --build

# 3. Access
# Web form:  http://localhost:3000
# API:       http://localhost:8000
# Health:    http://localhost:8000/health
```

Database schema and seed data are initialized automatically on first startup.

## Option B: Kubernetes (Local Cluster)

### 1. Build container images

```bash
docker build -t crm-api:latest .
docker build -t crm-web:latest --build-arg NEXT_PUBLIC_API_URL="" ./web
```

> `NEXT_PUBLIC_API_URL=""` makes the frontend use relative paths (`/api/chat`) so it works through the Ingress without CORS issues.

### 2. Install ingress-nginx controller

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.2/deploy/static/provider/cloud/deploy.yaml

# Wait for controller to be ready
kubectl -n ingress-nginx wait --for=condition=ready pod \
  -l app.kubernetes.io/component=controller --timeout=300s
```

### 3. Install metrics-server (required for HPA)

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Patch for local cluster (no valid TLS certs)
kubectl patch deployment metrics-server -n kube-system \
  --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'
```

### 4. Deploy all manifests

```bash
# Apply namespace first, then everything else
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/
```

### 5. Create secrets (real values)

The manifest has empty placeholders. Replace with real credentials:

```bash
kubectl -n crm delete secret crm-secrets
kubectl -n crm create secret generic crm-secrets \
  --from-literal=OPENAI_API_KEY="sk-your-key" \
  --from-literal=POSTGRES_PASSWORD="postgres"
```

### 6. Set the OpenAI model (optional)

```bash
kubectl -n crm patch configmap crm-config \
  --type merge -p '{"data":{"OPENAI_MODEL":"gpt-4.1-nano"}}'
```

### 7. Restart deployments to pick up secrets

```bash
kubectl -n crm rollout restart deployment postgres redis api web
```

### 8. Wait for all pods

```bash
kubectl -n crm get pods -w
# Wait until all 4 pods show 1/1 Running
```

### 9. Seed the knowledge base

The init container creates the schema, but the knowledge base needs to be seeded separately (requires OpenAI API for embeddings):

```bash
kubectl exec -n crm deployment/api -- \
  python -m database.migrations.002_seed_knowledge_base
```

### 10. Access

Everything runs through a single entry point — no port-forwarding needed:

| URL | What |
|-----|------|
| `http://localhost` | Web frontend |
| `http://localhost/api/chat` | Chat API |
| `http://localhost/health/live` | Liveness probe |
| `http://localhost/health/ready` | Readiness probe |
| `http://localhost/health` | General health |

## Verify Deployment

Run the full verification suite (27 checks):

```bash
bash k8s/verify-deployment.sh
```

This tests: resources, pods, health endpoints, database data, ingress routing, self-healing (pod kill + recovery), data persistence (PVC), horizontal scaling, HPA config, and end-to-end chat.

### Manual checks

```bash
# Health
curl http://localhost/health/live
curl http://localhost/health/ready

# Scale API to 3 replicas
kubectl -n crm scale deployment/api --replicas=3
kubectl -n crm get pods -l app=api

# Chaos test — kill a pod and watch self-healing
kubectl -n crm delete pod -l app=api --wait=false
kubectl -n crm get pods -w

# Check HPA
kubectl -n crm get hpa
```

## Teardown

```bash
# Docker Compose
docker compose down -v

# Kubernetes
kubectl delete namespace crm
kubectl delete -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.2/deploy/static/provider/cloud/deploy.yaml
```
