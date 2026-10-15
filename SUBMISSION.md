# Submission Status

MediQueue — Khushi Sarawagi · 24BCS10361

Module-by-module status against the course grading rubric. "Verified here" means
the raw command output or browser capture exists in [`evidence/`](evidence/README.md).

## Module Summary

| Module | Topic | Points | Status |
| --- | --- | --- | --- |
| M1 | Application — frontend, backend, database | 10 | Complete and verified locally |
| M2 | Testing — pytest and code quality | 10 | Complete and verified locally |
| M3 | Git and GitHub | 5 | Local history complete; push pending |
| M4 | Docker — Dockerfile and Compose | 10 | Complete and verified locally |
| M5 | CI/CD — GitHub Actions | 15 | Workflow complete; a green run needs a push |
| M6 | DevSecOps — Trivy scan | 5 | Configured as a hard gate; run output needs a push |
| M7 | Terraform — AWS infrastructure as code | 15 | Written and validated; apply deferred |
| M8 | Kubernetes + Helm | 15 | Complete and verified on a local Kind cluster |
| M9 | Observability — Prometheus + Grafana | 10 | Complete and verified on a local Kind cluster |
| M10 | Final presentation and documentation | 5 | README and slide deck complete; video pending |

## M1 — Application

| Criterion | Where |
| --- | --- |
| FastAPI starts and answers `/health` | `backend/app/main.py`, `evidence/` |
| At least four REST endpoints with GET/POST/PUT/DELETE | 11 routes across two resources |
| PostgreSQL table managed by Alembic | `backend/alembic/versions/0001_initial.py`, two tables |
| React frontend renders and calls the API | `frontend/src/main.jsx` |
| Responsive, usable UI | Screenshots at 320/390/768/1440/1920 px |

## M2 — Testing

| Criterion | Where |
| --- | --- |
| `pytest` runs without errors | `evidence/pytest.txt` |
| At least five cases over at least three endpoints | 26 cases |
| Tests never touch the production database | Dependency override plus rolled-back transaction |
| `pytest.ini` present | `backend/pytest.ini` |
| Ruff clean | `evidence/ruff.txt` |

## M3 — Git And GitHub

| Criterion | Where |
| --- | --- |
| Public repository | To be pushed to `github.com/khushi-infinity/mediqueue` |
| Meaningful commit messages | `git log`, `evidence/commit-history.txt` |
| Commit history screenshot, at least 10 commits | `evidence/screenshots/commit-history.png` (11 commits) |
| `.gitignore` covers `.env`, `__pycache__`, `node_modules`, `.venv` | `.gitignore` |

## M4 — Docker

| Criterion | Where |
| --- | --- |
| `backend/Dockerfile` builds | `evidence/compose-build.txt`, `evidence/screenshots/compose-build.png` |
| Multi-stage frontend build | `frontend/Dockerfile` |
| Non-root runtime users | `evidence/non-root.txt` (UIDs 10001 and 101) |
| `docker compose up --build` starts the stack | `evidence/compose.txt`, `evidence/screenshots/compose.png` |
| Browser at `localhost:3000` | `evidence/application-desktop.png` |

## M5 — CI/CD

| Criterion | Where |
| --- | --- |
| Workflow file present | `.github/workflows/mediqueue.yml` |
| Triggers on push to `main` | `on.push.branches` |
| Pytest fails the build | Job `test`, no `continue-on-error` |
| Frontend built in the pipeline | `npm ci && npm run build` |
| Both images built | Job `build-scan-deploy` |
| Images pushed to GHCR | `docker push` after the gates pass |
| SHA image tags, not `latest` | `${{ github.sha }}` and `scripts/promote.py` |

## M6 — DevSecOps

| Criterion | Where |
| --- | --- |
| Trivy scans both images | Two `aquasecurity/trivy-action` steps |
| Fails on HIGH or CRITICAL | `severity: HIGH,CRITICAL`, `exit-code: '1'` |
| Explain the result | `SECURITY-NOTES.md` |

## M7 — Terraform

| Criterion | Where |
| --- | --- |
| Valid HCL in `terraform/` | `versions.tf`, `variables.tf`, `main.tf`, `outputs.tf` |
| `terraform init` succeeds | `evidence/terraform-validate.txt` |
| `terraform plan` is non-empty | Requires a real account; deferred |
| VPC with two public subnets | `module.vpc.public_subnets` |
| EKS with a worker node group | `module.eks.eks_managed_node_groups` |
| `terraform destroy` | Deferred with apply |
| `terraform.tfvars.example` with no credentials | `terraform/terraform.tfvars.example` |

## M8 — Kubernetes + Helm

| Criterion | Where |
| --- | --- |
| `k8s/namespace.yaml` applies | `evidence/kubernetes.txt` |
| Chart with `Chart.yaml`, `values.yaml`, templates | `helm/mediqueue/` |
| `helm upgrade --install` deploys without errors | `evidence/helm.txt`, `evidence/screenshots/helm.png` |
| Two replicas each for backend and frontend | `values.yaml` |
| ClusterIP Services | `helm/mediqueue/templates/application.yaml` |
| Ingress routes `/` to frontend and `/api` to backend | `helm/mediqueue/templates/networking.yaml` |
| Ingress reachable at `mediqueue.localhost:8088` | `README.md` (Local Kubernetes) |
| All pods `Running`, migration Job `Complete` | `evidence/kubernetes.txt`, `evidence/screenshots/kubernetes.png` |
| HPA observed scaling the backend 2 → 3 and back to 2 | `LOCAL-REVIEW.md` (What Was Actually Run) |
| Argo CD reconciled the chart to `Synced`/`Healthy` | `evidence/argocd.json` |
| The UI passes the browser suite on Kubernetes | `evidence/k8s/browser-results.json` |

## M9 — Observability

| Criterion | Where |
| --- | --- |
| `/metrics` returns Prometheus format | `evidence/metrics.txt` |
| Prometheus installed and scraping every backend replica | `evidence/prometheus-targets.json` |
| Grafana installed and reachable | `evidence/kubernetes.txt` |
| At least one live dashboard panel | `helm/mediqueue/dashboards/mediqueue.json` |
| The provisioned dashboard rendering live data | `evidence/grafana-dashboard.png` |
| A load test producing real counters and route labels | `evidence/prometheus-targets.json` |

## M10 — Presentation And Documentation

| Criterion | Where |
| --- | --- |
| `README.md` with full technical documentation | `README.md` |
| Slide deck committed | `demo/slides.pdf` (generated by `scripts/build-slides.py`) |
| Presentation video in the repository | **Outstanding — must be recorded by the author** |

## Open Items

1. **Push to GitHub.** The CI evidence (pipeline run, Trivy output, GHCR package
   pages) can only exist after the repository is pushed and the workflow runs.
2. **Record the demo video** and commit it under `demo/`. The grading rubric
   treats a missing video as zero for M10.
3. **AWS apply and destroy**, with console screenshots, if the evaluation
   requires real cloud proof. The code is ready and validated.
4. **HPA scale-out** was observed locally (2 → 3 replicas at 55% CPU, back to 2
   when the load stopped). Re-capture it during the video with `scripts/load.py`
   running so the recording shows it live.
