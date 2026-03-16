"""
WCSU Alumni Meet & Greet 2026 — Name Badge Generator
Reads registrants.csv and produces a print-ready PDF with 6 badges per page.
Colors correspond to the 4 WCSU schools.
"""

import csv, re, os, textwrap
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.utils import ImageReader

# ── Layout constants (PDF points, origin bottom-left as reportlab uses) ─────
PAGE_W, PAGE_H = 612, 792
CELL_W = PAGE_W / 2          # 306
CELL_H = PAGE_H / 3          # 264

# Circle center (x from page left, y from page BOTTOM — reportlab convention)
# Measured empirically from existing badge layout
CIRCLE_R = 24   # pt radius

# Per-cell: (x_center, y_circle_center_from_bottom, y_name_baseline)
#   Columns: left=153, right=459
#   Rows (bottom-up): row0=bottom, row1=mid, row2=top
#   pdfplumber top → rl bottom: rl_y = PAGE_H - pdfplumber_y
BADGE_SLOTS = [
    # row 2 (top), col 0 (left)
    {"cx": 153, "cy": 792 - 171, "text_top_rl": 792 - 207},
    # row 2 (top), col 1 (right)
    {"cx": 459, "cy": 792 - 171, "text_top_rl": 792 - 207},
    # row 1 (mid), col 0
    {"cx": 153, "cy": 792 - 397, "text_top_rl": 792 - 434},
    # row 1 (mid), col 1
    {"cx": 459, "cy": 792 - 397, "text_top_rl": 792 - 434},
    # row 0 (bottom), col 0
    {"cx": 153, "cy": 792 - 607, "text_top_rl": 792 - 648},
    # row 0 (bottom), col 1
    {"cx": 459, "cy": 792 - 607, "text_top_rl": 792 - 648},
]

LINE_LEADING = 20   # pt between text baselines
TEXT_AREA_WIDTH = 250  # max text width within badge cell (~28pt padding each side)

# ── WCSU School colors ────────────────────────────────────────────────────────
SCHOOL_COLORS = {
    "ancell":       HexColor("#E8702A"),   # WCSU Orange  — Ancell School of Business
    "arts":         HexColor("#1B3A6B"),   # WCSU Navy    — School of Arts & Sciences
    "visual":       HexColor("#8E44AD"),   # Purple       — School of Visual & Performing Arts
    "professional": HexColor("#27AE60"),   # Forest Green — School of Professional Studies
    "faculty":      HexColor("#D4AC0D"),   # Dark Gold    — Faculty/Staff (no specific school)
    "community":    HexColor("#7F8C8D"),   # Gray         — Community guests
    "default":      HexColor("#95A5A6"),   # Light gray   — unknown
}

SCHOOL_LABELS = {
    "ancell":       "Ancell School of Business",
    "arts":         "School of Arts & Sciences",
    "visual":       "School of Visual & Performing Arts",
    "professional": "School of Professional Studies",
    "faculty":      "Faculty / Staff",
    "community":    "Community Guest",
    "default":      "",
}

# ── School detection ──────────────────────────────────────────────────────────
ANCELL_KEYWORDS = [
    "accounting", "finance", "financial", "business", "management",
    "marketing", "economics", "mba", "bba", "mis ", "management information",
    "real estate", "banking", "commercial", "entrepreneur",
]
ARTS_KEYWORDS = [
    "biology", "chemistry", "physics", "mathematics", "math",
    "computer science", "cybersecurity", "psychology", "sociology",
    "anthropology", "history", "political science", "political",
    "english", "communications", "communication", "nursing", "bsn", "rn",
    "public health", "social work", "justice", "jla", "criminology",
    "science", "applied", "liberal arts", "interdisciplinary",
]
VISUAL_KEYWORDS = [
    "graphic design", "graphic", "digital interactive", "theater", "theatre",
    "performing arts", "music", "dance", "film", "photography",
    "visual art", "dima", "art ", "arts ",
]
PROFESSIONAL_KEYWORDS = [
    "education", "health administration", "mha", "counseling",
    "mat ", "teaching", "doctoral", "literacy",
]

