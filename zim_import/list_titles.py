"""List Gutenberg book titles from an OpenZIM v5 catalog."""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path

from .gutenberg_catalog import GutenbergBook, list_gutenberg_books
from .zim_reader import ZimArchive, ZimError


def main(argv: Sequence[str] | None = None) -> int:
    _configure_stdio()
    args = _parse_args(argv)
    zim_path = Path(args.zim)
    if not zim_path.is_file():
        print(f"ZIM file not found: {zim_path}", file=sys.stderr)
        return 2
    try:
        with ZimArchive(zim_path) as archive:
            print(
                f"Opened {zim_path.name} (ZIM {archive.header.major}.{archive.header.minor}, "
                f"{archive.header.entry_count} entries)",
                file=sys.stderr,
            )
            books = list_gutenberg_books(archive)
    except ZimError as exc:
        print(f"Failed to read ZIM: {exc}", file=sys.stderr)
        return 1

    selected = books[: args.limit] if args.limit else books
    if args.output:
        _write_csv(Path(args.output), selected)
        print(f"Wrote {len(selected)} titles to {args.output}", file=sys.stderr)
    if args.limit or not args.output:
        _print_preview(selected)
    print(
        f"{len(books)} books in catalog; showing {len(selected)}",
        file=sys.stderr,
    )
    return 0


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract Gutenberg book titles from a ZIM catalog (no content extraction)."
    )
    parser.add_argument("zim", help="Path to the .zim file")
    parser.add_argument(
        "-o",
        "--output",
        help="UTF-8 CSV path (columns: id,title,has_epub)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only keep the first N books (after a full catalog scan)",
    )
    return parser.parse_args(argv)


def _write_csv(path: Path, books: Sequence[GutenbergBook]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "title", "has_epub"])
        for book in books:
            writer.writerow(
                [book.gutenberg_id, book.title, "yes" if book.has_epub else "no"]
            )


def _print_preview(books: Sequence[GutenbergBook]) -> None:
    if not books:
        print("No Gutenberg HTML books found.")
        return
    id_width = max(2, max(len(str(book.gutenberg_id)) for book in books))
    print(f"{'id':>{id_width}}  epub  title")
    for book in books:
        flag = "yes" if book.has_epub else "no"
        print(f"{book.gutenberg_id:>{id_width}}  {flag:<4}  {book.title}")


if __name__ == "__main__":
    raise SystemExit(main())
