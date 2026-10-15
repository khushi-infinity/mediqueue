#!/usr/bin/env bash
# Hand deployment ownership from Helm to Argo CD. Requires the Kind bootstrap first.
set -euo pipefail
cd "$(dirname "$0")/.."
context="kind-mediqueue"

if ! kubectl --context "$context" -n mediqueue get svc frontend >/dev/null 2>&1; then
  echo "Run scripts/local-k8s.sh first: no MediQueue release found in the cluster." >&2
  exit 1
fi

helm repo add argo https://argoproj.github.io/argo-helm >/dev/null 2>&1 || true
# Update only the repository this script uses: an unrelated unreachable index
# must not be able to abort the install.
helm repo update argo >/dev/null
helm --kube-context "$context" upgrade --install argocd argo/argo-cd \
  -n argocd --create-namespace -f gitops/values-argocd.yaml --version 7.7.11 --wait --timeout 10m

kubectl --context "$context" apply -f gitops/argocd-ingress.yaml

# ARGO_REPO_URL lets you verify GitOps before the repository is pushed to GitHub.
# Point it at any reachable clone of this repository, for example a local mirror:
#   git clone --bare . /tmp/gitserve/mediqueue.git && git daemon --reuseaddr \
#     --export-all --base-path=/tmp/gitserve --port=9418 &
#   ARGO_REPO_URL=git://172.29.0.1:9418/mediqueue.git bash scripts/local-gitops.sh
if [ -n "${ARGO_REPO_URL:-}" ]; then
  echo "Rendering the Application against $ARGO_REPO_URL"
  sed "s#repoURL: .*#repoURL: $ARGO_REPO_URL#" gitops/application.yaml > /tmp/mediqueue-application.yaml
  kubectl --context "$context" apply -f /tmp/mediqueue-application.yaml
else
  kubectl --context "$context" apply -f gitops/application.yaml
fi

echo "Waiting for Argo CD to reconcile the Helm chart from Git..."
kubectl --context "$context" -n argocd wait --for=jsonpath='{.status.sync.status}'=Synced application/mediqueue --timeout=600s
kubectl --context "$context" -n argocd wait --for=jsonpath='{.status.health.status}'=Healthy application/mediqueue --timeout=600s
kubectl --context "$context" -n argocd get application mediqueue

echo
echo "Argo CD UI: http://argocd.localhost:8088"
echo "Username:   admin"
echo "Password:   kubectl --context $context -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
echo
echo "Use one deployment owner at a time. Helm created this release for the Helm demo;"
echo "Argo CD now renders the same chart for the GitOps demo."
