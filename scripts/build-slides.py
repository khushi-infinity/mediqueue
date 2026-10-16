"""Build demo/slides.pdf — a diagram-led deck from the same facts the README documents.

Every slide is drawn with vector primitives, so the deck stays reproducible and
carries no binary assets except the four evidence screenshots on the proof slide.

Run with:  .venv/bin/python -m pip install -r scripts/requirements-docs.txt
           .venv/bin/python scripts/build-slides.py
"""
from __future__ import annotations

import itertools
import math
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo" / "slides.pdf"
WIDTH, HEIGHT = landscape(A4)

# --- palette ---------------------------------------------------------------
INK = HexColor("#10333c")
DEEP = HexColor("#0a3335")
TEAL = HexColor("#0e6b64")
MINT = HexColor("#7fd7c6")
PAPER = HexColor("#f2f6f7")
WHITE = HexColor("#ffffff")
GREY = HexColor("#5d7078")
LINE = HexColor("#d6e1e5")
SOFT = HexColor("#e7eff1")
AMBER = HexColor("#c0862b")
CORAL = HexColor("#c9564a")
BLUE = HexColor("#37799c")
GREEN = HexColor("#2f8f6b")
VIOLET = HexColor("#6f63ad")

TITLE = "MediQueue — Clinic Appointment Desk"
AUTHOR = "Khushi Sarawagi · 24BCS10361"
REPO = "github.com/khushi-infinity/mediqueue"

# Content frame.
L = 15 * mm
R = WIDTH - 15 * mm
CW = R - L
TOP = HEIGHT - 25 * mm
BOT = 19 * mm
BAR = 13 * mm  # footer band height

FACE = "Helvetica"
FACE_B = "Helvetica-Bold"
FACE_M = "Courier"


# --- text helpers ----------------------------------------------------------
def wrap(text: str, font: str, size: float, width: float) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if not current or stringWidth(candidate, font, size) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def tx(c: canvas.Canvas, s: str, x: float, y: float, font: str = FACE, size: float = 10,
       color: HexColor = INK, align: str = "left") -> None:
    c.setFont(font, size)
    c.setFillColor(color)
    if align == "center":
        c.drawCentredString(x, y, s)
    elif align == "right":
        c.drawRightString(x, y, s)
    else:
        c.drawString(x, y, s)


def para(c: canvas.Canvas, s: str, x: float, y: float, width: float, font: str = FACE,
         size: float = 9.2, leading: float | None = None, color: HexColor = GREY,
         align: str = "left") -> float:
    leading = leading or size * 1.32
    for line in wrap(s, font, size, width):
        if align == "center":
            tx(c, line, x + width / 2, y, font, size, color, "center")
        else:
            tx(c, line, x, y, font, size, color)
        y -= leading
    return y


# --- shape helpers ---------------------------------------------------------
def rounded(c: canvas.Canvas, x: float, y: float, w: float, h: float, r: float = 2 * mm,
            fill: HexColor | None = WHITE, stroke: HexColor | None = None,
            lw: float = 0.7) -> None:
    if fill is not None:
        c.setFillColor(fill)
    if stroke is not None:
        c.setStrokeColor(stroke)
        c.setLineWidth(lw)
    c.roundRect(x, y, w, h, min(r, min(w, h) / 2),
                stroke=1 if stroke is not None else 0,
                fill=1 if fill is not None else 0)


def node(c: canvas.Canvas, x: float, y: float, w: float, h: float, title: str,
         sub: str | None = None, fill: HexColor = WHITE, stroke: HexColor | None = LINE,
         tcolor: HexColor = INK, scolor: HexColor = GREY, tsize: float = 10,
         ssize: float = 7.6, r: float = 1.9 * mm, icon: str | None = None,
         icon_color: HexColor | None = None) -> None:
    rounded(c, x, y, w, h, r, fill, stroke)
    has_sub = bool(sub)
    offset = 2.1 * mm if has_sub else 0
    if icon:
        icon_at(c, icon, x + 5.2 * mm, y + h / 2, 4.2 * mm, icon_color or stroke or TEAL)
        left = x + 10 * mm
        tx(c, title, left, y + h / 2 + offset - tsize * 0.34, FACE_B, tsize, tcolor)
        if sub:
            tx(c, sub, left, y + h / 2 - offset - ssize * 0.34, FACE, ssize, scolor)
    else:
        tx(c, title, x + w / 2, y + h / 2 + offset - tsize * 0.34, FACE_B, tsize, tcolor, "center")
        if sub:
            tx(c, sub, x + w / 2, y + h / 2 - offset - ssize * 0.34, FACE, ssize, scolor, "center")


def card(c: canvas.Canvas, x: float, y: float, w: float, h: float, title: str,
         lines: list[str] | None = None, accent: HexColor = TEAL, icon: str | None = None,
         title_size: float = 11, body_size: float = 9, r: float = 2.2 * mm,
         body_color: HexColor = GREY) -> None:
    rounded(c, x, y, w, h, r, WHITE, LINE)
    c.setFillColor(accent)
    c.roundRect(x, y, 1.7 * mm, h, 0.85 * mm, stroke=0, fill=1)
    if icon:
        icon_at(c, icon, x + w - 6.6 * mm, y + h - 6.6 * mm, 4.4 * mm, accent)
    tx(c, title, x + 6 * mm, y + h - 6.4 * mm, FACE_B, title_size, INK)
    yy = y + h - 12.4 * mm
    for line in lines or []:
        yy = para(c, line, x + 6 * mm, yy, w - 11 * mm, FACE, body_size, body_size * 1.34,
                  body_color)
        yy -= 1.6 * mm


def chip_row(c: canvas.Canvas, x: float, y: float, labels: list[str], fill: HexColor = SOFT,
             tcolor: HexColor = TEAL, size: float = 8, h: float = 5.4 * mm,
             pad: float = 2.6 * mm, gap: float = 1.6 * mm) -> float:
    cx = x
    for label in labels:
        w = stringWidth(label, FACE_B, size) + 2 * pad
        rounded(c, cx, y, w, h, h / 2, fill, None)
        tx(c, label, cx + w / 2, y + h / 2 - size * 0.34, FACE_B, size, tcolor, "center")
        cx += w + gap
    return cx - gap - x


def badge(c: canvas.Canvas, cx: float, cy: float, text: str, fill: HexColor = MINT,
          tcolor: HexColor = DEEP, size: float = 9, d: float = 7 * mm) -> None:
    c.setFillColor(fill)
    c.circle(cx, cy, d / 2, stroke=0, fill=1)
    tx(c, text, cx, cy - size * 0.36, FACE_B, size, tcolor, "center")


def stat(c: canvas.Canvas, x: float, y: float, w: float, h: float, value: str, label: str,
         accent: HexColor = TEAL) -> None:
    rounded(c, x, y, w, h, 2 * mm, WHITE, LINE)
    tx(c, value, x + w / 2, y + h - 9 * mm, FACE_B, 19, accent, "center")
    tx(c, label, x + w / 2, y + 3.4 * mm, FACE, 7.6, GREY, "center")


def zone(c: canvas.Canvas, x: float, y: float, w: float, h: float, title: str,
         color: HexColor = TEAL, dash: list[int] | None = None) -> None:
    if dash:
        c.setDash(dash)
    rounded(c, x, y, w, h, 3 * mm, None, color, 1.0)
    c.setDash([])
    tw = stringWidth(title, FACE_B, 8.4) + 4.4 * mm
    c.setFillColor(PAPER)
    c.rect(x + 4 * mm, y + h - 2.2 * mm, tw, 4.4 * mm, stroke=0, fill=1)
    tx(c, title, x + 6.2 * mm, y + h - 1.2 * mm, FACE_B, 8.4, color)


def arrow_head(c: canvas.Canvas, x: float, y: float, angle: float, size: float,
               color: HexColor) -> None:
    a = math.radians(angle)
    p = c.beginPath()
    p.moveTo(x, y)
    p.lineTo(x - size * math.cos(a) + size * 0.52 * math.sin(a),
             y - size * math.sin(a) - size * 0.52 * math.cos(a))
    p.lineTo(x - size * math.cos(a) - size * 0.52 * math.sin(a),
             y - size * math.sin(a) + size * 0.52 * math.cos(a))
    p.close()
    c.setFillColor(color)
    c.drawPath(p, stroke=0, fill=1)


def elbow(c: canvas.Canvas, pts: list[tuple[float, float]], color: HexColor = TEAL,
          lw: float = 1.1, head: float = 2.3 * mm, dash: list[int] | None = None,
          label: str | None = None, label_size: float = 7.4) -> None:
    c.setStrokeColor(color)
    c.setLineWidth(lw)
    c.setLineCap(1)
    c.setLineJoin(1)
    if dash:
        c.setDash(dash)
    for (x1, y1), (x2, y2) in itertools.pairwise(pts):
        c.line(x1, y1, x2, y2)
    c.setDash([])
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    arrow_head(c, x2, y2, math.degrees(math.atan2(y2 - y1, x2 - x1)), head, color)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        tw = stringWidth(label, FACE_B, label_size) + 2.4 * mm
        c.setFillColor(PAPER)
        c.rect(mx - tw / 2, my - 1.7 * mm, tw, 3.4 * mm, stroke=0, fill=1)
        tx(c, label, mx, my - label_size * 0.34, FACE_B, label_size, color, "center")


def line_str(c: canvas.Canvas, x1: float, y1: float, x2: float, y2: float,
             color: HexColor = LINE, lw: float = 0.7, dash: list[int] | None = None) -> None:
    c.setStrokeColor(color)
    c.setLineWidth(lw)
    if dash:
        c.setDash(dash)
    c.line(x1, y1, x2, y2)
    c.setDash([])


