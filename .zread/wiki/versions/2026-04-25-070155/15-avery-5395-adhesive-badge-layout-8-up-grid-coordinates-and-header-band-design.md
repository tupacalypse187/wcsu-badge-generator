This page documents the precise geometric model behind the Avery 5395 adhesive badge format — the default output of the badge generator. Every dimension, coordinate, and vertical rhythm is derived from the manufacturer's PDF template and calibrated against reportlab's bottom-left coordinate origin. Understanding these values is essential for anyone adjusting margins, fonts, or the header band height through the layout constants described on [Adjusting Layout Constants: Font Sizes, Circle Radius, and Line Spacing](23-adjusting-layout-constants-font-sizes-circle-radius-and-line-spacing).

Sources: [generate_badges.py](generate_badges.py#L49-L68)

## The 8-Up Grid: Physical Dimensions and Slot Coordinates

The Avery 5395 label sheet is a US Letter page (612 × 792 pt) divided into a **2-column × 4-row grid** of 8 adhesive badges. Each badge cell measures **243 × 167.976 pt** (3⅜″ × 2⅓″). The cell width and height are defined as `AVERY_BADGE_W` and `AVERY_BADGE_H`, and the grid positions were extracted directly from the PDF rectangle objects in [docs/Avery5395AdhesiveNameBadges.pdf](docs/Avery5395AdhesiveNameBadges.pdf) using pdfplumber.

Sources: [generate_badges.py](generate_badges.py#L50-L51)

### Column geometry

The two columns are not perfectly centered within the 612 pt page width. Column centers sit at **171 pt** (left) and **441 pt** (right), which means each column is inset approximately 4.5 pt from where a mathematically perfect center (153 and 459 pt) would fall. This offset mirrors the manufacturer's die-cut placement — the `cx` values in `AVERY_SLOTS` reproduce these exact positions so badge content aligns with the label boundaries on the physical sheet.

Sources: [generate_badges.py](generate_badges.py#L63-L70)

### Row geometry and the `cell_top` convention

Rows are numbered 0 through 3 from top to bottom, matching the physical reading order of the sheet. Rather than storing a center-y coordinate, each slot stores `cell_top` — the reportlab y-value of the **top edge** of the badge cell. All vertical positioning within a badge is then computed relative to `cell_top` using downward offsets. The four `cell_top` values are:

| Row | `cell_top` (pt) | Distance from page top | Distance between rows |
|-----|-----------------|------------------------|----------------------|
| 0 (top) | 751.50 | 40.50 pt | — |
| 1 | 570.05 | 221.95 pt | 181.45 pt |
| 2 | 388.55 | 403.45 pt | 181.50 pt |
| 3 (bottom) | 207.10 | 584.90 pt | 181.45 pt |

The inter-row spacing is approximately 181.5 pt — slightly more than the 168 pt cell height — accounting for the die-cut gap between label rows on the physical sheet. The top margin (40.5 pt) and bottom margin (207.1 pt − 0 = 207.1 pt below the bottom cell's top edge) are asymmetrical, which is expected for Avery templates designed to fit standard printer margins.

Sources: [generate_badges.py](generate_badges.py#L63-L70)

### Complete slot map

The `AVERY_SLOTS` list defines all 8 positions. Slots are ordered top-to-bottom, left-to-right — the same order badges are filled from the registrant list. When a page has fewer than 8 remaining badges, the trailing slots are simply skipped.

```python
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

Sources: [generate_badges.py](generate_badges.py#L63-L70)

## Vertical Anatomy of a Single Badge Cell

Each badge is divided into two vertical zones: a **colored header band** at the top and a **white content area** below it. The band height is controlled by `AVERY_HEADER_H` (52 pt), leaving approximately 116 pt of white space for the logo and text lines. Every y-coordinate within a cell is expressed as a downward offset from `cell_top`.

Sources: [generate_badges.py](generate_badges.py#L52-L58)

### Zone 1 — Colored header band (0 to −52 pt from `cell_top`)

The header band spans the full cell width (`AVERY_BADGE_W = 243 pt`) and is filled with the registrant's school color from the `SCHOOL_COLORS` dictionary, which is described in detail on [Changing School Colors in the SCHOOL_COLORS Dictionary](24-changing-school-colors-in-the-school_colors-dictionary). The band serves a dual purpose: it provides instant visual school identification and hosts the two most prominent text elements.

**"Meet & Greet 2026"** is drawn in white Helvetica 9 pt, positioned at `cell_top − 13` pt — placing it near the top of the band with comfortable padding from the upper edge. This event identifier is static across all badges.

The **attendee name** occupies the lower portion of the band at `cell_top − 33` pt, rendered in white Helvetica-Bold. The `fit_text` function auto-scales the font from a maximum of 15 pt down to a minimum of 7 pt until the name fits within `AVERY_TEXT_W` (218 pt). This scaling behavior is documented on [Text Rendering: Auto-Scaling Names, Word Wrapping, and Font Management](17-text-rendering-auto-scaling-names-word-wrapping-and-font-management). Alumni names include graduation year suffixes (e.g., `'71`), which are assembled by the logic described on [Name Line Assembly with Alumni Year Suffixes](19-name-line-assembly-with-alumni-year-suffixes).

Sources: [generate_badges.py](generate_badges.py#L449-L466)

### Zone 2 — White content area (−52 to −168 pt from `cell_top`)

Below the header band, the remaining ~116 pt of white space holds three elements stacked vertically: the WCSU Alumni Association logo, the school/registration-type line, and the occupation line. All text in this zone uses dark ink colors against the white background for readability.

Sources: [generate_badges.py](generate_badges.py#L468-L488)

### Logo placement

The WCSU Alumni Association logo ([template/wcsu_aa_logo.png](template/wcsu_aa_logo.png)) is rendered at 185 × 53.8 pt (`AVERY_LOGO_W × AVERY_LOGO_H`), centered horizontally on `cx`. The source image is 258 × 75 px RGBA, and the rendered dimensions preserve the aspect ratio via `185 * (75 / 258)`. The logo's top edge sits at `cell_top − AVERY_HEADER_H − 10` (a 10 pt gap below the header band), and its bottom edge lands at `cell_top − AVERY_HEADER_H − 10 − AVERY_LOGO_H`.

If the logo file is missing, the generator skips it silently — the badge still renders with text only, shifted up by the absent logo's height. The `mask="auto"` flag on `drawImage` ensures the PNG's alpha channel is respected, so any transparency in the logo composites cleanly against the white badge area.

Sources: [generate_badges.py](generate_badges.py#L469-L480)

### Text block below the logo

The school/registration-type line begins 14 pt below the logo's bottom edge. It is rendered in Helvetica 11 pt with WCSU Navy (`#1B3A6B`) and uses the `wrap_and_draw` function for automatic word wrapping at `AVERY_TEXT_W` (218 pt) with a 13 pt line leading. The format of this line varies by registration type — see [Registration Type Display Logic: Name, School, and Occupation Formatting](20-registration-type-display-logic-name-school-and-occupation-formatting) for the full set of display rules.

The occupation line follows 6 pt below the last baseline of the type line (using `next_y` from `wrap_and_draw` to avoid overlap when the type text wraps to multiple lines). It is rendered in Helvetica 10 pt with a dark gray (`#444444`) color, also subject to word wrapping at 218 pt with 12 pt leading. Occupation text is pre-cleaned to remove newlines and truncate at 85 characters before reaching the rendering stage.

Sources: [generate_badges.py](generate_badges.py#L482-L490)

## Vertical Rhythm Summary

The following table shows every y-position within a badge cell relative to `cell_top`, along with the element at each position. Negative values go downward (reportlab's y-axis increases upward).

| Offset from `cell_top` | Element | Style |
|------------------------|---------|-------|
| 0 pt | Top edge of badge cell | — |
| −13 pt | "Meet & Greet 2026" | White, Helvetica 9 pt |
| −33 pt | Attendee name (auto-scaled) | White, Helvetica-Bold 7–15 pt |
| −52 pt | Bottom of header band / top of white area | Color boundary |
| −62 pt | Top of logo image | 10 pt gap from band |
| −115.8 pt | Bottom of logo image | ≈ 53.8 pt logo height |
| −129.8 pt | School/type line baseline | Navy, Helvetica 11 pt, 14 pt gap |
| −135.8 pt+ | Occupation line baseline | Gray, Helvetica 10 pt, 6 pt gap |
| −167.976 pt | Bottom edge of badge cell | — |

Sources: [generate_badges.py](generate_badges.py#L52-L58), [generate_badges.py](generate_badges.py#L449-L490)

## Rendering Pipeline: How the Grid Fills

The function `generate_adhesive_badges_pdf` implements the full rendering loop. It accepts the registrant list, the template background image, the output path, and an optional logo path. The process follows three phases per page:

1. **Background stamp** — the full-page Avery template PNG (rendered from [docs/Avery5395AdhesiveNameBadges.pdf](docs/Avery5395AdhesiveNameBadges.pdf) via `ensure_template_png`) is drawn at 612 × 792 pt with `preserveAspectRatio=True`. This provides the die-cut guide outlines visible on screen and in print previews. The auto-rendering mechanism is described on [Template Auto-Rendering: PDF-to-PNG Conversion via pypdfium2](14-template-auto-rendering-pdf-to-png-conversion-via-pypdfium2).

2. **Batch slicing** — badges are sliced into groups of 8 (`badges[page_idx * 8 : page_idx * 8 + 8]`). If the final page has fewer than 8 badges, the remaining slots are left empty, producing blank adhesive cells on the sheet.

3. **Per-badge rendering** — for each badge in the batch, the slot's `cx` and `cell_top` values anchor the header band, text, and logo. The function draws elements in strict top-to-bottom order: colored rectangle → event text → name → logo → type line → occupation line.

The page count is computed as `(len(badges) + 7) // 8`, which uses integer ceiling division to ensure even a single remaining badge gets its own page. This avoids the off-by-one error that `(len(badges) / 8)` would produce for non-multiples of 8.

Sources: [generate_badges.py](generate_badges.py#L418-L491)

## Blank Walk-In Sheets: Same Grid, Empty Names

The `generate_blank_adhesive_pdf` function reuses the identical `AVERY_SLOTS` coordinate system and the same visual structure, but instead of registrant data, it iterates over the six entries in `SCHOOLS_ORDERED` (Ancell, Arts, Visual, Professional, Faculty, Community — intentionally excluding `default`). Each school produces one full page of 8 badges with the colored header band, "Meet & Greet 2026" text, and the WCSU AA logo. The name field is left blank, and the school label appears in place of the type line — providing hand-write-ready sheets for walk-in attendees. This process is documented on [Preparing Blank Walk-In Badge Sheets for On-Site Registration](5-preparing-blank-walk-in-badge-sheets-for-on-site-registration).

Sources: [generate_badges.py](generate_badges.py#L493-L530)

## Key Layout Constants at a Glance

For developers who need to adjust spacing or sizing, these are the constants that control the Avery layout. All are defined at module level in [generate_badges.py](generate_badges.py) and affect every adhesive badge uniformly.

| Constant | Value | Unit | Purpose |
|----------|-------|------|---------|
| `AVERY_BADGE_W` | 243.0 | pt | Full cell width (3⅜″) |
| `AVERY_BADGE_H` | 167.976 | pt | Full cell height (2⅓″) |
| `AVERY_HEADER_H` | 52 | pt | Colored header band height |
| `AVERY_TEXT_W` | 218 | pt | Max text width (243 − 2 × 12.5 pt side margins) |
| `AVERY_LOGO_W` | 185.0 | pt | Logo rendered width |
| `AVERY_LOGO_H` | ≈ 53.8 | pt | Logo rendered height (aspect-preserving) |

Adjusting any of these values changes the layout globally. For example, reducing `AVERY_HEADER_H` from 52 to 44 pt would shrink the colored band and push the logo and text lines upward — useful if you need more room for multi-line occupation text. See [Adjusting Layout Constants: Font Sizes, Circle Radius, and Line Spacing](23-adjusting-layout-constants-font-sizes-circle-radius-and-line-spacing) for guided customization instructions.

Sources: [generate_badges.py](generate_badges.py#L50-L58)

## What to Explore Next

- **[Text Rendering: Auto-Scaling Names, Word Wrapping, and Font Management](17-text-rendering-auto-scaling-names-word-wrapping-and-font-management)** — how `fit_text` and `wrap_and_draw` handle long names and word wrapping within the 218 pt text width
- **[School Color Coding System and Visual Legend](7-school-color-coding-system-and-visual-legend)** — the visual mapping between school keys and the six header band colors
- **[WCSU Paper Badge Layout: 6-Up Grid, Colored Circles, and Template Background](16-wcsu-paper-badge-layout-6-up-grid-colored-circles-and-template-background)** — the alternative 6-up format with a fundamentally different layout model
- **[Print Day Guide: Media Selection, Scale Settings, and Per-Sheet Counts](27-print-day-guide-media-selection-scale-settings-and-per-sheet-counts)** — practical printing instructions for the 8-up adhesive sheets