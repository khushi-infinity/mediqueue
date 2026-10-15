# Demonstration Walkthrough

A complete pass through every layer of the project. Run the commands in order;
each block states what you should see.

---

## 0. Before you start

```bash
python3 -m venv .venv && .venv/bin/python -m pip install -r backend/requirements-dev.txt
```

Requirements: Docker Desktop (or another Docker engine), Node 20+, Python 3.13,
Helm 3, kubectl, kind and Terraform 1.11+.

---

## 1. The application

```bash
docker compose up --build -d
python3 scripts/seed.py
```

Open <http://localhost:3000>.

* The dashboard shows four KPI cards, a status tab strip, a search box and an
  appointment queue.
* Book an appointment, change its status to **Completed**, search for the
  patient, then delete it.
* Point out that every number on screen came from `/api/stats` and
  `/api/appointments`, not from hard-coded demo state.

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
curl -s http://localhost:8000/metrics | head
open http://localhost:8000/docs
```

* `/health` is a cheap liveness signal.
* `/ready` performs a real database query and returns 503 if the schema is
  missing.
* `/docs` is the generated Swagger UI covering all 11 routes.

Show the data really is in PostgreSQL:

```bash
docker compose exec postgres psql -U mediqueue -d mediqueue \
  -c "SELECT a.id, a.patient_name, d.full_name, a.status FROM appointments a JOIN doctors d ON d.id = a.doctor_id ORDER BY a.id LIMIT 5;"
```

---

## 2. Tests and code quality

```bash
cd backend && ../.venv/bin/python -m ruff check . && ../.venv/bin/python -m pytest -v
cd ..
```

26 tests cover CRUD on two resources, filters, statistics, pagination
stability, wildcard escaping, validation, 404/409 handling, readiness failure
and metrics label cardinality. Tests run against isolated in-memory SQLite
locally and a dedicated PostgreSQL database in CI — never application data.

---

## 3. Git and GitHub

```bash
git log --oneline
```

Every commit is a meaningful, scoped change, and every one is authored as
`Khushi Sarawagi <248908730+khushi-infinity@users.noreply.github.com>`, so they
link to the GitHub account. Open
<https://github.com/khushi-infinity/mediqueue> and show the commit history: at
least ten commits, Conventional Commit subjects, no credentials anywhere in it.

---

## 4. CI/CD pipeline

Open the run that is already green rather than pushing a new commit:
<https://github.com/khushi-infinity/mediqueue/actions/runs/38755163712>. Both
jobs passed in five minutes.

1. **test** — ruff, Alembic, pytest against PostgreSQL, frontend production
   build, `helm lint`, `terraform validate`.
2. **build-scan-deploy** — build both images tagged with the commit SHA, scan
   both with Trivy (`exit-code: 1`), create an ephemeral Kind cluster, deploy
   the chart, run a smoke test, run the Playwright suite through a port-forward,
   publish to GHCR and commit the verified SHA into `values-release.json`.

Download the run's artifacts and show them, or open the captures already in the
repository:

- `evidence/ci-trivy.txt` — 0 vulnerabilities in the Alpine layer and every
  Python package, in both images.
- `evidence/ci-tests.txt` — 26 tests, 0 failures, from the runner.
- `evidence/ci-browser.txt` — 17 browser checks, 0 failures, from the runner.
- `evidence/dashboards/github-run.png` and `github-packages.png` — the run page
  and the GHCR package page, with the image tagged by commit SHA.

The packages are public, so anyone can pull
`ghcr.io/khushi-infinity/mediqueue-backend:<commit-sha>` without credentials.

---

## 5. Terraform

```bash
cd terraform
terraform init
terraform plan
```

Show the plan: two public subnets, two private subnets, one NAT gateway, an EKS
cluster and a managed node group. With a real account, `terraform apply` and the
AWS console screenshots belong here; `terraform destroy` proves no runaway cost.

---

## 6. Kubernetes and Helm

```bash
bash scripts/local-k8s.sh
kubectl --context kind-mediqueue -n mediqueue get pods,svc,ingress,hpa
helm --kube-context kind-mediqueue list -n mediqueue
open http://mediqueue.localhost:8088
```

* Two frontend replicas, two-or-more backend replicas, one Postgres pod.
* The `mediqueue-migrate-1` Job completed before the backend became Ready.
* The Ingress routes `/api` to the backend Service and `/` to the frontend.

If `mediqueue.localhost` does not resolve on your machine:

```bash
curl -H "Host: mediqueue.localhost" http://127.0.0.1:8088/api/appointments
```

---

## 7. Observability and autoscaling

```bash
python3 scripts/load.py --url http://mediqueue.localhost:8088 --seconds 60 --workers 4
kubectl --context kind-mediqueue -n mediqueue get hpa
kubectl --context kind-mediqueue -n mediqueue top pods
```

* <http://localhost:9090/targets> shows the backend job `UP`.
* <http://localhost:3001> shows the provisioned **MediQueue / Service Health**
  dashboard with live request rate, p95 latency and status-code panels.
* The HPA targets 70% CPU across 2–4 replicas. A 40-second run of
  `scripts/load.py` on a single-node cluster is enough to push it from two
  replicas to three; when the load stops it returns to two.

---

## 8. GitOps with Argo CD

```bash
bash scripts/local-gitops.sh
```

Argo CD syncs `helm/mediqueue` from `main` **on GitHub**, rendering the
CI-promoted `values-release.json` first and the `values-local.yaml` overlay last,
so the local cluster uses its loaded images. Show the Application as **Synced**
and **Healthy** with the tracked revision matching the pushed commit, then change
a value in Git and watch self-healing reconcile it.

Offline, or before a push, the same thing can be rehearsed against a local
mirror: `ARGO_REPO_URL=git://host.docker.internal:9418/mediqueue.git
bash scripts/local-gitops.sh` (see the README for the two commands that create
the mirror).

---

## 9. Failure simulation

```bash
python3 scripts/troubleshooting-check.py
```

Watch an `ImagePullBackOff` and an endpoint-less Service be diagnosed, repaired
and cleaned up. `evidence/troubleshooting.txt` holds the captured transcript.

---

## 10. Wrap up

```bash
docker compose down          # keeps the database volume
kind delete cluster --name mediqueue
cd terraform && terraform destroy
```

State the honest limits: no authentication or RBAC, a single PostgreSQL
instance, ephemeral Prometheus and Grafana storage, and an observability stack
whose alerts have no external notification target.
