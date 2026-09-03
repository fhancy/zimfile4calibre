from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.zim_v5_writer import TestEntry, write_zim_v5
from zim_import.extract import extract_book, preferred_format
from zim_import.gutenberg_catalog import list_gutenberg_books
from zim_import.zim_reader import ZimArchive


class ExtractTests(unittest.TestCase):
    def test_extracts_epub_in_preference_to_pdf(self) -> None:
        dest = ROOT / "tests" / "_extracted"
        dest.mkdir(exist_ok=True)
        epub = b"PK\x03\x04epub-payload"
        path = write_zim_v5(
            [
                TestEntry("A", "text/html", "Delta.4.html", "Delta", content=b"html"),
                TestEntry(
                    "I",
                    "application/epub+zip",
                    "Delta.4.epub",
                    "",
                    content=epub,
                ),
                TestEntry(
                    "I",
                    "application/pdf",
                    "Delta.4.pdf",
                    "",
                    content=b"%PDF-fake",
                ),
            ]
        )
        self.addCleanup(path.unlink)
        with ZimArchive(path) as zim:
            books = list_gutenberg_books(zim)
            self.assertEqual(preferred_format(books[0]), "epub")
            out = extract_book(zim, books[0], dest)
        self.addCleanup(out.unlink)
        self.assertEqual(out.read_bytes(), epub)
        self.assertTrue(out.name.endswith(".epub"))
        self.assertIn("4 -", out.name)

    def test_falls_back_to_pdf(self) -> None:
        dest = ROOT / "tests" / "_extracted"
        dest.mkdir(exist_ok=True)
        pdf = b"%PDF-1.4 fake"
        path = write_zim_v5(
            [
                TestEntry("A", "text/html", "Solo.5.html", "Solo", content=b"html"),
                TestEntry("I", "application/pdf", "Solo.5.pdf", "", content=pdf),
            ]
        )
        self.addCleanup(path.unlink)
        with ZimArchive(path) as zim:
            books = list_gutenberg_books(zim)
            self.assertEqual(preferred_format(books[0]), "pdf")
            out = extract_book(zim, books[0], dest)
        self.addCleanup(out.unlink)
        self.assertEqual(out.read_bytes(), pdf)

    def test_converts_html_when_no_ebook_file(self) -> None:
        dest = ROOT / "tests" / "_extracted"
        dest.mkdir(exist_ok=True)
        png = b"\x89PNG\r\n\x1a\nfake"
        html = (
            '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
            '<div><link href="../-/fonts/font-awesome/css/font-awesome.min.css" rel="stylesheet"/>'
            '<span class="zim_info"><a href="x_cover.6.html">i</a></span></div>'
            '<p>Hello</p><img src="../I/pic.png"/>'
            "</body></html>"
        )
        path = write_zim_v5(
            [
                TestEntry("A", "text/html", "Hello.6.html", "Hello", content=html.encode()),
                TestEntry("I", "image/png", "pic.png", "", content=png),
                TestEntry("-", "text/css", "fonts/font-awesome/css/font-awesome.min.css", "", content=b"css"),
            ]
        )
        self.addCleanup(path.unlink)
        from unittest.mock import patch

        with patch("zim_import.html_convert._ebook_convert", return_value=None):
            with ZimArchive(path) as zim:
                books = list_gutenberg_books(zim)
                self.assertIsNone(preferred_format(books[0]))
                out = extract_book(zim, books[0], dest, html_format="epub")
        self.addCleanup(out.unlink)
        data = out.read_bytes()
        self.assertTrue(data.startswith(b"PK"))
        self.assertIn(png, data)
        self.assertNotIn(b"font-awesome", data)
