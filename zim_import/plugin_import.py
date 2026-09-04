"""Turn extracted Gutenberg files into Calibre add_books() records."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from .extract import ExtractError, extract_book
from .gutenberg_catalog import GutenbergBook
from .zim_reader import ZimArchive, ZimError

ProgressFn = Callable[[int, int, str], None]


def filter_books_for_import(
    books: Sequence[GutenbergBook],
    *,
    epub_only: bool = True,
    include_pdf: bool = True,
    include_html: bool = False,
) -> list[GutenbergBook]:
    """Apply the Gutenberg/EPUB-first import policy."""
    selected: list[GutenbergBook] = []
    for book in books:
        if book.has_epub:
            selected.append(book)
            continue
        if include_pdf and book.has_pdf:
            selected.append(book)
            continue
        if include_html:
            selected.append(book)
    if epub_only:
        return [book for book in selected if book.has_epub]
    return selected


def extract_records(
    archive: ZimArchive,
    books: Sequence[GutenbergBook],
    dest_dir: Path,
    *,
    html_format: str = "epub",
    progress: ProgressFn | None = None,
) -> tuple[list[tuple[object, dict[str, str]]], list[tuple[GutenbergBook, str]]]:
    """Extract files and build Calibre ``add_books`` tuples.

    Returns ``(records, errors)`` where each record is ``(Metadata, {FMT: path})``.
    """
    records: list[tuple[object, dict[str, str]]] = []
    errors: list[tuple[GutenbergBook, str]] = []
    total = len(books)
    dest_dir.mkdir(parents=True, exist_ok=True)
    for index, book in enumerate(books, start=1):
        if progress is not None:
            progress(index, total, book.title)
        try:
            path = extract_book(archive, book, dest_dir, html_format=html_format)
            records.append(_metadata_record(path, book))
        except (ExtractError, ZimError, OSError) as exc:
            errors.append((book, str(exc)))
    return records, errors


def _metadata_record(path: Path, book: GutenbergBook) -> tuple[object, dict[str, str]]:
    fmt = path.suffix[1:].lower()
    try:
        from calibre.ebooks.metadata.book.base import Metadata
        from calibre.ebooks.metadata.meta import get_metadata
    except ImportError:
        mi = _fallback_metadata(book)
        return mi, {fmt.upper(): str(path)}

    with path.open("rb") as handle:
        mi = get_metadata(handle, fmt)
    if not mi.title or mi.title.lower() in {"unknown", "unknown title"}:
        mi.title = book.title
    mi.set_identifier("gutenberg", str(book.gutenberg_id))
    tags = list(mi.tags or [])
    for tag in ("ZIM", "Gutenberg"):
        if tag not in tags:
            tags.append(tag)
    mi.tags = tags
    return mi, {fmt.upper(): str(path)}


def _fallback_metadata(book: GutenbergBook) -> object:
    return type(
        "SimpleMetadata",
        (),
        {
            "title": book.title,
            "authors": ["Unknown"],
            "tags": ["ZIM", "Gutenberg"],
            "identifiers": {"gutenberg": str(book.gutenberg_id)},
        },
    )()
