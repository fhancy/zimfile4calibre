"""Extract the first N Gutenberg books as EPUB (or PDF if no EPUB)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .extract import ExtractError, extract_book, preferred_format
from .gutenberg_catalog import list_gutenberg_books
from .list_titles import _configure_stdio
from .zim_reader import ZimArchive, ZimError


def main(argv: Sequence[str] | None = None) -> int:
    _configure_stdio()
    args = _parse_args(argv)
    zim_path = Path(args.zim)
    dest = Path(args.output)
    if not zim_path.is_file():
        print(f"ZIM file not found: {zim_path}", file=sys.stderr)
        return 2
    try:
        with ZimArchive(zim_path) as archive:
            print(
                f"Opened {zim_path.name} (ZIM {archive.header.major}.{archive.header.minor})",
                file=sys.stderr,
            )
            books = list_gutenberg_books(archive)[: args.limit]
            extracted = 0
            skipped = 0
            for book in books:
                native = preferred_format(book)
                source = native or (f"html->{args.html_format}" if args.html_format != "none" else None)
                if source is None:
                    print(
                        f"SKIP {book.gutenberg_id}  {book.title}  (no EPUB/PDF)",
                        file=sys.stderr,
                    )
                    skipped += 1
                    continue
                try:
                    path = extract_book(
                        archive, book, dest, html_format=args.html_format
                    )
                except (ExtractError, ZimError) as exc:
                    print(f"FAIL {book.gutenberg_id}  {book.title}  {exc}", file=sys.stderr)
                    skipped += 1
                    continue
                size_kib = path.stat().st_size / 1024
                kind = native or f"html->{args.html_format}"
                print(f"OK   {book.gutenberg_id}  {kind:<10}  {size_kib:8.1f} KiB  {path.name}")
                extracted += 1
    except ZimError as exc:
        print(f"Failed to read ZIM: {exc}", file=sys.stderr)
        return 1
    print(f"Extracted {extracted} file(s), skipped {skipped}, into {dest}", file=sys.stderr)
    return 0 if extracted else 1


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract Gutenberg EPUB/PDF files from a ZIM archive."
    )
    parser.add_argument("zim", help="Path to the .zim file")
    parser.add_argument(
        "-o",
        "--output",
        default="extracted",
        help="Output directory (default: extracted)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of catalog books to consider (default: 20)",
    )
    parser.add_argument(
        "--html-format",
        choices=("epub", "pdf", "none"),
        default="epub",
        help="When a book has only HTML: convert to epub (default), pdf, or skip",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
