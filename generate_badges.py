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
        "--output", metavar="PATH",
        help=(
            "Full output path including directory "
            "(default: output/2026_MeetGreet_NameTags.pdf). "
            "Use --name instead if you just want a custom filename in output/."
        )
    )
    args = parser.parse_args()

    csv_paths = args.csv if args.csv else [os.path.join(_here, "data", "registrants.csv")]

    # Resolve output path: --name wins over --output; fall back to default
    _output_dir = os.path.join(_here, "output")
    if args.name:
        fname = args.name if args.name.lower().endswith(".pdf") else f"{args.name}.pdf"
        output_pdf = os.path.join(_output_dir, fname)
    elif args.output:
        output_pdf = args.output
    else:
        output_pdf = os.path.join(_output_dir, "2026_MeetGreet_NameTags.pdf")
    source_pdf   = os.path.join(_here, "template", "badge_template.pdf")
    template_png = os.path.join(_here, "template", "template_blank.png")

    # Ensure output directory exists (gitignored, so not always present after a fresh clone)
    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)

    ensure_template_png(template_png, source_pdf)
    registrants = load_registrants(csv_paths)
    print(f"Loaded {len(registrants)} unique registrants")
    generate_badges_pdf(registrants, template_png, output_pdf)
