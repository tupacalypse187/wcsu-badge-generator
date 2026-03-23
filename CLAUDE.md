# CLAUDE.md — WCSU Meet & Greet Badge Generator

## Project Overview

This project auto-generates print-ready name badge PDFs for the **WCSU Alumni Association Meet & Greet** event (March 25, 2026). It reads one or more CSV files (event registrant exports or class rosters) and produces either Avery 5395 adhesive labels (default, 8-up) or a 6-up paper badge layout, with color-coded school affiliation per attendee.

---

## Key Files

| File | Purpose |
|---|---|
| `generate_badges.py` | Main script — reads CSV(s), maps schools, outputs PDF; also generates blank walk-in sheets via `--blank` |
| `convert_classlist.py` | Convert an xlsx class roster to badge-generator CSV format |
| `requirements.txt` | Python dependencies |
| `data/registrants.csv` | Registrant data exported from Google Sheets (gitignored — PII) |
| `template/badge_template.pdf` | Single-page blank paper badge template (~140 KB, committed) |
| `template/wcsu_aa_logo.png` | WCSU Alumni Association logo — 258×75px RGBA (committed) |
| `template/template_blank.png` | Rendered from badge_template.pdf on first run (gitignored — auto-generated) |
| `template/avery_blank.png` | Rendered from Avery5395AdhesiveNameBadges.pdf on first run (gitignored — auto-generated) |
| `docs/Avery5395AdhesiveNameBadges.pdf` | Avery 5395 blank template used to render avery_blank.png (committed) |
| `docs/sample_badge.png` | Example adhesive badge image used in README |
| `docs/sample_badge_paper.png` | Example paper badge image used in README |
| `docs/badge_color_legend.png` | Color legend grid used in README |
| `output/` | Generated PDFs — regenerated each run (gitignored) |

---

## Architecture

### PDF Generation Pipeline

1. **`ensure_template_png(template_png, source_pdf, page_index, scale)`** — renders a PNG background from a source PDF at 3× scale if the PNG doesn't exist or is zero-bytes. Called for both badge formats before rendering.
2. **`load_registrants(csv_paths)`** — reads one or more CSVs (UTF-8-BOM), auto-detects format, deduplicates globally by email (or first+last name if no email), prints per-file counts.
3. **`_detect_format(fieldnames)`** — returns `'event'` or `'classlist'` based on column headers.
4. **`_normalize_row(row, fmt)`** — converts either CSV format into the canonical internal dict; collapses N/A sentinels to empty string via `_clean()`.
5. **`build_badge_data(row)`** — extracts name line (with `'YY` graduation year suffix for alumni), school key, school label, color, type string, and occupation line.
6. **`detect_school(major, org, reg_type)`** — keyword-matches `Class / Major` and `Community Business/Organization` to assign a school color key.
7. **`generate_adhesive_badges_pdf(...)`** — renders 8-up Avery 5395 adhesive badges (DEFAULT). Each badge has a full-width colored school header band with white name text, WCSU AA logo, and school/occupation lines below.
8. **`generate_badges_pdf(...)`** — renders 6-up paper badges on the WCSU template background. Each badge has a colored circle + name/school/occ text.

### Template Auto-Rendering

Both formats auto-render their background PNG from a committed source PDF on first run:

| Format | Source PDF | Output PNG | Page index |
|---|---|---|---|
| Adhesive | `docs/Avery5395AdhesiveNameBadges.pdf` | `template/avery_blank.png` | 0 |
| Paper | `template/badge_template.pdf` | `template/template_blank.png` | 0 |

`ensure_template_png()` checks both `os.path.exists()` and `os.path.getsize() > 0` — a zero-byte file triggers re-render. If the template changes, replace the source PDF and delete the PNG; it regenerates automatically.

### CLI Flags (`generate_badges.py`)

