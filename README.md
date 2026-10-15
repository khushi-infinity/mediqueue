# MediQueue

[![MediQueue CI/CD](https://github.com/khushi-infinity/mediqueue/actions/workflows/mediqueue.yml/badge.svg)](https://github.com/khushi-infinity/mediqueue/actions/workflows/mediqueue.yml)
[![Images: GHCR](https://img.shields.io/badge/images-ghcr.io%2Fkhushi--infinity-2496ed?logo=docker&logoColor=white)](https://github.com/khushi-infinity/mediqueue/pkgs/container/mediqueue-backend)

**Khushi Sarawagi | 24BCS10361**

MediQueue is a clinic appointment desk. Reception staff book, check in, complete
and cancel patient visits across six departments. Every appointment belongs to a
registered doctor, so department ownership lives in exactly one place. The
front desk searches patients, filters the queue by status or urgency, and reads
live counts without opening a single spreadsheet.

The application is an original domain implemented for the DevOps capstone, using
the architecture taught in the course.

**Start here:** [Submission status](SUBMISSION.md) | [Local quality review](LOCAL-REVIEW.md) | [Demo guide](demo/WALKTHROUGH.md) | [AWS deployment](terraform/README.md) | [Troubleshooting](troubleshooting/README.md)

**Verified locally:** 26 API tests, Ruff clean, a healthy Docker Compose stack,
a Kind cluster with all pods running and a completed migration Job, Prometheus
scraping every backend replica, the provisioned Grafana dashboard, Argo CD
reporting the application Synced and Healthy, 17 passing browser checks against
both Compose and Kubernetes, Helm lint and a 16-object render, and a valid
Terraform module tree. See [evidence](evidence/README.md) for the raw
transcripts and browser screenshots of the app and every dashboard.

## Architecture

```text
flowchart LR
  User[Browser] --> Ingress[Traefik Ingress]
  Ingress --> React[React / Nginx]
  Ingress --> API[FastAPI replicas]
  React --> API
  API --> DB[(PostgreSQL PVC)]
  Migration[Alembic Job] --> DB
  API --> Prometheus
  Prometheus --> Grafana
  Git[GitHub] --> CI[Tests / Build / Trivy]
  CI --> Registry[GHCR SHA images]
  Git --> Argo[Argo CD]
  Argo --> Helm[Helm manifests]
  Helm --> API
  Terraform --> AWS[AWS VPC / EKS / Nodes]
```

Local Kubernetes uses Kind on Docker Desktop. AWS infrastructure is a separate,
deliberately deferred deployment. Application data in Compose and Kubernetes
lives in separate PostgreSQL volumes.

## Stack

| Layer | Implementation |
| --- | --- |
| Frontend | React 19, Vite, Lucide icons, hand-written responsive CSS |
| API | Python 3.13, FastAPI, Pydantic validation, SQLAlchemy 2 |
| Database | PostgreSQL 17, two related tables, one Alembic migration |
| Quality | Pytest, Ruff, PostgreSQL integration tests in CI, Playwright |
| Containers | Non-root Python and multi-stage Nginx images |
| Automation | GitHub Actions, Trivy HIGH/CRITICAL gate, GHCR commit tags |
| Infrastructure | Terraform VPC, public/private subnets, NAT, EKS, EBS CSI |
| Deployment | Kubernetes, Helm, Traefik, HPA, readiness/liveness probes |
| GitOps | Argo CD application pointed at this repository |
| Monitoring | Prometheus per-pod scraping, Grafana provisioned dashboard |

## Local Setup

From this directory, with Docker Desktop running:

```bash
docker compose up --build -d
python3 scripts/seed.py
```

| Surface | Address |
| --- | --- |
| Application | <http://localhost:3000> |
| API docs | <http://localhost:8000/docs> |
| Liveness | <http://localhost:8000/health> |
| Database readiness | <http://localhost:8000/ready> |
| Metrics | <http://localhost:8000/metrics> |

The seed script inserts synthetic demonstration patients, doctors and
appointments. They are example data, not real patient records. Compose defaults
are for a loopback-only classroom environment; use `.env.example` to choose a
different database password. Choose a long random alphanumeric value, because
this Compose file interpolates it into the connection URL — do not URL-encode
the shared password.

```bash
docker compose ps
docker compose logs backend
docker compose exec postgres psql -U mediqueue -d mediqueue \
  -c "SELECT id, patient_name, status FROM appointments ORDER BY id;"
docker compose down
```

`down` preserves the database volume. Adding `-v` permanently deletes local data.

## API

| Method | Route | Behavior |
| --- | --- | --- |
| GET | `/` | Service identity and links |
| GET | `/api/appointments` | List; optional `status`, `department`, `urgency`, `doctor_id`, `q`, `limit`, `offset` |
| GET | `/api/appointments/{id}` | Retrieve one appointment or return 404 |
| POST | `/api/appointments` | Validate and book an appointment, return 201 |
| PUT | `/api/appointments/{id}` | Update all editable fields |
| DELETE | `/api/appointments/{id}` | Delete an appointment, return 204 |
| GET | `/api/doctors` | List doctors; optional `department`, `active` |
| GET | `/api/doctors/{id}` | Retrieve one doctor or return 404 |
| POST | `/api/doctors` | Register a doctor, return 201 |
| PUT | `/api/doctors/{id}` | Update a doctor |
| DELETE | `/api/doctors/{id}` | Delete an unused doctor, 409 if already booked |
| GET | `/api/stats` | Counts by status plus unresolved urgent appointments |
| GET | `/health`, `/ready`, `/metrics` | Operational endpoints |

Invalid inputs return 422. Booking an unknown or inactive doctor returns 422.
Search escapes SQL wildcard characters. Request metrics use route templates
rather than appointment or doctor IDs, so metric label cardinality stays bounded.

## Tests And Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd backend
../.venv/bin/python -m pytest -v
../.venv/bin/python -m ruff check .
```

Tests cover CRUD on both resources, filters, statistics, pagination stability,
wildcard escaping, validation of every constrained field, missing IDs, the
doctor-deletion conflict, readiness failure and metric label cardinality. Local
unit tests use isolated in-memory SQLite; CI additionally runs them against a
dedicated PostgreSQL database with each test inside a rolled-back transaction.
No test touches application data.

Browser regression checks exercise the running application, including real CRUD,
validation, responsive layout at 320/768/1920 px, and mocked failure, empty and
pagination boundaries. CI runs them against its isolated Kubernetes deployment
before publishing:

```bash
npm --prefix frontend ci
node frontend/node_modules/playwright/cli.js install chromium
node scripts/browser-check.mjs
```

No seed data is required: the check registers its own doctor if the roster is
empty and deletes the appointment it creates. Use `APP_URL` to target another
deployment.

For a lightweight development server, run `alembic upgrade head` and
`uvicorn app.main:app --port 8000` inside `backend`, then `npm ci` and
`npm run dev` inside `frontend`. SQLite is the development fallback when
`DATABASE_URL` is unset; both deployment paths use PostgreSQL.

## CI/CD And Security

The workflow is [`.github/workflows/mediqueue.yml`](.github/workflows/mediqueue.yml).
It triggers on pushes to `main`, pull requests touching application paths, and
manual runs. GitOps promotion commits use `[skip ci]` to avoid redundant builds.

1. Ruff, Alembic, pytest against PostgreSQL and the frontend production build run.
2. Helm and Terraform are validated without creating cloud resources.
3. Both Docker images are built and tagged with the full Git commit SHA.
4. Trivy scans both images and blocks the pipeline on any HIGH or CRITICAL finding.
5. An ephemeral Kind cluster deploys the Helm chart and runs smoke and browser tests.
6. A successful `main`-branch run publishes both images to GHCR.
7. CI commits those verified SHA tags to `helm/mediqueue/values-release.json`, and
   Argo CD reconciles that release.

Test and scan reports are uploaded as workflow artifacts. There is no
`continue-on-error` on the quality or security gates. Trivy covers installed OS
and application packages; it does not establish that application authorization
or business logic is secure.

Registry names:

```text
ghcr.io/khushi-infinity/mediqueue-backend:<full-commit-sha>
ghcr.io/khushi-infinity/mediqueue-frontend:<full-commit-sha>
```

New GHCR packages may be private. Make them public in package settings, or
configure a Kubernetes image-pull Secret using a token with `read:packages`.
Never commit that token.

## Local Kubernetes And Helm

Install Kind, Helm 3 and kubectl. With Docker running, bootstrap a new cluster:

```bash
bash scripts/local-k8s.sh
python3 scripts/seed.py --url http://mediqueue.localhost:8088
kubectl --context kind-mediqueue -n mediqueue get pods,svc,ingress,hpa
helm --kube-context kind-mediqueue list -n mediqueue
```

The script creates only a dedicated `mediqueue` cluster, generates local
Secrets, builds and loads single-platform images, installs Traefik and Metrics
Server, and installs the Helm chart. It refuses to overwrite an application
already managed by Argo CD. Backend and frontend each run at least two replicas.
A migration Job prepares the database before backend readiness succeeds.
PostgreSQL uses a StatefulSet and a PersistentVolumeClaim.

| Service | Local address |
| --- | --- |
| Ingress | <http://mediqueue.localhost:8088> |
| Prometheus | <http://localhost:9090> |
| Grafana | <http://localhost:3001> |

Grafana username: `admin`. Retrieve the generated password locally with
`bash scripts/grafana-password.sh`. Do not include it in screenshots.

If your system does not resolve `mediqueue.localhost`, verify routing directly:

```bash
curl -H "Host: mediqueue.localhost" http://127.0.0.1:8088/api/appointments
```

## Observability And Autoscaling

The chart provisions Prometheus and Grafana. Prometheus discovers every backend
replica through a headless Service, so one replica's request counters cannot
hide another's. The Grafana dashboard `MediQueue / Service Health` displays
healthy replicas, request rate, p95 latency, per-route traffic and status codes.

```bash
python3 scripts/load.py --url http://mediqueue.localhost:8088 --seconds 60 --workers 4
kubectl --context kind-mediqueue -n mediqueue get hpa
kubectl --context kind-mediqueue -n mediqueue top pods
```

The HPA targets 70% CPU and scales between two and four backend replicas. A
40-second run of the load script was enough to push the backend from two
replicas to three on a single-node Kind cluster, and it returned to two once the
load stopped — an observed scale-out rather than a configured one. Prometheus
defines unavailable-backend and error-ratio alerts. No external alert
notification destination is configured in the local demonstration.

## Argo CD And GitOps

[`gitops/application.yaml`](gitops/application.yaml) tracks this repository's
Helm chart on `main`. It passes two value files, and later files win:
`values-release.json` is the CI-promoted release, and `values-local.yaml` is
applied last so a local cluster uses the images loaded with
`kind load docker-image` rather than registry digests. CI updates
`values-release.json` only after tests, scans and the ephemeral Kubernetes smoke
deployment pass. On AWS, swap the last file for `values-aws.yaml` so the promoted
GHCR images are pulled normally. Automated sync and self-healing are enabled;
automatic pruning is disabled. Promotion commits use `[skip ci]` to avoid an
image-build loop.

After the local Helm bootstrap, transfer deployment ownership to Argo CD:

```bash
bash scripts/local-gitops.sh
```

This installs a pinned Argo CD chart, applies the Ingress and the Application,
and waits for Synced/Healthy status. The local Argo CD UI is at
<http://argocd.localhost:8088>; its `admin` password lives in the
`argocd-initial-admin-secret` Secret in the `argocd` namespace.

Use one deployment owner at a time. Bootstrap with Helm for the Helm
demonstration, then let Argo CD reconcile the rendered resources for the GitOps
demonstration. Argo CD uses Helm as a template renderer; its syncs do not create
Helm release history. The initial Helm demonstration uses loaded local images.
The GitOps demonstration pulls the scanned registry images by immutable SHA.
For AWS, replace the local networking values with `values-aws.yaml` and configure
the cloud cluster destination.

Until the repository is pushed to GitHub, GitOps can still be verified against
any reachable clone of it by overriding the tracked repository:

```bash
git clone --bare . /tmp/gitserve/mediqueue.git
git daemon --reuseaddr --export-all --base-path=/tmp/gitserve --port=9418 &
ARGO_REPO_URL=git://172.29.0.1:9418/mediqueue.git bash scripts/local-gitops.sh
```

`172.29.0.1` is the Docker bridge gateway on this machine; substitute the value
from `docker network inspect kind`. Every other field of the Application,
including the Helm path and value files, stays exactly as committed.

Once the repository is pushed, point Argo CD at GitHub and stop the mirror:

```bash
kubectl --context kind-mediqueue -n argocd apply -f gitops/application.yaml
pkill -f git-daemon
```

## AWS Infrastructure

[`terraform/`](terraform/README.md) provisions two public and two private
subnets, one NAT gateway, an EKS cluster, a managed node group and an EBS CSI
IAM role. EKS API access is limited to supplied CIDRs. AWS is **prepared but
deferred**, so no AWS screenshots exist and no cloud bill was incurred. See the
[AWS runbook](terraform/README.md) for plan, deployment and cleanup.

## Known Limits

- This is a classroom clinic desk with no authentication or RBAC; keep it local
  or add authentication before exposing real patient data on a public network.
- PostgreSQL is a single instance. A production service needs backups, recovery
  tests, encryption policy and preferably a managed database.
- Local Prometheus and Grafana storage is ephemeral; PostgreSQL data is persistent.
- AWS plan/apply/destroy proof and a complete AWS walkthrough require a real account.
- Local screenshots cannot stand in for a successful GitHub Actions run.
- The demo video must be recorded by the author; a generated deck is not a substitute.

## Sources

- [Current project brief](https://github.com/Nency-Ravaliya/devsecops-python/blob/main/README.md)
- [Grading rubric](https://github.com/Nency-Ravaliya/devsecops-python/blob/main/GRADING.md)
- [Submission instructions](https://github.com/Nency-Ravaliya/devsecops-python/blob/main/SUBMISSION.md)
- Clinic illustration: original SVG drawn for this project (`frontend/public/clinic.svg`)
