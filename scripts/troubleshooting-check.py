"""Apply the deliberately broken demo objects, capture the observed failure, then clean up."""
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parents[1]
evidence = root / "evidence"
evidence.mkdir(exist_ok=True)
kubectl = ["kubectl", "--context", "kind-mediqueue"]
transcript: list[str] = []


def run(*args: str, timeout: int = 180) -> str:
    result = subprocess.run(
        [*kubectl, *args], cwd=root, check=False, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    block = f"$ kubectl {' '.join(args)}\n{result.stdout}{result.stderr}"
    transcript.append(block)
    print(block)
    return result.stdout


def main() -> None:
    for manifest in ("broken-image.yaml", "broken-service.yaml"):
        run("apply", "-f", f"troubleshooting/{manifest}")
    run("wait", "-n", "mediqueue", "--for=condition=Available", "deployment/broken-image-demo", "--timeout=20s")
    run("-n", "mediqueue", "get", "pods", "-l", "app=broken-image-demo")
    run("-n", "mediqueue", "describe", "deployment", "broken-image-demo")
    run("-n", "mediqueue", "get", "endpointslices", "-l", "kubernetes.io/service-name=broken-backend-demo")

    # Repair both faults and prove the recovery.
    run("-n", "mediqueue", "set", "image", "deployment/broken-image-demo", "demo=nginx:stable-alpine")
    run("wait", "-n", "mediqueue", "--for=condition=Available", "deployment/broken-image-demo", "--timeout=180s")
    run("-n", "mediqueue", "set", "selector", "service/broken-backend-demo", "app=backend")
    run("-n", "mediqueue", "get", "endpointslices", "-l", "kubernetes.io/service-name=broken-backend-demo")
    run("-n", "mediqueue", "delete", "deployment", "broken-image-demo", "--ignore-not-found")
    run("-n", "mediqueue", "delete", "service", "broken-backend-demo", "--ignore-not-found")

    header = f"Troubleshooting transcript captured at {datetime.now(UTC).isoformat()}\n\n"
    (evidence / "troubleshooting.txt").write_text(header + "\n".join(transcript), encoding="utf-8")
    (evidence / "troubleshooting.json").write_text(
        json.dumps({"capturedAt": datetime.now(UTC).isoformat(), "blocks": len(transcript)}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
