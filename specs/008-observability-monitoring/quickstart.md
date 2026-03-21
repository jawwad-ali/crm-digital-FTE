# Quickstart: Observability & Monitoring Dashboard

**Feature**: 008-observability-monitoring
**Prerequisite**: Feature 007 (K8s cluster running with Ingress)

## Deploy Monitoring Stack

```bash
# 1. Rebuild API image with metrics dependency
docker build -t crm-api:latest .

# 2. Apply monitoring manifests
kubectl apply -f k8s/

# 3. Wait for pods
kubectl -n crm get pods -w
# Wait for prometheus and grafana pods to show 1/1 Running
```

## Access

| URL | What |
|-----|------|
| `http://localhost/grafana` | Grafana dashboard |
| `http://localhost/metrics` | Raw Prometheus metrics (API) |
| `http://localhost` | Web frontend (unchanged) |

## Verify

```bash
# Check metrics endpoint
curl -s http://localhost/metrics | head -20

# Check Prometheus is scraping
curl -s http://localhost/prometheus/api/v1/targets | grep -o '"health":"up"'

# Open Grafana
# Default login: admin / admin (local dev only)
# Dashboard: CRM Agent Overview (pre-provisioned)
```

## What You'll See

- **Request Rate**: Requests per second by endpoint
- **P95 Latency**: 95th percentile response time
- **Escalation Rate**: Percentage of requests escalated to human
- **Sentiment Trend**: Average customer sentiment over time
- **Pod Resources**: CPU and memory per pod

## Teardown

Monitoring pods are part of the `crm` namespace:

```bash
kubectl delete namespace crm  # Removes everything including monitoring
```
