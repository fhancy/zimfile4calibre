from __future__ import annotations

import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.zim_v5_writer import TestEntry, write_zim_v5
from zim_import.list_titles import main


class ListTitlesCliTests(unittest.TestCase):
    def test_preview_and_csv(self) -> None:
        zim_path = write_zim_v5(
            [
                TestEntry("A", "text/html", "Delta.4.html", "Delta"),
                TestEntry("I", "application/epub+zip", "Delta.4.epub", ""),
            ]
        )
        self.addCleanup(zim_path.unlink)
        csv_path = ROOT / "tests" / "_cli_out.csv"
        self.addCleanup(lambda: csv_path.unlink(missing_ok=True))
        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            code = main([str(zim_path), "-o", str(csv_path), "--limit", "5"])
        self.assertEqual(code, 0)
        self.assertIn("Delta", stdout.getvalue())
        text = csv_path.read_text(encoding="utf-8")
        self.assertIn("4,Delta,yes", text)


if __name__ == "__main__":
    unittest.main()
