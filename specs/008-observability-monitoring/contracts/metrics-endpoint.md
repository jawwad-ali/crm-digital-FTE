# Contract: /metrics Endpoint

## Endpoint

```
GET /metrics
Content-Type: text/plain; version=0.0.4; charset=utf-8
```

## Response Format (Prometheus text exposition)

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",handler="/api/chat",status="202"} 47.0
http_requests_total{method="GET",handler="/health/live",status="200"} 312.0

# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="POST",handler="/api/chat",le="0.5"} 30.0
http_request_duration_seconds_bucket{method="POST",handler="/api/chat",le="1.0"} 42.0
http_request_duration_seconds_bucket{method="POST",handler="/api/chat",le="+Inf"} 47.0

# HELP crm_agent_requests_total Total agent interactions
# TYPE crm_agent_requests_total counter
crm_agent_requests_total{channel="web",resolution_type="auto_resolved"} 35.0
crm_agent_requests_total{channel="web",resolution_type="escalated"} 12.0

# HELP crm_agent_escalation_total Total escalated requests
# TYPE crm_agent_escalation_total counter
crm_agent_escalation_total{channel="web"} 12.0

# HELP crm_agent_response_time_seconds Agent response time
# TYPE crm_agent_response_time_seconds histogram
crm_agent_response_time_seconds_bucket{channel="web",le="1.0"} 10.0
crm_agent_response_time_seconds_bucket{channel="web",le="3.0"} 40.0
crm_agent_response_time_seconds_bucket{channel="web",le="+Inf"} 47.0
```

## Requirements

- Endpoint MUST respond in < 200ms
- Endpoint MUST NOT require authentication
- Endpoint MUST NOT block API request handling
- API MUST function normally if no one scrapes `/metrics`
