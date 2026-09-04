# ZIM Import for Calibre

Import **selected books** from a Gutenberg OpenZIM archive into Calibre. A `.zim` file is a collection, not a single ebook: the plugin lists titles from the directory, then extracts only the EPUB/PDF files you choose.

## Confirmed source

Development target: `E:\Downloads\gutenberg_en_all_2021-12.zim`

- OpenZIM **v5** (namespaces `A` / `I` / `-`)
- About **56 000** distinct Gutenberg books (HTML catalog pages, covers excluded)
- About **49 000** EPUB/PDF/MOBI files in namespace `I`
- Import is **selective** (dialog), not “add the 64 GB ZIM as one book”

## CLI (Python 3.11+)

From this directory:

```text
python -m zim_import.list_titles "E:\Downloads\gutenberg_en_all_2021-12.zim" --limit 20
python -m zim_import.list_titles "E:\Downloads\gutenberg_en_all_2021-12.zim" -o titles.csv
python -m zim_import.list_formats "E:\Downloads\gutenberg_en_all_2021-12.zim" --limit 20
python -m zim_import.extract_books "E:\Downloads\gutenberg_en_all_2021-12.zim" -o extracted --limit 5
```

`list_titles` and `list_formats` only read the ZIM catalog (tens of seconds). They do not decompress book content.

## Calibre plugin

Requires Calibre 6+ (tested against Calibre 8.3).

```text
python scripts/build_plugin.py
calibre-customize -a dist/ZIM_Import.zip
```

Or, from this folder: `calibre-customize -b .`

Then add **Import ZIM** to the toolbar: Preferences → Toolbars & menus → Main toolbar.

Default filter is **EPUB only**. Selected files are extracted to a temp folder and added with `db.add_books()`, tagged `ZIM` / `Gutenberg`, identifier `gutenberg:<id>`. Duplicates are skipped.

## Tests

```text
python -m unittest discover -s tests -v
```
