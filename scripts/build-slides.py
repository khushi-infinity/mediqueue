"""Build demo/slides.pdf from the same facts the README documents.

Run with:  .venv/bin/python -m pip install -r scripts/requirements-docs.txt
           .venv/bin/python scripts/build-slides.py
"""
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parents[1] / "demo" / "slides.pdf"
WIDTH, HEIGHT = landscape(A4)
INK = HexColor("#10333c")
TEAL = HexColor("#0e6b64")
MINT = HexColor("#7fd7c6")
GREY = HexColor("#5d7078")
PAPER = HexColor("#f4f7f8")

TITLE = "MediQueue — Clinic Appointment Desk"
AUTHOR = "Khushi Sarawagi · 24BCS10361"

SLIDES = [
    ("Project Overview", [
        "Clinic front desk for booking patient visits across six departments",
        "Reception books, checks in, completes or cancels appointments",
        "Doctors are a first-class resource; each appointment references one",
        "Live queue view: KPI strip, status tabs, search, pagination",
        "Built as an original domain for the DevOps capstone, not a TaskBoard clone",
    ]),
    ("The Problem It Solves", [
        "Paper diaries and phone-call scheduling lose track of who is next",
        "No shared answer to: how many patients are still waiting right now?",
        "MediQueue keeps one queue that the whole front desk can see",
        "Urgency is explicit, so the sickest patient is visible first",
        "Everything is an API call, so the same data feeds the dashboard",
    ]),
    ("Tech Stack", [
        "Frontend   React 19, Vite, Lucide icons, hand-written responsive CSS",
        "API        Python 3.13, FastAPI, Pydantic, SQLAlchemy 2",
        "Database   PostgreSQL 17 with Alembic migrations",
        "Quality    Pytest (26 cases), Ruff, Playwright browser regression suite",
        "Containers Non-root Alpine images, multi-stage Nginx frontend",
        "CI/CD      GitHub Actions, Trivy gate, GHCR by commit SHA",
        "Infra      Terraform (VPC + EKS), Helm, Kubernetes, Prometheus, Grafana",
    ]),
    ("Application Data Model", [
        "doctors      id, full_name, department, specialization, active",
        "appointments id, patient_name, patient_phone, doctor_id (FK),",
        "             scheduled_for, reason, status, urgency, notes",
        "Department belongs to the doctor, so it is never duplicated",
        "Statuses: scheduled, checked_in, completed, cancelled",
        "Urgency: routine, soon, urgent",
        "11 API routes including full CRUD on both resources plus /api/stats",
    ]),
    ("Testing And Code Quality", [
        "Tests run before any image is built or pushed — the first quality gate",
        "26 pytest cases across both resources and every route group",
        "Covered: CRUD, filters, stats, validation, 404/409, wildcard escaping,",
        "         pagination stability, readiness failure, metric cardinality",
        "Local runs use isolated in-memory SQLite; CI uses dedicated PostgreSQL",
        "Ruff enforces import order, bugbear rules and a 110-column limit",
        "17 Playwright checks exercise the real running application in a browser",
    ]),
    ("Containers", [
        "backend   python:3.13-alpine, runs as UID 10001, pip removed from image",
        "frontend  node:24 build stage, nginx-unprivileged runtime as UID 101",
        "docker compose up --build starts Postgres, a migration job, API, nginx",
        "The migrate service runs alembic upgrade head and must finish first",
        "Compose healthchecks gate each service on the previous one being ready",
    ]),
    ("CI/CD Pipeline", [
        "Job 1  TEST      ruff, alembic, pytest on PostgreSQL, frontend build,",
        "                 helm lint, terraform validate  (no cloud resources)",
        "Job 2  BUILD     both images tagged with the full Git commit SHA",
        "       SCAN      Trivy on both images, exit-code 1 on HIGH/CRITICAL",
        "       DEPLOY    ephemeral Kind cluster, helm upgrade --install, smoke test",
        "       VERIFY    Playwright suite against the deployed Kubernetes app",
        "       PUBLISH   push to GHCR, then promote the SHA into values-release.json",
        "Commit A -> image A -> release A. Traceability from prod back to source.",
        "Result: run 38755163712 green in five minutes — 26 tests, 17 browser",
        "checks, both Trivy scans clean.",
    ]),
    ("Security: Trivy Gate", [
        "Scans installed OS packages and application dependencies in both images",
        "The pipeline fails on any HIGH or CRITICAL finding — no continue-on-error",
        "In CI both images scan clean: the Alpine layer and every Python package",
        "report zero vulnerabilities, so the gate is armed but never has to fire",
        "Security layers are different things: SAST, dependency scanning, secret",
        "scanning, container scanning and runtime security are not interchangeable",
        "A clean scan is not a proof of secure business logic or authorisation",
        "No credentials are committed; local secrets are generated at deploy time",
    ]),
    ("Terraform: AWS Infrastructure", [
        "VPC 10.52.0.0/16 across two availability zones",
        "Two public subnets and two private subnets, tagged for load balancers",
        "One NAT gateway for private subnet egress",
        "Managed EKS control plane with api/audit/authenticator logging",
        "Managed node group: 1-3 x t3.medium, AL2023, 30 GB disk",
        "EBS CSI driver via IRSA so PersistentVolumeClaims can bind",
        "EKS API restricted to supplied CIDRs; 0.0.0.0/0 is rejected by validation",
    ]),
    ("Kubernetes And Helm", [
        "Helm renders 16 objects from one chart and one values file",
        "backend and frontend Deployments, two replicas each, non-root runtime",
        "ClusterIP Services; readiness gates endpoint membership",
        "PostgreSQL StatefulSet with a PersistentVolumeClaim",
        "A migration Job runs before the backend init container waits for schema",
        "Ingress routes /api to the backend and / to the frontend",
        "HPA targets 70% CPU across 2-4 backend replicas; 2 -> 3 observed under load",
    ]),
    ("Observability", [
        "The API exposes /metrics in Prometheus text format",
        "A headless Service lets Prometheus discover every backend replica",
        "Counters are labelled with route templates, never raw IDs",
        "Grafana ships with a provisioned MediQueue / Service Health dashboard:",
        "  healthy replicas, request rate, p95 latency, route and status breakdown",
        "Alerts: backend unavailable and error ratio over five percent",
        "No external notification target is configured in the local demo",
    ]),
    ("GitOps With Argo CD", [
        "The Application tracks helm/mediqueue on main",
        "Promoted release first, local overlay last, so the cluster uses its own images",
        "CI writes values-release.json only after tests, scans and Kind smoke pass",
        "Automated sync and self-healing are on; automatic pruning is off",
        "Promotion commits use [skip ci] to avoid an image-build loop",
        "One deployment owner at a time: Helm for the Helm demo, Argo CD after",
    ]),
    ("Troubleshooting Lab", [
        "ImagePullBackOff: diagnose from pod events, fix the tag, watch the rollout",
        "Service with no endpoints: the selector does not match any pod labels",
        "Migration failure: /ready returns 503 and the pod stays out of endpoints",
        "Helm rollback restores chart configuration, not database migrations",
        "scripts/troubleshooting-check.py captures the whole transcript as evidence",
    ]),
    ("Known Limits", [
        "No authentication or RBAC — keep it local or add auth before exposing data",
        "Single PostgreSQL instance: no backups, failover or encryption policy",
        "Prometheus and Grafana storage is ephemeral; Postgres data is persistent",
        "Alerts have no notification destination configured",
        "AWS plan/apply/destroy proof requires a real account and is deferred",
    ]),
    ("Key Learnings", [
        "A deployment is only as trustworthy as the gates in front of it",
        "Readiness is a different question from liveness, and it changes routing",
        "Immutable SHA tags make production traceable back to a commit",
        "Metrics must be bounded: route templates, not IDs, keep dashboards sane",
        "Infrastructure as code is reviewable; console clicks are not",
        "One owner per deployment avoids Helm and Argo CD fighting each other",
    ]),
]


