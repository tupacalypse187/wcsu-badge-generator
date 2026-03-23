"""
WCSU Meet & Greet 2026 — Name Badge Generator
Reads registrants.csv and produces a print-ready PDF.

Two badge formats supported (--type flag):
  adhesive  [DEFAULT] — Avery 5395 adhesive labels, 8-up (2×4), 3-3/8" × 2-1/3"
  paper               — WCSU paper badge template, 6-up (2×3), 4-1/4" × 3-2/3"

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
CIRCLE_R = 24   # pt radius

# Template has ~17.7pt left/right margins and ~73pt top/bottom margins.
# Actual badge content area: 576.3pt wide x 648pt tall → each badge 288.2pt x 216pt.
# True column centers: left=161.8pt, right=449.9pt (rounded to 162 / 450).
#
# Per-cell: (x_center, y_circle_center_from_bottom, y_name_baseline)
#   Columns: left=162, right=450
#   Rows (bottom-up): row0=bottom, row1=mid, row2=top
BADGE_SLOTS = [
    # row 2 (top), col 0 (left)
    {"cx": 162, "cy": 792 - 171, "text_top_rl": 792 - 207},
    # row 2 (top), col 1 (right)
    {"cx": 450, "cy": 792 - 171, "text_top_rl": 792 - 207},
    # row 1 (mid), col 0
    {"cx": 162, "cy": 792 - 397, "text_top_rl": 792 - 434},
    # row 1 (mid), col 1
    {"cx": 450, "cy": 792 - 397, "text_top_rl": 792 - 434},
    # row 0 (bottom), col 0
    {"cx": 162, "cy": 792 - 607, "text_top_rl": 792 - 648},
    # row 0 (bottom), col 1
    {"cx": 450, "cy": 792 - 607, "text_top_rl": 792 - 648},
]

LINE_LEADING = 20   # pt between text baselines
TEXT_AREA_WIDTH = 250  # max text width within badge cell (~28pt padding each side)

# ── Avery 5395 Adhesive Badge Layout ─────────────────────────────────────────
# Template: docs/Avery5395AdhesiveNameBadges.pdf
# 2 cols × 4 rows on US Letter; each badge 243 × 167.976 pt (3-3/8" × 2-1/3")
# Measurements extracted directly from PDF rect objects (pdfplumber).
#
# Column x-centers: left=171, right=441
# Row cell_top values (reportlab y, bottom-left origin): 751.5 / 570.05 / 388.55 / 207.1
#
# Design: full-width colored header band (school color, 40pt) at top of each
# badge with white WCSU + event text; name/school/occ centered in white area below.

AVERY_BADGE_W  = 243.0      # pt — badge cell width
AVERY_BADGE_H  = 167.976    # pt — badge cell height
AVERY_HEADER_H = 52         # pt — colored school band at top of each badge (holds name)
AVERY_TEXT_W   = 218        # pt — max text width (243 − 2×12.5 side margins)

# Logo: template/wcsu_aa_logo.png — 258×75 px RGBA, scaled to fit inside badge
# Drawn at 185pt wide → height = 185 * (75/258) ≈ 54pt
AVERY_LOGO_W = 185.0
AVERY_LOGO_H = round(AVERY_LOGO_W * 75 / 258, 1)   # ≈ 53.8 pt

# (cx, cell_top) pairs — cell_top is the reportlab y of the top edge of each badge.
# Ordered top-to-bottom, left-to-right (same order as the physical sheet).
AVERY_SLOTS = [
    {"cx": 171, "cell_top": 751.5},   # row 0, col 0
    {"cx": 441, "cell_top": 751.5},   # row 0, col 1
    {"cx": 171, "cell_top": 570.05},  # row 1, col 0
    {"cx": 441, "cell_top": 570.05},  # row 1, col 1
    {"cx": 171, "cell_top": 388.55},  # row 2, col 0
    {"cx": 441, "cell_top": 388.55},  # row 2, col 1
    {"cx": 171, "cell_top": 207.1},   # row 3, col 0
    {"cx": 441, "cell_top": 207.1},   # row 3, col 1
]

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

# Ordered list used by the blank badge generator (one page per school).
# Intentionally excludes 'default' — walk-in blanks only cover the 6 real categories.
SCHOOLS_ORDERED = [
    ("ancell",       HexColor("#E8702A"), "Ancell School of Business"),
    ("arts",         HexColor("#1B3A6B"), "School of Arts & Sciences"),
    ("visual",       HexColor("#8E44AD"), "School of Visual & Performing Arts"),
    ("professional", HexColor("#27AE60"), "School of Professional Studies"),
    ("faculty",      HexColor("#D4AC0D"), "Faculty / Staff"),
    ("community",    HexColor("#7F8C8D"), "Community Guest"),
]

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
def extract_years(text):
    """Return all graduation years found in text as sorted 2-digit strings.

    Handles both apostrophe-style ('71, '98) and 4-digit (1971, 1998) formats.
    Returns e.g. ['71', '98'] for a double-degree alumna like Lois '71 & '98.
    """
    found = set()
    for m in re.finditer(r"'(\d{2})\b", text):
        y = int(m.group(1))
        found.add(f"20{y:02d}" if y <= 26 else f"19{y:02d}")
    for m in re.finditer(r"\b(19\d{2}|20\d{2})\b", text):
        found.add(m.group(1))
    return [yr[2:] for yr in sorted(found)]

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

# ── CSV format detection & normalization ──────────────────────────────────────
# Two supported CSV formats are auto-detected by their column headers.
#
# Format A — Event registrant export (e.g. Eventbrite / Google Sheets):
#   Required columns:
#     • Attendee (First Name)
#     • Attendee (Last Name)
#     • Registration Options   (Alumni / Faculty/Staff / Student / Community)
#     • Class / Major
#   Optional columns (leave blank if unknown):
#     • Email                         — used for deduplication
#     • Community Business/Organization
#     • Occupation / Position Title
#
# Format B — Class roster / simple list:
#   Required columns:
#     • First Name
#     • Last Name
#     • Registration Options   (Alumni / Faculty/Staff / Student / Community)
#     • Class / Major
#   (No email, org, or occupation columns needed)

# Patterns treated as "no value" — collapsed to empty string during normalization
_NA_VALUES = {"n/a", "na", "n.a.", "n.a", "none", "null", "-", "--", "---",
              "not available", "not applicable", "unknown", "tbd", "tba"}

def _clean(value, fallback=""):
    """Strip whitespace and collapse N/A-like sentinel values to empty string.

    Args:
        value:    Raw cell value from the CSV row.
        fallback: Returned instead of "" when the cleaned value is empty
                  (use "Guest" for name fields that should never be blank).
    """
    v = (value or "").strip()
    if v.lower() in _NA_VALUES:
        v = ""
    return v if v else fallback

def _detect_format(fieldnames):
    """Return 'event' or 'classlist' based on CSV column headers."""
    cols = {c.strip() for c in fieldnames}
    if "Attendee (First Name)" in cols:
        return "event"
    if "First Name" in cols and "Last Name" in cols:
        return "classlist"
    raise ValueError(
        f"Unrecognized CSV format. Found columns: {sorted(cols)}\n"
        "Expected either 'Attendee (First Name)' (event export) or "
        "'First Name' + 'Last Name' (class roster)."
    )

def _normalize_row(row, fmt):
    """Convert any supported row format to the canonical internal dict.

    All values are passed through _clean() so N/A-like sentinels
    (e.g. 'N/A', 'NA', 'None', '-') become empty strings.
    Name fields use fallback='Guest' so a badge is never entirely blank.
    """
    if fmt == "event":
        return {
            "Attendee (First Name)":           _clean(row.get("Attendee (First Name)"), fallback="Guest"),
            "Attendee (Last Name)":            _clean(row.get("Attendee (Last Name)")),
            "Registration Options":            _clean(row.get("Registration Options")),
            "Class / Major":                   _clean(row.get("Class / Major")),
            "Community Business/Organization": _clean(row.get("Community Business/Organization")),
            "Occupation / Position Title":     _clean(row.get("Occupation / Position Title")),
            "Email":                           _clean(row.get("Email", "")).lower(),
        }
    else:  # classlist
        return {
            "Attendee (First Name)":           _clean(row.get("First Name"), fallback="Guest"),
            "Attendee (Last Name)":            _clean(row.get("Last Name")),
            "Registration Options":            _clean(row.get("Registration Options")),
            "Class / Major":                   _clean(row.get("Class / Major")),
            "Community Business/Organization": "",
            "Occupation / Position Title":     "",
            "Email":                           "",
        }

# ── CSV parsing ───────────────────────────────────────────────────────────────
def load_registrants(csv_paths):
    """Load and deduplicate registrants from one or more CSV files.

    csv_paths can be a single path string or a list of path strings.
    Both CSV formats are accepted and can be mixed across files:
      - Event export (columns: Attendee (First Name), Attendee (Last Name), …)
      - Class roster (columns: First Name, Last Name, …)
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
            fmt = _detect_format(reader.fieldnames or [])
            print(f"  {os.path.basename(csv_path)}: detected format '{fmt}'")
            for raw in reader:
                row = _normalize_row(raw, fmt)
                email = row["Email"]
                fname = row["Attendee (First Name)"]
                lname = row["Attendee (Last Name)"]
                key = email if email else f"{fname.lower()}_{lname.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)
        added = len(rows) - count_before
        print(f"  {os.path.basename(csv_path)}: {added} registrants added")
    return rows