def detect_school(major, org, reg_type):
    """Return school key based on major/org text."""
    txt = f"{major} {org}".lower()

    # Faculty: check org for school name
    if "ancell" in txt:
        return "ancell"
    if "professional studies" in txt or "dean" in txt:
        return "professional"
    if "visual" in txt or "performing" in txt:
        return "visual"

    if reg_type == "Faculty/Staff":
        return "faculty"
    if reg_type == "Community":
        return "community"

    # Alumni / Student: keyword match (order matters — most specific first)
    for kw in VISUAL_KEYWORDS:
        if kw in txt:
            return "visual"
    for kw in PROFESSIONAL_KEYWORDS:
        if kw in txt:
            return "professional"
    for kw in ANCELL_KEYWORDS:
        if kw in txt:
            return "ancell"
    for kw in ARTS_KEYWORDS:
        if kw in txt:
            return "arts"

    return "default"

# ── Class year extraction ─────────────────────────────────────────────────────
def extract_year(text):
    """Pull a 2- or 4-digit graduation year from the class/major string."""
    m = re.search(r"'(\d{2})\b", text)
    if m:
        y = int(m.group(1))
        return f"20{y:02d}" if y <= 26 else f"19{y:02d}"
    m = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if m:
        return m.group(1)
    return None

# ── Text helpers ──────────────────────────────────────────────────────────────
def fit_text(c_obj, text, x, y, max_w, font_name, max_size=14, min_size=7):
    """Draw centered text, scaling font size down until it fits."""
    size = max_size
    while size >= min_size:
        c_obj.setFont(font_name, size)
        if c_obj.stringWidth(text, font_name, size) <= max_w:
            break
        size -= 0.5
    c_obj.drawCentredString(x, y, text)
    return size

def wrap_and_draw(c_obj, text, x, y, max_w, font_name, font_size, leading):
    """Wrap text if needed, return next y (below drawn text)."""
    c_obj.setFont(font_name, font_size)
    words = text.split()
    line = ""
    lines = []
    for w in words:
        test = f"{line} {w}".strip()
        if c_obj.stringWidth(test, font_name, font_size) <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    for ln in lines:
        c_obj.drawCentredString(x, y, ln)
        y -= leading
    return y

# ── CSV parsing ───────────────────────────────────────────────────────────────
def load_registrants(csv_paths):
    """Load and deduplicate registrants from one or more CSV files.

    csv_paths can be a single path string or a list of path strings.
    Deduplication is global across all files — the same person won't
    appear twice even if they're in multiple CSVs.
    """
    if isinstance(csv_paths, str):
        csv_paths = [csv_paths]

    rows = []
    seen = set()
    for csv_path in csv_paths:
        count_before = len(rows)
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row["Email"].strip().lower()
                fname = row["Attendee (First Name)"].strip()
                lname = row["Attendee (Last Name)"].strip()
                key = email if email else f"{fname.lower()}_{lname.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)
        added = len(rows) - count_before
        if len(csv_paths) > 1:
            print(f"  {os.path.basename(csv_path)}: {added} registrants")
    return rows

def build_badge_data(row):
    reg   = row["Registration Options"].strip()
    fname = row["Attendee (First Name)"].strip().title()
    lname = row["Attendee (Last Name)"].strip().title()
    major = row["Class / Major"].strip()
    org   = row["Community Business/Organization"].strip()
    title = row["Occupation / Position Title"].strip()

    # ── Name line ──────────────────────────────────────────────────────────
    year = extract_year(major)
    if reg == "Alumni" and year:
        suffix = f" '{year[2:]}"
        name_line = f"{fname} {lname}{suffix}"
    else:
        name_line = f"{fname} {lname}"

    # ── School detection & type line ───────────────────────────────────────
    school = detect_school(major, org, reg)
    school_label = SCHOOL_LABELS.get(school, "")
    color = SCHOOL_COLORS.get(school, SCHOOL_COLORS["default"])

    if reg in ("Alumni", "Student"):
        type_str = f"{reg}  ·  {school_label}" if school_label else reg
    elif reg == "Faculty/Staff":
        dept = org if org and "wcsu" not in org.lower() else ""
        type_str = dept if dept else "Faculty / Staff"
    else:  # Community
        type_str = org if org else "Community Guest"

    # ── Occupation / title ─────────────────────────────────────────────────
    # Collapse newlines, take first meaningful segment, truncate
    title_clean = " ".join(title.replace("\n", " ").split())
    # If multiple roles separated by / or ;, take the first
    for sep in ["\n", "  ", "1)", "2)"]:
        title_clean = title_clean.split(sep)[0].strip()
    occ_line = title_clean[:85] if title_clean else ""

    return {
        "name": name_line,
        "type": type_str,
        "occ":  occ_line,
        "color": color,
        "school": school,
    }

