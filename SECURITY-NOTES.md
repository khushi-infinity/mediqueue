# Security Notes

What the pipeline actually checks, and what it does not.

## What Runs

| Control | Where | Blocks the pipeline |
| --- | --- | --- |
| Container vulnerability scan | `aquasecurity/trivy-action` on both images | Yes, on HIGH or CRITICAL |
| Lint and import/bugbear rules | `ruff check .` in `backend/` | Yes |
| Application tests | `pytest` against PostgreSQL | Yes |
| Infrastructure validation | `terraform fmt -check`, `init -backend=false`, `validate` | Yes |
| Chart validation | `helm lint`, `helm template` | Yes |
| Runtime smoke test | `curl` against the deployed Kind release | Yes |

## What A Trivy Scan Means

Trivy inspects the packages installed inside the built image — operating system
packages from the Alpine base, and Python or Node dependencies pulled in during
the build. A clean result means no *known* vulnerabilities with an available
advisory were found in those packages at scan time. It does not mean the
application is secure.

The scan does not evaluate:

- authorisation or business logic (MediQueue has no authentication at all)
- input handling beyond the Pydantic validation enforced at the API boundary
- secrets committed to Git, which need separate secret scanning
- runtime behaviour, lateral movement or container breakout

## Layered View

```text
SAST                 not configured
Dependency scanning  Trivy (as part of the image scan)
Secret scanning      not configured; secrets are generated at deploy time instead
Container scanning   Trivy, gating on HIGH and CRITICAL
Runtime security     not configured; this is a classroom deployment
```

Naming the gaps is more honest than pretending one scanner covers the pipeline.

## Deliberate Hardening Already In Place

- Both images run as non-root users (UID 10001 for the API, UID 101 for Nginx).
- The API image deletes `pip` after installing dependencies.
- Every pod drops all Linux capabilities and forbids privilege escalation.
- `automountServiceAccountToken: false` on every workload.
- Nginx in the frontend runs as the unprivileged variant and sends no server tokens.
- Database, Grafana and session secrets are generated at deploy time and are
  never committed; `.gitignore` excludes `.env`, `terraform.tfvars` and state files.
- The EKS API endpoint rejects `0.0.0.0/0` through a Terraform variable validation.
