#!/usr/bin/env bash
# Bootstrap a dedicated local Kind cluster with Traefik, Metrics Server and the Helm release.
# Requires Docker Desktop, kind, kubectl and Helm 3. Intended for a loopback-only classroom demo.
set -euo pipefail
cd "$(dirname "$0")/.."
context="kind-mediqueue"

if ! kind get clusters 2>/dev/null | grep -qx mediqueue; then
  kind create cluster --config k8s/kind.yaml
fi
kubectl --context "$context" apply -f k8s/namespace.yaml

if kubectl --context "$context" -n mediqueue get deployment backend | grep -q .; then
  if kubectl --context "$context" -n mediqueue get application.argoproj.io mediqueue >/dev/null 2>&1; then
    echo "MediQueue is already managed by Argo CD. Remove the Application before a Helm-owned bootstrap." >&2
    exit 1
  fi
fi

docker build -t mediqueue-backend:local backend
docker build -t mediqueue-frontend:local frontend
kind load docker-image mediqueue-backend:local mediqueue-frontend:local --name mediqueue

password="$(openssl rand -hex 20)"
kubectl --context "$context" -n mediqueue create secret generic mediqueue-db \
  --from-literal=POSTGRES_DB=mediqueue --from-literal=POSTGRES_USER=mediqueue \
  --from-literal="POSTGRES_PASSWORD=$password" \
  --from-literal="DATABASE_URL=postgresql+psycopg://mediqueue:$password@postgres:5432/mediqueue" \
  --dry-run=client -o yaml | kubectl --context "$context" apply -f -
kubectl --context "$context" -n mediqueue create secret generic mediqueue-grafana \
  --from-literal="password=$(openssl rand -hex 20)" \
  --dry-run=client -o yaml | kubectl --context "$context" apply -f -

helm repo add traefik https://traefik.github.io/charts >/dev/null 2>&1 || true
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ >/dev/null 2>&1 || true
helm repo update >/dev/null
helm --kube-context "$context" upgrade --install traefik traefik/traefik \
  -n kube-system -f k8s/traefik-values.yaml --wait
helm --kube-context "$context" upgrade --install metrics-server metrics-server/metrics-server \
  -n kube-system --set 'args={--kubelet-insecure-tls}' --wait

helm --kube-context "$context" upgrade --install mediqueue helm/mediqueue \
  -n mediqueue -f helm/mediqueue/values-local.yaml \
  --wait --wait-for-jobs --timeout 10m

kubectl --context "$context" -n mediqueue get pods,svc,ingress,hpa
echo
echo "Ingress:    http://mediqueue.localhost:8088"
echo "Prometheus: http://localhost:9090"
echo "Grafana:    http://localhost:3001"
echo "Seed data:  python3 scripts/seed.py --url http://mediqueue.localhost:8088"
