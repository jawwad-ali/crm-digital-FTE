#!/usr/bin/env bash
# =============================================================================
# K8s Deployment Verification Suite
#
# Run this anytime to verify the CRM platform is healthy on K8s.
# Covers: pod health, self-healing, data persistence, scaling, ingress routing,
# and end-to-end chat flow.
#
# Usage:
#   bash k8s/verify-deployment.sh
#
# Prerequisites:
#   - kubectl configured to the target cluster
#   - All manifests applied: kubectl apply -f k8s/
#   - Secrets populated: kubectl -n crm get secret crm-secrets
# =============================================================================

set -uo pipefail

NAMESPACE="crm"
INGRESS_URL="http://localhost"
PASS=0
FAIL=0
TOTAL=0

# --- Helpers ----------------------------------------------------------------

pass() { ((PASS++)); ((TOTAL++)); echo "  [PASS] $1"; }
fail() { ((FAIL++)); ((TOTAL++)); echo "  [FAIL] $1"; }

check() {
  local desc="$1"
  shift
  if "$@" > /dev/null 2>&1; then
    pass "$desc"
  else
    fail "$desc"
  fi
}

wait_for_pod() {
  local label="$1" timeout="${2:-60}"
  local end=$((SECONDS + timeout))
  while [ $SECONDS -lt $end ]; do
    local ready
    ready=$(kubectl get pods -n "$NAMESPACE" -l "app=$label" -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "")
    if [ "$ready" = "True" ]; then return 0; fi
    sleep 3
  done
  return 1
}

section() { echo ""; echo "== $1 =="; }

# =============================================================================
section "1. NAMESPACE & RESOURCES"
# =============================================================================

check "Namespace 'crm' exists" \
  kubectl get ns "$NAMESPACE"

check "ConfigMap 'crm-config' exists" \
  kubectl get configmap crm-config -n "$NAMESPACE"

check "Secret 'crm-secrets' exists" \
  kubectl get secret crm-secrets -n "$NAMESPACE"

check "PVC 'postgres-pvc' is Bound" \
  bash -c "kubectl get pvc postgres-pvc -n $NAMESPACE -o jsonpath='{.status.phase}' | grep -q Bound"

check "PVC 'redis-pvc' is Bound" \
  bash -c "kubectl get pvc redis-pvc -n $NAMESPACE -o jsonpath='{.status.phase}' | grep -q Bound"

# =============================================================================
section "2. ALL PODS RUNNING"
# =============================================================================

for app in postgres redis api web; do
  check "Pod '$app' is Ready" \
    bash -c "kubectl get pods -n $NAMESPACE -l app=$app -o jsonpath='{.items[0].status.conditions[?(@.type==\"Ready\")].status}' | grep -q True"
done

# =============================================================================
section "3. HEALTH ENDPOINTS"
# =============================================================================

check "/health/live returns 'alive'" \
  bash -c "curl -sf $INGRESS_URL/health/live | grep -q alive"

check "/health/ready returns 'ready'" \
  bash -c "curl -sf $INGRESS_URL/health/ready | grep -q ready"

check "/health returns 'ok'" \
  bash -c "curl -sf $INGRESS_URL/health | grep -q ok"

# =============================================================================
section "4. DATABASE HAS DATA"
# =============================================================================

KB_COUNT=$(kubectl exec -n "$NAMESPACE" deployment/postgres -- \
  psql -U postgres -d crm -tAc "SELECT COUNT(*) FROM knowledge_base;" 2>/dev/null || echo "0")

if [ "$KB_COUNT" -gt 0 ] 2>/dev/null; then
  pass "Knowledge base has $KB_COUNT articles"
else
  fail "Knowledge base is empty (agent will escalate everything)"
fi