def wrap(c: canvas.Canvas, text: str, width: float, font: str = "Helvetica", size: float = 13) -> list[str]:
    c.setFont(font, size)
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if c.stringWidth(candidate, font, size) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def title_slide(c: canvas.Canvas) -> None:
    c.setFillColor(TEAL)
    c.rect(0, 0, WIDTH, HEIGHT, stroke=0, fill=1)
    c.setFillColor(MINT)
    c.rect(0, HEIGHT - 14 * mm, WIDTH, 14 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 34)
    c.drawString(28 * mm, HEIGHT - 70 * mm, "MediQueue")
    c.setFont("Helvetica", 18)
    c.drawString(28 * mm, HEIGHT - 86 * mm, "Clinic Appointment Desk")
    c.setFont("Helvetica", 13)
    c.drawString(28 * mm, HEIGHT - 104 * mm, "DevOps Final Capstone — application, CI/CD, infrastructure,")
    c.drawString(28 * mm, HEIGHT - 114 * mm, "Kubernetes, GitOps and observability")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(28 * mm, 30 * mm, AUTHOR)
    c.showPage()


def content_slide(c: canvas.Canvas, index: int, heading: str, bullets: list[str]) -> None:
    c.setFillColor(PAPER)
    c.rect(0, 0, WIDTH, HEIGHT, stroke=0, fill=1)
    c.setFillColor(TEAL)
    c.rect(0, HEIGHT - 22 * mm, WIDTH, 22 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20 * mm, HEIGHT - 14 * mm, heading)
    c.setFont("Helvetica", 10)
    c.drawRightString(WIDTH - 20 * mm, HEIGHT - 14 * mm, f"{index} / {len(SLIDES)}")

    c.setFillColor(INK)
    y = HEIGHT - 40 * mm
    for bullet in bullets:
        c.setFillColor(TEAL)
        c.circle(24 * mm, y + 1.6 * mm, 1.4 * mm, stroke=0, fill=1)
        c.setFillColor(INK)
        for line in wrap(c, bullet, WIDTH - 60 * mm):
            c.setFont("Helvetica", 13)
            c.drawString(30 * mm, y, line)
            y -= 7.5 * mm
        y -= 2.5 * mm
    c.setFillColor(GREY)
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, 12 * mm, f"{TITLE} — {AUTHOR}")
    c.showPage()


