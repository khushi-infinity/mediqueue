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

## Claims That Are Not Verified Here

Stated plainly, because an unevidenced claim is worse than a missing one:

- **No GitHub Actions run exists yet.** The workflow is written but cannot be
  proven until the repository is pushed. There are no pipeline, Trivy or GHCR
  screenshots in `evidence/`.
- **AWS is not deployed.** Terraform is formatted and validated only. No plan,
  apply or destroy output from a real account exists, so no VPC or EKS console
  screenshots are present.
- **HPA scale-out is configured, not observed.** Light local traffic does not
  reach the CPU threshold. The manifest is not evidence of scaling.
- **Argo CD is a local demonstration.** It reconciles the chart from this
  repository on a Kind cluster; it is not a production GitOps pipeline.
- **No authentication or authorisation exists.** The API is open. It is safe for
  a loopback classroom demo and nothing else.
- **The Trivy gate has never been exercised in CI.** It is configured with
  `exit-code: '1'`; that it *would* fail a build is a design claim, not a
  captured result.
- **The demo video does not exist.** M10 requires one, and it must be recorded by
  the author. The slide deck is not a substitute.

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
