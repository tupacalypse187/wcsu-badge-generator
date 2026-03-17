# CLAUDE.md — WCSU Meet & Greet Badge Generator

## Project Overview

This project auto-generates print-ready name badge PDFs for the **WCSU Alumni Association Meet & Greet** event (March 25, 2026). It reads a Google Sheets–exported CSV of event registrants and produces a 6-up badge layout on letter-size pages, with color-coded circles indicating each attendee's WCSU school.

---

## Key Files

| File | Purpose |
|---|---|
| `generate_badges.py` | Main script — reads CSV, maps schools, outputs PDF |
| `data/registrants.csv` | Registrant data exported from Google Sheets (gitignored — PII) |
| `requirements.txt` | Python dependencies |
| `template/badge_template.pdf` | Single-page blank badge template extracted from the original 54-page PDF (~140 KB, committed) |
| `template/template_blank.png` | Rendered from source PDF on first run (gitignored — auto-generated) |
| `output/2026_MeetGreet_NameTags.pdf` | Output — regenerated each run (gitignored) |
| `docs/sample_badge.png` | Example badge image used in README |
| `docs/badge_color_legend.png` | Color legend grid used in README |

---

## Architecture

### PDF Generation Pipeline

1. **`ensure_template_png(template_png, source_pdf)`** — renders `template_blank.png` from page index 2 of the source PDF at 3× scale if the PNG doesn't already exist
2. **`load_registrants(csv_path)`** — reads CSV with UTF-8-BOM encoding, deduplicates by email (or first+last name if no email)
3. **`build_badge_data(row)`** — extracts name, class year, school, and occupation from each CSV row
4. **`detect_school(major, org, reg_type)`** — keyword-matches to one of 4 WCSU schools or assigns Faculty/Community
5. **`generate_badges_pdf(...)`** — uses reportlab to render 6 badges per page using the blank template PNG as background, then overlays colored circles and text

### Template Background

The blank template is `template/badge_template.pdf` — a single-page PDF extracted from page 3 of the original 54-page event file (~140 KB vs ~8.5 MB). It is rendered to `template_blank.png` at 3× scale (1836×2376 px) automatically by `ensure_template_png()` on first run (`page_index=0`). This PNG is embedded as the background in each generated page via reportlab's `drawImage`.

`template_blank.png` does not need to be committed to the repo — it is regenerated automatically if missing. If the template changes, replace `badge_template.pdf` with the new single-page extract, delete `template_blank.png`, and re-run.

### Badge Layout (PDF points, reportlab origin = bottom-left)

Page size: 612 × 792 pt (US Letter)
Each badge cell: 306 × 264 pt (2 columns × 3 rows)

| Element | Left Col X | Right Col X | Row 1 Y | Row 2 Y | Row 3 Y |
|---|---|---|---|---|---|
| Circle center | 162 | 450 | 621 | 395 | 185 |
| Name baseline | 162 | 450 | 565 | 338 | 124 |

Template has ~17.7pt left/right page margins; actual badge width is 288pt (not 306pt). Column centers are 162pt and 450pt, not the naive 153/459.

Circle radius: 24 pt

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

---

## CSV Column Reference

The registrant CSV has these columns (note UTF-8-BOM header):

| Column | Used for |
|---|---|
| `Registration Options` | Alumni / Faculty/Staff / Student / Community |
| `Attendee (First Name)` | Name line on badge |
| `Attendee (Last Name)` | Name line on badge |
| `Class / Major` | School detection + class year extraction |
| `Community Business/Organization` | School detection (org name), community type line |
| `Occupation / Position Title` | Third line on badge |
| `Email` | Deduplication key |

---

## Common Tasks

### Regenerate badges from updated CSV
```bash
source .venv/bin/activate        # macOS
# Place latest export at data/registrants.csv first
python3 generate_badges.py
# Output → output/2026_MeetGreet_NameTags.pdf
```

### Fix a gray (unmatched) badge
Update the registrant's `Class / Major` in `registrants.csv` with a more specific major, then re-run the script. No code changes needed.

### Add a new school keyword
Edit the relevant keyword list in `generate_badges.py`:
- `ANCELL_KEYWORDS` — business-related majors
- `ARTS_KEYWORDS` — liberal arts, sciences, nursing, etc.
- `VISUAL_KEYWORDS` — art, design, theater, etc.
- `PROFESSIONAL_KEYWORDS` — education, health admin, etc.

### Adjust font sizes or text layout
Key layout constants at the top of `generate_badges.py`:
- `CIRCLE_R` — circle radius in PDF points
- `LINE_LEADING` — vertical spacing between text lines
- `TEXT_AREA_WIDTH` — max text width before wrapping
- Font sizes are in `generate_badges_pdf()` — `fit_text()` for name, `wrap_and_draw()` for type/occupation

### Change a school color
Edit the `SCHOOL_COLORS` dict in `generate_badges.py`. Colors are `HexColor` objects from reportlab.

---

## Known Edge Cases

- **Duplicate registrants**: Deduplicated by lowercase email. If two rows share an email (e.g., a correction re-submission), only the first is kept.
- **Multi-line occupations in CSV**: Newlines are collapsed; only the first segment is used.
- **Very long names or titles**: `fit_text()` auto-scales down to a minimum of 8pt. `wrap_and_draw()` wraps at `TEXT_AREA_WIDTH`.
- **Ambiguous majors** (e.g., `"BA"`, `"2019"`, typos): Assigned gray/default. Fix by updating `Class / Major` in the CSV.
- **Faculty in specific schools**: If the org field contains `"Ancell"` or `"Professional Studies"`, they get that school's color instead of dark gold.

---

## Environment

- Python 3.10+
- Key packages: `reportlab`, `pypdfium2`, `Pillow`, `pdfplumber`
- See `requirements.txt` for pinned versions

---

## Event Details

- **Event**: WCSU Alumni Association Meet & Greet
- **Date**: March 25, 2026
- **Organizer contact**: Career Success Center, WCSU
- **Template source**: `template/badge_template.pdf` (extracted from original 54-page event PDF, page 3)
- **Registrant data source**: Google Sheets (exported as CSV before each print run)
