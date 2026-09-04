"""Build the Calibre plugin ZIP (code + icon, no tests)."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
ZIP_NAME = "ZIM_Import.zip"

INCLUDE_ROOT = (
    "__init__.py",
    "plugin-import-name-zim_import.txt",
    "about.txt",
)
INCLUDE_GLOBS = (
    "zim_import/*.py",
    "images/icon.png",
)


def main() -> Path:
    DIST.mkdir(exist_ok=True)
    zip_path = DIST / ZIP_NAME
    files: list[Path] = [ROOT / name for name in INCLUDE_ROOT]
    for pattern in INCLUDE_GLOBS:
        files.extend(ROOT.glob(pattern))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            if not path.is_file():
                continue
            archive.write(path, path.relative_to(ROOT).as_posix())
    return zip_path


if __name__ == "__main__":
    created = main()
    print(created)