TABLES=$(kubectl exec -n "$NAMESPACE" deployment/postgres -- \
  psql -U postgres -d crm -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")

if [ "$TABLES" -ge 5 ] 2>/dev/null; then
  pass "Schema has $TABLES tables"
else
  fail "Schema incomplete — expected >= 5 tables, got $TABLES"
fi

# =============================================================================
section "5. INGRESS ROUTING"
# =============================================================================

check "Ingress 'crm-ingress' exists" \
  kubectl get ingress crm-ingress -n "$NAMESPACE"

check "Frontend loads at $INGRESS_URL/" \
  bash -c "curl -sf $INGRESS_URL/ | grep -qi 'html'"

check "API routes through Ingress (/health/live)" \
  bash -c "curl -sf $INGRESS_URL/health/live | grep -q alive"

# =============================================================================
section "6. SELF-HEALING (pod kill + recovery)"
# =============================================================================

echo "  Killing API pod..."
kubectl delete pod -n "$NAMESPACE" -l app=api --wait=false > /dev/null 2>&1

echo "  Waiting for new pod (max 60s)..."
if wait_for_pod "api" 60; then
  pass "API pod recovered and is Ready"
else
  fail "API pod did not recover within 60s"
fi

# Verify it serves traffic after recovery
sleep 5
check "API serves traffic after recovery" \
  bash -c "curl -sf $INGRESS_URL/health/live | grep -q alive"

# =============================================================================
section "7. DATA PERSISTENCE (postgres kill + verify)"
# =============================================================================

BEFORE=$(kubectl exec -n "$NAMESPACE" deployment/postgres -- \
  psql -U postgres -d crm -tAc "SELECT COUNT(*) FROM knowledge_base;" 2>/dev/null || echo "0")

echo "  KB articles before kill: $BEFORE"
echo "  Killing postgres pod..."
kubectl delete pod -n "$NAMESPACE" -l app=postgres --wait=false > /dev/null 2>&1

echo "  Waiting for postgres recovery (max 60s)..."
if wait_for_pod "postgres" 60; then
  pass "Postgres pod recovered"
else
  fail "Postgres pod did not recover within 60s"
fi

sleep 5
AFTER=$(kubectl exec -n "$NAMESPACE" deployment/postgres -- \
  psql -U postgres -d crm -tAc "SELECT COUNT(*) FROM knowledge_base;" 2>/dev/null || echo "0")

echo "  KB articles after kill: $AFTER"
if [ "$BEFORE" = "$AFTER" ] && [ "$AFTER" -gt 0 ] 2>/dev/null; then
  pass "Data persisted across restart ($AFTER articles intact)"
else
  fail "Data lost: before=$BEFORE, after=$AFTER"
fi

# Wait for API to recover (init container may need postgres)
echo "  Waiting for API to recover after postgres restart..."
wait_for_pod "api" 60 || true
sleep 5

# =============================================================================
section "8. HORIZONTAL SCALING"
# =============================================================================

echo "  Scaling API to 3 replicas..."
kubectl -n "$NAMESPACE" scale deployment/api --replicas=3 > /dev/null 2>&1
sleep 30

READY_COUNT=$(kubectl get pods -n "$NAMESPACE" -l app=api --field-selector=status.phase=Running -o name 2>/dev/null | wc -l)
if [ "$READY_COUNT" -ge 3 ] 2>/dev/null; then
  pass "Scaled to $READY_COUNT API replicas"
else
  fail "Expected 3 replicas, got $READY_COUNT"
fi

# Verify all serve traffic
ALL_ALIVE=true
for i in 1 2 3 4 5; do
  if ! curl -sf "$INGRESS_URL/health/live" | grep -q alive; then
    ALL_ALIVE=false
    break
  fi
done
if $ALL_ALIVE; then
  pass "All replicas serving traffic (5/5 requests succeeded)"
else
  fail "Some requests failed during multi-replica test"
fi

echo "  Scaling back to 1 replica..."
kubectl -n "$NAMESPACE" scale deployment/api --replicas=1 > /dev/null 2>&1

# =============================================================================
section "9. HPA CONFIGURED"
# =============================================================================

check "HPA 'api-hpa' exists" \
  kubectl get hpa api-hpa -n "$NAMESPACE"

HPA_MAX=$(kubectl get hpa api-hpa -n "$NAMESPACE" -o jsonpath='{.spec.maxReplicas}' 2>/dev/null || echo "0")
if [ "$HPA_MAX" = "5" ]; then
  pass "HPA max replicas = 5"
else
  fail "HPA max replicas = $HPA_MAX (expected 5)"
fi

HPA_TARGET=$(kubectl get hpa api-hpa -n "$NAMESPACE" -o jsonpath='{.spec.metrics[0].resource.target.averageUtilization}' 2>/dev/null || echo "0")
if [ "$HPA_TARGET" = "70" ]; then
  pass "HPA CPU target = 70%"
else
  fail "HPA CPU target = $HPA_TARGET% (expected 70)"
fi

# =============================================================================
section "10. END-TO-END CHAT"
# =============================================================================

echo "  Submitting chat request..."
CHAT_RESPONSE=$(curl -sf -X POST "$INGRESS_URL/api/chat?sync=true" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@verify.com","channel":"web","message":"What are your business hours?"}' 2>/dev/null || echo "")

if echo "$CHAT_RESPONSE" | grep -q "reply\|response\|message\|hours\|support"; then
  pass "End-to-end chat returned a response"
else
  fail "Chat did not return expected response: $CHAT_RESPONSE"
fi

# =============================================================================
section "RESULTS"
# =============================================================================

echo ""
echo "  Total: $TOTAL  |  Passed: $PASS  |  Failed: $FAIL"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo "  ALL TESTS PASSED — deployment is healthy."
  exit 0
else
  echo "  $FAIL TEST(S) FAILED — investigate before going live."
  exit 1
fi
