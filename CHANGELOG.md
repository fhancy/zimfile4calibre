# Changelog

## 0.1.9

- Hide Windows console flashes from `ebook-convert` (`CREATE_NO_WINDOW`)
- HTML→EPUB uses built-in zip (faster; no console); PDF still uses Calibre convert
- Progress bar inside the import dialog (no oversized progress window)
- Larger ZIM cluster cache (32)

## 0.1.8

- Recognize modern Gutenberg OpenZIM layout (namespace `C/`, URLs `Title.ID` without `.html`)
- Keep legacy `A/*.html` + `I/*.epub` support
- Clearer empty-catalog message

## 0.1.7

- Support OpenZIM major versions 5 and 6
- Plugin author set to `fhancy`
- Clear message when a ZIM opens but is not a Gutenberg collection
- Default “EPUB only” filter off; status shows HTML-only count
- Transparent toolbar icon

## 0.1.6

- HTML→EPUB/PDF output format combo for books without native ebook files
- Format availability columns (EPUB / PDF / HTML)
- Checkbox selection fix for Calibre 9 / Qt6 (int CheckState)

## 0.1.5–0.1.3

- Qt6 enum compatibility (`qt_compat`) for Calibre 9
- Toolbar action genesis fix (`load_resources` instead of removed `get_icons`)
- Import dialog: catalog load, multi-select, extract + `add_books`

## 0.1.0

- Initial Calibre Interface Action plugin scaffold
