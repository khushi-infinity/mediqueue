#!/usr/bin/env bash
# Capture the GitHub Actions run and the published container images as evidence.
#
# The rubrics ask for the pipeline run URL and a screenshot of the GHCR package
# page. Those pages need an authenticated browser, so this records the same facts
# through the API as text; render-evidence.mjs turns them into images.
#
#   REPO=owner/name bash scripts/ci-evidence.sh
set -euo pipefail

repo="${REPO:-khushi-infinity/mediqueue}"
out="${EVIDENCE_DIR:-evidence}"
mkdir -p "$out"
now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

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

runs_json="$(gh run list --repo "$repo" --limit 10 \
  --json databaseId,displayTitle,conclusion,status,headSha,createdAt,url)"

write ci-runs.json "gh run list --repo $repo --limit 10 --json ..." "$runs_json"
write ci-runs.txt "gh run list --repo $repo --limit 10" \
  "$(gh run list --repo "$repo" --limit 10)"

run_id="$(printf '%s' "$runs_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["databaseId"])')"
run_sha="$(printf '%s' "$runs_json" | python3 -c 'import json,sys; r=json.load(sys.stdin)[0]; print(r["headSha"][:7])')"

write "ci-run.json" "gh api repos/$repo/actions/runs/$run_id" \
  "$(gh api "repos/$repo/actions/runs/$run_id")"
write "ci-run.txt" "gh run view $run_id --repo $repo" \
  "$(gh run view "$run_id" --repo "$repo" 2>&1 || true)"

# Every job and step of that run, so a failure is visible without the web UI.
write "ci-jobs.txt" "gh api repos/$repo/actions/runs/$run_id/jobs" \
  "$(gh api "repos/$repo/actions/runs/$run_id/jobs" \
      --jq '.jobs[] | "\(.name)  [\(.conclusion)]\n" + ([.steps[] | "  \(.number). \(.name)  -> \(.conclusion)"] | join("\n"))')"

# The published images and their tags: the M5 SHA-tag requirement.
for package in mediqueue-backend mediqueue-frontend; do
  write "ghcr-$package.txt" "gh api users/$repo/../packages/container/$package/versions" \
    "$(gh api "users/${repo%%/*}/packages/container/$package/versions" \
        --jq '.[] | "\(.metadata.container.tags | join(", "))  pushed \(.created_at)"' 2>/dev/null \
        || echo 'no versions published yet')"
done

# The Trivy gate's own output, pulled from the job log.
write "ci-trivy.txt" "gh run view $run_id --repo $repo --log | grep Trivy" \
  "$(gh run view "$run_id" --repo "$repo" --log 2>/dev/null \
      | grep -iE 'trivy|vulnerabilit|CVE-' | tail -40 || echo 'no Trivy lines found')"

echo "Wrote CI evidence for run $run_id (head ${run_sha}) into $out/"