```
--csv PATH        Path to a registrant CSV. Repeat for multiple files.
                  Default: data/registrants.csv
                  Both event and classlist formats can be mixed.
                  Not used with --blank.

--type TYPE       Badge format: adhesive (default) or paper
                    adhesive → Avery 5395, 8-up, 3-3/8"×2-1/3"
                    paper    → WCSU template, 6-up, 4-1/4"×3-2/3"

--blank           Generate blank walk-in sheets instead of named badges.
                  One page per school color (6 pages). No CSV required.
                  Combine with --type for adhesive (default) or paper.

--name FILENAME   Output filename — saved to output/ automatically.
                  .pdf extension added if omitted.
                  Example: --name ACC306  → output/ACC306.pdf

--output PATH     Full output path (overrides --name and default location).
```

Default output filenames (when neither `--name` nor `--output` is given):

| Mode | Adhesive default | Paper default |
|---|---|---|
| Named badges | `output/2026_MeetGreet_NameTags_Adhesive.pdf` | `output/2026_MeetGreet_NameTags_Paper.pdf` |
| Blank sheets | `output/2026_MeetGreet_Blank_Adhesive.pdf` | `output/2026_MeetGreet_Blank_Paper.pdf` |

### Badge Layout — Paper (6-up)

Page size: 612 × 792 pt (US Letter), reportlab origin = bottom-left

Each badge cell: 306 × 264 pt (2 columns × 3 rows)

Template has ~17.7pt left/right page margins; actual badge content width ≈ 288pt.
True column centers: left = 162pt, right = 450pt.

| Element | Left Col X | Right Col X | Row 1 Y (top) | Row 2 Y (mid) | Row 3 Y (bot) |
|---|---|---|---|---|---|
| Circle center `cy` | 162 | 450 | 621 | 395 | 185 |
| Text top `text_top_rl` | 162 | 450 | 585 | 358 | 144 |

Circle radius: 24 pt

```python
BADGE_SLOTS = [
    {"cx": 162, "cy": 792 - 171, "text_top_rl": 792 - 207},
    {"cx": 450, "cy": 792 - 171, "text_top_rl": 792 - 207},
    {"cx": 162, "cy": 792 - 397, "text_top_rl": 792 - 434},
    {"cx": 450, "cy": 792 - 397, "text_top_rl": 792 - 434},
    {"cx": 162, "cy": 792 - 607, "text_top_rl": 792 - 648},
    {"cx": 450, "cy": 792 - 607, "text_top_rl": 792 - 648},
]
```

### Badge Layout — Adhesive (Avery 5395, 8-up)

Each badge cell: 243 × 167.976 pt (3-3/8" × 2-1/3"), 2 cols × 4 rows.

Column x-centers: left = 171pt, right = 441pt.

```python
AVERY_BADGE_W  = 243.0
AVERY_BADGE_H  = 167.976
AVERY_HEADER_H = 52        # colored school header band height
AVERY_TEXT_W   = 218       # max text width (243 − 2×12.5 margins)
AVERY_LOGO_W   = 185.0
AVERY_LOGO_H   = round(AVERY_LOGO_W * 75 / 258, 1)   # ≈ 53.8 pt

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
```

Adhesive badge layout (top → bottom within each cell):
- Full-width colored header band (AVERY_HEADER_H = 52pt)
  - "Meet & Greet 2026" in white 9pt at top
  - Attendee name in white bold ~15pt below
- WCSU Alumni Association logo (185×54pt, centered)
- School / type line (Helvetica 11pt, navy)
- Occupation line (Helvetica 10pt, dark gray)

### School Color Map

| School key | School Name | Hex Color | Color Name |
|---|---|---|---|
| `ancell` | Ancell School of Business | `#E8702A` | Orange |
| `arts` | School of Arts & Sciences | `#1B3A6B` | Navy |
| `visual` | School of Visual & Performing Arts | `#8E44AD` | Purple |
| `professional` | School of Professional Studies | `#27AE60` | Forest Green |
| `faculty` | Faculty / Staff (no specific school) | `#D4AC0D` | Dark Gold |
| `community` | Community Guest | `#7F8C8D` | Gray |
| `default` | Unmatched / ambiguous major | `#95A5A6` | Light Gray |

