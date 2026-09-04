from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zim_import.gutenberg_catalog import GutenbergBook
from zim_import.list_formats import iter_ebook_entries
from zim_import.plugin_import import filter_books_for_import
from zim_import.zim_reader import ZimEntry


def _entry(namespace: str, mime: str, url: str) -> ZimEntry:
    return ZimEntry(
        index=0,
        namespace=namespace,
        mime=mime,
        url=url,
        title="",
        is_redirect=False,
    )


def _book(gutenberg_id: int, title: str, has_epub: bool, has_pdf: bool = False) -> GutenbergBook:
    return GutenbergBook(
        gutenberg_id=gutenberg_id,
        title=title,
        html_url=f"{title}.{gutenberg_id}.html",
        has_epub=has_epub,
        has_pdf=has_pdf,
    )


class ListFormatsTests(unittest.TestCase):
    def test_lists_epub_and_pdf_skips_html_and_images(self) -> None:
        entries = list(
            iter_ebook_entries(
                [
                    _entry("A", "text/html", "Alpha.1.html"),
                    _entry("I", "application/epub+zip", "Alpha.1.epub"),
                    _entry("I", "application/pdf", "Beta.2.pdf"),
                    _entry("I", "image/jpeg", "cover.jpg"),
                    _entry("I", "mobi", "Gamma.3.mobi"),
                ]
            )
        )
        urls = [item.url for item in entries]
        self.assertEqual(urls, ["Alpha.1.epub", "Beta.2.pdf", "Gamma.3.mobi"])


class PluginImportPolicyTests(unittest.TestCase):
    def test_epub_only_is_the_default_policy(self) -> None:
        books = [
            _book(1, "With Epub", True),
            _book(2, "Pdf Only", False, True),
            _book(3, "Html Only", False, False),
        ]
        selected = filter_books_for_import(books)
        self.assertEqual([book.gutenberg_id for book in selected], [1])

    def test_can_include_pdf_when_epub_only_disabled(self) -> None:
        books = [
            _book(1, "With Epub", True),
            _book(2, "Pdf Only", False, True),
            _book(3, "Html Only", False, False),
        ]
        selected = filter_books_for_import(
            books, epub_only=False, include_pdf=True, include_html=False
        )
        self.assertEqual([book.gutenberg_id for book in selected], [1, 2])


if __name__ == "__main__":
    unittest.main()
