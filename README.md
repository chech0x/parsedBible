# Bible Data Tools

This repository contains tools to download and process Bible chapter data.

## 1. Downloading Chapters (`fetch_bible.py`)

This script downloads Bible chapters from BibleGateway concurrently and saves them as structured JSON files.

### Requirements

- Python 3.7+
- `aiohttp`
- `beautifulsoup4`
- `tqdm`

Install dependencies:
```bash
pip install -r requirements.txt 
```
_(Note: The requirements file seems named `requirenments.txt`, consider renaming it to `requirements.txt`)_

### Usage

```bash
python fetch_bible.py --version <VERSION_CODE> [--book <BOOK_NAME>] [--chapters <RANGE>] [--dest <DIR>] [--concurrency <N>]
```

**Arguments:**

*   `--version VERSION_CODE`: **Required**. The Bible version code (e.g., `PDT`, `NTV`, `RVR1960`). Used for the download URL and directory naming.
*   `--book BOOK_NAME`: Optional. The name of the book to download (e.g., "Genesis", "Psalms", "Apocalipsis"). If omitted, the script will download all 66 books of the Bible.
*   `--chapters RANGE`: Optional. Specifies the chapters to download. Can be a single number, a comma-separated list (`1,3,5`), a range (`1-5`), or a combination (`1-5,8,10`). Default is `all`.
*   `--dest DIR`: Optional. The root directory where the downloaded files will be saved. Defaults to `./data`. Files will be organized as `<DIR>/<VERSION>/<ORDER_CODE>/<CODE>.<CHAP>.json` (e.g., `./data/PDT/01_gen/gen.001.json`).
*   `--concurrency N`: Optional. The number of chapters to download simultaneously. Defaults to `10`.

**Examples:**

*   Download the entire PDT version:
    ```bash
    python fetch_bible.py --version PDT
    ```
*   Download only Genesis chapter 1 from NTV version into the `downloads` directory:
    ```bash
    python fetch_bible.py --version NTV --book Genesis --chapters 1 --dest ./downloads
    ```
*   Download Psalms chapters 1 to 5 and chapter 23 from RVR1960:
    ```bash
    python fetch_bible.py --version RVR1960 --book Salmos --chapters 1-5,23 
    ```

## 2. Converting JSON to FreeShow Format (`convert_bible.py`)

This script reads the downloaded JSON chapter files for specified Bible versions and converts them into the FreeShow Bible format (`.fsb.json`) containing structured Bible data ready for import.

### Usage

```bash
python convert_bible.py <repo_root> [--versions <VERSION_CODE> [<VERSION_CODE> ...]] [--outdir <DIR>]
```

**Arguments:**

*   `<repo_root>`: **Required**. The path to the root directory containing the version folders (e.g., `./data`). Put this argument first when using `--versions` (because `--versions` accepts multiple values).
*   `--versions VERSION_CODE [VERSION_CODE ...]`: Optional. If specified, only process these exact version codes (case-insensitive). 
*   `--outdir DIR`: Optional. The output directory for the `.fsb.json` files. Defaults to `./exports`.

**Example:**

*   Convert only PDT and NTV versions found within the `./data` directory:
    ```bash
    python convert_bible.py ./data --versions PDT NTV
    ```
*   Convert only RVR60 found within `./my_bible_downloads` and output to `./generated`:
    ```bash
    python convert_bible.py ./my_bible_downloads --versions RVR60 --outdir ./generated
    ```

The resulting `.fsb.json` files will be placed in the specified output directory (defaulting to `./exports`), ready for import into FreeShow.
