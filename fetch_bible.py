#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_bible.py — Downloads chapters from BibleGateway in parallel (asyncio + aiohttp)
and saves them as structured JSON.

v 1.4.2 (17-Apr-2025)
=====================
* --book is optional ⇒ omitted = Full Bible (66 books)
* Complete BOOK_INFO (alias→code+order) and CHAPS (chapters per book)
* Creates directories before downloading; clear error if no permissions
* Default concurrency 10 with progress bar per book
"""

import argparse
import asyncio
import html
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import aiohttp
from bs4 import BeautifulSoup, element
from tqdm.asyncio import tqdm

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Sion-AI/1.4.2)",
    "Accept-Charset": "utf-8"
}

# ---------------------------------------------------------------------------
# Table: any name → (folder code, canonical order)
# ---------------------------------------------------------------------------
BOOK_INFO: Dict[str, Tuple[str, int]] = {}
_names_orders = [
    # (order, code, aliases …)
    (1,  "gen", ["genesis", "génesis", "gen"]),
    (2,  "exo", ["exodus", "éxodo", "exo"]),
    (3,  "lev", ["leviticus", "levítico", "lev"]),
    (4,  "num", ["numbers", "números", "num"]),
    (5,  "deu", ["deuteronomy", "deuteronomio", "deu"]),
    (6,  "jos", ["joshua", "josué", "jos"]),
    (7,  "jdg", ["judges", "jueces", "jdg"]),
    (8,  "rut", ["ruth", "rut"]),
    (9,  "1sa", ["1 samuel", "first samuel", "1sa"]),
    (10, "2sa", ["2 samuel", "second samuel", "2sa"]),
    (11, "1ki", ["1 kings", "1 reyes", "1ki"]),
    (12, "2ki", ["2 kings", "2 reyes", "2ki"]),
    (13, "1ch", ["1 chronicles", "1 cronicas", "1 crónicas", "1ch"]),
    (14, "2ch", ["2 chronicles", "2 cronicas", "2 crónicas", "2ch"]),
    (15, "ezr", ["ezra", "esdras", "ezr"]),
    (16, "neh", ["nehemiah", "nehemias", "nehemías", "neh"]),
    (17, "est", ["esther", "ester", "est"]),
    (18, "job", ["job"]),
    (19, "psa", ["psalms", "salmos", "psa"]),
    (20, "pro", ["proverbs", "proverbios", "pro"]),
    (21, "ecc", ["ecclesiastes", "eclesiastes", "eclesiastés", "ecc"]),
    (22, "sng", ["song of solomon", "song of songs", "cantares", "cantar de los cantares", "sng"]),
    (23, "isa", ["isaiah", "isaias", "isaías", "isa"]),
    (24, "jer", ["jeremiah", "jeremias", "jeremías", "jer"]),
    (25, "lam", ["lamentations", "lamentaciones", "lam"]),
    (26, "ezk", ["ezekiel", "ezequiel", "ezk"]),
    (27, "dan", ["daniel", "dan"]),
    (28, "hos", ["hosea", "oseas", "hos"]),
    (29, "jol", ["joel", "jol"]),
    (30, "amo", ["amos", "amós", "amo"]),
    (31, "oba", ["obadiah", "abdias", "abdías", "oba"]),
    (32, "jon", ["jonah", "jonas", "jonás", "jon"]),
    (33, "mic", ["micah", "miqueas", "mic"]),
    (34, "nam", ["nahum", "nam"]),
    (35, "hab", ["habakkuk", "habacuc", "hab"]),
    (36, "zep", ["zephaniah", "sofonias", "sofonías", "zep"]),
    (37, "hag", ["haggai", "hageo", "hag"]),
    (38, "zec", ["zechariah", "zacarias", "zacarías", "zec"]),
    (39, "mal", ["malachi", "malaquias", "malaquías", "mal"]),
    (40, "mat", ["matthew", "mateo", "mat"]),
    (41, "mrk", ["mark", "marcos", "mrk"]),
    (42, "luk", ["luke", "lucas", "luk"]),
    (43, "jhn", ["john", "juan", "jhn"]),
    (44, "act", ["acts", "hechos", "act"]),
    (45, "rom", ["romans", "romanos", "rom"]),
    (46, "1co", ["1 corinthians", "1 corintios", "1co"]),
    (47, "2co", ["2 corinthians", "2 corintios", "2co"]),
    (48, "gal", ["galatians", "galatas", "gálatas", "gal"]),
    (49, "eph", ["ephesians", "efesios", "eph"]),
    (50, "php", ["philippians", "filipenses", "php"]),
    (51, "col", ["colossians", "colosenses", "col"]),
    (52, "1th", ["1 thessalonians", "1 tesalonicenses", "1th"]),
    (53, "2th", ["2 thessalonians", "2 tesalonicenses", "2th"]),
    (54, "1ti", ["1 timothy", "1 timoteo", "1ti"]),
    (55, "2ti", ["2 timothy", "2 timoteo", "2ti"]),
    (56, "tit", ["titus", "tito", "tit"]),
    (57, "phm", ["philemon", "filemon", "filemón", "phm"]),
    (58, "heb", ["hebrews", "hebreos", "heb"]),
    (59, "jas", ["james", "santiago", "jas"]),
    (60, "1pe", ["1 peter", "1 pedro", "1pe"]),
    (61, "2pe", ["2 peter", "2 pedro", "2pe"]),
    (62, "1jn", ["1 john", "1 juan", "1jn"]),
    (63, "2jn", ["2 john", "2 juan", "2jn"]),
    (64, "3jn", ["3 john", "3 juan", "3jn"]),
    (65, "jud", ["jude", "judas", "jud"]),
    (66, "rev", ["revelation", "apocalipsis", "revelacion", "revelación", "rev"]),
]
for order, code, names in _names_orders:
    for n in names:
        BOOK_INFO[n] = (code, order)

# Chapters per book
CHAPS = {
    "gen": 50, "exo": 40, "lev": 27, "num": 36, "deu": 34,
    "jos": 24, "jdg": 21, "rut": 4,  "1sa": 31, "2sa": 24, "1ki": 22, "2ki": 25,
    "1ch": 29, "2ch": 36, "ezr": 10, "neh": 13, "est": 10, "job": 42, "psa": 150,
    "pro": 31, "ecc": 12, "sng": 8,  "isa": 66, "jer": 52, "lam": 5,  "ezk": 48,
    "dan": 12, "hos": 14, "jol": 3,  "amo": 9,  "oba": 1,  "jon": 4,  "mic": 7,
    "nam": 3,  "hab": 3,  "zep": 3,  "hag": 2,  "zec": 14, "mal": 4,
    "mat": 28, "mrk": 16, "luk": 24, "jhn": 21, "act": 28, "rom": 16,
    "1co": 16, "2co": 13, "gal": 6,  "eph": 6,  "php": 4,  "col": 4,
    "1th": 5,  "2th": 3,  "1ti": 6,  "2ti": 4,  "tit": 3,  "phm": 1,
    "heb": 13, "jas": 5,  "1pe": 5,  "2pe": 3,  "1jn": 5,  "2jn": 1, "3jn": 1,
    "jud": 1,  "rev": 22,
}

# ---------------------------------------------------------------------------


async def fetch_html(session: aiohttp.ClientSession, url: str) -> str:
    # Fetches the HTML content of a given URL.
    async with session.get(url, headers=HEADERS, timeout=30) as r:
        r.raise_for_status()
        return await r.text(encoding='utf-8')


def parse_chapter_html(html_text: str, book_code: str, version: str, chapter: int) -> dict:
    # Parses the HTML content of a Bible chapter to extract verses.
    soup = BeautifulSoup(html_text, "html.parser", from_encoding='utf-8')
    container = soup.find("div", class_=re.compile(r"^passage-content"))
    if container is None:
        # If BibleGateway returns 404 or an empty div → chapter does not exist
        raise ValueError("passage-content not found")

    # --- Pre-processing: Remove unwanted elements --- 
    for element_to_remove in container.find_all(["sup", "div", "h3"], 
                                               class_=["footnote", "footnotes", "crossreference", "crossrefs"]):
        element_to_remove.decompose() # Remove footnotes, cross-references, etc.
    for h3 in container.find_all("h3"):
         # Ensure all H3 titles are removed, even if they lack a class
         h3.decompose()

    verses_data = {} # Dictionary: verse_num -> [list of text/format parts]
    current_verse_num = None
    ignore_next_text_node_if_matches_num = False # Flag to ignore the number text right after finding it

    # Iterate over all descendant nodes in order
    for node in container.descendants:
        if isinstance(node, element.Tag):
            # --- Identify start of verse --- 
            verse_marker_found = False
            extracted_num = None

            if node.name == 'sup' and 'versenum' in node.get('class', []):
                # Standard verse number marker
                extracted_num = node.get_text(strip=True)
                verse_marker_found = True
            # Capture the chapter number as verse 1
            elif node.name == 'span' and 'chapternum' in node.get('class', []):
                 # Verse 1 often uses chapternum
                 extracted_num = node.get_text(strip=True)
                 if extracted_num.isdigit(): # Make sure it's the chapter number
                     extracted_num = "1" # Assign as verse 1
                     verse_marker_found = True
                 
            if verse_marker_found and extracted_num and extracted_num.isdigit():
                # Found a new verse number
                current_verse_num = extracted_num
                if current_verse_num not in verses_data:
                    verses_data[current_verse_num] = []
                ignore_next_text_node_if_matches_num = True # Set flag
                # The number itself is not added to the text.
                continue # Skip to the next node
                
            # --- Handle line breaks --- 
            if node.name == 'br' and current_verse_num:
                # Only add newline if the last element wasn't already one
                if not verses_data[current_verse_num] or verses_data[current_verse_num][-1] != "\n":
                    verses_data[current_verse_num].append("\n")
                ignore_next_text_node_if_matches_num = False # Any content after <br> is not the number 
                
            # Ignore empty spans or containers that don't directly add text here
            if node.name == 'span' and not node.get_text(strip=True):
                 ignore_next_text_node_if_matches_num = False # Reset flag if span is empty
                 continue

        elif isinstance(node, element.NavigableString):
            # --- Add text to the current verse --- 
            text_part = str(node)
            
            if current_verse_num:
                 # Ignore if it's the number text we just found
                if ignore_next_text_node_if_matches_num and text_part.strip() == current_verse_num:
                    ignore_next_text_node_if_matches_num = False # Deactivate flag
                    continue # Skip this text
                
                 # Add the text (preserving original spaces)
                verses_data[current_verse_num].append(text_part)
                # If we added real text, the next text node can't be the number
                if text_part.strip(): 
                    ignore_next_text_node_if_matches_num = False 

    # --- Format output --- 
    verses = []
    # Ensure all verse numbers exist up to the maximum found
    if verses_data:
        max_verse = max(map(int, verses_data.keys()))
        for i in range(1, max_verse + 1):
            num_str = str(i)
            verse_content = verses_data.get(num_str, [])
            
            # Join parts preserving format
            raw_text = html.unescape("".join(verse_content))
            
            # Create readable text: replace newlines/tabs with space, normalize spaces
            readable_text = raw_text.replace('\n', ' ').replace('\t', ' ')
            readable_text_normalized = " ".join(readable_text.split()).strip()
            
            verses.append({
                "verse": num_str,
                "text": raw_text.strip(), # Remove leading/trailing whitespace from the full text
                "readableText": readable_text_normalized
            })
    else: # If no verses were found
        pass # Or handle the case of an empty/error chapter

    return {
        "book": book_code.upper(), # Convert book code to uppercase
        "rev": version,
        "chapter": str(chapter),
        "verses": verses,
    }


def parse_range(arg: str, max_chaps: int) -> List[int]:
    # Converts 'all' or '1-5,8,10' into a list of ints respecting the maximum.
    if arg.lower() == "all":
        return list(range(1, max_chaps + 1))

    out: List[int] = []
    for part in arg.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try: # Add error handling for invalid ranges
                a, b = map(int, part.split("-"))
                if a <= b:
                     out.extend(range(a, b + 1))
                else:
                     print(f"Warning: Invalid range '{part}', skipping.", file=sys.stderr) # Warn about invalid range
            except ValueError:
                 print(f"Warning: Invalid range format '{part}', skipping.", file=sys.stderr) # Warn about format error
        else:
            try: # Add error handling for invalid numbers
                out.append(int(part))
            except ValueError:
                 print(f"Warning: Invalid chapter number '{part}', skipping.", file=sys.stderr) # Warn about non-integer

    # Filter out chapters exceeding the book's maximum
    return [n for n in out if 1 <= n <= max_chaps]


async def grab(
    sem: asyncio.Semaphore,
    session: aiohttp.ClientSession,
    version: str,
    book_name: str, # Use the formatted book name for the URL
    book_code: str,
    chap: int,
    out_dir: Path,
):
    # Fetches and parses a single chapter, saving it to a JSON file.
    # Use the user-provided (capitalized) book name for the URL for better compatibility
    url = f"https://www.biblegateway.com/passage/?search={book_name}%20{chap}&version={version}"
    async with sem:
        try:
            html_text = await fetch_html(session, url)
            data = parse_chapter_html(html_text, book_code, version, chap)
            if not data["verses"]: # Check if parsing resulted in empty verses
                print(f"Warning: No verses found for {book_name} {chap} ({version}). Skipping file save.", file=sys.stderr)
                return None
        except ValueError as e: # Catch specific parsing errors
             print(f"Error parsing {book_name} {chap} ({version}): {e}. Skipping.", file=sys.stderr)
             return None
        except aiohttp.ClientResponseError as e: # Catch HTTP errors
             print(f"HTTP Error fetching {book_name} {chap} ({version}): {e.status} {e.message}. Skipping.", file=sys.stderr)
             return None
        except asyncio.TimeoutError: # Catch timeouts
             print(f"Timeout fetching {book_name} {chap} ({version}). Skipping.", file=sys.stderr)
             return None
        except Exception as e: # Catch other potential errors during fetch/parse
            # Non-existent chapter or network error -> does not interrupt the rest
            print(f"Error processing {book_name} {chap} ({version}): {e}. Skipping.", file=sys.stderr)
            return None

    # Create directory and save file only if data was successfully parsed
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{book_code}.{chap:03}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    return chap # Return chapter number on success


async def download_book(
    version: str,
    book_name: str, # User input, potentially needs normalization for URL? No, use normalized `pretty_book_name`
    book_code: str,
    order: int,
    chapters: str,
    dest_root: Path,
    concurrency: int,
):
    # Downloads all specified chapters for a given book.
    max_chaps = CHAPS.get(book_code) # Use .get for safety
    if max_chaps is None:
        print(f"Error: Chapter count not found for book code '{book_code}'. Skipping book.", file=sys.stderr)
        return

    chapter_list = parse_range(chapters, max_chaps)
    if not chapter_list:
        print(f"No valid chapters specified for {book_name}. Skipping book.", file=sys.stderr)
        return

    # Use normalized book name (first alias, capitalized) for display/directory, but potentially keep original `book_name` for URL?
    # Let's stick to the capitalized first alias for consistency.
    pretty_book_name = next(alias for alias, (code, _) in BOOK_INFO.items() if code == book_code).title() # Get canonical name

    prefix = f"{order:02d}_{book_code}" # Use order for consistent dir naming
    out_dir = dest_root / version.upper() / prefix

    # Try creating the output directory early to fail fast on permission errors
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        print(f"🚫 Permission denied creating directory {out_dir}: {e}. Skipping book '{pretty_book_name}'.", file=sys.stderr)
        return
    except OSError as e:
        print(f"🚫 OS Error creating directory {out_dir}: {e}. Skipping book '{pretty_book_name}'.", file=sys.stderr)
        return


    sem = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as session:
        tasks = [
            # Pass pretty_book_name for the URL? Let's test with this first.
            grab(sem, session, version.upper(), pretty_book_name, book_code, c, out_dir) 
            for c in chapter_list
        ]
        
        # Use tqdm for progress bar
        successful_downloads = 0
        print(f"Downloading {pretty_book_name} ({version.upper()})...")
        with tqdm(total=len(tasks), desc=pretty_book_name, unit="chap") as pbar:
            for future in asyncio.as_completed(tasks):
                result = await future
                if result is not None: # Check if grab returned a chapter number (success)
                    successful_downloads += 1
                pbar.update(1)
        
        print(f"Finished {pretty_book_name}: {successful_downloads}/{len(tasks)} chapters downloaded successfully.")


def normalise_book(user_input: str) -> Tuple[str, str, int]:
    # Normalizes user book input to get canonical code and order.
    key = user_input.lower().strip()
    if key not in BOOK_INFO:
        # Consider suggesting alternatives or listing known books on error?
        raise SystemExit(f"⚠️ Book '{user_input}' not recognized.")
    code, order = BOOK_INFO[key]
    # Return the capitalized version of the first alias for consistency
    pretty_name = next(alias for alias, (c, o) in BOOK_INFO.items() if c == code and o == order).title()
    return pretty_name, code, order


async def main():
    # ----------------- CLI Setup -----------------
    parser = argparse.ArgumentParser(description="Download Bible chapters from BibleGateway in parallel.")
    parser.add_argument("--version", required=True, help="Bible version code (e.g., PDT, NTV, RVR1960). Case-insensitive for directory, but used as-is for URL.")
    parser.add_argument("--book", help="Book name (e.g., Genesis, Psalms). Omit to download the entire Bible (all 66 books).")
    parser.add_argument("--chapters", default="all", help="Chapter range (e.g., '1-5,8,10' or 'all'). Default is 'all'.")
    parser.add_argument("--dest", default="./data", help="Root directory for downloads (default: ./data).")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of simultaneous downloads (default: 10).")
    args = parser.parse_args()

    dest_root = Path(args.dest).expanduser().resolve()
    # Attempt to create the root destination directory early
    try:
        dest_root.mkdir(exist_ok=True, parents=True)
    except PermissionError as e:
        raise SystemExit(f"🚫 Permission denied to create root destination directory {dest_root}: {e}") from e
    except OSError as e:
        raise SystemExit(f"🚫 OS Error creating root destination directory {dest_root}: {e}") from e

    version_code = args.version.upper() # Use uppercase for directory structure consistency

    if args.book:
        # Single book download
        try:
            pretty_book_name, book_code, order = normalise_book(args.book)
            await download_book(version_code, pretty_book_name, book_code, order, args.chapters, dest_root, args.concurrency)
        except SystemExit as e: # Catch normalization errors
            print(e, file=sys.stderr)
            sys.exit(1) # Exit if book name is invalid
    else:
        # Full Bible download
        print(f"📖 Downloading full Bible ({version_code})...")
        # Use _names_orders to ensure canonical book order
        for order, book_code, aliases in _names_orders: 
            # Use the first alias, capitalized, as the standard name
            pretty_book_name = aliases[0].title() 
            # Order is already available from the loop
            await download_book(version_code, pretty_book_name, book_code, order, "all", dest_root, args.concurrency)

    print("✅ Download finished.")


if __name__ == "__main__":
    # Ensure graceful shutdown on Ctrl+C
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Download interrupted by user.", file=sys.stderr)
        sys.exit(1)