### School Detection Logic

`detect_school(major, org, reg_type)` — priority order:
1. **Exact org match** — if `"ancell"` in combined text → Ancell; `"professional studies"` or `"dean"` → Professional; `"visual"` or `"performing"` → Visual
2. **Faculty/Staff** — if `reg_type == "Faculty/Staff"` and no org match → `faculty`
3. **Community** — if `reg_type == "Community"` → `community`
4. **Keyword match** — VISUAL_KEYWORDS → PROFESSIONAL_KEYWORDS → ANCELL_KEYWORDS → ARTS_KEYWORDS (most-specific first)
5. **Default** — gray if nothing matches

Keyword lists in `generate_badges.py`:
- `ANCELL_KEYWORDS` — accounting, finance, business, management, marketing, mis, mba, bba…
- `ARTS_KEYWORDS` — biology, chemistry, nursing, psychology, computer science, cybersecurity…
- `VISUAL_KEYWORDS` — graphic design, theater, music, dance, film, dima…
- `PROFESSIONAL_KEYWORDS` — education, health administration, counseling, mha…

---

## CSV Format Reference

Two layouts are auto-detected by their column headers.

### Format A — Event registrant export (Google Sheets / Eventbrite)

| Column | Required | Notes |
|---|---|---|
| `Attendee (First Name)` | ✅ | |
| `Attendee (Last Name)` | ✅ | |
| `Registration Options` | ✅ | `Alumni` / `Student` / `Faculty/Staff` / `Community` |
| `Class / Major` | ✅ | Used for school color detection and graduation year |
| `Email` | optional | Used for deduplication (preferred over name) |
| `Community Business/Organization` | optional | Shown on badge for community/faculty guests |
| `Occupation / Position Title` | optional | Third line on badge |

### Format B — Class roster / simple list

| Column | Required | Notes |
|---|---|---|
| `First Name` | ✅ | |
| `Last Name` | ✅ | |
| `Registration Options` | ✅ | Usually `Student` |
| `Class / Major` | ✅ | e.g. `Ancell School of Business` |

> N/A-like sentinels (`N/A`, `NA`, `None`, `-`, `TBD`, etc.) are automatically treated as blank by `_clean()`.

---

## Blank Badge Sheets (`--blank` flag)

Blank walk-in sheets are generated by passing `--blank` to the main script — no separate script needed.

- One page per school color (6 pages per format)
- Each badge shows: colored header band (adhesive) or colored circle (paper) + WCSU AA logo — no name
- School order: Ancell (orange), Arts & Sciences (navy), Visual & Performing Arts (purple), Professional Studies (green), Faculty/Staff (gold), Community (gray)

```bash
# Adhesive blanks (default) — output/2026_MeetGreet_Blank_Adhesive.pdf
python3 generate_badges.py --blank

# Paper blanks — output/2026_MeetGreet_Blank_Paper.pdf
python3 generate_badges.py --blank --type paper
```

Blank generation functions in `generate_badges.py`:
- `generate_blank_adhesive_pdf(template_png, output_pdf, logo_png)` — 8-up Avery 5395
- `generate_blank_paper_pdf(template_png, output_pdf)` — 6-up WCSU template (logo already in background)

---

## convert_classlist.py

Converts an xlsx class roster (columns: First Name, Last Name, optionally Email) to badge-generator CSV format.

```bash
# Accounting class — Ancell (orange)
python3 convert_classlist.py data/ClassListACC306.xlsx \
  --major "Accounting" --output data/acc306_badges.csv

# Nursing class — Arts & Sciences (navy)
python3 convert_classlist.py data/ClassListNUR201.xlsx \
  --major "Nursing" --output data/nur201_badges.csv

# Faculty roster
python3 convert_classlist.py data/FacultyList.xlsx \
  --reg-type Faculty/Staff --org "School of Arts & Sciences"
```

