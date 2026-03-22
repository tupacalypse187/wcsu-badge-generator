"""
generate_blank_badges.py — WCSU Meet & Greet 2026

Produces blank name badge sheets for walk-in attendees to write their names
by hand at the event.

One page per school color — 6 pages total per format:
  • Ancell School of Business (orange)
  • School of Arts & Sciences (navy)
  • School of Visual & Performing Arts (purple)
  • School of Professional Studies (green)
  • Faculty / Staff (dark gold)
  • Community Guest (gray)

Each badge shows:
  • Colored header band (adhesive) or colored circle (paper) — school color
  • WCSU Alumni Association logo
  • No name or text — write-in at the event

Usage:
    # Adhesive blanks — Avery 5395, 8-up (default)
    python3 generate_blank_badges.py

    # Paper blanks — WCSU template, 6-up
    python3 generate_blank_badges.py --type paper

    # Custom output path
    python3 generate_blank_badges.py --output output/Walkin_Blanks_Adhesive.pdf
"""

import os
import argparse

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader

# ── Re-use layout constants from the main generator ──────────────────────────
# (duplicated here so this script is self-contained and runnable standalone)

PAGE_W, PAGE_H = 612, 792

# ── Paper badge layout (6-up) ─────────────────────────────────────────────────
CIRCLE_R = 24
BADGE_SLOTS = [
    {"cx": 162, "cy": 792 - 171, "text_top_rl": 792 - 207},
    {"cx": 450, "cy": 792 - 171, "text_top_rl": 792 - 207},
    {"cx": 162, "cy": 792 - 397, "text_top_rl": 792 - 434},
    {"cx": 450, "cy": 792 - 397, "text_top_rl": 792 - 434},
    {"cx": 162, "cy": 792 - 607, "text_top_rl": 792 - 648},
    {"cx": 450, "cy": 792 - 607, "text_top_rl": 792 - 648},
]

# ── Adhesive badge layout (Avery 5395, 8-up) ──────────────────────────────────
AVERY_BADGE_W  = 243.0
AVERY_BADGE_H  = 167.976
AVERY_HEADER_H = 52
AVERY_TEXT_W   = 218
AVERY_LOGO_W   = 185.0
AVERY_LOGO_H   = round(AVERY_LOGO_W * 75 / 258, 1)  # ≈ 53.8 pt

AVERY_SLOTS = [
    {"cx": 171, "cell_top": 751.5},
    {"cx": 441, "cell_top": 751.5},
    {"cx": 171, "cell_top": 570.05},
    {"cx": 441, "cell_top": 570.05},
    {"cx": 171, "cell_top": 388.55},
    {"cx": 441, "cell_top": 388.55},
    {"cx": 171, "cell_top": 207.1},
    {"cx": 441, "cell_top": 207.1},
]

# ── School color + label map ───────────────────────────────────────────────────
# Order matches the physical flow of the event (business → arts → visual → professional → faculty → community)
SCHOOLS = [
    ("ancell",       HexColor("#E8702A"), "Ancell School of Business"),
    ("arts",         HexColor("#1B3A6B"), "School of Arts & Sciences"),
    ("visual",       HexColor("#8E44AD"), "School of Visual & Performing Arts"),
    ("professional", HexColor("#27AE60"), "School of Professional Studies"),
    ("faculty",      HexColor("#D4AC0D"), "Faculty / Staff"),
    ("community",    HexColor("#7F8C8D"), "Community Guest"),
]

# ── Template renderer (mirrors ensure_template_png in generate_badges.py) ─────
def ensure_template_png(template_png, source_pdf, page_index=0, scale=3.0):
    if os.path.exists(template_png) and os.path.getsize(template_png) > 0:
        return
    if not os.path.exists(source_pdf):
        raise FileNotFoundError(
            f"Template PNG not found and source PDF is missing: {source_pdf}\n"
            "Ensure the source PDF is committed in the repo."
        )
    print(f"Rendering template from {os.path.basename(source_pdf)} (page {page_index + 1})...")
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(source_pdf)
    bitmap = pdf[page_index].render(scale=scale)
    bitmap.to_pil().save(template_png)
    print(f"✓ Saved {os.path.basename(template_png)}")


# ── Blank adhesive badge sheet ─────────────────────────────────────────────────
def generate_blank_adhesive(template_png, output_pdf, logo_png=None):
    """One page per school color — 8 blank adhesive label slots per page.

    Each badge shows the colored header band with 'Meet & Greet 2026' and the
    WCSU Alumni Association logo — name field is blank for hand-writing.
    """
    template_img = ImageReader(template_png)
    logo_img = ImageReader(logo_png) if logo_png and os.path.exists(logo_png) else None

    c = canvas.Canvas(output_pdf, pagesize=letter)
    c.setTitle("WCSU Meet & Greet 2026 — Blank Walk-In Badges (Adhesive)")
    c.setAuthor("WCSU Alumni Association")
    c.setSubject("Blank adhesive name badges — walk-in attendees")
    c.setCreator("WCSU Badge Generator")

    for _school_key, color, label in SCHOOLS:
        # Draw Avery template background
        c.drawImage(template_img, 0, 0, width=PAGE_W, height=PAGE_H,
                    preserveAspectRatio=True)

        for slot in AVERY_SLOTS:
            cx       = slot["cx"]
            cell_top = slot["cell_top"]
            x0       = cx - AVERY_BADGE_W / 2

            # ── Colored header band ───────────────────────────────────────────
            c.setFillColor(color)
            c.rect(x0, cell_top - AVERY_HEADER_H,
                   AVERY_BADGE_W, AVERY_HEADER_H, fill=1, stroke=0)

            # ── "Meet & Greet 2026" — top of header, white ────────────────────
            c.setFillColor(white)
            c.setFont("Helvetica", 9)
            c.drawCentredString(cx, cell_top - 13, "Meet & Greet 2026")

            # ── Name line blank — subtle placeholder ──────────────────────────
            # Draw a short underline in the header area to indicate write-here
            c.setStrokeColor(HexColor("#FFFFFF60"))  # semi-transparent white
            c.setLineWidth(0.5)
            underline_w = AVERY_TEXT_W * 0.75
            c.line(cx - underline_w / 2, cell_top - 36,
                   cx + underline_w / 2, cell_top - 36)

            # ── Logo — top of white area ──────────────────────────────────────
            logo_top_y = cell_top - AVERY_HEADER_H - 10
            logo_btm_y = logo_top_y - AVERY_LOGO_H
            logo_x     = cx - AVERY_LOGO_W / 2

            if logo_img:
                c.drawImage(logo_img, logo_x, logo_btm_y,
                            width=AVERY_LOGO_W, height=AVERY_LOGO_H,
                            mask="auto", preserveAspectRatio=True)

            # ── School label — below logo, navy ───────────────────────────────
            type_y = logo_btm_y - 14
            c.setFillColor(HexColor("#1B3A6B"))
            c.setFont("Helvetica", 10)
            c.drawCentredString(cx, type_y, label)

        c.showPage()

    c.save()
    print(f"✓ Generated {len(SCHOOLS)} pages of blank adhesive badges → {output_pdf}")


