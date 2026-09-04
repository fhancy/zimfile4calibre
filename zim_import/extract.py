"""Extract Gutenberg EPUB/PDF blobs, or convert HTML when no ebook file exists."""

from __future__ import annotations

import re
from pathlib import Path

from .gutenberg_catalog import GutenbergBook
from .html_convert import ConvertError, convert_html_book
from .zim_reader import ZimArchive, ZimError

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class ExtractError(Exception):
    """Raised when a book has no extractable or convertible file."""


def preferred_format(book: GutenbergBook) -> str | None:
    if book.has_epub and book.epub_cluster is not None and book.epub_blob is not None:
        return "epub"
    if book.has_pdf and book.pdf_cluster is not None and book.pdf_blob is not None:
        return "pdf"
    return None


def extract_book(
    archive: ZimArchive,
    book: GutenbergBook,
    dest_dir: Path,
    *,
    html_format: str = "epub",
) -> Path:
    """Write a native EPUB/PDF, or convert the HTML page when requested."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    native = preferred_format(book)
    if native:
        data = (
            archive.read_blob(book.epub_cluster, book.epub_blob)  # type: ignore[arg-type]
            if native == "epub"
            else archive.read_blob(book.pdf_cluster, book.pdf_blob)  # type: ignore[arg-type]
        )
        path = dest_dir / _filename(book, native)
        path.write_bytes(data)
        return path
    if html_format in {"epub", "pdf"}:
        path = dest_dir / _filename(book, html_format)
        try:
            return convert_html_book(archive, book, path, html_format)
        except (ConvertError, ZimError) as exc:
            raise ExtractError(str(exc)) from exc
    raise ExtractError(f"No EPUB or PDF for Gutenberg id {book.gutenberg_id}")


def _filename(book: GutenbergBook, fmt: str) -> str:
    title = book.title.strip().strip("\"'")
    title = _UNSAFE.sub("_", title)
    title = re.sub(r"\s+", " ", title).strip(" ._") or "untitled"
    title = title[:150]
    return f"{book.gutenberg_id} - {title}.{fmt}"
