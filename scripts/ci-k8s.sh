#!/usr/bin/env bash
# Deploy the freshly built images into an ephemeral Kind cluster and smoke-test them.
set -euo pipefail
cd "$(dirname "$0")/.."
owner="${IMAGE_OWNER:-khushi-infinity}"
backend="ghcr.io/$owner/mediqueue-backend:$IMAGE_TAG"
frontend="ghcr.io/$owner/mediqueue-frontend:$IMAGE_TAG"

kind load docker-image "$backend" "$frontend" --name mediqueue-ci
kind load docker-image postgres:17-alpine --name mediqueue-ci || true
kubectl apply -f k8s/namespace.yaml

password="$(openssl rand -hex 20)"
kubectl -n mediqueue create secret generic mediqueue-db \
  --from-literal=POSTGRES_DB=mediqueue --from-literal=POSTGRES_USER=mediqueue \
  --from-literal="POSTGRES_PASSWORD=$password" \
  --from-literal="DATABASE_URL=postgresql+psycopg://mediqueue:$password@postgres:5432/mediqueue"
kubectl -n mediqueue create secret generic mediqueue-grafana --from-literal="password=$(openssl rand -hex 20)"

helm upgrade --install mediqueue helm/mediqueue -n mediqueue \
  --set backend.tag="$IMAGE_TAG" --set frontend.tag="$IMAGE_TAG" \
  --set backend.repository="$backend" --set frontend.repository="$frontend" \
  --set autoscaling.enabled=false --set ingress.enabled=false \
  --wait --wait-for-jobs --timeout 8m

kubectl -n mediqueue run smoke --restart=Never --image=curlimages/curl:8.12.1 \
  --command -- sh -ec 'curl --fail --retry 10 http://backend:8000/ready && curl --fail http://frontend:8080/api/appointments && curl --fail http://prometheus:9090/-/ready'
kubectl -n mediqueue wait --for=jsonpath='{.status.phase}'=Succeeded pod/smoke --timeout=120s
kubectl -n mediqueue logs smoke
