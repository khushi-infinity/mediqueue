#!/usr/bin/env bash
# Print the generated local Argo CD admin password. Do not paste it into screenshots.
set -euo pipefail
kubectl --context kind-mediqueue -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d
echo
