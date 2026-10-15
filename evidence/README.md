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
node scripts/render-evidence.mjs               # terminal screenshots of the transcripts
ARGO_PASSWORD="$(bash scripts/argocd-password.sh)" node scripts/dashboard-screenshots.mjs
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
| `screenshots/` | Terminal-style renderings of every `.txt` transcript above |
| `dashboards/` | Browser captures of the Prometheus and Argo CD UIs and the app through the Ingress |

## Dashboards

Captured in a real browser against the running cluster, not composed by hand.

| File | What it shows |
| --- | --- |
| `dashboards/prometheus-targets.png` | Every backend replica discovered by the `mediqueue` job, all `UP` |
| `dashboards/prometheus-graph.png` | A live `rate()` graph of request rate broken down by route |
| `dashboards/prometheus-alerts.png` | The two configured alert rules |
| `dashboards/prometheus-rules.png` | The loaded rule group with its expressions |
| `dashboards/argocd-applications.png` | The Argo CD applications list, showing `mediqueue` Synced and Healthy |
| `dashboards/argocd-mediqueue.png` | The application detail view with its resource tree |
| `dashboards/app-ingress.png` | The application served through the Ingress hostname, no port-forward |
| `grafana-dashboard.png` | The provisioned Grafana dashboard with live panels |

The Prometheus graphs and the Grafana panels were captured while a load test was
running, so they show real traffic. Argo CD is captured separately with the load
stopped: its UI ships a large JavaScript bundle, and on a single-node cluster a
saturating load test can starve the server past the page timeouts.

Regenerate them with:

```bash
python3 scripts/load.py --url http://mediqueue.localhost:8088 --seconds 200 --workers 4 &
DASHBOARDS=prometheus,app node scripts/dashboard-screenshots.mjs
GRAFANA_PASSWORD="$(bash scripts/grafana-password.sh)" node scripts/grafana-screenshot.mjs
DASHBOARDS=argo ARGO_PASSWORD="$(bash scripts/argocd-password.sh)" node scripts/dashboard-screenshots.mjs
```

## About The Screenshots

Several rubrics ask for screenshots of command output. `screenshots/*.png` are
plain renderings of the `.txt` transcripts next to them: the script reads the
captured file and draws its text into a terminal-shaped frame, with the recorded
command in the title bar. Nothing is retyped, and the `.txt` file remains the
source of truth. Transcripts longer than 45 lines are cut with a marker saying
how many lines continue in the text file.

`screenshots/kubernetes.png`, `screenshots/helm.png` and `screenshots/compose.png`
are the images M4 and M8 ask for, and `screenshots/commit-history.png` is the
commit history M3 asks for.

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
