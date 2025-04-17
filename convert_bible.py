#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Converts ALL Bible versions found under a repository
(structured like parsedBible/NTV/, parsedBible/PDT/, parsedBible/RVR60/, etc.)
to the FreeShow format (.fsb.json).

Quick Usage:
    # Convert all versions found in /path/to/parsedBible to default ./exports dir
    python convert_bible.py /path/to/parsedBible
    # Convert only NTV and PDT found in /path/to/parsedBible to specific dir
    python convert_bible.py --versions NTV PDT --outdir /output/dir /path/to/parsedBible

This will create, for example:
    exports/NTV.fsb.json
    exports/PDT.fsb.json
    # But not RVR60.fsb.json if it wasn't specified with --versions
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Dict, List

# -------- Config: Map of abbreviations to English book names -------- #
# (Keeping original Spanish names for now, as changing them might break things
# if the input JSON relies on these exact names. Translation can be done later if needed.)
BOOKS = {
    "gen": "Genesis",  "exo": "Exodus",  "lev": "Leviticus", "num": "Numbers",
    "deu": "Deuteronomy", "jos": "Joshua", "jdg": "Judges",  "rut": "Ruth",
    "1sa": "1 Samuel",  "2sa": "2 Samuel",  "1ki": "1 Kings",  "2ki": "2 Kings",
    "1ch": "1 Chronicles", "2ch": "2 Chronicles", "ezr": "Ezra",  "neh": "Nehemiah",
    "est": "Esther",  "job": "Job",  "psa": "Psalms",  "pro": "Proverbs",
    "ecc": "Ecclesiastes", "sng": "Song of Solomon", "isa": "Isaiah",
    "jer": "Jeremiah", "lam": "Lamentations", "ezk": "Ezekiel", "dan": "Daniel",
    "hos": "Hosea",  "jol": "Joel",  "amo": "Amos",  "oba": "Obadiah",
    "jon": "Jonah",  "mic": "Micah", "nam": "Nahum", "hab": "Habakkuk",
    "zep": "Zephaniah", "hag": "Haggai", "zec": "Zechariah", "mal": "Malachi",
    "mat": "Matthew", "mrk": "Mark", "luk": "Luke", "jhn": "John",
    "act": "Acts",  "rom": "Romans", "1co": "1 Corinthians", "2co": "2 Corinthians",
    "gal": "Galatians", "eph": "Ephesians", "php": "Philippians", "col": "Colossians",
    "1th": "1 Thessalonians", "2th": "2 Thessalonians", "1ti": "1 Timothy",
    "2ti": "2 Timothy", "tit": "Titus", "phm": "Philemon", "heb": "Hebrews",
    "jas": "James", "1pe": "1 Peter", "2pe": "2 Peter", "1jn": "1 John",
    "2jn": "2 John", "3jn": "3 John", "jud": "Jude", "rev": "Revelation",
}

# -------- Utility Functions -------- #
def clean_text(raw: str) -> str:
    """Unescapes HTML entities and removes extra whitespace."""
    return html.unescape(raw.strip())

