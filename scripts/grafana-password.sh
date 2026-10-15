#!/usr/bin/env bash
# Print the generated local Grafana password. Do not paste it into screenshots.
set -euo pipefail
kubectl --context kind-mediqueue -n mediqueue get secret mediqueue-grafana -o jsonpath='{.data.password}' | base64 -d
echo