# --- icons -----------------------------------------------------------------
def icon_at(c: canvas.Canvas, name: str, cx: float, cy: float, s: float, color: HexColor) -> None:
    """Draw a small vector glyph inside a square of side ``s`` centred on (cx, cy)."""
    h = s / 2
    c.saveState()
    c.setFillColor(color)
    c.setStrokeColor(color)
    c.setLineWidth(max(0.75, s * 0.09))
    c.setLineJoin(1)
    c.setLineCap(1)

    if name == "db":
        w = s * 0.8
        c.roundRect(cx - w / 2, cy - h * 0.85, w, s * 0.72, s * 0.16, stroke=0, fill=1)
        c.setStrokeColor(WHITE)
        c.setLineWidth(max(0.6, s * 0.07))
        c.line(cx - w / 2 + s * 0.06, cy + h * 0.22, cx + w / 2 - s * 0.06, cy + h * 0.22)
        c.line(cx - w / 2 + s * 0.06, cy - h * 0.06, cx + w / 2 - s * 0.06, cy - h * 0.06)

    elif name == "server":
        c.roundRect(cx - s * 0.42, cy - h * 0.9, s * 0.84, s * 0.8, s * 0.12, stroke=0, fill=1)
        c.setStrokeColor(WHITE)
        c.setLineWidth(max(0.6, s * 0.07))
        c.line(cx - s * 0.26, cy + h * 0.3, cx + s * 0.26, cy + h * 0.3)
        c.line(cx - s * 0.26, cy - h * 0.05, cx + s * 0.26, cy - h * 0.05)
        c.setFillColor(WHITE)
        c.circle(cx + s * 0.28, cy + h * 0.3, s * 0.045, stroke=0, fill=1)

    elif name == "browser":
        c.roundRect(cx - s * 0.46, cy - h * 0.86, s * 0.92, s * 0.78, s * 0.12, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.rect(cx - s * 0.46, cy + h * 0.28, s * 0.92, s * 0.09, stroke=0, fill=1)
        for i in range(3):
            c.circle(cx - s * 0.33 + i * s * 0.15, cy + h * 0.46, s * 0.045, stroke=0, fill=1)

    elif name == "cube":
        c.saveState()
        c.translate(cx, cy)
        c.rotate(45)
        c.roundRect(-s * 0.33, -s * 0.33, s * 0.66, s * 0.66, s * 0.08, stroke=0, fill=1)
        c.restoreState()
        c.setFillColor(WHITE)
        c.circle(cx, cy, s * 0.1, stroke=0, fill=1)

    elif name == "shield":
        p = c.beginPath()
        p.moveTo(cx - s * 0.38, cy + h * 0.62)
        p.lineTo(cx + s * 0.38, cy + h * 0.62)
        p.lineTo(cx + s * 0.38, cy - h * 0.1)
        p.curveTo(cx + s * 0.38, cy - h * 0.66, cx + s * 0.12, cy - h * 0.8,
                  cx, cy - h * 0.92)
        p.curveTo(cx - s * 0.12, cy - h * 0.8, cx - s * 0.38, cy - h * 0.66,
                  cx - s * 0.38, cy - h * 0.1)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
        c.setStrokeColor(WHITE)
        c.setLineWidth(max(0.7, s * 0.1))
        c.line(cx - s * 0.16, cy + s * 0.02, cx - s * 0.03, cy - s * 0.14)
        c.line(cx - s * 0.03, cy - s * 0.14, cx + s * 0.19, cy + s * 0.16)

    elif name == "cloud":
        c.circle(cx - s * 0.22, cy, s * 0.24, stroke=0, fill=1)
        c.circle(cx + s * 0.06, cy + s * 0.12, s * 0.29, stroke=0, fill=1)
        c.circle(cx + s * 0.3, cy - s * 0.02, s * 0.2, stroke=0, fill=1)
        c.rect(cx - s * 0.24, cy - s * 0.14, s * 0.56, s * 0.18, stroke=0, fill=1)

    elif name == "gauge":
        c.setStrokeColor(color)
        c.setLineWidth(max(1.1, s * 0.16))
        c.arc(cx - s * 0.42, cy - s * 0.44, cx + s * 0.42, cy + s * 0.54, 18, 144)
        c.setLineWidth(max(0.9, s * 0.11))
        c.line(cx, cy + s * 0.05, cx + s * 0.23, cy + s * 0.35)
        c.setFillColor(color)
        c.circle(cx, cy + s * 0.05, s * 0.075, stroke=0, fill=1)

    elif name == "check":
        c.circle(cx, cy, h * 0.92, stroke=0, fill=1)
        c.setStrokeColor(WHITE)
        c.setLineWidth(max(0.9, s * 0.13))
        c.line(cx - s * 0.24, cy + s * 0.02, cx - s * 0.06, cy - s * 0.18)
        c.line(cx - s * 0.06, cy - s * 0.18, cx + s * 0.26, cy + s * 0.2)

    elif name == "warn":
        p = c.beginPath()
        p.moveTo(cx, cy + h * 0.9)
        p.lineTo(cx + s * 0.48, cy - h * 0.72)
        p.lineTo(cx - s * 0.48, cy - h * 0.72)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.rect(cx - s * 0.045, cy - s * 0.3, s * 0.09, s * 0.6, stroke=0, fill=1)
        c.circle(cx, cy - h * 0.5, s * 0.055, stroke=0, fill=1)

    elif name == "terminal":
        c.roundRect(cx - s * 0.48, cy - h * 0.74, s * 0.96, s * 0.7, s * 0.1, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.setFont(FACE_B, s * 0.42)
        c.drawString(cx - s * 0.32, cy - s * 0.1, ">")
        c.rect(cx - s * 0.02, cy - s * 0.16, s * 0.26, s * 0.075, stroke=0, fill=1)

    elif name == "git":
        c.setStrokeColor(color)
        c.setLineWidth(max(0.9, s * 0.1))
        c.line(cx - s * 0.08, cy + h * 0.5, cx - s * 0.08, cy - h * 0.5)
        p = c.beginPath()
        p.moveTo(cx - s * 0.08, cy + h * 0.1)
        p.curveTo(cx + s * 0.36, cy + h * 0.1, cx + s * 0.36, cy - h * 0.16,
                  cx + s * 0.3, cy - h * 0.46)
        c.drawPath(p, stroke=1, fill=0)
        c.setFillColor(color)
        c.circle(cx - s * 0.08, cy + h * 0.62, s * 0.15, stroke=0, fill=1)
        c.circle(cx - s * 0.08, cy - h * 0.64, s * 0.15, stroke=0, fill=1)
        c.circle(cx + s * 0.31, cy - h * 0.6, s * 0.15, stroke=0, fill=1)

    elif name == "queue":
        for i, dy in enumerate((h * 0.5, 0, -h * 0.5)):
            w = s * (0.9 - i * 0.14)
            c.setFillColor(color)
            c.roundRect(cx - s * 0.45, cy + dy - s * 0.11, w, s * 0.22, s * 0.07,
                        stroke=0, fill=1)

    elif name == "clock":
        c.setStrokeColor(color)
        c.setLineWidth(max(0.9, s * 0.11))
        c.circle(cx, cy, h * 0.86, stroke=1, fill=0)
        c.line(cx, cy, cx, cy + h * 0.5)
        c.line(cx, cy, cx + h * 0.42, cy - h * 0.1)

    elif name == "doc":
        w, hh = s * 0.68, s * 0.84
        p = c.beginPath()
        p.moveTo(cx - w / 2, cy + hh / 2)
        p.lineTo(cx + w / 2 - s * 0.2, cy + hh / 2)
        p.lineTo(cx + w / 2, cy + hh / 2 - s * 0.2)
        p.lineTo(cx + w / 2, cy - hh / 2)
        p.lineTo(cx - w / 2, cy - hh / 2)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
        c.setStrokeColor(WHITE)
        c.setLineWidth(max(0.55, s * 0.06))
        for i in range(3):
            c.line(cx - w / 2 + s * 0.12, cy + hh * 0.2 - i * s * 0.18,
                   cx + w / 2 - s * 0.12, cy + hh * 0.2 - i * s * 0.18)

    elif name == "search":
        c.setStrokeColor(color)
        c.setLineWidth(max(1.0, s * 0.13))
        c.circle(cx - s * 0.08, cy + s * 0.08, s * 0.28, stroke=1, fill=0)
        c.line(cx + s * 0.13, cy - s * 0.13, cx + s * 0.38, cy - s * 0.38)

    elif name == "lock":
        c.setFillColor(color)
        c.roundRect(cx - s * 0.34, cy - h * 0.72, s * 0.68, s * 0.5, s * 0.1,
                    stroke=0, fill=1)
        c.setStrokeColor(color)
        c.setLineWidth(max(0.9, s * 0.11))
        c.arc(cx - s * 0.2, cy - s * 0.34, cx + s * 0.2, cy + s * 0.32, 0, 180)

    elif name == "k8s":
        c.setStrokeColor(color)
        c.setLineWidth(max(0.9, s * 0.1))
        c.circle(cx, cy, h * 0.82, stroke=1, fill=0)
        for i in range(7):
            a = math.radians(i * 360 / 7 - 90)
            c.line(cx, cy, cx + h * 0.82 * math.cos(a), cy + h * 0.82 * math.sin(a))
        c.setFillColor(color)
        c.circle(cx, cy, s * 0.1, stroke=0, fill=1)

    c.restoreState()


# --- slide chrome ----------------------------------------------------------
def chrome(c: canvas.Canvas, index: int, total: int, heading: str, kicker: str | None = None) -> None:
    c.setFillColor(PAPER)
    c.rect(0, 0, WIDTH, HEIGHT, stroke=0, fill=1)
    c.setFillColor(DEEP)
    c.rect(0, HEIGHT - 19 * mm, WIDTH, 19 * mm, stroke=0, fill=1)
    c.setFillColor(MINT)
    c.rect(0, HEIGHT - 19.9 * mm, WIDTH, 0.9 * mm, stroke=0, fill=1)
    tx(c, heading, 15 * mm, HEIGHT - 12.2 * mm, FACE_B, 18.5, WHITE)
    if kicker:
        tx(c, kicker, R, HEIGHT - 12.2 * mm, FACE, 9, MINT, "right")
    tx(c, f"{TITLE} — {AUTHOR}", L, 8.6 * mm, FACE, 7.6, GREY)
    tx(c, f"{index} / {total}", R, 8.6 * mm, FACE_B, 8.6, TEAL, "right")
    c.setFillColor(LINE)
    c.rect(L, 12.4 * mm, CW, 0.7 * mm, stroke=0, fill=1)
    c.setFillColor(MINT)
    c.rect(L, 12.4 * mm, CW * index / total, 0.7 * mm, stroke=0, fill=1)


def footer_note(c: canvas.Canvas, text: str) -> None:
    tx(c, text, L, BOT + 1.5 * mm, FACE, 7.8, GREY)


# --- compound visuals ------------------------------------------------------
def mock_app(c: canvas.Canvas, x: float, y: float, w: float, h: float,
             rows: list[tuple[str, str, str, HexColor]] | None = None,
             kpis: list[tuple[str, str]] | None = None) -> None:
    """A small mock of the running front desk screen."""
    rounded(c, x, y, w, h, 2.6 * mm, WHITE, LINE)
    bar = 8.5 * mm
    line_str(c, x, y + h - bar, x + w, y + h - bar, LINE, 0.7)
    for i, colour in enumerate((CORAL, AMBER, GREEN)):
        c.setFillColor(colour)
        c.circle(x + 4.6 * mm + i * 3.4 * mm, y + h - bar / 2, 0.95 * mm, stroke=0, fill=1)
    tx(c, "mediqueue.localhost", x + w - 5 * mm, y + h - bar / 2 - 1.3, FACE_B, 7, GREY,
       "right")

    ty = y + h - bar - 5 * mm
    if kpis:
        kw = (w - 10 * mm - 2 * 2.6 * mm) / 3
        for i, (value, label) in enumerate(kpis):
            kx = x + 5 * mm + i * (kw + 2.6 * mm)
            rounded(c, kx, ty - 11 * mm, kw, 13 * mm, 1.4 * mm, SOFT, None)
            tx(c, value, kx + kw / 2, ty - 3.6 * mm, FACE_B, 12.5, TEAL, "center")
            tx(c, label, kx + kw / 2, ty - 8.6 * mm, FACE, 6.6, GREY, "center")
        ty -= 16 * mm

    for name, meta, status, colour in rows or []:
        c.setFillColor(colour)
        c.circle(x + 7 * mm, ty - 2 * mm, 1.5 * mm, stroke=0, fill=1)
        tx(c, name, x + 11 * mm, ty - 1.4 * mm, FACE_B, 8.4, INK)
        tx(c, meta, x + 11 * mm + 32 * mm, ty - 1.4 * mm, FACE, 7.6, GREY)
        sw = stringWidth(status, FACE_B, 7) + 4.4 * mm
        rounded(c, x + w - 5 * mm - sw, ty - 4.6 * mm, sw, 5.2 * mm, 2.6 * mm,
                colour, None)
        tx(c, status, x + w - 5 * mm - sw / 2, ty - 3.6 * mm, FACE_B, 7, WHITE, "center")
        line_str(c, x + 5 * mm, ty - 7 * mm, x + w - 5 * mm, ty - 7 * mm, LINE, 0.6)
        ty -= 10.6 * mm


def gate_ladder(c: canvas.Canvas, x: float, y: float, w: float,
                steps: list[tuple[str, str]], step_h: float = 15.5 * mm,
                gap: float = 2.4 * mm) -> None:
    """Vertical chain of checks where each one must pass before the next runs."""
    for i, (label, detail) in enumerate(steps):
        sy = y - i * (step_h + gap)
        rounded(c, x, sy - step_h, w, step_h, 1.8 * mm, WHITE, LINE)
        icon_at(c, "check", x + 7 * mm, sy - step_h / 2, 5 * mm, GREEN)
        tx(c, label, x + 13 * mm, sy - step_h / 2 + 1.6 * mm, FACE_B, 9.6, INK)
        tx(c, detail, x + 13 * mm, sy - step_h / 2 - 3.4 * mm, FACE, 7.8, GREY)
        if i < len(steps) - 1:
            elbow(c, [(x + w / 2, sy - step_h - 0.2 * mm), (x + w / 2, sy - step_h - 2.2 * mm)],
                  TEAL, 0.9, 1.7 * mm)


def erd(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    """Two entities joined one-to-many; each box is sized to its own columns."""
    doctors = [("id", "PK"), ("full_name", ""), ("department", ""),
               ("specialization", ""), ("active", "")]
    appts = [("id", "PK"), ("doctor_id", "FK → doctors.id"), ("patient_name", ""),
             ("patient_phone", ""), ("scheduled_for", ""), ("reason", ""),
             ("status", ""), ("urgency", ""), ("notes", "")]

    bw = min(64 * mm, (w - 22 * mm) / 2)
    top = y + h
    hd = 13 * mm + len(doctors) * 6.4 * mm + 5 * mm
    ha = 13 * mm + len(appts) * 6.4 * mm + 5 * mm
    lx, rx = x, x + w - bw

    def entity(ex: float, name: str, fields: list[tuple[str, str]], bh: float,
               colour: HexColor) -> None:
        rounded(c, ex, top - bh, bw, bh, 2 * mm, WHITE, LINE)
        rounded(c, ex, top - 9.5 * mm, bw, 9.5 * mm, 2 * mm, colour, None)
        c.setFillColor(colour)
        c.rect(ex, top - 9.5 * mm, bw, 3 * mm, stroke=0, fill=1)
        tx(c, name, ex + 5 * mm, top - 6.4 * mm, FACE_B, 11.5, WHITE)
        tx(c, f"{len(fields)} columns", ex + bw - 5 * mm, top - 6.4 * mm, FACE, 7, WHITE,
           "right")
        fy = top - 15 * mm
        for field, tag in fields:
            tx(c, field, ex + 5 * mm, fy, FACE_M, 7.6, INK if tag else GREY)
            if tag:
                tx(c, tag, ex + bw - 5 * mm, fy, FACE_B, 6.6,
                   TEAL if "PK" in tag else AMBER, "right")
            fy -= 6.4 * mm

    entity(lx, "doctors", doctors, hd, TEAL)
    entity(rx, "appointments", appts, ha, BLUE)

    ly = top - hd * 0.55
    c.setStrokeColor(TEAL)
    c.setLineWidth(1.1)
    c.line(lx + bw, ly, rx, ly)
    for dy in (2.3 * mm, 0, -2.3 * mm):
        c.line(rx - 4.6 * mm, ly + dy, rx, ly)
    tx(c, "1", lx + bw + 3 * mm, ly + 2.4 * mm, FACE_B, 9.5, TEAL)
    tx(c, "N", rx - 3.8 * mm, ly + 2.4 * mm, FACE_B, 9.5, TEAL, "right")
    mid = (lx + bw + rx) / 2
    label = "one doctor, many visits"
    tw = stringWidth(label, FACE_B, 7.2) + 3.4 * mm
    c.setFillColor(PAPER)
    c.rect(mid - tw / 2, ly - 2.1 * mm, tw, 4.6 * mm, stroke=0, fill=1)
    tx(c, label, mid, ly - 1.3 * mm, FACE_B, 7.2, TEAL, "center")


def cluster_map(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    """Kubernetes objects as one vertical request path plus a scrape loop."""
    zone(c, x, y, w, h, "Kubernetes — Kind locally · EKS on AWS", TEAL, [3, 3])
    pad = 7 * mm
    ix0, ix1 = x + pad, x + w - pad
    iw = ix1 - ix0

    ing_h, row_h, data_h, mon_h = 15 * mm, 22 * mm, 15 * mm, 15 * mm
    gap = max(6 * mm, (h - 14 * mm - (ing_h + row_h + data_h + 2 * mon_h)) / 4)

    ing_w = min(62 * mm, iw - 8 * mm)
    ing_x = ix0 + (iw - ing_w) / 2
    ing_y = y + h - 7 * mm - ing_h

    row_top = ing_y - gap
    row_y = row_top - row_h
    top_pg = row_y - gap
    pg_y = top_pg - data_h
    top_prom = pg_y - gap
    prom_y = top_prom - mon_h
    top_graf = prom_y - gap
    graf_y = top_graf - mon_h

    app_x0, app_x1 = ix0 + 8 * mm, ix1 - 8 * mm
    fw = (app_x1 - app_x0 - 6 * mm) / 2
    front_x = app_x0
    back_x = app_x0 + fw + 6 * mm
    front_mid, back_mid = front_x + fw / 2, back_x + fw / 2
    ing_mid = ing_x + ing_w / 2

    node(c, ing_x, ing_y, ing_w, ing_h, "Ingress",
         "host mediqueue.localhost", tsize=9.4, ssize=7,
         icon="browser", icon_color=VIOLET)
    node(c, front_x, row_y, fw, row_h, "frontend", "2 replicas · nginx, UID 101",
         tsize=9.8, ssize=7.2, icon="cube", icon_color=BLUE)
    node(c, back_x, row_y, fw, row_h, "backend", "2 replicas · FastAPI, UID 10001",
         tsize=9.8, ssize=7.2, icon="server", icon_color=TEAL)

    elbow(c, [(ing_mid, ing_y), (ing_mid, ing_y - 2.6 * mm), (front_mid, ing_y - 2.6 * mm),
              (front_mid, row_top)], TEAL, 1.0, 2 * mm)
    elbow(c, [(ing_mid, ing_y - 2.6 * mm), (back_mid, ing_y - 2.6 * mm),
              (back_mid, row_top)], TEAL, 1.0, 2 * mm, label="routes /api")

    pg_w = min(72 * mm, iw - 44 * mm)
    pg_x = ix0 + (iw - pg_w) / 2
    node(c, pg_x, pg_y, pg_w, data_h, "postgres",
         "StatefulSet · PersistentVolumeClaim · UID 70", tsize=9.4, ssize=7,
         icon="db", icon_color=AMBER)
    elbow(c, [(back_mid, row_y), (back_mid, top_pg + 3 * mm),
              (pg_x + pg_w / 2, top_pg + 3 * mm), (pg_x + pg_w / 2, top_pg)],
          TEAL, 1.0, 1.9 * mm, label="DATABASE_URL")

    mon_w = min(74 * mm, iw - 44 * mm)
    mon_x = ix0 + (iw - mon_w) / 2
    node(c, mon_x, prom_y, mon_w, mon_h, "Prometheus", "scrape every 10s · /metrics",
         tsize=9.4, ssize=7, icon="gauge", icon_color=CORAL)
    node(c, mon_x, graf_y, mon_w, mon_h, "Grafana",
         "provisioned dashboard · 2 alert rules", tsize=9.4, ssize=7,
         icon="gauge", icon_color=GREEN)
    elbow(c, [(mon_x + mon_w / 2, prom_y), (mon_x + mon_w / 2, top_graf)],
          GREEN, 1.1, 2 * mm, label="queries")

    corridor = ix1 - 3 * mm
    elbow(c, [(mon_x + mon_w, prom_y + mon_h / 2), (corridor, prom_y + mon_h / 2),
              (corridor, row_y + row_h / 2), (app_x1, row_y + row_h / 2)],
          CORAL, 1.0, 1.9 * mm, dash=[2, 2], label="scrape")


def metrics_flow(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    boxes = [("backend ×2", "/metrics", TEAL, "server"),
             ("headless Service", "discovers replicas", VIOLET, "queue"),
             ("Prometheus", "scrape every 10s", CORAL, "gauge"),
             ("Grafana + alerts", "dashboard and rules", GREEN, "gauge")]
    bw = (w - 3 * 7 * mm) / 4
    for i, (label, sub, colour, icon) in enumerate(boxes):
        bx = x + i * (bw + 7 * mm)
        node(c, bx, y, bw, h, label, sub, tsize=9, ssize=7, icon=icon, icon_color=colour)
        if i < 3:
            elbow(c, [(bx + bw + 1.4 * mm, y + h / 2), (bx + bw + 6 * mm, y + h / 2)],
                  TEAL, 1.1, 2.1 * mm)


def dashboard_mock(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    rounded(c, x, y, w, h, 2.4 * mm, WHITE, LINE)
    tx(c, "MediQueue / Service Health", x + 5 * mm, y + h - 6 * mm, FACE_B, 9.4, INK)
    tx(c, "provisioned in Grafana", x + w - 5 * mm, y + h - 6 * mm, FACE, 7, GREY, "right")

    tiles = [("2 / 2", "healthy replicas", GREEN), ("12.4 /s", "request rate", TEAL),
             ("41 ms", "p95 latency", BLUE), ("0.0 %", "5xx ratio", AMBER)]
    tw = (w - 10 * mm - 3 * 3 * mm) / 4
    for i, (value, label, colour) in enumerate(tiles):
        txx = x + 5 * mm + i * (tw + 3 * mm)
        rounded(c, txx, y + h - 25 * mm, tw, 15 * mm, 1.4 * mm, PAPER, LINE)
        tx(c, value, txx + tw / 2, y + h - 15 * mm, FACE_B, 13, colour, "center")
        tx(c, label, txx + tw / 2, y + h - 21 * mm, FACE, 6.4, GREY, "center")

    # drawn chart: bars + a trend line
    cx0, cy0 = x + 5 * mm, y + 5 * mm
    cwid, chgt = w - 10 * mm, h - 32 * mm
    for gy in (0.25, 0.5, 0.75, 1.0):
        line_str(c, cx0, cy0 + chgt * gy, cx0 + cwid, cy0 + chgt * gy, SOFT, 0.6)
    bars = [0.30, 0.42, 0.36, 0.55, 0.48, 0.62, 0.58, 0.74, 0.66, 0.82, 0.7, 0.9]
    bwid = cwid / len(bars) - 1.6 * mm
    pts = []
    for i, value in enumerate(bars):
        bx = cx0 + i * (cwid / len(bars)) + 0.8 * mm
        c.setFillColor(MINT)
        c.roundRect(bx, cy0, bwid, chgt * value, 0.8 * mm, stroke=0, fill=1)
        pts.append((bx + bwid / 2, cy0 + chgt * value))
    c.setStrokeColor(TEAL)
    c.setLineWidth(1.1)
    for (x1, y1), (x2, y2) in itertools.pairwise(pts):
        c.line(x1, y1, x2, y2)


def gitops_loop(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    zone(c, x, y, w, h, "GitOps loop — one owner per deployment", TEAL, [3, 3])
    bw, bh = 52 * mm, 15 * mm
    left = x + 12 * mm
    right = x + w - 12 * mm - bw
    top = y + h - 24 * mm
    bottom = y + 20 * mm

    node(c, left, top, bw, bh, "main on GitHub", "the desired state", icon="git",
         icon_color=BLUE, tsize=9.2, ssize=7)
    node(c, right, top, bw, bh, "Argo CD", "automated sync + self-heal", icon="k8s",
         icon_color=TEAL, tsize=9.2, ssize=7)
    node(c, right, bottom, bw, bh, "Cluster", "Ingress · Deployments · StatefulSet",
         icon="cube", icon_color=VIOLET, tsize=9.2, ssize=6.6)
    node(c, left, bottom, bw, bh, "CI promotion commit", "values-release.json · [skip ci]",
         icon="doc", icon_color=AMBER, tsize=9.2, ssize=6.6)

    elbow(c, [(left + bw + 2 * mm, top + bh / 2), (right - 2 * mm, top + bh / 2)],
          TEAL, 1.2, 2.3 * mm, label="tracks main")
    elbow(c, [(right + bw / 2, top - 1.5 * mm), (right + bw / 2, bottom + bh + 1.5 * mm)],
          TEAL, 1.2, 2.3 * mm, label="helm apply")
    elbow(c, [(right - 2 * mm, bottom + bh / 2), (left + bw + 2 * mm, bottom + bh / 2)],
          AMBER, 1.2, 2.3 * mm, label="writes the verified SHA")
    elbow(c, [(left + bw / 2, bottom + bh + 1.5 * mm), (left + bw / 2, top - 1.5 * mm)],
          BLUE, 1.2, 2.3 * mm, label="commit")


def aws_vpc(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    zone(c, x, y, w, h, "AWS VPC 10.52.0.0/16 · two availability zones", TEAL, None)
    inner = 6 * mm
    ix, iw = x + inner, w - 2 * inner

    cp_h = 12 * mm
    node(c, ix + (iw - min(80 * mm, iw)) / 2, y + h - 7 * mm - cp_h, min(80 * mm, iw), cp_h,
         "managed EKS control plane", "api · audit · authenticator logging",
         icon="k8s", icon_color=VIOLET, tsize=9, ssize=6.6)

    ig_h = 11 * mm
    ig_y = y + h - 7 * mm - cp_h - 7 * mm - ig_h
    node(c, ix + 4 * mm, ig_y, 34 * mm, ig_h, "Internet gateway", None,
         tsize=8.4, icon="cloud", icon_color=BLUE)

    ng_h = 14 * mm
    ng_y = y + 8 * mm
    az_top = ig_y - 8 * mm
    az_bot = ng_y + ng_h + 7 * mm
    az_h = az_top - az_bot
    az_w = (iw - 7 * mm) / 2

    row_h = (az_h - 16 * mm - 2 * 9 * mm) / 3
    for i, name in enumerate(("AZ a", "AZ b")):
        ax = ix + i * (az_w + 7 * mm)
        zone(c, ax, az_bot, az_w, az_h, name, BLUE, [2, 2])
        r1 = az_top - 8 * mm
        node(c, ax + 5 * mm, r1 - row_h, az_w - 10 * mm, row_h, "public subnet",
             "tagged for load balancers", tsize=8.6, ssize=6.6)
        r2 = r1 - row_h - 9 * mm
        if i == 0:
            node(c, ax + 5 * mm, r2 - row_h, az_w - 10 * mm, row_h, "NAT gateway",
                 "private egress", tsize=8.6, ssize=6.6, icon="cloud", icon_color=AMBER)
        else:
            node(c, ax + 5 * mm, r2 - row_h, az_w - 10 * mm, row_h, "route table",
                 "0.0.0.0/0 → NAT in AZ a", tsize=8.6, ssize=6.6, fill=PAPER,
                 stroke=LINE, tcolor=GREY, scolor=GREY)
        r3 = r2 - row_h - 9 * mm
        node(c, ax + 5 * mm, r3 - row_h, az_w - 10 * mm, row_h, "private subnet",
             "no public IP", tsize=8.6, ssize=6.6)
        elbow(c, [(ax + az_w / 2, r3 - row_h), (ax + az_w / 2, ng_y + ng_h)],
              TEAL, 1.0, 1.9 * mm, dash=[2, 2], label="runs in" if i == 0 else None)

    node(c, ix + 6 * mm, ng_y, iw - 12 * mm, ng_h, "managed node group",
         "1–3 × t3.medium · AL2023 · 30 GB gp3 · spans both AZs",
         tsize=9, ssize=6.8, icon="server", icon_color=TEAL)

    elbow(c, [(ix + 4 * mm + 34 * mm + 1.5 * mm, ig_y + ig_h / 2),
              (ix + az_w / 2 + 5 * mm, ig_y + ig_h / 2), (ix + az_w / 2, az_top - 8 * mm)],
          BLUE, 1.0, 1.9 * mm)


def evidence_grid(c: canvas.Canvas, shots: list[tuple[str, str]], top: float,
                  ch: float = 66 * mm) -> None:
    cols = 2
    gap = 7 * mm
    cw = (CW - gap) / cols
    for i, (rel, caption) in enumerate(shots):
        col, row = i % cols, i // cols
        x = L + col * (cw + gap)
        y = top - ch - row * (ch + gap)
        rounded(c, x, y, cw, ch, 2 * mm, WHITE, LINE)
        c.setFillColor(PAPER)
        c.roundRect(x + 1.6 * mm, y + 9.6 * mm, cw - 3.2 * mm, ch - 12 * mm, 1.4 * mm,
                    stroke=0, fill=1)
        path = ROOT / rel
        if path.exists():
            c.drawImage(_reader(path), x + 2.4 * mm, y + 10.4 * mm, cw - 4.8 * mm,
                        ch - 13.6 * mm, preserveAspectRatio=True, anchor="c", mask=None)
        else:
            tx(c, "capture unavailable", x + cw / 2, y + ch / 2, FACE, 9, GREY, "center")
        c.setFillColor(TEAL)
        c.circle(x + 4.4 * mm, y + 4.9 * mm, 1.15 * mm, stroke=0, fill=1)
        tx(c, caption, x + 7 * mm, y + 3.6 * mm, FACE_B, 8.4, INK)


_CACHE: dict[str, ImageReader] = {}


def _reader(path: Path) -> ImageReader:
    key = str(path)
    if key not in _CACHE:
        try:
            from PIL import Image  # reportlab depends on Pillow

            img = Image.open(path).convert("RGB")
            img.thumbnail((1100, 1100))
            _CACHE[key] = ImageReader(img)
        except (OSError, ValueError, ImportError):  # pragma: no cover - raw-file fallback
            _CACHE[key] = ImageReader(str(path))
    return _CACHE[key]


# --- slides ----------------------------------------------------------------
def slide_title(c: canvas.Canvas, index: int, total: int) -> None:
    c.setFillColor(DEEP)
    c.rect(0, 0, WIDTH, HEIGHT, stroke=0, fill=1)
    c.setFillAlpha(0.09)
    c.setFillColor(MINT)
    c.circle(WIDTH - 46 * mm, HEIGHT - 20 * mm, 52 * mm, stroke=0, fill=1)
    c.circle(WIDTH - 100 * mm, -8 * mm, 44 * mm, stroke=0, fill=1)
    c.setFillAlpha(1)
    c.setFillColor(MINT)
    c.rect(0, 0, WIDTH, 3.5 * mm, stroke=0, fill=1)

    tx(c, "MediQueue", 20 * mm, HEIGHT - 46 * mm, FACE_B, 42, WHITE)
    tx(c, "Clinic Appointment Desk", 21 * mm, HEIGHT - 58 * mm, FACE, 17, MINT)
    para(c, "DevOps final capstone — application, CI/CD, infrastructure, Kubernetes, "
            "GitOps and observability", 21 * mm, HEIGHT - 70 * mm, 110 * mm, FACE, 10.5,
         14, WHITE)
    chip_row(c, 21 * mm, HEIGHT - 90 * mm,
             ["React 19", "FastAPI", "PostgreSQL 17", "Docker", "Kubernetes"],
             SOFT, TEAL, 7.4, 5.4 * mm, 2.6 * mm)
    chip_row(c, 21 * mm, HEIGHT - 98 * mm,
             ["Helm", "Terraform", "Prometheus", "Grafana", "Argo CD"],
             SOFT, TEAL, 7.4, 5.4 * mm, 2.6 * mm)
    tx(c, AUTHOR, 21 * mm, 26 * mm, FACE_B, 12.5, WHITE)
    tx(c, REPO, 21 * mm, 20 * mm, FACE, 9.5, MINT)

    mock_app(c, WIDTH - 120 * mm, 30 * mm, 102 * mm, 84 * mm,
             kpis=[("6", "doctors"), ("10", "in queue"), ("3", "urgent")],
             rows=[("Meera K.", "cardiology · 10:30", "Scheduled", BLUE),
                   ("Arun P.", "neurology · 10:45", "Checked in", AMBER),
                   ("Sara T.", "orthopaedics · 11:00", "Urgent", CORAL),
                   ("Nita R.", "dermatology · 11:15", "Completed", GREEN)])


def slide_agenda(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "What This Covers", f"{len(TOPICS)} topics")
    rows = (len(TOPICS) + 1) // 2
    col_w = (CW - 10 * mm) / 2
    for i, (heading, _) in enumerate(TOPICS):
        col, row = divmod(i, rows)
        x = L + col * (col_w + 10 * mm)
        y = TOP - 10 * mm - row * 17.6 * mm
        rounded(c, x, y - 11.4 * mm, col_w, 13.2 * mm, 1.8 * mm, WHITE, LINE)
        badge(c, x + 8 * mm, y - 4.8 * mm, f"{i + 1}", MINT, DEEP, 8.4, 7.2 * mm)
        tx(c, heading, x + 15 * mm, y - 6.2 * mm, FACE_B, 10.4, INK)


def slide_overview(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Project Overview", "what the front desk actually does")
    mock_app(c, L, TOP - 92 * mm, 116 * mm, 92 * mm,
             kpis=[("6", "doctors"), ("10", "in queue"), ("3", "urgent")],
             rows=[("Meera K.", "cardiology · 10:30", "Scheduled", BLUE),
                   ("Arun P.", "neurology · 10:45", "Checked in", AMBER),
                   ("Sara T.", "orthopaedics · 11:00", "Urgent", CORAL),
                   ("Nita R.", "dermatology · 11:15", "Completed", GREEN),
                   ("Omar S.", "general · 11:30", "Scheduled", BLUE)])

    sw = (116 * mm - 2 * 4 * mm) / 3
    for i, (value, label, colour) in enumerate(
            [("6", "doctors on the desk", TEAL), ("11", "API routes", BLUE),
             ("7", "status + urgency levels", VIOLET)]):
        stat(c, L + i * (sw + 4 * mm), TOP - 122 * mm, sw, 22 * mm, value, label, colour)

    card(c, L, 26 * mm, 116 * mm, 34 * mm, "The API behind it",
         ["Every screen is one call: /api/doctors, /api/appointments, /api/stats.",
          "Filters, search and pagination are server-side, so the UI stays thin.",
          "OpenAPI docs are generated, and the browser tests read them."],
         TEAL, icon="server", body_size=8.6)

    rx = L + 126 * mm
    rw = R - rx
    card(c, rx, TOP - 48 * mm, rw, 48 * mm, "Who it is for",
         ["Reception books, checks in, completes or cancels visits.",
          "Doctors are a first-class resource; every appointment references one.",
          "Six departments share one queue."], TEAL, icon="queue")
    card(c, rx, TOP - 102 * mm, rw, 48 * mm, "What it shows",
         ["A KPI strip, status tabs, search and stable pagination.",
          "Urgency is explicit, so the sickest patient is visible first.",
          "Every view is an API call, so the same data feeds the dashboard."],
         BLUE, icon="search")
    card(c, rx, TOP - 156 * mm, rw, 48 * mm, "Why this domain",
         ["An original clinic queue, built for the capstone.",
          "Not a TaskBoard reskin: two related resources, not one flat list.",
          "11 routes with full CRUD plus /api/stats."], VIOLET, icon="doc")


def slide_problem(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "The Problem It Solves", "before · after")
    pw = (CW - 30 * mm) / 2
    card(c, L, TOP - 96 * mm, pw, 96 * mm, "Paper diary and phone calls",
         ["Nobody can see the whole queue at once.",
          "Two staff members can book the same slot.",
          "How many patients are still waiting? No shared answer.",
          "Urgency lives in the receptionist's head.",
          "Nothing is queryable, so nothing can be measured."],
         CORAL, icon="warn", title_size=12.5, body_size=9.8)

    elbow(c, [(L + pw + 3 * mm, TOP - 48 * mm), (R - pw - 3 * mm, TOP - 48 * mm)],
          TEAL, 1.4, 3 * mm, label="one queue")

    card(c, R - pw, TOP - 96 * mm, pw, 96 * mm, "One shared queue in MediQueue",
         ["Every visit is a row with a status the whole desk can see.",
          "Departments belong to doctors, so they are never duplicated.",
          "Urgency is explicit: routine, soon, urgent.",
          "KPI strip answers 'how many are waiting' at a glance.",
          "The same API feeds the UI, the tests and the metrics."],
         GREEN, icon="check", title_size=12.5, body_size=9.8)

    band = [("Duplicate bookings", "gone — a visit is one row with one status", TEAL),
            ("The waiting room", "visible — the KPI strip answers it at a glance", BLUE),
            ("Urgency", "explicit — routine, soon or urgent on every row", AMBER)]
    bw = (CW - 2 * 8 * mm) / 3
    for i, (title, detail, colour) in enumerate(band):
        card(c, L + i * (bw + 8 * mm), 26 * mm, bw, 40 * mm, title, [detail], colour,
             body_size=9)

    footer_note(c, "MediQueue keeps one queue that the front desk, the API and the "
                   "dashboard all read from the same place.")


def slide_architecture(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Architecture", "commit SHA is the artifact identity")
    lw = 104 * mm
    h = 15 * mm
    gap = 5.4 * mm
    steps = [("Developer", "git push", BLUE, "terminal"),
             ("GitHub · main", "the desired state", VIOLET, "git"),
             ("GitHub Actions", "test · build · scan · verify", TEAL, "server"),
             ("GHCR", "images tagged with the commit SHA", AMBER, "cube"),
             ("values-release.json", "committed by CI, [skip ci]", BLUE, "doc"),
             ("Argo CD", "sync + self-heal, pruning off", TEAL, "k8s")]
    y = TOP - h
    for i, (label, sub, colour, icon) in enumerate(steps):
        node(c, L, y, lw, h, label, sub, tsize=9.8, ssize=7.2, icon=icon, icon_color=colour)
        if i < len(steps) - 1:
            elbow(c, [(L + lw / 2, y - 0.6 * mm), (L + lw / 2, y - gap + 0.6 * mm)],
                  TEAL, 1.0, 2 * mm)
        y -= h + gap

    cx = L + lw + 16 * mm
    cwd = R - cx
    cluster_map(c, cx, BOT + 6 * mm, cwd, TOP - BOT - 6 * mm)
    elbow(c, [(L + lw + 1 * mm, TOP - 5 * (h + gap) - h / 2),
              (cx - 1 * mm, TOP - 5 * (h + gap) - h / 2)], TEAL, 1.3, 2.6 * mm,
          label="helm apply")
    card(c, L, 26 * mm, lw, 36 * mm, "One identity end to end",
         ["The image tag is the commit SHA that built it.",
          "Argo CD applies the exact SHA CI already verified on Kind.",
          "Nothing is deployed that has not passed every gate behind it."],
         BLUE, icon="git", body_size=8.6)
    footer_note(c, "The same image is built, scanned, verified on an ephemeral Kind "
                   "cluster, published, promoted and then reconciled — one SHA end to end.")


def slide_tech(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Tech Stack", "eight layers, one repository")
    layers = [("Frontend", "React 19 · Vite · Lucide icons · hand-written responsive CSS",
               BLUE, "browser"),
              ("API", "Python 3.13 · FastAPI · Pydantic · SQLAlchemy 2", TEAL, "server"),
              ("Data", "PostgreSQL 17 · Alembic migrations", AMBER, "db"),
              ("Quality", "pytest (26 cases) · Ruff · Playwright (17 checks)", GREEN, "check"),
              ("Containers", "non-root Alpine images · multi-stage Nginx frontend",
               VIOLET, "cube"),
              ("CI/CD", "GitHub Actions · Trivy gate · GHCR by commit SHA", CORAL, "shield"),
              ("Infrastructure", "Terraform (VPC + EKS) · Helm · Kubernetes", BLUE, "cloud"),
              ("Observability", "Prometheus · Grafana · Argo CD GitOps", TEAL, "gauge")]
    lh = 17.6 * mm
    y = TOP - lh
    for name, detail, colour, icon in layers:
        rounded(c, L, y, CW, lh, 1.9 * mm, WHITE, LINE)
        rounded(c, L, y, 42 * mm, lh, 1.9 * mm, colour, None)
        c.setFillColor(colour)
        c.rect(L + 34 * mm, y, 8 * mm, lh, stroke=0, fill=1)
        icon_at(c, icon, L + 8.5 * mm, y + lh / 2, 5.6 * mm, WHITE)
        tx(c, name, L + 15 * mm, y + lh / 2 - 3.4, FACE_B, 11, WHITE)
        tx(c, detail, L + 48 * mm, y + lh / 2 - 3.4, FACE, 9.4, INK)
        y -= lh + 2.6 * mm


def slide_data(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Application Data Model",
           "two related resources, one real foreign key")
    erd(c, L, TOP - 76 * mm, 168 * mm, 76 * mm)

    tx(c, "status", L, TOP - 88 * mm, FACE_B, 10, INK)
    chip_row(c, L, TOP - 95 * mm, ["scheduled", "checked_in", "completed", "cancelled"],
             SOFT, TEAL, 8.6, 6.4 * mm, 3 * mm)
    tx(c, "urgency", L, TOP - 110 * mm, FACE_B, 10, INK)
    chip_row(c, L, TOP - 117 * mm, ["routine", "soon", "urgent"], HexColor("#f6e6d6"),
             AMBER, 8.6, 6.4 * mm, 3 * mm)

    rx = L + 180 * mm
    rw = R - rx
    card(c, rx, TOP - 52 * mm, rw, 52 * mm, "Design decisions",
         ["Department belongs to the doctor, so it is never repeated per visit.",
          "doctor_id is a real foreign key, so a visit cannot outlive its doctor.",
          "Status and urgency are validated enums, not free text."],
         TEAL, icon="doc", body_size=8.6)
    card(c, rx, TOP - 104 * mm, rw, 48 * mm, "Constraints & indexes",
         ["Primary key on both tables; appointments.doctor_id is indexed.",
          "List filters escape wildcards, so a search for % is a search for %.",
          "Pagination is stable because the sort ends on a unique column."],
         BLUE, icon="db", body_size=8.6)

    for i, (title, detail, colour) in enumerate(
            [("Migrations", ("Alembic owns the schema; CI runs alembic upgrade head "
              "against real PostgreSQL before pytest."), AMBER),
             ("API surface", ("11 routes: /api/doctors and /api/appointments with "
              "full CRUD, plus /api/stats and /healthz."), TEAL),
             ("Freshness", ("updated_at is set by the API, so the desk can see how "
              "long a patient has been waiting."), VIOLET)]):
        bw = (CW - 2 * 7 * mm) / 3
        card(c, L + i * (bw + 7 * mm), 26 * mm, bw, 40 * mm, title, [detail], colour,
             body_size=8.6)


def slide_testing(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Testing And Code Quality",
           "no image is built until these pass")
    gate_ladder(c, L, TOP - 4 * mm, 110 * mm,
                [("Ruff", "import order · bugbear rules · 110-column limit"),
                 ("pytest", "26 cases against PostgreSQL in CI, SQLite locally"),
                 ("frontend build", "the production bundle must compile"),
                 ("helm lint", "the chart must be valid before it ships"),
                 ("terraform validate", "no cloud resources are created")],
                step_h=26 * mm, gap=5 * mm)

    rx = L + 124 * mm
    rw = R - rx
    stat(c, rx, TOP - 26 * mm, (rw - 4 * mm) / 2, 22 * mm, "26", "pytest API cases", TEAL)
    stat(c, rx + (rw + 4 * mm) / 2, TOP - 26 * mm, (rw - 4 * mm) / 2, 22 * mm, "17",
         "Playwright checks", BLUE)
    card(c, rx, TOP - 100 * mm, rw, 64 * mm, "What the tests cover",
         ["CRUD on both resources and every route group",
          "filters, stats and pagination stability",
          "validation, 404 and 409 conflict paths",
          "wildcard escaping in list filters",
          "readiness failing when the database is gone",
          "metric cardinality: route templates, never raw IDs"],
         GREEN, icon="check", body_size=8.8)
    card(c, rx, 26 * mm, rw, 53 * mm, "Local and in CI",
         ["Locally pytest uses SQLite, so a laptop needs no database.",
          "In CI the same tests run against PostgreSQL 17 first.",
          "Playwright drives the real frontend through the Ingress.",
          "A failing gate stops the run; nothing is published."],
         BLUE, icon="terminal", body_size=8.8)


def slide_containers(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Containers", "the same images run in Compose and in the cluster")
    boxes = [("postgres", "postgres:17-alpine", AMBER, "db"),
             ("migrate", "alembic upgrade head · then exits", BLUE, "terminal"),
             ("backend", "python:3.13-alpine · UID 10001", TEAL, "server"),
             ("frontend", "nginx-unprivileged · UID 101", VIOLET, "browser")]
    bw = (CW - 3 * 14 * mm) / 4
    for i, (label, sub, colour, icon) in enumerate(boxes):
        bx = L + i * (bw + 14 * mm)
        node(c, bx, TOP - 34 * mm, bw, 22 * mm, label, sub, tsize=10, ssize=7.2,
             icon=icon, icon_color=colour)
        if i < 3:
            elbow(c, [(bx + bw + 2 * mm, TOP - 23 * mm), (bx + bw + 12 * mm, TOP - 23 * mm)],
                  TEAL, 1.2, 2.4 * mm)
    footer_note(c, "Compose healthchecks gate each service on the previous one being "
                   "ready; the migrate service must finish before the API starts.")
    card(c, L, TOP - 104 * mm, (CW - 6 * mm) / 2, 44 * mm, "Backend image",
         ["Multi-stage build; pip is removed from the runtime layer.",
          "Runs as UID 10001, not root.",
          "Uvicorn workers behind a readiness probe."], TEAL, icon="server")
    card(c, L + (CW + 6 * mm) / 2, TOP - 104 * mm, (CW - 6 * mm) / 2, 44 * mm,
         "Frontend image",
         ["node:24 builds the bundle; Nginx serves it.",
          "nginx-unprivileged listens as UID 101, not root.",
          "/healthz is a real endpoint, so the probe is honest."], VIOLET, icon="browser")

    for i, (title, detail, colour) in enumerate(
            [("Runs as non-root", "No container in the stack needs root to start.", TEAL),
             ("No secrets baked in", ("Credentials arrive as environment variables at "
              "deploy time, never in a layer."), CORAL),
             ("Readiness, not hope", ("Traffic only reaches pods that report ready, so "
              "a rollout cannot serve 503s."), BLUE)]):
        bw = (CW - 2 * 7 * mm) / 3
        card(c, L + i * (bw + 7 * mm), 26 * mm, bw, 42 * mm, title, [detail], colour,
             body_size=8.8)


def slide_cicd(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "CI/CD Pipeline", "run 38755163712 — green in five minutes")
    lanes = [("Job 1 · test",
              [("ruff", TEAL), ("alembic + pytest", TEAL), ("frontend build", TEAL),
               ("helm lint", TEAL), ("terraform validate", TEAL)], BLUE),
             ("Job 2 · build-scan-deploy",
              [("build images (SHA)", TEAL), ("Trivy ×2", CORAL), ("Kind deploy + smoke", TEAL),
               ("Playwright", TEAL), ("push to GHCR", AMBER), ("promote SHA", AMBER)], TEAL)]
    y = TOP - 4 * mm
    trivy_gx = None
    for lane, stages, colour in lanes:
        tx(c, lane, L, y, FACE_B, 11, colour)
        bw = (CW - (len(stages) - 1) * 6 * mm) / len(stages)
        by = y - 26 * mm
        for i, (name, accent) in enumerate(stages):
            bx = L + i * (bw + 6 * mm)
            node(c, bx, by, bw, 15 * mm, name, None, tsize=8.6,
                 stroke=accent, tcolor=INK, fill=WHITE)
            if i < len(stages) - 1:
                elbow(c, [(bx + bw + 0.8 * mm, by + 7.5 * mm),
                          (bx + bw + 5.2 * mm, by + 7.5 * mm)], LINE, 1.0, 1.8 * mm)
            if name == "Trivy ×2":
                trivy_gx = bx + bw / 2
        y -= 34 * mm
    if trivy_gx:
        icon_at(c, "shield", trivy_gx, TOP - 66 * mm, 6 * mm, CORAL)
        tx(c, "the gate", trivy_gx + 4.5 * mm, TOP - 67.6 * mm, FACE_B, 7.4, CORAL)

    card(c, L, 57 * mm, (CW - 6 * mm) / 2, 56 * mm, "Guarantees",
         ["No continue-on-error on any quality or security gate.",
          "Images are tagged with the full commit SHA, never latest.",
          "The Kind cluster is ephemeral: created and thrown away per run.",
          ("Superseded runs cancel themselves, so main is never queued behind a "
          "stale build."),
          "Promotion commits carry [skip ci], so a release cannot loop."],
         TEAL, icon="shield", body_size=8.8)
    card(c, L + (CW + 6 * mm) / 2, 57 * mm, (CW - 6 * mm) / 2, 56 * mm,
         "What the run produced",
         ["26 tests and 17 browser checks, zero failures.",
          "Both Trivy scans clean: alpine and every Python package.",
          "Both images published to GHCR with a recorded digest.",
          ("helm template asserts the exact image references before the deploy "
          "step waits eight minutes."),
          "The deployed chart is verified on Kind before anything is published."],
         GREEN, icon="check", body_size=8.8)

    for i, (value, label) in enumerate([("5", "minutes, end to end"),
                                        ("2", "jobs, test then deploy"),
                                        ("0", "retries needed"),
                                        ("8", "minute deploy budget")]):
        bw = (CW - 3 * 5 * mm) / 4
        stat(c, L + i * (bw + 5 * mm), 26 * mm, bw, 22 * mm, value, label, TEAL)


def slide_security(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Security: The Trivy Gate", "one layer, not the whole story")
    layers = [("Static analysis (SAST)", "reads source", SOFT, GREY),
              ("Dependency scanning", "known CVEs in libraries", SOFT, GREY),
              ("Secret scanning", "credentials in the tree", SOFT, GREY),
              ("Container image scanning", "Trivy — the layer this project runs", MINT, DEEP),
              ("Runtime security", "what runs at deploy time", SOFT, GREY)]
    lh = 17 * mm
    y = TOP - 13 * mm - lh
    for name, detail, fill, tcolor in layers:
        rounded(c, L, y, 132 * mm, lh, 1.8 * mm, fill, LINE if fill == SOFT else MINT)
        tx(c, name, L + 6 * mm, y + lh / 2 - 0.6 * mm, FACE_B, 9.8, tcolor)
        tx(c, detail, L + 76 * mm, y + lh / 2 - 0.6 * mm, FACE, 8, GREY)
        y -= lh + 3 * mm

    rx = L + 146 * mm
    rw = R - rx
    card(c, rx, TOP - 44 * mm, rw, 44 * mm, "The gate",
         ["severity: HIGH,CRITICAL",
          "exit-code: 1 — a finding fails the build",
          "vuln-type: os,library on both images",
          "Runs after the build, before any deploy."], CORAL, icon="shield",
         body_size=8.8)
    card(c, rx, TOP - 90 * mm, rw, 44 * mm, "What it does not prove",
         ["Business logic and authorisation are not scanned.",
          "A clean image is not a clean application.",
          "No runtime or network policy is enforced here."], AMBER, icon="warn",
         body_size=8.8)
    stat(c, rx, TOP - 116 * mm, (rw - 4 * mm) / 2, 20 * mm, "0", "HIGH or CRITICAL", GREEN)
    stat(c, rx + (rw + 4 * mm) / 2, TOP - 116 * mm, (rw - 4 * mm) / 2, 20 * mm, "2/2",
         "images scanned", TEAL)

    for i, (title, detail, colour) in enumerate(
            [("No secrets in the tree", ("Database and Grafana credentials are generated "
              "at deploy time and never committed."), CORAL),
             ("Non-root containers", ("Both images run as an unprivileged UID, so a "
              "container escape starts with nothing."), TEAL),
             ("Prove, then publish", ("An image is scanned and deployed to Kind before "
              "it is ever pushed to the registry."), BLUE)]):
        bw = (CW - 2 * 7 * mm) / 3
        card(c, L + i * (bw + 7 * mm), 26 * mm, bw, 40 * mm, title, [detail], colour,
             body_size=8.6)

    footer_note(c, "No credentials are committed; every local secret is generated at "
                   "deploy time.")


def slide_kubernetes(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Kubernetes And Helm", "one chart, one values file, 16 objects")
    cluster_map(c, L, BOT + 6 * mm, 176 * mm, TOP - BOT - 6 * mm)
    rx = L + 190 * mm
    rw = R - rx
    card(c, rx, TOP - 46 * mm, rw, 46 * mm, "Helm rendering",
         ["1 chart + values files produce 16 objects.",
          "Values are merged in order, later files win.",
          "values.yaml → values-release.json (CI) → values-local.yaml."],
         TEAL, icon="doc", body_size=8.8)
    card(c, rx, TOP - 92 * mm, rw, 42 * mm, "Scheduling",
         ["Readiness gates endpoint membership, so traffic only reaches ready pods.",
          "HPA targets 70% CPU across 2–4 replicas; 2 → 3 was observed under load.",
          "PostgreSQL is a StatefulSet with a PVC; the rest is stateless."],
         BLUE, icon="gauge", body_size=8.8)
    card(c, rx, TOP - 138 * mm, rw, 42 * mm, "16 rendered objects",
         ["Deployments and Services for both tiers.",
          "A StatefulSet with its PersistentVolumeClaim for PostgreSQL.",
          "Ingress, ConfigMap, ServiceAccount and the HorizontalPodAutoscaler.",
          "A one-shot Job runs the migration before the API rolls out."],
         VIOLET, icon="cube", body_size=8.8)
    sw = (rw - 4 * mm) / 2
    stat(c, rx, 26 * mm, sw, 19 * mm, "16", "objects, one chart", TEAL)
    stat(c, rx + sw + 4 * mm, 26 * mm, sw, 19 * mm, "2–4", "replicas, HPA", BLUE)


def slide_observability(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Observability", "scrape every replica, not just one")
    metrics_flow(c, L, TOP - 28 * mm, CW, 22 * mm)
    dashboard_mock(c, L, TOP - 108 * mm, CW, 76 * mm)
    card(c, L, 26 * mm, (CW - 7 * mm) / 2, 46 * mm, "What we measure",
         ["Request rate and latency per route template.",
          "5xx ratio, so a broken deploy is visible in seconds.",
          "Live replica count against the HPA target.",
          "Database readiness, because a queue with no store is down."],
         TEAL, icon="gauge", body_size=8.8)
    card(c, L + (CW + 7 * mm) / 2, 26 * mm, (CW - 7 * mm) / 2, 46 * mm, "Two alert rules",
         ["One fires when no backend replica is scrapeable.",
          "One fires on a sustained 5xx ratio.",
          "Both were observed INACTIVE on the live stack.",
          "Locally there is no notification target, so they only change state."],
         CORAL, icon="warn", body_size=8.8)
    footer_note(c, "Counters are labelled with route templates, never raw IDs, so metric "
                   "cardinality stays bounded.")


def slide_gitops(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "GitOps With Argo CD", "CI writes it, Argo CD applies it")
    gitops_loop(c, L, TOP - 112 * mm, CW, 108 * mm)
    for i, (title, detail, colour) in enumerate(
            [("Default branch", ("main is the only source of truth; Argo CD tracks the "
              "branch, never a hand-made tag."), BLUE),
             ("Sync policy", ("automated with self-heal, so drift is corrected without "
              "anyone noticing it happened."), TEAL),
             ("Pruning off", ("a bad commit cannot delete the database or its volume, "
              "so the worst case is a stalled sync."), AMBER)]):
        bw = (CW - 2 * 7 * mm) / 3
        card(c, L + i * (bw + 7 * mm), 26 * mm, bw, 42 * mm, title, [detail], colour,
             body_size=8.8)
    footer_note(c, "Promotion commits carry [skip ci] so a release never re-triggers an "
                   "image build.")


def slide_terraform(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Terraform: AWS Infrastructure", "written and validated, apply deferred")
    aws_vpc(c, L, BOT + 6 * mm, 176 * mm, TOP - BOT - 6 * mm)
    rx = L + 190 * mm
    rw = R - rx
    card(c, rx, TOP - 52 * mm, rw, 52 * mm, "What the plan creates",
         ["VPC 10.52.0.0/16 across two availability zones",
          "two public and two private subnets, tagged for load balancers",
          "one NAT gateway for private egress",
          "managed EKS control plane with api/audit/authenticator logging",
          "managed node group: 1–3 × t3.medium, AL2023, 30 GB"], TEAL, icon="cloud",
         body_size=8.4)
    card(c, rx, TOP - 96 * mm, rw, 44 * mm, "Guardrails",
         ["EBS CSI driver via IRSA, so PVCs can actually bind.",
          "The EKS API is restricted to supplied CIDRs.",
          "0.0.0.0/0 is rejected by input validation."], AMBER, icon="shield",
         body_size=8.4)
    card(c, rx, 30 * mm, rw, 49 * mm, "How it is verified",
         ["terraform fmt -check and terraform validate run in CI.",
          "The plan is reviewed as code, not as console clicks.",
          "No apply is run, so no AWS account has been touched.",
          "Applying and destroying is a single documented command."], BLUE,
         icon="terminal", body_size=8.4)
    footer_note(c, "Infrastructure as code is reviewable; console clicks are not.")


def slide_evidence(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Evidence: It Runs", "captured on this machine and in CI")
    evidence_grid(c, [
        ("evidence/dashboards/app-ingress.png", "Served through the Ingress hostname"),
        ("evidence/dashboards/prometheus-targets.png", "Both backend replicas UP"),
        ("evidence/dashboards/argocd-applications.png", "Argo CD synced from GitHub"),
        ("evidence/dashboards/github-run.png", "Pipeline green: both jobs passed"),
    ], TOP - 4 * mm, ch=62 * mm)
    for i, (value, label) in enumerate([("26", "tests passed"), ("17", "browser checks"),
                                        ("0", "CVEs found"), ("2", "images published")]):
        bw = (CW - 3 * 5 * mm) / 4
        stat(c, L + i * (bw + 5 * mm), 24 * mm, bw, 20 * mm, value, label, TEAL)


def slide_troubleshooting(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Troubleshooting Lab", "scripts/troubleshooting-check.py")
    headers = ["Symptom", "First command", "Root cause", "Fix"]
    widths = [46 * mm, 58 * mm, 62 * mm, CW - 166 * mm]
    rows = [("ImagePullBackOff", "kubectl describe pod", "a tag that does not exist",
             "correct the tag, watch the rollout", CORAL),
            ("Service has no endpoints", "kubectl get endpoints",
             "selector matches no pod labels", "fix the selector or the labels", AMBER),
            ("/ready returns 503", "kubectl logs <pod>", "the migration never ran",
             "run the Job, then let readiness pass", BLUE),
            ("HPA will not scale", "kubectl top pods", "no CPU request on the container",
             "set resource requests, then re-check", GREEN)]
    y = TOP - 12 * mm
    cx = L
    for head, col in zip(headers, widths):
        tx(c, head.upper(), cx + 2 * mm, y, FACE_B, 8, GREY)
        cx += col
    y -= 8 * mm
    rh = 26 * mm
    for symptom, command, cause, fix, colour in rows:
        rounded(c, L, y - rh, CW, rh, 1.8 * mm, WHITE, LINE)
        c.setFillColor(colour)
        c.roundRect(L, y - rh, 1.7 * mm, rh, 0.85 * mm, stroke=0, fill=1)
        my = y - rh / 2 - 3.2 * mm
        cx = L
        para(c, symptom, cx + 6 * mm, my, widths[0] - 8 * mm, FACE_B, 9.6, 11.6, INK)
        cx += widths[0]
        tx(c, command, cx + 2 * mm, my, FACE_M, 7.6, TEAL)
        cx += widths[1]
        para(c, cause, cx + 2 * mm, my, widths[2] - 4 * mm, FACE, 9, 11.4, GREY)
        cx += widths[2]
        para(c, fix, cx + 2 * mm, my, widths[3] - 4 * mm, FACE, 9, 11.4, INK)
        y -= rh + 4 * mm
    card(c, L, y - 26 * mm, CW, 26 * mm, "The lesson that matters",
         [("helm rollback restores chart configuration, not database migrations — "
          "schema changes need their own, forward-only path.")],
         VIOLET, icon="warn", body_size=9)


def slide_limits(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Known Limits", "stated plainly, not discovered later")
    items = [("No authentication or RBAC",
              ("Anyone who can reach the ingress can read and change every appointment. "
              "Keep it local, or add auth before it holds real data."), "High", CORAL),
             ("Single PostgreSQL instance",
              ("No backups, no failover and no encryption policy. A lost volume loses "
              "the whole queue."), "Medium", AMBER),
             ("Ephemeral monitoring storage",
              ("Prometheus and Grafana keep their data in the pod, so history is lost on "
              "every restart."), "Low", BLUE),
             ("Alerts have no destination",
              ("The rules fire and change state, but nothing is notified until a receiver "
              "is configured."), "Low", BLUE),
             ("AWS apply deferred",
              ("Terraform is written and validated only; no account has been touched, so "
              "the EKS path is unproven in practice."), "Info", GREY)]
    cw = (CW - 8 * mm) / 2
    ch = 34 * mm
    for i, (title, detail, sev, colour) in enumerate(items):
        col, row = divmod(i, 3)
        x = L + col * (cw + 8 * mm)
        y = TOP - 42 * mm - row * 47 * mm
        rounded(c, x, y, cw, ch, 2.2 * mm, WHITE, LINE)
        c.setFillColor(colour)
        c.roundRect(x, y, 1.7 * mm, ch, 0.85 * mm, stroke=0, fill=1)
        tx(c, title, x + 6 * mm, y + ch - 9 * mm, FACE_B, 10.5, INK)
        para(c, detail, x + 6 * mm, y + ch - 16.5 * mm, cw - 30 * mm, FACE, 8.8, 11.4, GREY)
        sw = stringWidth(sev, FACE_B, 7.4) + 5 * mm
        rounded(c, x + cw - 5 * mm - sw, y + ch - 13.4 * mm, sw, 6 * mm, 3 * mm, colour, None)
        tx(c, sev, x + cw - 5 * mm - sw / 2, y + ch - 11.4 * mm, FACE_B, 7.4, WHITE, "center")


def slide_learnings(c: canvas.Canvas, index: int, total: int) -> None:
    chrome(c, index, total, "Key Learnings", "what the work actually taught")
    items = ["A deployment is only as trustworthy as the gates in front of it.",
             "Readiness is a different question from liveness, and it changes routing.",
             "Immutable SHA tags make production traceable back to a commit.",
             "Metrics must be bounded: route templates, not IDs, keep dashboards sane.",
             "Infrastructure as code is reviewable; console clicks are not.",
             "One owner per deployment avoids Helm and Argo CD fighting each other."]
    cw = (CW - 10 * mm) / 2
    ch = 40 * mm
    rows = (len(items) + 1) // 2
    for i, text in enumerate(items):
        col, row = divmod(i, rows)
        x = L + col * (cw + 10 * mm)
        y = TOP - 46 * mm - row * 48 * mm
        rounded(c, x, y, cw, ch, 2 * mm, WHITE, LINE)
        badge(c, x + 9 * mm, y + ch / 2, f"{i + 1}", MINT, DEEP, 9, 8.4 * mm)
        lines = wrap(text, FACE, 9.6, cw - 24 * mm)
        ty = y + ch / 2 + len(lines) * 12.6 / 2 - 9.6 * 0.34
        for line in lines:
            tx(c, line, x + 18 * mm, ty, FACE, 9.6, INK)
            ty -= 12.6


TOPICS: list[tuple[str, object]] = [
    ("Project Overview", slide_overview),
    ("The Problem It Solves", slide_problem),
    ("Architecture", slide_architecture),
    ("Tech Stack", slide_tech),
    ("Application Data Model", slide_data),
    ("Testing And Code Quality", slide_testing),
    ("Containers", slide_containers),
    ("CI/CD Pipeline", slide_cicd),
    ("Security: Trivy Gate", slide_security),
    ("Kubernetes And Helm", slide_kubernetes),
    ("Observability", slide_observability),
    ("GitOps With Argo CD", slide_gitops),
    ("Terraform: AWS Infrastructure", slide_terraform),
    ("Evidence: It Runs", slide_evidence),
    ("Troubleshooting Lab", slide_troubleshooting),
    ("Known Limits", slide_limits),
    ("Key Learnings", slide_learnings),
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=landscape(A4))
    c.setTitle(TITLE)
    c.setAuthor(AUTHOR)
    c.setSubject("DevOps final capstone: application, CI/CD, infrastructure, Kubernetes, "
                 "GitOps and observability")
    pages = [slide_title, slide_agenda] + [fn for _, fn in TOPICS]
    total = len(pages)
    for i, page in enumerate(pages, 1):
        page(c, i, total)
        c.showPage()
    c.save()
    print(f"Wrote {OUT} with {total} slides")


if __name__ == "__main__":
    main()
