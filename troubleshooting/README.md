# Troubleshooting Demonstration

These exercises use separate demo objects and never break the real backend.

```bash
kubectl --context kind-mediqueue apply -f troubleshooting/broken-image.yaml
kubectl --context kind-mediqueue apply -f troubleshooting/broken-service.yaml
```

`scripts/troubleshooting-check.py` runs the whole sequence below, captures the
observed output into `evidence/troubleshooting.txt` and cleans the demo objects
up again.

## 1. ImagePullBackOff

```bash
kubectl --context kind-mediqueue -n mediqueue get pods -l app=broken-image-demo
kubectl --context kind-mediqueue -n mediqueue describe deployment broken-image-demo
kubectl --context kind-mediqueue -n mediqueue get events --sort-by=.lastTimestamp
```

The deliberately nonexistent tag `nginx:this-tag-does-not-exist` cannot be
pulled. The investigation path is:

```text
ImagePullBackOff
      ↓
describe pod / deployment
      ↓
wrong image tag in the manifest
      ↓
set a known-good image and watch the rollout
```

```bash
kubectl --context kind-mediqueue -n mediqueue set image deployment/broken-image-demo demo=nginx:stable-alpine
kubectl --context kind-mediqueue -n mediqueue rollout status deployment/broken-image-demo --timeout=180s
kubectl --context kind-mediqueue -n mediqueue delete deployment broken-image-demo
```

## 2. Service Has No Endpoints

```bash
kubectl --context kind-mediqueue -n mediqueue get endpointslices -l kubernetes.io/service-name=broken-backend-demo
kubectl --context kind-mediqueue -n mediqueue get pods --show-labels
```

Compare the Service selector `app=nonexistent-backend` with the real
`app=backend` pod labels. **No matching labels means no endpoints, which means
no traffic** — the Service is not broken, its selector is.

```bash
kubectl --context kind-mediqueue -n mediqueue set selector service/broken-backend-demo app=backend
kubectl --context kind-mediqueue -n mediqueue get endpointslices -l kubernetes.io/service-name=broken-backend-demo
kubectl --context kind-mediqueue -n mediqueue delete service broken-backend-demo
```

## 3. Database Or Migration Failure

```bash
kubectl --context kind-mediqueue -n mediqueue logs job/mediqueue-migrate-1
kubectl --context kind-mediqueue -n mediqueue get pods -l app=postgres
kubectl --context kind-mediqueue -n mediqueue describe pvc data-postgres-0
```

A running backend process is not proof of a healthy service: `/ready` performs a
real query against the `doctors` table and returns 503 when the database or the
schema is unavailable, so Kubernetes keeps the pod out of the Service endpoints
until the migration Job has succeeded.

## 4. A Pod Is Ready But Traffic Still Fails

Check what the Ingress actually routes to and whether the pod is in the
endpoint list:

```bash
kubectl --context kind-mediqueue -n mediqueue get ingress mediqueue -o yaml
kubectl --context kind-mediqueue -n mediqueue get endpointslices -l kubernetes.io/service-name=backend
kubectl --context kind-mediqueue -n mediqueue get endpointslices -l kubernetes.io/service-name=frontend
```

Readiness gates endpoint membership. A pod that is `Running` but not `Ready`
receives no traffic by design.

## 5. Helm Recovery

```bash
helm --kube-context kind-mediqueue history mediqueue -n mediqueue
helm --kube-context kind-mediqueue rollback mediqueue <revision> -n mediqueue --wait
```

A Helm rollback restores *chart configuration*; it does not reverse a database
migration. Backward-compatible schema changes and a tested restore procedure are
what make application rollback dependable.
