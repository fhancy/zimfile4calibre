"""List EPUB/PDF (and MOBI) MIME types and paths without extracting blobs."""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

from .list_titles import _configure_stdio
from .zim_reader import ZimArchive, ZimEntry, ZimError

EBOOK_MIMES = frozenset(
    {
        "application/epub+zip",
        "application/pdf",
        "mobi",
        "application/x-mobipocket-ebook",
    }
)
EBOOK_SUFFIXES = (".epub", ".pdf", ".mobi", ".azw3")


def iter_ebook_entries(entries: Iterable[ZimEntry]) -> Iterator[ZimEntry]:
    """Yield ebook files from a ZIM directory listing (no cluster I/O)."""
    for entry in entries:
        if entry.is_redirect:
            continue
        mime = (entry.mime or "").lower()
        url = entry.url.lower()
        if mime in EBOOK_MIMES or url.endswith(EBOOK_SUFFIXES):
            yield entry


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
            found = list(iter_ebook_entries(archive.iter_entries()))
    except ZimError as exc:
        print(f"Failed to read ZIM: {exc}", file=sys.stderr)
        return 1

    selected = found[: args.limit] if args.limit else found
    if args.output:
        _write_csv(Path(args.output), selected)
        print(f"Wrote {len(selected)} ebook paths to {args.output}", file=sys.stderr)
    if args.limit or not args.output:
        _print_preview(selected)
    print(
        f"{len(found)} ebook files in catalog; showing {len(selected)}",
        file=sys.stderr,
    )
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List EPUB/PDF MIME types and paths from a ZIM catalog."
    )
    parser.add_argument("zim", help="Path to the .zim file")
    parser.add_argument("-o", "--output", help="UTF-8 CSV path (columns: mime,ns,url)")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only print the first N ebook files (after a full catalog scan)",
    )
    return parser.parse_args(argv)


def _write_csv(path: Path, entries: Sequence[ZimEntry]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["mime", "namespace", "url", "title"])
        for entry in entries:
            writer.writerow([entry.mime, entry.namespace, entry.url, entry.title])


def _print_preview(entries: Sequence[ZimEntry]) -> None:
    if not entries:
        print("No EPUB/PDF/MOBI files found.")
        return
    print(f"{'mime':<24}  ns  url")
    for entry in entries:
        print(f"{entry.mime:<24}  {entry.namespace:<2}  {entry.url}")


if __name__ == "__main__":
    raise SystemExit(main())
