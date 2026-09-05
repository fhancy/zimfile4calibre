from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.zim_v5_writer import TestEntry, write_zim_v5
from zim_import.gutenberg_catalog import GutenbergBook, iter_gutenberg_books, list_gutenberg_books
from zim_import.zim_reader import ZimArchive, ZimEntry


def _entry(
    namespace: str,
    mime: str,
    url: str,
    title: str = "",
    is_redirect: bool = False,
    cluster: int | None = None,
    blob: int | None = None,
) -> ZimEntry:
    return ZimEntry(
        index=0,
        namespace=namespace,
        mime=mime,
        url=url,
        title=title,
        is_redirect=is_redirect,
        cluster=cluster,
        blob=blob,
    )


class GutenbergCatalogTests(unittest.TestCase):
    def test_keeps_html_books_excludes_covers_and_joins_epub(self) -> None:
        books = list(
            iter_gutenberg_books(
                [
                    _entry("A", "text/html", "Alpha.1.html", "Alpha"),
                    _entry("A", "text/html", "Beta_cover.2.html", "Beta (cover)"),
                    _entry("A", "text/html", "Beta.2.html", "Beta"),
                    _entry("I", "application/epub+zip", "Alpha.1.epub", "", cluster=2, blob=3),
                    _entry("-", "text/css", "1_style.css", ""),
                ]
            )
        )
        by_id = {book.gutenberg_id: book for book in books}
        self.assertEqual(set(by_id), {1, 2})
        self.assertEqual(by_id[1].title, "Alpha")
        self.assertEqual(by_id[1].epub_cluster, 2)
        self.assertEqual(by_id[1].epub_blob, 3)
        self.assertEqual(by_id[2].title, "Beta")
        self.assertFalse(by_id[2].has_epub)

    def test_prefers_cover_stem_over_author_page(self) -> None:
        books = list(
            iter_gutenberg_books(
                [
                    _entry("A", "text/html", '"1683-1920".50075.html', '"1683-1920"'),
                    _entry(
                        "A",
                        "text/html",
                        '"1683-1920"_cover.50075.html',
                        '"1683-1920" (cover)',
                    ),
                    _entry(
                        "A",
                        "text/html",
                        "Edward Clarence Farnsworth.50075.html",
                        "Edward Clarence Farnsworth",
                    ),
                ]
            )
        )
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0].gutenberg_id, 50075)
        self.assertEqual(books[0].title, '"1683-1920"')
        self.assertEqual(books[0].html_url, '"1683-1920".50075.html')

    def test_falls_back_to_url_title_when_dirent_title_is_empty(self) -> None:
        books = list(
            iter_gutenberg_books(
                [_entry("A", "text/html", "From URL.99.html", "")]
            )
        )
        self.assertEqual(books[0].title, "From URL")
        self.assertEqual(books[0].gutenberg_id, 99)

    def test_list_gutenberg_books_on_synthetic_zim(self) -> None:
        path = write_zim_v5(
            [
                TestEntry("A", "text/html", "Gamma.3.html", "Gamma"),
                TestEntry("I", "application/epub+zip", "Gamma.3.epub", ""),
            ]
        )
        self.addCleanup(path.unlink)
        with ZimArchive(path) as zim:
            books = list_gutenberg_books(zim)
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0].gutenberg_id, 3)
        self.assertEqual(books[0].title, "Gamma")
        self.assertTrue(books[0].has_epub)
        self.assertEqual(books[0].html_url, "Gamma.3.html")

    def test_modern_c_namespace_without_html_suffix(self) -> None:
        books = list(
            iter_gutenberg_books(
                [
                    _entry("C", "text/html", "Polio.66660", "Polio"),
                    _entry("C", "text/html", "Polio_cover.66660", "Polio"),
                    _entry(
                        "C",
                        "application/epub+zip",
                        "Polio.66660.epub",
                        "",
                        cluster=1,
                        blob=2,
                    ),
                    _entry("C", "text/html", "Home", "Home"),
                ]
            )
        )
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0].gutenberg_id, 66660)
        self.assertEqual(books[0].title, "Polio")
        self.assertEqual(books[0].html_url, "Polio.66660")
        self.assertTrue(books[0].has_epub)
        self.assertEqual(books[0].epub_cluster, 1)
        self.assertEqual(books[0].epub_blob, 2)


if __name__ == "__main__":
    unittest.main()
