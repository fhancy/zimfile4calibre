"""Identify Gutenberg books inside a 2021-era OpenZIM catalog."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from zim_import.zim_reader import ZimArchive, ZimEntry

BOOK_HTML = re.compile(r"^(?P<title>.+)\.(?P<id>\d+)\.html$")
COVER_HTML = re.compile(r"^(?P<stem>.+)_cover\.(?P<id>\d+)\.html$")
BOOK_EPUB = re.compile(r"^(?P<title>.+)\.(?P<id>\d+)\.epub$")
BOOK_PDF = re.compile(r"^(?P<title>.+)\.(?P<id>\d+)\.pdf$")


@dataclass
class GutenbergBook:
    gutenberg_id: int
    title: str
    html_url: str
    has_epub: bool = False
    has_pdf: bool = False
    epub_url: str | None = None
    pdf_url: str | None = None
    epub_cluster: int | None = None
    epub_blob: int | None = None
    pdf_cluster: int | None = None
    pdf_blob: int | None = None
    html_cluster: int | None = None
    html_blob: int | None = None


def list_gutenberg_books(archive: ZimArchive) -> list[GutenbergBook]:
    """Return one HTML book per Gutenberg id, files joined by that id."""
    return list(iter_gutenberg_books(archive.iter_entries()))


def iter_gutenberg_books(entries: Iterable[ZimEntry]) -> Iterator[GutenbergBook]:
    pages: dict[int, list[ZimEntry]] = defaultdict(list)
    cover_stems: dict[int, str] = {}
    epubs: dict[int, ZimEntry] = {}
    pdfs: dict[int, ZimEntry] = {}

    for entry in entries:
        if entry.is_redirect:
            continue
        if entry.namespace == "A" and entry.mime == "text/html":
            cover = COVER_HTML.match(entry.url)
            if cover:
                cover_stems[int(cover.group("id"))] = cover.group("stem")
                continue
            match = BOOK_HTML.match(entry.url)
            if match:
                pages[int(match.group("id"))].append(entry)
            continue
        if entry.namespace == "I" and entry.mime == "application/epub+zip":
            match = BOOK_EPUB.match(entry.url)
            if match:
                epubs[int(match.group("id"))] = entry
            continue
        if entry.namespace == "I" and entry.mime == "application/pdf":
            match = BOOK_PDF.match(entry.url)
            if match:
                pdfs[int(match.group("id"))] = entry

    for gutenberg_id, candidates in pages.items():
        chosen = _choose_book_page(gutenberg_id, candidates, cover_stems.get(gutenberg_id))
        match = BOOK_HTML.match(chosen.url)
        assert match is not None
        title = chosen.title.strip() or match.group("title")
        epub = epubs.get(gutenberg_id)
        pdf = pdfs.get(gutenberg_id)
        yield GutenbergBook(
            gutenberg_id=gutenberg_id,
            title=title,
            html_url=chosen.url,
            has_epub=epub is not None,
            has_pdf=pdf is not None,
            epub_url=epub.url if epub else None,
            pdf_url=pdf.url if pdf else None,
            epub_cluster=epub.cluster if epub else None,
            epub_blob=epub.blob if epub else None,
            pdf_cluster=pdf.cluster if pdf else None,
            pdf_blob=pdf.blob if pdf else None,
            html_cluster=chosen.cluster,
            html_blob=chosen.blob,
        )


def _choose_book_page(
    gutenberg_id: int,
    candidates: list[ZimEntry],
    cover_stem: str | None,
) -> ZimEntry:
    if cover_stem:
        expected = f"{cover_stem}.{gutenberg_id}.html"
        for entry in candidates:
            if entry.url == expected:
                return entry
    if len(candidates) == 1:
        return candidates[0]

    def score(entry: ZimEntry) -> tuple[int, int]:
        match = BOOK_HTML.match(entry.url)
        url_title = match.group("title") if match else entry.url
        title_matches_url = int(
            bool(entry.title) and entry.url == f"{entry.title}.{gutenberg_id}.html"
        )
        return (title_matches_url, len(url_title))

    return max(candidates, key=score)
