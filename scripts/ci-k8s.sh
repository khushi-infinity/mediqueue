#!/usr/bin/env bash
# Deploy the freshly built images into an ephemeral Kind cluster and smoke-test them.
set -euo pipefail
cd "$(dirname "$0")/.."
owner="${IMAGE_OWNER:-khushi-infinity}"

# The chart composes the image as "{{ repository }}:{{ tag }}", so the
# repository value must not carry a tag of its own.
backend_repository="ghcr.io/$owner/mediqueue-backend"
frontend_repository="ghcr.io/$owner/mediqueue-frontend"

kind load docker-image "$backend_repository:$IMAGE_TAG" "$frontend_repository:$IMAGE_TAG" --name mediqueue-ci
# Preload the database image so the migration Job does not race a slow first
# pull. kind can only load an image the Docker daemon already holds.
docker pull postgres:17-alpine
kind load docker-image postgres:17-alpine --name mediqueue-ci
kubectl apply -f k8s/namespace.yaml

password="$(openssl rand -hex 20)"
kubectl -n mediqueue create secret generic mediqueue-db \
  --from-literal=POSTGRES_DB=mediqueue --from-literal=POSTGRES_USER=mediqueue \
  --from-literal="POSTGRES_PASSWORD=$password" \
  --from-literal="DATABASE_URL=postgresql+psycopg://mediqueue:$password@postgres:5432/mediqueue"
kubectl -n mediqueue create secret generic mediqueue-grafana --from-literal="password=$(openssl rand -hex 20)"

image_args=(
  --set "backend.repository=$backend_repository" --set "backend.tag=$IMAGE_TAG"
  --set "frontend.repository=$frontend_repository" --set "frontend.tag=$IMAGE_TAG"
)

# Fail fast if the render would produce "repo:sha:sha", which the kubelet
# rejects as an invalid reference. The expensive alternative is an eight
# minute Helm wait that ends in a timeout.
rendered="$(helm template mediqueue helm/mediqueue -n mediqueue \
  "${image_args[@]}" --set autoscaling.enabled=false --set ingress.enabled=false)"
for expected in "$backend_repository:$IMAGE_TAG" "$frontend_repository:$IMAGE_TAG"; do
  if ! grep -qF "image: \"$expected\"" <<<"$rendered"; then
    echo "render did not produce the expected image reference: $expected" >&2
    exit 1
  fi
done

helm upgrade --install mediqueue helm/mediqueue -n mediqueue \
  "${image_args[@]}" \
  --set autoscaling.enabled=false --set ingress.enabled=false \
  --wait --wait-for-jobs --timeout 8m

# Prove the running pods use the freshly built image, not a stale tag.
for deployment in backend frontend; do
  running="$(kubectl -n mediqueue get deployment "$deployment" -o jsonpath='{.spec.template.spec.containers[0].image}')"
  echo "$deployment is running $running"
  [ "$running" = "ghcr.io/$owner/mediqueue-$deployment:$IMAGE_TAG" ] || {
    echo "unexpected image on $deployment: $running" >&2
    exit 1
  }
done

kubectl -n mediqueue run smoke --restart=Never --image=curlimages/curl:8.12.1 \
  --command -- sh -ec 'curl --fail --retry 10 http://backend:8000/ready && curl --fail http://frontend:8080/api/appointments && curl --fail http://prometheus:9090/-/ready'
kubectl -n mediqueue wait --for=jsonpath='{.status.phase}'=Succeeded pod/smoke --timeout=120s
kubectl -n mediqueue logs smoke