# ── PDF generator ─────────────────────────────────────────────────────────────
def generate_badges_pdf(registrants, template_png, output_pdf):
    template_img = ImageReader(template_png)
    c = canvas.Canvas(output_pdf, pagesize=letter)

    badges = [build_badge_data(r) for r in registrants]

    # 6 badges per page
    page_count = (len(badges) + 5) // 6
    for page_idx in range(page_count):
        batch = badges[page_idx * 6: page_idx * 6 + 6]

        # Draw full-page template background
        c.drawImage(template_img, 0, 0, width=PAGE_W, height=PAGE_H,
                    preserveAspectRatio=True)

        for i, badge in enumerate(batch):
            slot = BADGE_SLOTS[i]
            cx   = slot["cx"]
            cy   = slot["cy"]
            ty   = slot["text_top_rl"]  # baseline for first text line

            # ── Colored circle ────────────────────────────────────────────
            c.setFillColor(badge["color"])
            c.setStrokeColor(HexColor("#1a1a1a"))
            c.setLineWidth(1.5)
            c.circle(cx, cy, CIRCLE_R, stroke=1, fill=1)

            # ── Name (largest, bold) ──────────────────────────────────────
            c.setFillColor(HexColor("#1B3A6B"))
            name_y = ty
            fit_text(c, badge["name"], cx, name_y,
                     TEXT_AREA_WIDTH, "Helvetica-Bold", max_size=14, min_size=8)

            # ── Type / School line ────────────────────────────────────────
            c.setFillColor(HexColor("#1B3A6B"))
            type_y = name_y - LINE_LEADING
            wrap_and_draw(c, badge["type"], cx, type_y,
                          TEXT_AREA_WIDTH, "Helvetica", 12, 14)

            # ── Occupation ────────────────────────────────────────────────
            c.setFillColor(HexColor("#333333"))
            occ_y = type_y - LINE_LEADING - 1
            wrap_and_draw(c, badge["occ"], cx, occ_y,
                          TEXT_AREA_WIDTH, "Helvetica", 11, 13)

        c.showPage()

    c.save()
    print(f"✓ Generated {page_count} pages for {len(badges)} badges → {output_pdf}")

# ── Template renderer ─────────────────────────────────────────────────────────
def ensure_template_png(template_png, source_pdf, page_index=0, scale=3.0):
    """Render template_blank.png from the source PDF if it doesn't exist."""
    if os.path.exists(template_png) and os.path.getsize(template_png) > 0:
        return
    if not os.path.exists(source_pdf):
        raise FileNotFoundError(
            f"Template PNG not found and source PDF is missing: {source_pdf}\n"
            "Place 'badge_template.pdf' in the template/ folder and re-run."
        )
    print(f"Rendering template from {os.path.basename(source_pdf)} (page {page_index + 1})...")
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(source_pdf)
    bitmap = pdf[page_index].render(scale=scale)
    bitmap.to_pil().save(template_png)
    print(f"✓ Saved {os.path.basename(template_png)}")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    _here = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(
        description="Generate WCSU name badge PDF from a registrants CSV."
    )
    parser.add_argument(
        "--csv", action="append", metavar="PATH",
        help="Path to a registrants CSV. Repeat to merge multiple files: "
             "--csv data/registrants.csv --csv data/acc306_badges.csv "
             "(default: data/registrants.csv)"
    )
    parser.add_argument(
        "--output", default=os.path.join(_here, "output", "2026_MeetGreet_NameTags.pdf"),
        help="Output PDF path (default: output/2026_MeetGreet_NameTags.pdf)"
    )
    args = parser.parse_args()

    csv_paths  = args.csv if args.csv else [os.path.join(_here, "data", "registrants.csv")]
    output_pdf = args.output
    source_pdf   = os.path.join(_here, "template", "badge_template.pdf")
    template_png = os.path.join(_here, "template", "template_blank.png")

    # Ensure output directory exists (gitignored, so not always present after a fresh clone)
    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)

    ensure_template_png(template_png, source_pdf)
    registrants = load_registrants(csv_paths)
    print(f"Loaded {len(registrants)} unique registrants")
    generate_badges_pdf(registrants, template_png, output_pdf)