def build_badge_data(row):
    reg   = row["Registration Options"].strip()
    fname = row["Attendee (First Name)"].strip().title()
    lname = row["Attendee (Last Name)"].strip().title()
    major = row["Class / Major"].strip()
    org   = row["Community Business/Organization"].strip()
    title = row["Occupation / Position Title"].strip()

    # ── Name line ──────────────────────────────────────────────────────────
    years = extract_years(major)
    if reg == "Alumni" and years:
        # Format: '71  /  '71 & '98  /  '71, '98 & '04
        if len(years) == 1:
            year_str = f"'{years[0]}"
        else:
            year_str = ", ".join(f"'{y}" for y in years[:-1]) + f" & '{years[-1]}"
        name_line = f"{fname} {lname} {year_str}"
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

    # ── PDF metadata ──────────────────────────────────────────────────────────
    c.setTitle("Meet and Greet Name Tags")
    c.setAuthor("WCSU Alumni Association")
    c.setSubject("WCSU Alumni Association Meet & Greet — March 25, 2026")
    c.setCreator("WCSU Badge Generator")

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


# ── Avery 5395 adhesive badge generator ──────────────────────────────────────
def generate_adhesive_badges_pdf(registrants, template_png, output_pdf, logo_png=None):
    """Generate Avery 5395 adhesive name badge PDF — 8 badges per page.

    Layout (top → bottom within each 243×168pt cell):
      ┌──────────────────────────────────────┐
      │  [School-color header band, 52pt]    │
      │  Meet & Greet 2026  (9pt)    │
      │  First Last  (bold, white, ~15pt)   │
      ├──────────────────────────────────────┤
      │  [WCSU Alumni Association logo]      │
      │  Student · Ancell School of Business │  ← 11pt
      │  Occupation Title                    │  ← 10pt
      └──────────────────────────────────────┘
    """
    template_img = ImageReader(template_png)
    logo_img     = ImageReader(logo_png) if logo_png and os.path.exists(logo_png) else None

    c = canvas.Canvas(output_pdf, pagesize=letter)

    # ── PDF metadata ──────────────────────────────────────────────────────────
    c.setTitle("Meet and Greet Name Tags")
    c.setAuthor("WCSU Alumni Association")
    c.setSubject("WCSU Alumni Association Meet & Greet — March 25, 2026")
    c.setCreator("WCSU Badge Generator")

    badges = [build_badge_data(r) for r in registrants]

    # 8 badges per page (2 cols × 4 rows)
    page_count = (len(badges) + 7) // 8
    for page_idx in range(page_count):
        batch = badges[page_idx * 8: page_idx * 8 + 8]

        # Draw Avery template background (cut-guide outlines)
        c.drawImage(template_img, 0, 0, width=PAGE_W, height=PAGE_H,
                    preserveAspectRatio=True)

        for i, badge in enumerate(batch):
            slot     = AVERY_SLOTS[i]
            cx       = slot["cx"]
            cell_top = slot["cell_top"]
            x0       = cx - AVERY_BADGE_W / 2   # left edge of badge cell

            # ── Colored header band ───────────────────────────────────────────
            c.setFillColor(badge["color"])
            c.rect(x0, cell_top - AVERY_HEADER_H,
                   AVERY_BADGE_W, AVERY_HEADER_H, fill=1, stroke=0)

            # ── "Meet & Greet 2026" — top of header, white ────────────
            c.setFillColor(white)
            c.setFont("Helvetica", 9)
            c.drawCentredString(cx, cell_top - 13, "Meet & Greet 2026")

            # ── Attendee name — lower part of header, white bold ─────────────
            c.setFillColor(white)
            fit_text(c, badge["name"], cx, cell_top - 33,
                     AVERY_TEXT_W, "Helvetica-Bold", max_size=15, min_size=7)

            # ── Logo (WCSU Alumni Association) — top of white area ────────────
            # Vertically, logo sits just below the header; school/occ text below it.
            # White area height: AVERY_BADGE_H − AVERY_HEADER_H ≈ 116pt
            # Logo: AVERY_LOGO_W × AVERY_LOGO_H ≈ 185×54pt, centered on cx.
            # Positions from cell_top:
            #   logo top    = −62  (10pt gap from header bottom)
            #   logo bottom = −62 − AVERY_LOGO_H
            #   type  base  = logo_bottom − 7
            #   occ   base  = type_base  − 16
            logo_top_y = cell_top - AVERY_HEADER_H - 10          # top of logo (reportlab y)
            logo_btm_y = logo_top_y - AVERY_LOGO_H               # bottom of logo (reportlab y)
            logo_x     = cx - AVERY_LOGO_W / 2

            if logo_img:
                c.drawImage(logo_img, logo_x, logo_btm_y,
                            width=AVERY_LOGO_W, height=AVERY_LOGO_H,
                            mask="auto", preserveAspectRatio=True)

            # ── School / type line ────────────────────────────────────────────
            # 14pt gap below logo (was 8) — pushes text block down into white area.
            type_y = logo_btm_y - 14
            c.setFillColor(HexColor("#1B3A6B"))
            next_y = wrap_and_draw(c, badge["type"], cx, type_y,
                                   AVERY_TEXT_W, "Helvetica", 11, 13)

            # ── Occupation ────────────────────────────────────────────────────
            # 19pt leading from type baseline (was 16); use next_y from wrap so
            # a wrapped type line never collides with occupation text.
            occ_y = next_y - 6
            c.setFillColor(HexColor("#444444"))
            wrap_and_draw(c, badge["occ"], cx, occ_y,
                          AVERY_TEXT_W, "Helvetica", 10, 12)

        c.showPage()

    c.save()
    print(f"✓ Generated {page_count} pages for {len(badges)} adhesive badges → {output_pdf}")


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