def architecture_slide(c: canvas.Canvas, index: int) -> None:
    c.setFillColor(PAPER)
    c.rect(0, 0, WIDTH, HEIGHT, stroke=0, fill=1)
    c.setFillColor(TEAL)
    c.rect(0, HEIGHT - 22 * mm, WIDTH, 22 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20 * mm, HEIGHT - 14 * mm, "Architecture")
    c.setFont("Helvetica", 10)
    c.drawRightString(WIDTH - 20 * mm, HEIGHT - 14 * mm, f"{index} / {len(SLIDES)}")

    rows = [
        ("GitHub push", "commit SHA is the artifact identity"),
        ("GitHub Actions", "ruff · pytest · frontend build · helm lint · terraform validate"),
        ("Build and scan", "docker build both images · Trivy HIGH/CRITICAL gate"),
        ("Ephemeral Kind", "helm upgrade --install · smoke test · Playwright suite"),
        ("GHCR", "images tagged with the full commit SHA"),
        ("GitOps promotion", "values-release.json -> Argo CD reconciles"),
        ("Kubernetes", "Ingress -> frontend / backend (/api) -> PostgreSQL PVC"),
        ("Observability", "Prometheus scrapes every replica -> Grafana dashboard"),
        ("Terraform", "VPC (2 AZ) + EKS managed node group for the AWS target"),
    ]
    y = HEIGHT - 42 * mm
    for label, detail in rows:
        c.setFillColor(HexColor("#ffffff"))
        c.roundRect(20 * mm, y - 4 * mm, 68 * mm, 12 * mm, 2 * mm, stroke=0, fill=1)
        c.setFillColor(TEAL)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(24 * mm, y, label)
        c.setFillColor(GREY)
        c.setFont("Helvetica", 11)
        c.drawString(94 * mm, y, detail)
        c.setStrokeColor(MINT)
        c.setLineWidth(1)
        c.line(32 * mm, y - 4.5 * mm, 32 * mm, y - 9.5 * mm)
        y -= 16 * mm
    c.setFillColor(GREY)
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, 12 * mm, f"{TITLE} — {AUTHOR}")
    c.showPage()


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=landscape(A4))
    c.setTitle(TITLE)
    c.setAuthor(AUTHOR)
    title_slide(c)
    total = len(SLIDES) + 2  # title, content slides and one architecture diagram
    index = 1
    for heading, bullets in SLIDES:
        index += 1
        if heading == "Kubernetes And Helm":
            architecture_slide(c, index)
        content_slide(c, index, heading, bullets)
    c.save()
    print(f"Wrote {OUT} with {total} slides")


if __name__ == "__main__":
    main()
