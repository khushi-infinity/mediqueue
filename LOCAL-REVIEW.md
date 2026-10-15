# Local Quality Review

A deliberately self-critical pass over what was actually executed, what was
found and fixed, and what remains unproven.

## What Was Actually Run

| Check | Command | Result |
| --- | --- | --- |
| API tests | `.venv/bin/python -m pytest -q` | 26 passed |
| Lint | `.venv/bin/python -m ruff check .` | Clean |
| Stack build and run | `docker compose up --build -d` | 3 long-running services healthy |
| Migration | `alembic upgrade head` inside the `migrate` service | Exited 0 |
| Seed data | `python3 scripts/seed.py` | 6 doctors, 10 appointments |
| Live API | `/health`, `/ready`, `/api/stats`, `/api/doctors`, `/api/appointments` | All correct |
| Browser suite | `node scripts/browser-check.mjs` | 17 checks passed, 0 page errors |
| Chart lint | `helm lint helm/mediqueue` | 0 failed |
| Chart render | `helm template` | 16 objects, valid YAML |
| Terraform | `fmt -check`, `init -backend=false`, `validate` | Format clean, configuration valid |
| Kind cluster | `bash scripts/local-k8s.sh` | 8 pods Running, migration Job Complete |
| Ingress routing | `curl -H 'Host: mediqueue.localhost'` | `/` and `/api` both 200 |
| Prometheus | `/api/v1/targets` | Both backend replicas `up` |
| Load test | `python3 scripts/load.py --seconds 40` | 2649 requests, 0 failures |
| Autoscaling | `kubectl get hpa` after the load test | Backend scaled 2 → 3, then back to 2 |
| Grafana | `/api/health`, dashboard search | 11.6.0 healthy, dashboard provisioned |
| Failure lab | `python3 scripts/troubleshooting-check.py` | Diagnosed, repaired, cleaned up |
| GitOps | `bash scripts/local-gitops.sh` | Application `Synced` + `Healthy` |
| CI pipeline | `git push origin main` | Both jobs green; both Trivy scans clean |
| CI artifacts | `gh run download 38755163712` | 26 tests, 17 browser checks, 0 findings |
| Terminal screenshots | `node scripts/render-evidence.mjs` | 20 PNGs rendered from the transcripts |
| Dashboard screenshots | `node scripts/dashboard-screenshots.mjs` | 11 browser captures of Prometheus, Grafana, Argo CD, GitHub and the Ingress |
| Slide deck | `.venv/bin/python scripts/build-slides.py` | 17-page PDF written |

## Defects Found And Fixed During This Review

1. **Two faulty tests, not faulty code.** `test_missing_appointment[put]` posted
   an API *response* body back at the API; the output schema's extra keys tripped
   `extra="forbid"` and produced 422 instead of the expected 404. The assertion
   for bounded metric labels was also written twice, once interpolated by an
   f-string so it silently compared the wrong string. Both rewritten.
2. **Horizontal page scroll at 320 px.** The page-title action button did not
   fit beside the heading, so the document was 340 px wide in a 320 px viewport.
   Fixed with `flex-wrap` and `min-width: 0` on the title block.
3. **Root `scrollWidth` inflated by the table.** The appointment table is wider
   than its scroller on narrow screens. Even though `overflow: auto` clipped it
   visually (body width was correct), Chromium still aggregated the table's
   overflow into `documentElement.scrollWidth`. Adding `position: relative` to
   `.table-wrap` contains it. Found by bisecting elements with
   `display: none` rather than by guessing at CSS.
4. **Malformed SVG path** in the clinic illustration (`132cc…`), which silently
   dropped the drawn heart. Rewritten as a valid path.
5. **Invalid CSS declaration** (`color: #8397+9d`) in the table header rule. It
   was ignored by the browser, so the header still rendered — but it was still
   wrong and is now removed.
6. **Synthetic seed text typo** ("P wears a fitness tracker"), corrected.
7. **Terraform provider lock file was ignored.** Committing
   `.terraform.lock.hcl` pins provider versions for everyone; ignoring it makes
   builds non-reproducible. Removed from `terraform/.gitignore`.
8. **Two `subprocess.run` calls without an explicit `check`.** Ruff's `PLW1510`
   flagged them; they now pass `check=False` explicitly, which is the intent
   (the exit code is captured, not raised).
9. **The migration Job raced PostgreSQL on a fresh cluster.** A headless Service
   has no DNS record until its pod is ready, so on first install the Alembic Job
   failed with a name-resolution error and burned its retries while the database
   image was still being pulled. It now has a `pg_isready` init container, and
   both bootstrap scripts preload the database image.