`--major` controls badge color — pass the correct major/school name. Omitting it produces gray badges (with a warning). Auto-inference from filename was intentionally removed (wrong color is worse than gray).

Column aliases recognized: `First Name`, `Firstname`, `Given Name`; `Last Name`, `Lastname`, `Surname`; `Email`, `E-mail`; `Major`, `Class`, `Class / Major`, `Program`, `Degree`; plus org and title aliases.

---

## Common Tasks

### Regenerate badges from updated CSV
```bash
source .venv/bin/activate        # macOS / Linux
# Place latest export at data/registrants.csv first
python3 generate_badges.py
# Output → output/2026_MeetGreet_NameTags_Adhesive.pdf (default)
python3 generate_badges.py --type paper
# Output → output/2026_MeetGreet_NameTags_Paper.pdf
```

### Fix a gray (unmatched) badge
Update the registrant's `Class / Major` in the CSV with a more specific major (e.g. `"BA English"` instead of `"BA"`) and re-run. No code changes needed.

### Add a new school keyword
Edit the relevant keyword list in `generate_badges.py`:
- `ANCELL_KEYWORDS` — business-related majors
- `ARTS_KEYWORDS` — liberal arts, sciences, nursing, etc.
- `VISUAL_KEYWORDS` — art, design, theater, etc.
- `PROFESSIONAL_KEYWORDS` — education, health admin, etc.

### Adjust font sizes or layout
Key layout constants at the top of `generate_badges.py`:
- `CIRCLE_R` — circle radius in PDF points (paper format)
- `LINE_LEADING` — vertical spacing between text baselines
- `TEXT_AREA_WIDTH` — max text width before wrapping
- `AVERY_HEADER_H` — colored band height for adhesive format
- Font sizes are set inline in `generate_badges_pdf()` and `generate_adhesive_badges_pdf()` — `fit_text()` auto-scales for name, `wrap_and_draw()` wraps school/occ lines

### Change a school color
Edit the `SCHOOL_COLORS` dict in `generate_badges.py`. Colors are `HexColor` objects from reportlab.

---

## Known Edge Cases

- **Duplicate registrants**: Deduplicated globally across all --csv files by lowercase email. If two rows share an email (e.g. a correction re-submission), only the first is kept. Falls back to `firstname_lastname` key if no email.
- **Multi-line occupations in CSV**: Newlines collapsed; only the first segment is used. Roles separated by `/` or `;` also truncated to first.
- **Very long names or titles**: `fit_text()` auto-scales down to a minimum of 7pt. `wrap_and_draw()` wraps at the respective `TEXT_W` constant.
- **Ambiguous majors** (e.g. `"BA"`, `"2019"`, typos): Assigned gray/default. Fix by updating `Class / Major` in the CSV.
- **Faculty in specific schools**: If the org field contains `"Ancell"` or `"Professional Studies"`, they get that school's color instead of dark gold.
- **Alumni graduation years**: `extract_years()` handles both `'71` apostrophe-style and four-digit `1971` formats, and handles multiple years (e.g. `'71 & '98`).

---

## Environment

- Python 3.10–3.13 (3.13 recommended; 3.14+ not yet supported by all deps)
- Key packages: `reportlab`, `pypdfium2`, `Pillow`, `openpyxl`
- See `requirements.txt` for pinned versions

---

## Event Details

- **Event**: WCSU Alumni Association Meet & Greet
- **Date**: March 25, 2026
- **Organizer contact**: Career Success Center, WCSU
- **Venue**: Western Connecticut State University, Danbury, CT
- **Registrant data source**: Google Sheets (export as CSV before each print run)
- **Adhesive labels**: Avery 5395, 3-3/8" × 2-1/3", 8 per sheet
- **Paper badges**: Letter cardstock 65–80 lb, cut along grid lines after printing