# ── Blank badge generators (walk-in sheets, one page per school) ──────────────
def generate_blank_adhesive_pdf(template_png, output_pdf, logo_png=None):
    """Avery 5395 blank sheets — 8 badges per page, one page per school color.

    Each badge shows the colored header band with 'Meet & Greet 2026' and
    the WCSU AA logo. The name area is blank for hand-writing at the event.
    """
    template_img = ImageReader(template_png)
    logo_img = ImageReader(logo_png) if logo_png and os.path.exists(logo_png) else None

    c = canvas.Canvas(output_pdf, pagesize=letter)
    c.setTitle("WCSU Meet & Greet 2026 — Blank Walk-In Badges (Adhesive)")
    c.setAuthor("WCSU Alumni Association")
    c.setSubject("Blank adhesive name badges — walk-in attendees")
    c.setCreator("WCSU Badge Generator")

    for _key, color, label in SCHOOLS_ORDERED:
        c.drawImage(template_img, 0, 0, width=PAGE_W, height=PAGE_H,
                    preserveAspectRatio=True)

        for slot in AVERY_SLOTS:
            cx       = slot["cx"]
            cell_top = slot["cell_top"]
            x0       = cx - AVERY_BADGE_W / 2

            # Colored header band
            c.setFillColor(color)
            c.rect(x0, cell_top - AVERY_HEADER_H,
                   AVERY_BADGE_W, AVERY_HEADER_H, fill=1, stroke=0)

            # "Meet & Greet 2026" — white, top of header
            c.setFillColor(white)
            c.setFont("Helvetica", 9)
            c.drawCentredString(cx, cell_top - 13, "Meet & Greet 2026")

            # Logo in white area
            logo_top_y = cell_top - AVERY_HEADER_H - 10
            logo_btm_y = logo_top_y - AVERY_LOGO_H
            if logo_img:
                c.drawImage(logo_img, cx - AVERY_LOGO_W / 2, logo_btm_y,
                            width=AVERY_LOGO_W, height=AVERY_LOGO_H,
                            mask="auto", preserveAspectRatio=True)

            # School label — below logo, navy
            c.setFillColor(HexColor("#1B3A6B"))
            c.setFont("Helvetica", 10)
            c.drawCentredString(cx, logo_btm_y - 14, label)

        c.showPage()

    c.save()
    print(f"✓ Generated {len(SCHOOLS_ORDERED)} pages of blank adhesive badges → {output_pdf}")


