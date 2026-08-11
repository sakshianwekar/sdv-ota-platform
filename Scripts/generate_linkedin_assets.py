#!/usr/bin/env python3
"""Generate LinkedIn launch assets: architecture diagram + carousel PDF."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Docs" / "linkedin-assets"
OUT.mkdir(parents=True, exist_ok=True)

# Professional automotive/tech palette (avoid purple-glow / cream-terracotta clichés)
NAVY = HexColor("#0B1F33")
STEEL = HexColor("#1A3A52")
TEAL = HexColor("#1F7A6C")
TEAL_LIGHT = HexColor("#2A9B88")
SLATE = HexColor("#E8EEF2")
MUTED = HexColor("#8FA3B5")
ACCENT = HexColor("#D4A017")  # restrained gold highlight
WHITE = white
DARK_TEXT = HexColor("#102433")


def _try_font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _register_pdf_fonts() -> tuple[str, str]:
    regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if Path(regular).exists() and Path(bold).exists():
        pdfmetrics.registerFont(TTFont("Body", regular))
        pdfmetrics.registerFont(TTFont("Body-Bold", bold))
        return "Body", "Body-Bold"
    return "Helvetica", "Helvetica-Bold"


def rounded_rect(draw: ImageDraw.ImageDraw, xy, fill, radius=18, outline=None, width=2):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_arrow(draw: ImageDraw.ImageDraw, x1, y1, x2, y2, color=(47, 155, 136), width=4):
    draw.line((x1, y1, x2, y2), fill=color, width=width)
    # arrow head
    if x2 >= x1:
        draw.polygon([(x2, y2), (x2 - 12, y2 - 8), (x2 - 12, y2 + 8)], fill=color)
    else:
        draw.polygon([(x2, y2), (x2 + 12, y2 - 8), (x2 + 12, y2 + 8)], fill=color)


def create_architecture_diagram() -> Path:
    """Horizontal pipeline diagram for LinkedIn / carousel."""
    w, h = 1600, 900
    img = Image.new("RGB", (w, h), (11, 31, 51))
    draw = ImageDraw.Draw(img)

    title_font = _try_font(42, bold=True)
    sub_font = _try_font(22)
    box_font = _try_font(24, bold=True)
    small_font = _try_font(18)
    tiny_font = _try_font(16)

    # subtle top gradient bar
    for i in range(8):
        shade = 31 + i * 4
        draw.rectangle([0, i, w, i + 1], fill=(shade, 70 + i, 82))

    draw.text((60, 40), "SDV OTA Platform — Update Pipeline", font=title_font, fill=(232, 238, 242))
    draw.text(
        (60, 100),
        "Signed delivery  ·  A/B flash slots  ·  Health-checked auto-rollback",
        font=sub_font,
        fill=(143, 163, 181),
    )

    boxes = [
        ("OTA Cloud", "FastAPI", "Serves signed\npackages"),
        ("OTA Client", "Python", "Poll · download\nverify"),
        ("Installer", "Python", "Extract · checks\ncall bootloader"),
        ("Bootloader", "C", "stage · activate\nrollback"),
        ("Virtual ECU", "C firmware", "slotA / slotB\nA/B images"),
        ("Health\nMonitor", "C", "heartbeat watch\nauto-rollback"),
    ]

    box_w, box_h = 200, 170
    gap = 40
    total = len(boxes) * box_w + (len(boxes) - 1) * gap
    start_x = (w - total) // 2
    y = 280

    for i, (title, lang, desc) in enumerate(boxes):
        x = start_x + i * (box_w + gap)
        # card
        rounded_rect(
            draw,
            (x, y, x + box_w, y + box_h),
            fill=(26, 58, 82),
            radius=20,
            outline=(42, 155, 136),
            width=3,
        )
        # accent strip
        draw.rounded_rectangle((x, y, x + box_w, y + 10), radius=6, fill=(42, 155, 136))

        # title (may be two lines for Health Monitor)
        lines = title.split("\n")
        ty = y + 28
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=box_font)
            tw = bbox[2] - bbox[0]
            draw.text((x + (box_w - tw) // 2, ty), line, font=box_font, fill=(232, 238, 242))
            ty += 28

        # lang badge
        bb = draw.textbbox((0, 0), lang, font=tiny_font)
        lw = bb[2] - bb[0] + 20
        lx = x + (box_w - lw) // 2
        ly = ty + 4
        rounded_rect(draw, (lx, ly, lx + lw, ly + 26), fill=(31, 122, 108), radius=10)
        draw.text((lx + 10, ly + 4), lang, font=tiny_font, fill=(232, 238, 242))

        # description
        dy = ly + 40
        for dline in desc.split("\n"):
            db = draw.textbbox((0, 0), dline, font=small_font)
            dw = db[2] - db[0]
            draw.text((x + (box_w - dw) // 2, dy), dline, font=small_font, fill=(143, 163, 181))
            dy += 24

        if i < len(boxes) - 1:
            ax1 = x + box_w + 4
            ax2 = x + box_w + gap - 4
            draw_arrow(draw, ax1, y + box_h // 2, ax2, y + box_h // 2)

    # bottom callouts
    callouts = [
        (120, "1. Authenticity", "Ed25519 + SHA-256 before install"),
        (580, "2. Safe install", "Stage inactive A/B slot first"),
        (1040, "3. Recovery", "Health fail → automatic rollback"),
    ]
    cy = 540
    for cx, head, body in callouts:
        rounded_rect(draw, (cx, cy, cx + 420, cy + 110), fill=(16, 42, 61), radius=16, outline=(47, 90, 110), width=2)
        draw.text((cx + 24, cy + 22), head, font=box_font, fill=(42, 155, 136))
        draw.text((cx + 24, cy + 62), body, font=small_font, fill=(232, 238, 242))

    draw.text(
        (60, h - 70),
        "Sakshi Anwekar  ×  Tejas   ·   github.com/sakshianwekar/sdv-ota-platform",
        font=small_font,
        fill=(143, 163, 181),
    )

    path = OUT / "ota-architecture-diagram.png"
    img.save(path, "PNG", optimize=True)
    return path


def _wrap(c: canvas.Canvas, text: str, font: str, size: float, max_width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if c.stringWidth(trial, font, size) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def create_carousel_pdf(diagram_path: Path) -> Path:
    """Portrait LinkedIn document carousel ~1080x1350 px at 72dpi ≈ 15x18.75 in; use 1080x1350 points-ish via custom page."""
    # LinkedIn-friendly portrait: 1080 x 1350 points scaled — use points where 1pt≈1px for simplicity at export
    page_w, page_h = 1080, 1350
    body, bold = _register_pdf_fonts()
    path = OUT / "sdv-ota-linkedin-carousel.pdf"
    c = canvas.Canvas(str(path), pagesize=(page_w, page_h))

    def bg(dark: bool = True):
        c.setFillColor(NAVY if dark else SLATE)
        c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
        # top accent line
        c.setFillColor(TEAL)
        c.rect(0, page_h - 12, page_w, 12, fill=1, stroke=0)

    def footer(page_no: int, total: int = 9):
        c.setFillColor(MUTED)
        c.setFont(body, 18)
        c.drawString(56, 48, "SDV OTA Platform")
        c.drawRightString(page_w - 56, 48, f"{page_no} / {total}")

    def title(text: str, y: float, color=WHITE, size=46):
        c.setFillColor(color)
        c.setFont(bold, size)
        for i, line in enumerate(_wrap(c, text, bold, size, page_w - 120)):
            c.drawString(60, y - i * (size + 10), line)
        return y - (len(_wrap(c, text, bold, size, page_w - 120)) * (size + 10))

    def bullet(items: list[str], y: float, color=SLATE, size=28):
        c.setFont(body, size)
        c.setFillColor(color)
        for item in items:
            c.setFillColor(TEAL_LIGHT)
            c.circle(78, y + 8, 6, fill=1, stroke=0)
            c.setFillColor(color)
            lines = _wrap(c, item, body, size, page_w - 180)
            for i, line in enumerate(lines):
                c.drawString(100, y - i * (size + 8), line)
            y -= max(1, len(lines)) * (size + 8) + 18
        return y

    def card(x, y, w, h, heading, body_text):
        c.setFillColor(STEEL)
        c.roundRect(x, y, w, h, 18, fill=1, stroke=0)
        c.setFillColor(TEAL)
        c.roundRect(x, y + h - 10, w, 10, 4, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(bold, 24)
        c.drawString(x + 24, y + h - 48, heading)
        c.setFont(body, 18)
        c.setFillColor(MUTED)
        by = y + h - 84
        for line in _wrap(c, body_text, body, 18, w - 48):
            c.drawString(x + 24, by, line)
            by -= 24

    # --- Slide 1: Hook ---
    bg()
    c.setFillColor(TEAL_LIGHT)
    c.setFont(bold, 20)
    c.drawString(60, page_h - 90, "SOFTWARE-DEFINED VEHICLE")
    y = title("How do cars update firmware without bricking an ECU?", page_h - 160, size=44)
    c.setFillColor(MUTED)
    c.setFont(body, 26)
    for line in _wrap(
        c,
        "A complete software simulation of automotive OTA safety: signed packages, A/B flash slots, and automatic rollback.",
        body,
        26,
        page_w - 120,
    ):
        c.drawString(60, y - 40, line)
        y -= 36
    c.setFillColor(STEEL)
    c.roundRect(60, 180, page_w - 120, 120, 18, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(bold, 26)
    c.drawString(90, 250, "Sakshi Anwekar  ×  Tejas")
    c.setFillColor(MUTED)
    c.setFont(body, 20)
    c.drawString(90, 210, "github.com/sakshianwekar/sdv-ota-platform")
    footer(1)
    c.showPage()

    # --- Slide 2: Problem ---
    bg()
    c.setFillColor(TEAL_LIGHT)
    c.setFont(bold, 20)
    c.drawString(60, page_h - 90, "THE PROBLEM")
    title("Remote updates can fail unsafely", page_h - 160)
    bullet(
        [
            "Unsigned or tampered firmware can reach the vehicle",
            "Overwriting the running image risks a brick",
            "No automatic recovery when new firmware misbehaves",
        ],
        page_h - 320,
    )
    footer(2)
    c.showPage()

    # --- Slide 3: Application ---
    bg()
    c.setFillColor(TEAL_LIGHT)
    c.setFont(bold, 20)
    c.drawString(60, page_h - 90, "WHERE THIS MATTERS")
    title("Real automotive software delivery", page_h - 160)
    cards = [
        (60, 780, "SDV platforms", "Vehicles need continuous software improvement after sale."),
        (60, 560, "ECU firmware OTA", "Motor, brake, battery and other controllers update remotely."),
        (60, 340, "Fleet operations", "Multiple ECUs / vehicles need the same safe update contract."),
    ]
    for x, y0, hdg, txt in cards:
        card(x, y0, page_w - 120, 180, hdg, txt)
    footer(3)
    c.showPage()

    # --- Slide 4: Pipeline + diagram ---
    bg()
    c.setFillColor(TEAL_LIGHT)
    c.setFont(bold, 20)
    c.drawString(60, page_h - 90, "OUR SOLUTION")
    title("End-to-end OTA pipeline", page_h - 150, size=42)
    # embed diagram
    img_w = page_w - 80
    img_h = img_w * 900 / 1600
    c.drawImage(str(diagram_path), 40, page_h - 190 - img_h, width=img_w, height=img_h, preserveAspectRatio=True, mask="auto")
    c.setFillColor(MUTED)
    c.setFont(body, 20)
    c.drawCentredString(page_w / 2, 120, "Cloud → Client → Installer → Bootloader → ECU → Health Monitor")
    footer(4)
    c.showPage()

    # --- Slide 5: A/B ---
    bg()
    c.setFillColor(TEAL_LIGHT)
    c.setFont(bold, 20)
    c.drawString(60, page_h - 90, "SAFETY LAYER 1")
    title("A/B flash slots — never overwrite running firmware", page_h - 160, size=40)
    # two slot cards
    c.setFillColor(STEEL)
    c.roundRect(60, 720, 440, 280, 20, fill=1, stroke=0)
    c.roundRect(580, 720, 440, 280, 20, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.setFont(bold, 28)
    c.drawString(100, 940, "Active slot")
    c.drawString(620, 940, "Inactive slot")
    c.setFillColor(WHITE)
    c.setFont(body, 22)
    c.drawString(100, 860, "Currently running")
    c.drawString(100, 820, "Stay online")
    c.drawString(620, 860, "New package staged here")
    c.drawString(620, 820, "Activated only after verify")
    c.setFillColor(MUTED)
    c.setFont(body, 24)
    y = 640
    for line in _wrap(
        c,
        "Bootloader stages into the inactive slot, then flips active on activate. Rollback flips back if health fails.",
        body,
        24,
        page_w - 120,
    ):
        c.drawString(60, y, line)
        y -= 34
    footer(5)
    c.showPage()

    # --- Slide 6: Crypto ---
    bg()
    c.setFillColor(TEAL_LIGHT)
    c.setFont(bold, 20)
    c.drawString(60, page_h - 90, "SAFETY LAYER 2")
    title("Cryptographic trust before flash", page_h - 160)
    rows = [
        ("Ed25519 signature", "Proves the package is authentic"),
        ("SHA-256 checksum", "Proves the bytes were not altered"),
        ("Downgrade protection", "Rejects older versions before staging"),
        ("Tamper rejection", "Invalid signature/checksum never reaches flash"),
    ]
    y = 980
    for head, desc in rows:
        c.setFillColor(STEEL)
        c.roundRect(60, y - 90, page_w - 120, 100, 16, fill=1, stroke=0)
        c.setFillColor(TEAL_LIGHT)
        c.setFont(bold, 24)
        c.drawString(90, y - 35, head)
        c.setFillColor(MUTED)
        c.setFont(body, 20)
        c.drawString(90, y - 70, desc)
        y -= 130
    footer(6)
    c.showPage()

    # --- Slide 7: Proof ---
    bg()
    c.setFillColor(TEAL_LIGHT)
    c.setFont(bold, 20)
    c.drawString(60, page_h - 90, "WHAT WE PROVED")
    title("End-to-end results", page_h - 160)
    proofs = [
        ("Healthy update", "v1.0 → v1.1 activates and stays healthy"),
        ("Broken update", "Signed v1.2 fails health checks → auto-rollback"),
        ("Security gates", "Tamper and downgrade rejected before flash"),
        ("Fleet path", "Motor + Brake + Battery ECUs updated together"),
    ]
    y = 980
    for head, desc in proofs:
        c.setFillColor(STEEL)
        c.roundRect(60, y - 100, page_w - 120, 110, 16, fill=1, stroke=0)
        c.setFillColor(ACCENT)
        c.circle(100, y - 45, 10, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(bold, 26)
        c.drawString(130, y - 35, head)
        c.setFillColor(MUTED)
        c.setFont(body, 20)
        c.drawString(130, y - 70, desc)
        y -= 140
    footer(7)
    c.showPage()

    # --- Slide 8: Team ---
    bg()
    c.setFillColor(TEAL_LIGHT)
    c.setFont(bold, 20)
    c.drawString(60, page_h - 90, "THE TEAM")
    title("Built by two engineers", page_h - 160)
    # Sakshi card
    c.setFillColor(STEEL)
    c.roundRect(60, 700, page_w - 120, 260, 20, fill=1, stroke=0)
    c.setFillColor(TEAL_LIGHT)
    c.setFont(bold, 30)
    c.drawString(100, 900, "Sakshi Anwekar")
    c.setFillColor(MUTED)
    c.setFont(body, 22)
    for i, line in enumerate(
        [
            "OTA Cloud (FastAPI), OTA Client,",
            "Installer, packaging, security tests",
        ]
    ):
        c.drawString(100, 840 - i * 34, line)

    c.setFillColor(STEEL)
    c.roundRect(60, 380, page_w - 120, 260, 20, fill=1, stroke=0)
    c.setFillColor(TEAL_LIGHT)
    c.setFont(bold, 30)
    c.drawString(100, 580, "Tejas")
    c.setFillColor(MUTED)
    c.setFont(body, 22)
    for i, line in enumerate(
        [
            "Bootloader (C), Health Monitor,",
            "Virtual ECUs, firmware / fleet path",
        ]
    ):
        c.drawString(100, 520 - i * 34, line)
    footer(8)
    c.showPage()

    # --- Slide 9: CTA ---
    bg()
    c.setFillColor(TEAL_LIGHT)
    c.setFont(bold, 20)
    c.drawString(60, page_h - 90, "NEXT STEP")
    title("Want the repo and demo?", page_h - 160)
    c.setFillColor(STEEL)
    c.roundRect(60, 780, page_w - 120, 200, 20, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(bold, 28)
    c.drawString(100, 900, "GitHub")
    c.setFillColor(TEAL_LIGHT)
    c.setFont(body, 24)
    c.drawString(100, 840, "github.com/sakshianwekar/sdv-ota-platform")

    c.setFillColor(STEEL)
    c.roundRect(60, 520, page_w - 120, 220, 20, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(bold, 26)
    c.drawString(100, 680, "Discussion question")
    c.setFillColor(MUTED)
    c.setFont(body, 22)
    y = 630
    for line in _wrap(
        c,
        "In OTA systems, what matters more — cryptographic verification or runtime health checks? We implemented both as separate layers.",
        body,
        22,
        page_w - 200,
    ):
        c.drawString(100, y, line)
        y -= 30

    c.setFillColor(TEAL)
    c.roundRect(60, 280, page_w - 120, 180, 20, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(bold, 26)
    c.drawString(100, 390, "Open to conversations")
    c.setFont(body, 22)
    c.drawString(100, 340, "Embedded  ·  Backend  ·  Automotive software")
    c.setFont(body, 20)
    c.drawString(100, 300, "Links in the first comment on the LinkedIn post")
    footer(9)
    c.showPage()

    c.save()
    return path


def main():
    diagram = create_architecture_diagram()
    pdf = create_carousel_pdf(diagram)
    print(f"Diagram: {diagram}")
    print(f"PDF:     {pdf}")
    print(f"Sizes:   diagram={diagram.stat().st_size} bytes, pdf={pdf.stat().st_size} bytes")


if __name__ == "__main__":
    main()