def parse_version(version_dir: Path) -> Dict:
    """Processes a version directory (NTV/, PDT/, etc.) and returns the final JSON structure."""
    rev = version_dir.name.upper()
    bible = {
        "name": f"Bible {rev}", # Consider making the name dynamic or configurable?
        "metadata": {"source": "parsedBible repo", "revision": rev},
        "books": []
    }

    # Iterate through 01_gen, 02_exo, ... 66_rev
    for book_folder in sorted(version_dir.iterdir()):
        if not book_folder.is_dir():
            continue
        m = re.match(r"(\d{2})_([a-z0-9]+)", book_folder.name)
        if not m:
            continue
        order = int(m.group(1))
        abbr = m.group(2)
        book_name = BOOKS.get(abbr, abbr.capitalize()) # Use English name from map
        chapters: List[Dict] = []

        # Files like gen.001.json, gen.002.json...
        for jf in sorted(book_folder.glob(f"{abbr}.*.json")):
            m2 = re.match(rf"{abbr}\.(\d+)\.json", jf.name)
            if not m2:
                continue
            chap_num = int(m2.group(1).lstrip("0") or "0") # Get chapter number

            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                verses = [
                    {
                        "number": int(v["verse"]),
                        # Prioritize readableText if available, fallback to text
                        "text": clean_text(v.get("readableText") or v["text"])
                    }
                    for v in data.get("verses", []) # Use .get for safety
                ]
                if verses: # Only add chapter if it has verses
                    chapters.append({"number": chap_num, "verses": verses})
                else:
                    print(f"Warning: No verses found in {jf}. Skipping chapter.", file=sys.stderr)
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from {jf}. Skipping file.", file=sys.stderr)
            except KeyError as e:
                 print(f"Error: Missing key {e} in {jf}. Skipping file.", file=sys.stderr)

        # Only add book if it has chapters
        if chapters:
            bible["books"].append(
                {"number": order, "name": book_name, "chapters": chapters}
            )
        else:
            print(f"Warning: No valid chapters found for book {book_name} ({abbr}) in {version_dir.name}. Skipping book.", file=sys.stderr)

    bible["books"].sort(key=lambda b: b["number"]) # Ensure books are sorted by order
    return bible

# -------- Main Program -------- #
def main():
    p = argparse.ArgumentParser(
        description="Converts multiple Bible versions to the FreeShow format (.fsb.json)"
    )
    p.add_argument("repo_root", type=Path,
                   help="Path to the root folder (containing NTV/, PDT/, RVR60/)")
    p.add_argument("--outdir", type=Path, default=Path("exports"),
                   help="Output directory (default: ./exports)")
    p.add_argument("--versions", nargs="*",
                   help="Process only these specific versions (e.g., NTV PDT)")
    args = p.parse_args()

    repo_root = args.repo_root.resolve()
    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    # Auto-detect versions (subdirs containing a ##_gen folder pattern)
    try:
        potential_dirs = [d for d in repo_root.iterdir() if d.is_dir()]
        version_dirs = [
            d for d in potential_dirs
            if any(re.match(r"\d{2}_gen", x.name) for x in d.iterdir() if x.is_dir()) # Check subdirs exist and match
        ]
    except OSError as e:
         raise SystemExit(f"❌ Error reading repository root {repo_root}: {e}")

    # If the user specified versions, filter the detected list
    if args.versions:
        wanted = {v.upper() for v in args.versions}
        version_dirs = [d for d in version_dirs if d.name.upper() in wanted]
        # Check if any wanted versions were not found
        found_names = {d.name.upper() for d in version_dirs}
        not_found = wanted - found_names
        if not_found:
            print(f"Warning: Specified versions not found or invalid: {', '.join(sorted(not_found))}", file=sys.stderr)


    if not version_dirs:
        raise SystemExit("❌ No valid Bible versions found to process in the specified directory.")

    print(f"Found {len(version_dirs)} version(s) to process: {', '.join(d.name for d in version_dirs)}")

    processed_count = 0
    for vdir in version_dirs:
        print(f"\nProcessing {vdir.name}...")
        try:
            bible_json = parse_version(vdir)
            if not bible_json.get("books"): # Check if parsing resulted in no books
                 print(f"Warning: No valid book data found for version {vdir.name}. Skipping export.", file=sys.stderr)
                 continue
                 
            outfile = outdir / f"{vdir.name.upper()}.fsb.json"
            outfile.write_text(json.dumps(bible_json, ensure_ascii=False, indent=2),
                               encoding="utf-8")
            print(f"✅ Exported {vdir.name} → {outfile}")
            processed_count += 1
        except Exception as e:
             # Catch any unexpected error during parsing/writing for a specific version
             print(f"❌ Unexpected error processing version {vdir.name}: {e}. Skipping.", file=sys.stderr)
             # Optionally: raise e # or log traceback for debugging

    if processed_count > 0:
        print(f"\n🎉 All {processed_count} Bible version(s) ready for import into FreeShow!")
    else:
         print("\nℹ️ No versions were successfully processed.")

if __name__ == "__main__":
    main()
