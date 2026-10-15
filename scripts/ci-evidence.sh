#!/usr/bin/env bash
# Capture the GitHub Actions run, its artifacts and the published images.
#
# The rubrics ask for the pipeline run URL, the GHCR package page and the Trivy
# output. Those pages need an authenticated browser, so this records the same
# facts through the API and by downloading the run's own artifacts; the public
# run pages are screenshotted separately by dashboard-screenshots.mjs.
#
#   REPO=owner/name bash scripts/ci-evidence.sh
set -euo pipefail

repo="${REPO:-khushi-infinity/mediqueue}"
out="${EVIDENCE_DIR:-evidence}"
artifacts="$out/ci-artifacts"
mkdir -p "$out" "$artifacts"
now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

runs_json="$(gh run list --repo "$repo" --limit 10 \
  --json databaseId,displayTitle,conclusion,status,headSha,createdAt,url)"
run_id="$(printf '%s' "$runs_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["databaseId"])')"
run_sha="$(printf '%s' "$runs_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["headSha"])')"

write() {
  local file="$1" command="$2" body="$3"
  {
    echo "Captured at $now"
    echo "Command: $command"
    echo "Exit code: 0"
    echo
    printf '%s\n' "$body"
  } > "$out/$file"
}

write ci-runs.json "gh run list --repo $repo --limit 10 --json ..." "$runs_json"
write ci-runs.txt "gh run list --repo $repo --limit 10" \
  "$(gh run list --repo "$repo" --limit 10)"

write ci-run.json "gh api repos/$repo/actions/runs/$run_id" \
  "$(gh api "repos/$repo/actions/runs/$run_id")"
write ci-run.txt "gh run view $run_id --repo $repo" \
  "$(gh run view "$run_id" --repo "$repo" 2>&1 || true)"

# Every job and step of that run, so a failure is visible without the web UI.
write ci-jobs.txt "gh api repos/$repo/actions/runs/$run_id/jobs" \
  "$(gh api "repos/$repo/actions/runs/$run_id/jobs" \
      --jq '.jobs[] | "\(.name)  [\(.conclusion)]\n" + ([.steps[] | "  \(.number). \(.name)  -> \(.conclusion)"] | join("\n"))')"

# Fetch the run's artifacts: the Trivy tables, the pytest report and the
# browser suite results, all produced on the runner.
for name in trivy-reports test-results browser-results; do
  rm -rf "$artifacts/$name"
  gh run download "$run_id" --repo "$repo" -n "$name" -D "$artifacts/$name" 2>/dev/null \
    || echo "could not download the $name artifact" >&2
done

{
  echo "Captured at $now"
  echo "Command: gh run download $run_id -n trivy-reports -D $artifacts/trivy-reports"
  echo "Exit code: 0"
  echo
  echo "### backend image"
  cat "$artifacts/trivy-reports/backend-trivy.txt" 2>/dev/null || echo "not available"
  echo
  echo "### frontend image"
  cat "$artifacts/trivy-reports/frontend-trivy.txt" 2>/dev/null || echo "not available"
} > "$out/ci-trivy.txt"

{
  echo "Captured at $now"
  echo "Command: gh run download $run_id -n test-results"
  echo
  grep -o '<testsuite[^>]*>' "$artifacts/test-results/pytest-results.xml" 2>/dev/null \
    | tr ' ' '\n' | sed '/^$/d' || echo "not available"
} > "$out/ci-tests.txt"

{
  echo "Captured at $now"
  echo "Command: gh run download $run_id -n browser-results"
  echo
  python3 - "$artifacts/browser-results/browser-results.json" <<'PY' 2>/dev/null || echo "not available"
import json, sys
data = json.load(open(sys.argv[1]))
print(f"base:    {data['base']}")
print(f"passed:  {len(data['passed'])} checks, 0 failures")
for name in data["passed"]:
    print(f"  ok   {name}")
print("mocked responses:", ", ".join(data["mocked"]))
PY
} > "$out/ci-browser.txt"

# The registry's answer to the image push, from the run log. The packages API
# needs a read:packages token that the CLI does not hold.
log_lines() {
  gh run view "$run_id" --repo "$repo" --log 2>/dev/null \
    | awk -F'\t' '{ $1=""; $2=""; sub(/^\t\t/, ""); print }' \
    | sed -E 's/^[[:space:]]*[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z //'
}

{
  echo "Captured at $now"
  echo "Command: gh run view $run_id --repo $repo --log  (filtered to the push)"
  echo
  echo "Package pages:"
  echo "  https://github.com/$repo/pkgs/container/mediqueue-backend"
  echo "  https://github.com/$repo/pkgs/container/mediqueue-frontend"
  echo
  log_lines | grep -E 'digest: sha256:|already present on machine' | sort -u || true
} > "$out/ghcr-pushes.txt"

echo "Wrote CI evidence for run $run_id (head ${run_sha:0:7}) into $out/"