# ── Blank paper badge sheet ────────────────────────────────────────────────────
def generate_blank_paper(template_png, output_pdf, logo_png=None):
    """One page per school color — 6 blank paper badge slots per page.

    Each badge shows the colored circle and a write-in underline for the name.
    The template background already includes the WCSU Alumni Association logo,
    so no additional logo is drawn here.
    """
    template_img = ImageReader(template_png)

    c = canvas.Canvas(output_pdf, pagesize=letter)
    c.setTitle("WCSU Meet & Greet 2026 — Blank Walk-In Badges (Paper)")
    c.setAuthor("WCSU Alumni Association")
    c.setSubject("Blank paper name badges — walk-in attendees")
    c.setCreator("WCSU Badge Generator")

    for _school_key, color, label in SCHOOLS:
        # Draw paper template background (already contains logo)
        c.drawImage(template_img, 0, 0, width=PAGE_W, height=PAGE_H,
                    preserveAspectRatio=True)

        for slot in BADGE_SLOTS:
            cx = slot["cx"]
            cy = slot["cy"]
            ty = slot["text_top_rl"]

            # ── Colored circle ────────────────────────────────────────────────
            c.setFillColor(color)
            c.setStrokeColor(HexColor("#1a1a1a"))
            c.setLineWidth(1.5)
            c.circle(cx, cy, CIRCLE_R, stroke=1, fill=1)

            # ── Name write-in underline ────────────────────────────────────────
            name_y = ty
            line_w = 200
            c.setStrokeColor(HexColor("#333333"))
            c.setLineWidth(0.75)
            c.line(cx - line_w / 2, name_y - 2,
                   cx + line_w / 2, name_y - 2)

            # ── School label ──────────────────────────────────────────────────
            c.setFillColor(HexColor("#1B3A6B"))
            c.setFont("Helvetica", 10)
            c.drawCentredString(cx, name_y - 20, label)

        c.showPage()

    c.save()
    print(f"✓ Generated {len(SCHOOLS)} pages of blank paper badges → {output_pdf}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _here = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(
        description="Generate blank WCSU name badge sheets for walk-in attendees.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Output: one page per school color (6 pages total).
Each badge has the colored header/circle + WCSU logo — no name text.
Attendees write their name by hand at the event.

School pages (in order):
  1. Ancell School of Business     (orange)
  2. School of Arts & Sciences     (navy)
  3. School of Visual & Performing Arts  (purple)
  4. School of Professional Studies     (green)
  5. Faculty / Staff               (dark gold)
  6. Community Guest               (gray)
        """
    )
    parser.add_argument(
        "--type", choices=["adhesive", "paper"], default="adhesive",
        help=(
            "Badge format (default: adhesive). "
            "'adhesive' → Avery 5395 labels, 8-up. "
            "'paper'    → WCSU paper template, 6-up."
        )
    )
    parser.add_argument(
        "--output", metavar="PATH",
        help=(
            "Full output path. Defaults to "
            "output/2026_MeetGreet_Blank_Adhesive.pdf or "
            "output/2026_MeetGreet_Blank_Paper.pdf"
        )
    )
    args = parser.parse_args()

    _output_dir = os.path.join(_here, "output")
    os.makedirs(_output_dir, exist_ok=True)

    badge_type = args.type
    if args.output:
        output_pdf = args.output
    else:
        fname = (
            "2026_MeetGreet_Blank_Adhesive.pdf" if badge_type == "adhesive"
            else "2026_MeetGreet_Blank_Paper.pdf"
        )
        output_pdf = os.path.join(_output_dir, fname)

    logo_png = os.path.join(_here, "template", "wcsu_aa_logo.png")

    if badge_type == "adhesive":
        avery_source = os.path.join(_here, "docs", "Avery5395AdhesiveNameBadges.pdf")
        avery_png    = os.path.join(_here, "template", "avery_blank.png")
        ensure_template_png(avery_png, avery_source)
        generate_blank_adhesive(avery_png, output_pdf, logo_png=logo_png)
    else:
        paper_source = os.path.join(_here, "template", "badge_template.pdf")
        paper_png    = os.path.join(_here, "template", "template_blank.png")
        ensure_template_png(paper_png, paper_source)
        generate_blank_paper(paper_png, output_pdf)
