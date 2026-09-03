from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.zim_v5_writer import TestEntry, write_zim_v5
from zim_import.zim_reader import ZimArchive, ZimError


class ZimReaderTests(unittest.TestCase):
    def test_reads_namespaces_urls_and_titles(self) -> None:
        path = write_zim_v5(
            [
                TestEntry("A", "text/html", "Alpha.1.html", "Alpha"),
                TestEntry("I", "application/epub+zip", "Alpha.1.epub", ""),
                TestEntry("-", "text/css", "style.css", ""),
            ]
        )
        self.addCleanup(path.unlink)
        with ZimArchive(path) as zim:
            self.assertEqual((zim.header.major, zim.header.minor), (5, 0))
            self.assertEqual(zim.header.entry_count, 3)
            entries = list(zim.iter_entries())
        by_url = {item.url: item for item in entries}
        self.assertEqual(by_url["Alpha.1.html"].namespace, "A")
        self.assertEqual(by_url["Alpha.1.html"].mime, "text/html")
        self.assertEqual(by_url["Alpha.1.html"].title, "Alpha")
        self.assertFalse(by_url["Alpha.1.html"].is_redirect)
        self.assertEqual(by_url["Alpha.1.epub"].namespace, "I")
        self.assertEqual(by_url["Alpha.1.epub"].mime, "application/epub+zip")
        self.assertEqual(by_url["style.css"].namespace, "-")

    def test_reads_redirects(self) -> None:
        path = write_zim_v5(
            [
                TestEntry("A", "text/html", "real.html", "Real"),
                TestEntry("A", "text/html", "alias.html", "Alias", redirect_url="real.html"),
            ]
        )
        self.addCleanup(path.unlink)
        with ZimArchive(path) as zim:
            entries = {item.url: item for item in zim.iter_entries()}
        self.assertTrue(entries["alias.html"].is_redirect)
        self.assertEqual(entries["alias.html"].mime, "REDIRECT")
        self.assertFalse(entries["real.html"].is_redirect)

    def test_extracts_uncompressed_epub_blob(self) -> None:
        payload = b"PK\x03\x04fake-epub-bytes"
        path = write_zim_v5(
            [
                TestEntry("A", "text/html", "Alpha.1.html", "Alpha", content=b"<html/>"),
                TestEntry(
                    "I",
                    "application/epub+zip",
                    "Alpha.1.epub",
                    "",
                    content=payload,
                ),
            ]
        )
        self.addCleanup(path.unlink)
        with ZimArchive(path) as zim:
            entries = {item.url: item for item in zim.iter_entries()}
            self.assertEqual(zim.read_content(entries["Alpha.1.epub"]), payload)
            self.assertEqual(zim.read_content(entries["Alpha.1.html"]), b"<html/>")
        with ZimArchive(path) as zim:
            found = zim.get_entry("I", "Alpha.1.epub")
            self.assertIsNotNone(found)
            self.assertEqual(found.mime, "application/epub+zip")
            self.assertIsNone(zim.get_entry("A", "missing.html"))

    def test_rejects_bad_magic(self) -> None:
        path = write_zim_v5(
            [TestEntry("A", "text/html", "x.1.html", "x")]
        )
        self.addCleanup(path.unlink)
        path.write_bytes(b"not a zim file" + b"\x00" * 80)
        with self.assertRaises(ZimError):
            ZimArchive(path)


if __name__ == "__main__":
    unittest.main()