def generate_blank_paper_pdf(template_png, output_pdf):
    """WCSU paper template blank sheets — 6 badges per page, one page per school color.

    Each badge shows the colored circle and a write-in underline.
    The template background already includes the WCSU AA logo.
    """
    template_img = ImageReader(template_png)

    c = canvas.Canvas(output_pdf, pagesize=letter)
    c.setTitle("WCSU Meet & Greet 2026 — Blank Walk-In Badges (Paper)")
    c.setAuthor("WCSU Alumni Association")
    c.setSubject("Blank paper name badges — walk-in attendees")
    c.setCreator("WCSU Badge Generator")

    for _key, color, label in SCHOOLS_ORDERED:
        # Template background already includes logo
        c.drawImage(template_img, 0, 0, width=PAGE_W, height=PAGE_H,
                    preserveAspectRatio=True)

        for slot in BADGE_SLOTS:
            cx = slot["cx"]
            cy = slot["cy"]
            ty = slot["text_top_rl"]

            # Colored circle
            c.setFillColor(color)
            c.setStrokeColor(HexColor("#1a1a1a"))
            c.setLineWidth(1.5)
            c.circle(cx, cy, CIRCLE_R, stroke=1, fill=1)

            # School label — pushed lower to leave room for hand-writing
            c.setFillColor(HexColor("#1B3A6B"))
            c.setFont("Helvetica", 15)
            c.drawCentredString(cx, ty - 50, label)

        c.showPage()

    c.save()
    print(f"✓ Generated {len(SCHOOLS_ORDERED)} pages of blank paper badges → {output_pdf}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    _here = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(
        description="Generate WCSU name badge PDF from one or more CSVs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CSV FORMAT REFERENCE
--------------------
Two CSV layouts are auto-detected by their column headers.

Format A — Event registrant export (e.g. Eventbrite / Google Sheets):
  Required columns:
    Attendee (First Name)         First name
    Attendee (Last Name)          Last name
    Registration Options          Alumni / Student / Faculty/Staff / Community
    Class / Major                 Major, org, or graduation year
  Optional columns (blank is fine if not available):
    Email                         Used for deduplication (preferred over name)
    Community Business/Organization  Shown on badge for community/faculty guests
    Occupation / Position Title   Third line on badge

Format B — Class roster / simple list (e.g. exported grade book):
  Required columns:
    First Name
    Last Name
    Registration Options          Alumni / Student / Faculty/Staff / Community
    Class / Major                 Major or school name (e.g. "Ancell School of Business")
  (No Email, Organization, or Occupation columns needed)

Both formats can be mixed using multiple --csv flags.
        """
    )
    parser.add_argument(
        "--csv", action="append", metavar="PATH",
        help=(
            "Path to a registrants CSV (Format A: event export, or "
            "Format B: class roster). Repeat to merge multiple files: "
            "--csv data/registrants.csv --csv data/acc306.csv "
            "(default: data/registrants.csv). Run with --help for column details."
        )
    )
    parser.add_argument(
        "--name", metavar="FILENAME",
        help=(
            "Output filename only — saved to the output/ folder automatically. "
            "A .pdf extension is added if omitted. "
            "Example: --name ACC306_Badges  →  output/ACC306_Badges.pdf"
        )
    )
    parser.add_argument(
        "--type", choices=["adhesive", "paper"], default="adhesive",
        help=(
            "Badge format to generate (default: adhesive). "
            "'adhesive' → Avery 5395 labels, 8-up, 3-3/8\"×2-1/3\", requires docs/Avery5395AdhesiveNameBadges.pdf. "
            "'paper'    → WCSU paper badge template, 6-up, 4-1/4\"×3-2/3\", requires template/badge_template.pdf."
        )
    )
    parser.add_argument(
        "--output", metavar="PATH",
        help=(
            "Full output path including directory. "
            "Default: output/2026_MeetGreet_NameTags_Adhesive.pdf (adhesive) "
            "or output/2026_MeetGreet_NameTags_Paper.pdf (paper). "
            "Use --name instead if you just want a custom filename in output/."
        )
    )
    parser.add_argument(
        "--blank", action="store_true",
        help=(
            "Generate blank walk-in badge sheets instead of name badges. "
            "Produces one page per school color (6 pages total) with the colored "
            "header/circle and logo but no name — for hand-writing at the event. "
            "Use with --type to select adhesive (default) or paper format. "
            "Default output: output/2026_MeetGreet_Blank_Adhesive.pdf or "
            "output/2026_MeetGreet_Blank_Paper.pdf"
        )
    )
    args = parser.parse_args()

    badge_type  = args.type
    _output_dir = os.path.join(_here, "output")

    # Resolve output path: --name wins over --output; fall back to type+mode default
    if args.name:
        fname = args.name if args.name.lower().endswith(".pdf") else f"{args.name}.pdf"
        output_pdf = os.path.join(_output_dir, fname)
    elif args.output:
        output_pdf = args.output
    else:
        if args.blank:
            default_name = (
                "2026_MeetGreet_Blank_Adhesive.pdf" if badge_type == "adhesive"
                else "2026_MeetGreet_Blank_Paper.pdf"
            )
        else:
            default_name = (
                "2026_MeetGreet_NameTags_Adhesive.pdf" if badge_type == "adhesive"
                else "2026_MeetGreet_NameTags_Paper.pdf"
            )
        output_pdf = os.path.join(_output_dir, default_name)

    # Ensure output directory exists (gitignored, so not always present after a fresh clone)
    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)

    if args.blank:
        # ── Blank walk-in sheets — no CSV needed ──────────────────────────────
        if badge_type == "adhesive":
            avery_source_pdf = os.path.join(_here, "docs", "Avery5395AdhesiveNameBadges.pdf")
            avery_png        = os.path.join(_here, "template", "avery_blank.png")
            ensure_template_png(avery_png, avery_source_pdf)
            logo_png = os.path.join(_here, "template", "wcsu_aa_logo.png")
            generate_blank_adhesive_pdf(avery_png, output_pdf, logo_png=logo_png)
        else:
            paper_source_pdf = os.path.join(_here, "template", "badge_template.pdf")
            paper_png        = os.path.join(_here, "template", "template_blank.png")
            ensure_template_png(paper_png, paper_source_pdf)
            generate_blank_paper_pdf(paper_png, output_pdf)
    else:
        # ── Named badges — load CSV(s) ─────────────────────────────────────────
        csv_paths = args.csv if args.csv else [os.path.join(_here, "data", "registrants.csv")]
        registrants = load_registrants(csv_paths)
        print(f"Loaded {len(registrants)} unique registrants")

        if badge_type == "adhesive":
            avery_source_pdf = os.path.join(_here, "docs", "Avery5395AdhesiveNameBadges.pdf")
            avery_png        = os.path.join(_here, "template", "avery_blank.png")
            ensure_template_png(avery_png, avery_source_pdf)
            logo_png = os.path.join(_here, "template", "wcsu_aa_logo.png")
            generate_adhesive_badges_pdf(registrants, avery_png, output_pdf, logo_png=logo_png)
        else:
            paper_source_pdf = os.path.join(_here, "template", "badge_template.pdf")
            paper_png        = os.path.join(_here, "template", "template_blank.png")
            ensure_template_png(paper_png, paper_source_pdf)
            generate_badges_pdf(registrants, paper_png, output_pdf)
