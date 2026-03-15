# 🎓 WCSU Alumni Meet & Greet — Name Badge Generator

> **Event:** WCSU Alumni Association Meet & Greet · March 25, 2026
> **Venue:** Western Connecticut State University, Danbury, CT
> **Output:** Print-ready PDF — 6 badges per page, color-coded by WCSU school

---

## 📛 Example Badge

![Sample Badge](sample_badge.png)

---

## 🎨 Color Legend

Each badge displays a colored circle that identifies the attendee's WCSU school affiliation. Six colors are used in total:

| Color | School / Group | Hex |
|---|---|---|
| 🟠 **Orange** | Ancell School of Business | `#E8702A` |
| 🔵 **Navy** | School of Arts & Sciences | `#1B3A6B` |
| 🔴 **Red** | School of Visual & Performing Arts | `#C0392B` |
| 🟢 **Green** | School of Professional Studies | `#27AE60` |
| 🔵 **Steel Blue** | Faculty / Staff | `#2980B9` |
| ⬜ **Gray** | Community Guest | `#7F8C8D` |

![Color Legend Grid](badge_color_legend.png)

School assignment is **automatically detected** from the registrant's `Class / Major` and `Community Business/Organization` fields in the CSV. See [School Detection Logic](#-school-detection-logic) for details.

---

## 📁 Project Structure

```
meetandgreet/
├── generate_badges.py              # 🐍 Main badge generation script
├── registrants.csv                 # 📋 Event registrant data (from Google Sheets export)
├── requirements.txt                # 📦 Python dependencies
├── 2025 Meet & Greet Name Tags.pdf # 🖼  Original badge template (do not modify)
├── 2026_MeetGreet_NameTags.pdf     # ✅ Generated output — print this
├── sample_badge.png                # 🖼  Example badge (for docs)
├── badge_color_legend.png          # 🖼  Color legend grid (for docs)
├── CLAUDE.md                       # 🤖 AI assistant context file
└── README.md                       # 📖 This file
```

---

## ⚙️ Prerequisites

- Python 3.10 or higher
- `pip` / `venv`
- The original badge template PDF (`2025 Meet & Greet Name Tags.pdf`) must be present in the same directory

---

## 🐍 Setup — macOS

```bash
# 1. Navigate to the project folder
cd path/to/meetandgreet

# 2. Create a virtual environment
python3 -m venv .venv

# 3. Activate the virtual environment
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Verify setup
python3 -c "import reportlab, pypdfium2, PIL; print('✅ All dependencies ready')"
```

> **To deactivate** when done: `deactivate`

---

## 🪟 Setup — Windows 11

```powershell
# 1. Open PowerShell and navigate to the project folder
cd C:\path\to\meetandgreet

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the virtual environment
.venv\Scripts\Activate.ps1

# If you get an execution policy error, run this first (once):
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 4. Install dependencies
pip install -r requirements.txt

# 5. Verify setup
python -c "import reportlab, pypdfium2, PIL; print('All dependencies ready')"
```

> **To deactivate** when done: `deactivate`

---

## 🚀 Generating Badges

Once the venv is active, simply run:

```bash
# macOS / Linux
python3 generate_badges.py

# Windows
python generate_badges.py
```

The script will:
1. Read and deduplicate `registrants.csv`
2. Auto-detect each registrant's school from their `Class / Major` field
3. Assign the appropriate circle color
4. Generate `2026_MeetGreet_NameTags.pdf` — 6 badges per page

**Expected output:**
```
Loaded 171 unique registrants
✓ Generated 29 pages for 171 badges → 2026_MeetGreet_NameTags.pdf
```

---

## 🔄 Runbook — Adding New Registrants Before the Event

New people will register between now and **March 25, 2026**. Follow these steps each time you want to refresh the badge PDF:

### Step 1 — Export the latest registrant data

1. Open the Google Sheet: [WCSU Meet & Greet 2026 Registration](YOUR_GOOGLE_SHEET_URL)
2. Go to **File → Download → Comma-separated values (.csv)**
3. Save/replace `registrants.csv` in this project folder

### Step 2 — Activate the virtual environment

```bash
# macOS
source .venv/bin/activate

# Windows
.venv\Scripts\Activate.ps1
```

### Step 3 — Run the generator

```bash
python3 generate_badges.py   # macOS
python generate_badges.py    # Windows
```

### Step 4 — Print

1. Open `2026_MeetGreet_NameTags.pdf`
2. Print on **letter-size cardstock** (8.5" × 11")
3. Cut along the grid lines — 6 badges per sheet

> ⚠️ **Always regenerate from the latest CSV export** — the script replaces the full PDF each run, so old badges are never left in.

---

## 🏫 School Detection Logic

The script keyword-matches the `Class / Major` and `Community Business/Organization` CSV fields to assign a school. The matching priority is:

1. **Exact org match** — if `"Ancell"` appears in the org field → Ancell
2. **Visual & Performing Arts** — graphic design, theater, DIMA, dance, music, film…
3. **Professional Studies** — education, MHA, health administration, counseling…
4. **Ancell School of Business** — accounting, finance, management, MBA, BBA, MIS…
5. **School of Arts & Sciences** — biology, psychology, history, nursing, BSN, cybersecurity…
6. **Faculty/Staff** — any Faculty/Staff registrant not matched to a specific school
7. **Community Guest** — any Community registrant
8. **Default (gray)** — if no keyword matches (ambiguous major like `"BA"` or `"2019"`)

### 🛠 Fixing an Unmatched Badge

If a registrant's circle is gray but you know their school, update their `Class / Major` in the CSV:

| Scenario | Fix |
|---|---|
| Major entered as just `"BA"` | Change to `"BA English"` or specific field |
| Only a graduation year entered (e.g. `"2019"`) | Add the major: `"2019 / Nursing"` |
| Typo like `"buisness"` | Correct to `"Business"` |
| Medical secretary / healthcare | Change to `"Health Sciences"` |

Then re-run the generator — no other changes needed.

---

## 🖨 Print Tips

- Use **cardstock** (65–80 lb) for sturdiness
- Print at **100% scale** — do not "fit to page"
- Each badge is **3" × 2.2"** when cut from letter paper (6-up layout)
- The template includes **cut lines** (thin grid borders on each page)

---

## 🤖 Regenerating with Claude / AI

This project was originally built using [Claude in Cowork mode](https://claude.ai). The `CLAUDE.md` file provides full project context so Claude can pick up where it left off — including updating the script, adjusting colors, fixing school mappings, or regenerating from a fresh CSV.

To resume work with Claude, simply open this project folder in Cowork and reference `CLAUDE.md`.
