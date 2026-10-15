# Evidence

Raw output captured from commands that were actually run on this machine, plus
screenshots taken from the running application. Nothing here is hand-written or
synthesised.

Regenerate the command-based captures with:

```bash
python3 scripts/collect-evidence.py            # or --compose-build to rebuild first
python3 scripts/troubleshooting-check.py       # the failure-simulation transcript
node scripts/browser-check.mjs                 # application screenshots
GRAFANA_PASSWORD="$(bash scripts/grafana-password.sh)" node scripts/grafana-screenshot.mjs
```

Each `*.txt` file records the timestamp, the exact command and its exit code.
The matching `*.json` file carries the same result in machine-readable form.

## Real Deployment Evidence

| File | What it shows |
| --- | --- |
| `pytest.txt` | 26 API tests passing |
| `ruff.txt` | Ruff reporting no findings |
| `compose.txt` | The Docker Compose services and their health |
| `compose-build.txt` | A full `docker compose up --build` |
| `non-root.txt` | Image users `10001` (API) and `101` (Nginx), never root |
| `kubernetes.txt` | Pods, Services, Ingress and HPA in the `mediqueue` namespace |
| `helm.txt` | The installed Helm release and its revision history |
| `terraform-validate.txt` | `terraform validate` on the initialised module tree |
| `metrics.txt` | The Prometheus exposition from `GET /metrics` |
| `prometheus-targets.json` | Both backend replicas scraped by the `mediqueue` job |
| `argocd.json` | The Argo CD Application, its sync and health status |
| `commit-history.txt` | The commit log |
| `troubleshooting.txt` | `ImagePullBackOff` and an endpoint-less Service, diagnosed, repaired and cleaned up |
| `application-desktop.png` | The dashboard at 1440 px against the Compose stack |
| `application-mobile.png` | The dashboard at 390 px |
| `appointment-create.png` | The booking dialog |
| `appointment-mobile.png` | The booking dialog on a phone viewport |
| `grafana-dashboard.png` | The provisioned `MediQueue / Service Health` dashboard with live data |
| `browser-results.json` | The list of checks that passed |
| `k8s/` | The same browser suite and screenshots, captured against the Kubernetes deployment |

## Observed Scale-Out

During the 40-second load test the HorizontalPodAutoscaler raised the backend
Deployment from 2 to 3 replicas and reported `cpu: 55%/70%`. That is an observed
scale-out, not just a configured limit. `kubernetes.txt` captures the resulting
replica count.

## What Is Deliberately Mocked

The browser suite intercepts three responses so that states which are hard to
produce on demand can still be verified:

- a `503` from the appointment list, to prove the error panel and the disabled
  pagination controls
- 24 fixture rows, to prove the page boundary at 12 rows
- an empty list, to prove the empty-queue call to action

These are labelled `"mocked"` inside `browser-results.json` and are **not**
deployment evidence. Every create, update, delete, search and render assertion
runs against the real API and the real database.

## What Is Not Here

- No GitHub Actions run, because the repository has not been pushed yet.
- No AWS console screenshots, because the AWS deployment is deferred.
- No demo video, which must be recorded by the author.