10. **The GitOps overlay order defeated itself.** `Application` passed
    `[values-local.yaml, values-release.json]`, and because later Helm value
    files win, the promoted `ghcr.io/...` repository overrode the locally loaded
    image name. Argo CD rendered an unpullable image, the sync-hook Job sat in
    `ImagePullBackOff`, and the sync never completed. Rendering both orders side
    by side proved the cause; the overlay is now applied last and pins both the
    repository and the tag.
11. **A stuck Argo CD operation blocks all later syncs.** After deleting the
    wedged hook Job, the Application kept waiting on it; changing the spec could
    not start a new operation. Clearing `status.operationState` released it. Worth
    knowing before you spend ten minutes staring at `OutOfSync`.
12. **`input[type="text"]` does not match an input with no type attribute.** The
    Argo CD login field read `type === "text"` in the DOM, because that is the
    property's default value, but the CSS attribute selector matches attributes
    and therefore found nothing. Playwright waited out a 90-second timeout on an
    element that looked present. Selecting by accessible role fixed it. The same
    trap applies to any attribute selector on an omitted attribute.
13. **Screenshotting Argo CD under load does not work.** Its UI ships a large
    JavaScript bundle, and a saturating `scripts/load.py` run on a single-node
    cluster starved the server long enough that the page never hydrated. The
    dashboard capture now takes a `DASHBOARDS` subset so Prometheus and Grafana
    can be shot mid-load and Argo CD afterwards with the load stopped.
14. **The first pipeline run failed on a doubled image tag.** `ci-k8s.sh` passed
    a fully tagged reference as the chart's `repository` value while the chart
    composes `{{ repository }}:{{ tag }}`, so every pod came up with
    `ghcr.io/.../mediqueue-backend:<sha>:<sha>` and the release sat in
    `InvalidImageName` until the eight-minute Helm wait expired. The local
    bootstrap never reproduced it because `values-local.yaml` supplies
    `repository` and `tag` separately. The deploy now passes the repository
    without a tag, preloads the postgres image the way the local script does,
    and renders the chart first to assert the exact image references. The first
    run also confirmed what did work: `pytest` and both Trivy scans passed
    before the deploy step was reached.

## Claims That Are Not Verified Here

Stated plainly, because an unevidenced claim is worse than a missing one:

- **The pipeline is proven, but only on a hosted runner.** Both jobs of run
  [`38755163712`](https://github.com/khushi-infinity/mediqueue/actions/runs/38755163712)
  are green: 26 tests, both Trivy scans, the Kind deploy, 17 browser checks, the
  GHCR push and the GitOps promotion. What is *not* shown is the gate refusing a
  build: the images happen to be clean, so `exit-code: '1'` has never fired.
- **AWS is not deployed.** Terraform is formatted and validated only. No plan,
  apply or destroy output from a real account exists, so no VPC or EKS console
  screenshots are present.
- **Argo CD is verified locally, not in production.** It reconciled this chart
  from a local mirror of the repository on a Kind cluster and reached
  `Synced`/`Healthy`. The committed Application points at GitHub, but the
  captured sync came from a mirror through `ARGO_REPO_URL`, so no sync from
  GitHub itself is recorded here.
- **The autoscaler was observed scaling up and back down, but not under
  production load.** Two replicas became three at 55% CPU and returned to two.
  That is a real observation on a single node, not a capacity claim.
- **No authentication or authorisation exists.** The API is open. It is safe for
  a loopback classroom demo and nothing else.
- **The Trivy gate would fail a build, in principle.** The gate is configured with
  `exit-code: '1'` and `severity: HIGH,CRITICAL`, but both images scan clean, so
  the failure path has never actually fired. What is proven is the scan running
  in CI and reporting zero findings (`evidence/ci-trivy.txt`).
- **The demo video does not exist.** M10 requires one, and it must be recorded by
  the author. The slide deck is not a substitute.

## An Environment Incident Worth Recording

Mid-review the macOS volume reached 99% full (6.5 GB free) and Docker Desktop's
VM filesystem turned read-only, which took down the Kind cluster's API server.
No project defect was involved, and no project data was lost: the PostgreSQL
volume and the Kind node both survived a Docker restart. Reclaiming the npm cache
(18 GB of regenerable package data) restored 24 GB. The lesson is the ordinary
one — a container demo needs free disk, and a read-only error from the Docker
daemon is a host problem, not a manifest problem.

## How To Re-Run This Review

```bash
docker compose up --build -d && python3 scripts/seed.py
cd backend && ../.venv/bin/python -m ruff check . && ../.venv/bin/python -m pytest -v && cd ..
node scripts/browser-check.mjs
helm lint helm/mediqueue && helm template mediqueue helm/mediqueue > /dev/null
cd terraform && terraform fmt -check && terraform init -backend=false && terraform validate
```

`scripts/collect-evidence.py --compose-build` reruns the capture and writes each
result, with its command and exit code, into `evidence/`.
