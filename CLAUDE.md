# CLAUDE.md — WCSU Meet & Greet Badge Generator

## Project Overview

This project auto-generates print-ready name badge PDFs for the **WCSU Alumni Association Meet & Greet** event (March 25, 2026). It reads a Google Sheets–exported CSV of event registrants and produces a 6-up badge layout on letter-size pages, with color-coded circles indicating each attendee's WCSU school.

---

## Key Files

| File | Purpose |
|---|---|
| `generate_badges.py` | Main script — reads CSV, maps schools, outputs PDF |
| `registrants.csv` | Registrant data exported from Google Sheets |
| `requirements.txt` | Python dependencies |
| `2025 Meet & Greet Name Tags.pdf` | Source template — page index 2 (page 3) is the blank badge template used as the PDF background |
| `2026_MeetGreet_NameTags.pdf` | Output — regenerated each run |

---

## Architecture

### PDF Generation Pipeline

1. **`load_registrants(csv_path)`** — reads CSV with UTF-8-BOM encoding, deduplicates by email (or first+last name if no email)
2. **`build_badge_data(row)`** — extracts name, class year, school, and occupation from each CSV row
3. **`detect_school(major, org, reg_type)`** — keyword-matches to one of 4 WCSU schools or assigns Faculty/Community
4. **`generate_badges_pdf(...)`** — uses reportlab to render 6 badges per page using the blank template PNG as background, then overlays colored circles and text

### Template Background

The blank template is **page index 2** (third page) of `2025 Meet & Greet Name Tags.pdf`. It was pre-rendered to `template_blank.png` at 3× scale (1836×2376 px). This PNG is embedded as the background in each generated page via reportlab's `drawImage`.

The template is rendered once during the original setup. If the template PDF changes, re-render with:
```python
import pypdfium2 as pdfium
pdf = pdfium.PdfDocument("2025 Meet & Greet Name Tags.pdf")
page = pdf[2]
bitmap = page.render(scale=3.0)
bitmap.to_pil().save("template_blank.png")
```

### Badge Layout (PDF points, reportlab origin = bottom-left)

Page size: 612 × 792 pt (US Letter)
Each badge cell: 306 × 264 pt (2 columns × 3 rows)

| Element | Left Col X | Right Col X | Row 1 Y | Row 2 Y | Row 3 Y |
|---|---|---|---|---|---|
| Circle center | 153 | 459 | 621 | 395 | 185 |
| Name baseline | 153 | 459 | 565 | 338 | 124 |

Circle radius: 24 pt

### School Color Map

| School key | School Name | Hex Color |
|---|---|---|
| `ancell` | Ancell School of Business | `#E8702A` |
| `arts` | School of Arts & Sciences | `#1B3A6B` |
| `visual` | School of Visual & Performing Arts | `#C0392B` |
| `professional` | School of Professional Studies | `#27AE60` |
| `faculty` | Faculty / Staff (no specific school) | `#2980B9` |
| `community` | Community Guest | `#7F8C8D` |
| `default` | Unmatched / ambiguous major | `#95A5A6` |

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
source .venv/bin/activate   # macOS
python3 generate_badges.py
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
- **Faculty in specific schools**: If the org field contains `"Ancell"` or `"Professional Studies"`, they get that school's color instead of steel blue.

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
- **Template source**: `2025 Meet & Greet Name Tags.pdf` (provided by event team)
- **Registrant data source**: Google Sheets (exported as CSV before each print run)
