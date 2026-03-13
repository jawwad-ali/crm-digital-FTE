# Quickstart: K8s Deployment & 24/7 Readiness

**Feature**: 007-k8s-deployment-readiness

## Prerequisites

- Docker Desktop (with Kubernetes enabled) or Minikube
- `kubectl` CLI
- An OpenAI API key

## Option A: Docker Compose (Development)

```bash
# 1. Clone and configure
git clone https://github.com/jawwad-ali/ai-customer-support-agent.git
cd ai-customer-support-agent
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

```bash
# 1. Build container images
docker build -t crm-api:latest .
docker build -t crm-web:latest ./web

# 2. Create namespace and secrets
kubectl create namespace crm
kubectl -n crm create secret generic crm-secrets \
  --from-literal=OPENAI_API_KEY=sk-your-key \
  --from-literal=POSTGRES_PASSWORD=your-password

# 3. Deploy all manifests
kubectl apply -f k8s/ -n crm

# 4. Wait for pods
kubectl -n crm wait --for=condition=ready pod --all --timeout=120s

# 5. Access via port-forward
kubectl -n crm port-forward svc/web 3000:3000
kubectl -n crm port-forward svc/api 8000:8000
```

## Verify Deployment

```bash
# Health checks
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# Scale API to 3 replicas
kubectl -n crm scale deployment/api --replicas=3

# Watch pods
kubectl -n crm get pods -w

# Chaos test — kill a pod and watch self-healing
kubectl -n crm delete pod -l app=api --wait=false
```

## Teardown

```bash
# Docker Compose
docker compose down -v

# Kubernetes
kubectl delete namespace crm
```
