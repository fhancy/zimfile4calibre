# ZIM Import for Calibre

Calibre plugin to import **selected books** from a **Project Gutenberg OpenZIM** (`.zim`) archive into your library.

A `.zim` is a **collection**, not one ebook: the plugin lists titles from the archive directory, then extracts only the books you choose.

**Author:** fhancy  
**Version:** 0.1.7  
**Requires:** Calibre 6+  
**Source:** https://github.com/fhancy/zimfile4calibre

## What works

| | |
|---|---|
| Target content | Gutenberg OpenZIM (HTML catalog in `A/`, ebooks in `I/`) |
| ZIM versions | OpenZIM **v5** and **v6** |
| Formats | Native EPUB/PDF; HTML-only books → EPUB or PDF (user choice) |
| UI | Toolbar action **Import ZIM**: browse, search, multi-select, import |
| Metadata | Tags `ZIM` / `Gutenberg`, id `gutenberg:<id>`; duplicates skipped |

Validated against `gutenberg_en_all_2021-12.zim` (~56 000 titles).

## What does not work (yet)

- **DevDocs**, Wikipedia, Stack Exchange, and other non-Gutenberg ZIMs (different layout)
- Treating the whole `.zim` as a single Calibre book
- Per-row output format (HTML conversion format is global for the import)

## Install (users)

1. Download `ZIM_Import.zip` from a [release](https://github.com/fhancy/zimfile4calibre/releases) or build it (below).
2. In Calibre: **Preferences → Plugins → Load plugin from file** → select the ZIP.
3. Restart Calibre.
4. Add **Import ZIM** to the toolbar: **Preferences → Toolbars & menus**.

## Use

1. Click **Import ZIM**.
2. Choose a Gutenberg `.zim` and **Load catalog** (directory scan only; can take ~30 s on large archives).
3. Search / filter; select books (or **Select visible**).
4. If needed, set **When only HTML is available, convert to** EPUB or PDF.
5. **Import selected**.

Columns EPUB / PDF / HTML show **formats present in the ZIM** (not editable). Many Gutenberg books have both EPUB and HTML.

## Build from source

```text
python scripts/build_plugin.py
calibre-customize -a dist/ZIM_Import.zip
```

Or: `calibre-customize -b .` from the repo root.

## CLI (developers)

Python 3.11+ with `zstandard` (see `requirements.txt`):

```text
python -m zim_import.list_titles path\to\file.zim --limit 20
python -m zim_import.extract_books path\to\file.zim -o extracted --limit 5
```

## Tests

```text
python -m unittest discover -s tests -v
```

## License

See repository license / GitHub project page. Plugin intended for personal and community use with legally obtained OpenZIM archives.
