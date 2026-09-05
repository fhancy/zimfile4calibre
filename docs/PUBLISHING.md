# MobileRead publication notes

Calibre’s **Get plugins / Check for plugin updates** uses the [MobileRead plugin index](https://www.mobileread.com/forums/showthread.php?t=118764), not GitHub.

## Before posting

1. `python -m unittest discover -s tests -v`
2. `python scripts/build_plugin.py` → `dist/ZIM_Import.zip`
3. Install on a clean Calibre profile: `calibre-customize -a dist/ZIM_Import.zip`
4. Smoke-test: open Import ZIM, load a Gutenberg `.zim`, import 1–2 books
5. Confirm `__init__.py` `version` matches CHANGELOG and ZIP filename stays `ZIM_Import.zip`

## Forum thread (first post)

Suggested title: `[Plugin] ZIM Import - Gutenberg OpenZIM books into Calibre`

Attach **only** `ZIM_Import.zip` to the first post.

Draft body:

```text
ZIM Import
==========

Import selected Project Gutenberg books from an OpenZIM (.zim) archive into Calibre.

Requires: Calibre 6+
Author: fhancy
Main language: English
Version: 0.1.7
History: Yes

A .zim is a collection. This plugin lists titles, then extracts EPUB/PDF (or converts HTML) for the books you select.

Supported: Gutenberg-style OpenZIM v5/v6 (A/ + I/ namespaces).
Not supported: DevDocs, Wikipedia, and other non-Gutenberg ZIMs.

Source: https://github.com/fhancy/zimfile4calibre

Installation
------------
Preferences → Plugins → Load plugin from file → ZIM_Import.zip → restart Calibre
Add "Import ZIM" via Preferences → Toolbars & menus

Version History
---------------
<<SPOILER>>
0.1.7 - ZIM v6 support, author fhancy, clearer non-Gutenberg message
0.1.6 - HTML output format choice, Qt6 checkbox fix, format columns
0.1.0 - Initial release
<</SPOILER>>
```

(Use the forum’s real SPOILER BBCode tags instead of the placeholders above.)

## Index entry (PM to a Calibre moderator)

Adapt the sticky “Index Entry Sample”. Useful fields:

```text
Name: ZIM Import
Donate: 
Plugin Type: Interface Action
Plugin Category: Library Management / Import
Filename: ZIM_Import.zip
Forum Thread: <URL of your thread>
```

Internal plugin name (must match `name` in `__init__.py`): **ZIM Import**  
Import name file: `plugin-import-name-zim_import.txt` → package `zim_import`
