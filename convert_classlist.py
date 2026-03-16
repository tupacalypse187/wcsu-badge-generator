"""
convert_classlist.py — Convert a WCSU class roster xlsx to badge-generator CSV format.

Usage:
    python3 convert_classlist.py <input.xlsx> [options]

Options:
    --output PATH          Output CSV path (default: data/registrants.csv)
    --reg-type TYPE        Registration Options value (default: Student)
    --major MAJOR          Class / Major — controls badge circle color (see below)
    --org ORG              Community Business/Organization (default: blank)
    --title TITLE          Occupation / Position Title (default: blank)

Badge circle color is determined by --major (or the Class/Major column in the xlsx).
If omitted, badges will show a gray circle. Pass the correct major to get the right color:

    School                          Example --major values
    ──────────────────────────────  ──────────────────────────────────────────
    Ancell (Orange)                 Accounting, Finance, Marketing, Management, MIS
    Arts & Sciences (Navy)          Biology, Psychology, Nursing, Computer Science
    Visual & Performing Arts (Purple) Graphic Design, Theatre, Music, Digital Interactive Media
    Professional Studies (Green)    Education, Health Administration, Counseling
    Faculty/Staff (Dark Gold)       Use --reg-type Faculty/Staff instead of --major
    Community (Gray)                Use --reg-type Community instead of --major

Examples:
    # Accounting class — Ancell (orange)
    python3 convert_classlist.py data/ClassListACC306.xlsx --major "Accounting" --output data/acc306_badges.csv

    # Nursing class — Arts & Sciences (navy)
    python3 convert_classlist.py data/ClassListNUR201.xlsx --major "Nursing" --output data/nur201_badges.csv

    # Faculty roster
    python3 convert_classlist.py data/FacultyList.xlsx --reg-type Faculty/Staff --org "School of Arts & Sciences"

Then generate the PDF:
    python3 generate_badges.py --csv data/acc306_badges.csv --output output/ACC306_NameTags.pdf

The xlsx must have columns: Last Name, First Name (in any order, header row required).
Additional columns (Email, etc.) are used if present, otherwise left blank.
"""

import csv
import sys
import argparse
import os

try:
    import openpyxl
except ImportError:
    sys.exit("Missing dependency: pip install openpyxl --break-system-packages")

# ── Column name aliases (case-insensitive) ─────────────────────────────────────
FIRST_NAME_ALIASES = {"first name", "firstname", "first", "given name", "fname"}
LAST_NAME_ALIASES  = {"last name", "lastname", "last", "surname", "lname", "family name"}
EMAIL_ALIASES      = {"email", "e-mail", "email address"}
MAJOR_ALIASES      = {"major", "class", "class / major", "program", "degree"}
TITLE_ALIASES      = {"title", "occupation", "position", "job title", "occupation / position title"}
ORG_ALIASES        = {"organization", "org", "company", "business", "department",
                      "community business/organization"}


def find_col(headers, aliases):
    """Return 0-based column index matching any alias, or None."""
    lower = [h.lower().strip() if h else "" for h in headers]
    for alias in aliases:
        if alias in lower:
            return lower.index(alias)
    return None

def convert(input_path, output_path, reg_type, major, org, title):
    wb = openpyxl.load_workbook(input_path)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        sys.exit("Error: xlsx file is empty.")

    headers = rows[0]
    data    = rows[1:]

    # Locate columns
    col_first = find_col(headers, FIRST_NAME_ALIASES)
    col_last  = find_col(headers, LAST_NAME_ALIASES)
    col_email = find_col(headers, EMAIL_ALIASES)
    col_major = find_col(headers, MAJOR_ALIASES)
    col_title = find_col(headers, TITLE_ALIASES)
    col_org   = find_col(headers, ORG_ALIASES)

    if col_first is None or col_last is None:
        sys.exit(
            f"Error: could not find First Name / Last Name columns.\n"
            f"Found headers: {list(headers)}"
        )

    out_headers = [
        "Registration Options",
        "Attendee (First Name)",
        "Attendee (Last Name)",
        "Class / Major",
        "Community Business/Organization",
        "Occupation / Position Title",
        "Email",
    ]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    written = 0
    skipped = 0
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=out_headers)
        writer.writeheader()
        for row in data:
            first = (row[col_first] or "").strip() if col_first is not None else ""
            last  = (row[col_last]  or "").strip() if col_last  is not None else ""
            if not first and not last:
                skipped += 1
                continue
            writer.writerow({
                "Registration Options":             reg_type,
                "Attendee (First Name)":            first,
                "Attendee (Last Name)":             last,
                "Class / Major":                    (row[col_major] or major).strip() if col_major is not None else major,
                "Community Business/Organization":  (row[col_org]   or org).strip()   if col_org   is not None else org,
                "Occupation / Position Title":      (row[col_title] or title).strip() if col_title is not None else title,
                "Email":                            (row[col_email] or "").strip()    if col_email is not None else "",
            })
            written += 1

    print(f"✓ Converted {written} students → {output_path}")
    if skipped:
        print(f"  (skipped {skipped} blank rows)")

def main():
    parser = argparse.ArgumentParser(
        description="Convert a WCSU class roster xlsx to badge-generator CSV format."
    )
    parser.add_argument("input",      help="Path to input xlsx file")
    parser.add_argument("--output",   default="data/registrants.csv",
                        help="Output CSV path (default: data/registrants.csv)")
    parser.add_argument("--reg-type", default="Student",
                        help="Registration Options value (default: Student)")
    parser.add_argument("--major",    default="",
                        help="Class / Major — controls badge circle color (default: blank → gray circle)")
    parser.add_argument("--org",      default="",
                        help="Community Business/Organization (default: blank)")
    parser.add_argument("--title",    default="",
                        help="Occupation / Position Title (default: blank)")
    args = parser.parse_args()

    major = args.major
    if not major:
        print("⚠️  No --major specified — badge circles will be gray.")
        print("   Pass --major to assign a school color. See --help for options.")

    convert(
        input_path  = args.input,
        output_path = args.output,
        reg_type    = args.reg_type,
        major       = major,
        org         = args.org,
        title       = args.title,
    )

if __name__ == "__main__":
    main()
