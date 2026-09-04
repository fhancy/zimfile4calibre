"""Convert Gutenberg HTML entries in a ZIM archive to EPUB or PDF."""

from __future__ import annotations

import posixpath
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urlparse

from .gutenberg_catalog import GutenbergBook
from .zim_reader import ZimArchive, ZimError

ATTR_URL = re.compile(
    r"""(?P<attr>src|href)\s*=\s*(?P<quote>['"])(?P<url>.*?)(?P=quote)""",
    re.IGNORECASE,
)
CSS_URL = re.compile(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)", re.IGNORECASE)
ZIM_PATH = re.compile(r"^(?:\./|\.\./)*([A-IMX\-])/(.+)$")
CHROME_DIV = re.compile(
    r"<div>\s*<link[^>]*font-awesome.*?</div>",
    re.IGNORECASE | re.DOTALL,
)
CHROME_SPAN = re.compile(
    r'<span class="zim_(?:info|epub|up)"[^>]*>.*?</span>',
    re.IGNORECASE | re.DOTALL,
)
FONT_AWESOME = re.compile(
    r"<link[^>]*font-awesome[^>]*>",
    re.IGNORECASE,
)
SKIP_RESOURCE = re.compile(
    r"\.(?:epub|pdf|mobi|azw3)(?:$|[?#])|_cover\.\d+\.html$",
    re.IGNORECASE,
)

CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


class ConvertError(Exception):
    """Raised when HTML cannot be turned into EPUB/PDF."""


def convert_html_book(
    archive: ZimArchive,
    book: GutenbergBook,
    dest_path: Path,
    fmt: str,
) -> Path:
    if fmt not in {"epub", "pdf"}:
        raise ConvertError(f"Unsupported conversion format {fmt!r}")
    if book.html_cluster is None or book.html_blob is None:
        raise ConvertError(f"No HTML blob for Gutenberg id {book.gutenberg_id}")
    raw = archive.read_blob(book.html_cluster, book.html_blob)
    html = raw.decode("utf-8", "replace")
    html = _strip_zim_chrome(html)
    html, resources = _rewrite_resources(html, archive)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="zimhtml_") as tmp:
        work = Path(tmp)
        (work / "res").mkdir()
        html_file = work / "index.html"
        html_file.write_text(html, encoding="utf-8")
        for rel, data in resources.items():
            out = work / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
        if fmt == "pdf":
            _convert_with_calibre(html_file, dest_path, book.title)
        else:
            calibre = _ebook_convert()
            if calibre is not None:
                try:
                    _convert_with_calibre(html_file, dest_path, book.title)
                except ConvertError:
                    _write_minimal_epub(dest_path, book.title, html, resources)
            else:
                _write_minimal_epub(dest_path, book.title, html, resources)
    return dest_path


def _strip_zim_chrome(html: str) -> str:
    html = CHROME_DIV.sub("", html)
    html = CHROME_SPAN.sub("", html)
    html = FONT_AWESOME.sub("", html)
    return html


def _rewrite_resources(html: str, archive: ZimArchive) -> tuple[str, dict[str, bytes]]:
    resources: dict[str, bytes] = {}
    seen: dict[tuple[str, str], str] = {}

    def local_for(url: str) -> str | None:
        ref = _zim_ref(url)
        if ref is None:
            return None
        namespace, path = ref
        key = (namespace, path)
        if key in seen:
            return seen[key]
        entry = archive.get_entry(namespace, path)
        if entry is None:
            return None
        try:
            data = archive.read_content(entry)
        except ZimError:
            return None
        local = "res/" + _safe_resource_name(path)
        original = local
        n = 1
        while local in resources and resources[local] != data:
            stem, suffix = posixpath.splitext(original)
            local = f"{stem}_{n}{suffix}"
            n += 1
        resources[local] = data
        seen[key] = local
        return local

    def attr_sub(match: re.Match[str]) -> str:
        url = match.group("url")
        local = local_for(url)
        if local is None:
            return match.group(0)
        return f"{match.group('attr')}={match.group('quote')}{local}{match.group('quote')}"

    def css_sub(match: re.Match[str]) -> str:
        url = match.group(2)
        local = local_for(url)
        if local is None:
            return match.group(0)
        return f"url({local})"

    html = ATTR_URL.sub(attr_sub, html)
    html = CSS_URL.sub(css_sub, html)
    return html, resources


def _zim_ref(url: str) -> tuple[str, str] | None:
    url = unescape(url.strip())
    if not url or url.startswith(("#", "mailto:", "data:", "javascript:")):
        return None
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"}:
        return None
    path = unquote(parsed.path or url)
    if SKIP_RESOURCE.search(path):
        return None
    match = ZIM_PATH.match(path)
    if match:
        return match.group(1), match.group(2)
    if "/" not in path.replace("\\", "/"):
        return "I", path
    return None


def _safe_resource_name(path: str) -> str:
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name or "resource.bin"


def _ebook_convert() -> Path | None:
    found = shutil.which("ebook-convert")
    if found:
        return Path(found)
    bundled = Path(r"C:\Program Files\Calibre2\ebook-convert.exe")
    if bundled.is_file():
        return bundled
    return None


def _convert_with_calibre(html_file: Path, dest: Path, title: str) -> None:
    exe = _ebook_convert()
    if exe is None:
        raise ConvertError("Calibre ebook-convert is not installed")
    result = subprocess.run(
        [str(exe), str(html_file), str(dest), "--title", title],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0 or not dest.is_file():
        detail = (result.stderr or result.stdout or "unknown error").strip()
        raise ConvertError(f"ebook-convert failed: {detail[-500:]}")


def _write_minimal_epub(
    dest: Path,
    title: str,
    html: str,
    resources: dict[str, bytes],
) -> None:
    book_id = str(uuid.uuid4())
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    items = [
        '<item id="chap" href="index.xhtml" media-type="application/xhtml+xml"/>'
    ]
    for index, name in enumerate(sorted(resources)):
        items.append(
            f'<item id="r{index}" href="{_xml_escape(name)}" '
            f'media-type="{_mime_for(name)}"/>'
        )
    opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{safe_title}</dc:title>
    <dc:language>en</dc:language>
    <dc:identifier id="bookid">{book_id}</dc:identifier>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    {"".join(items)}
  </manifest>
  <spine toc="ncx">
    <itemref idref="chap"/>
  </spine>
</package>
"""
    ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{book_id}"/>
  </head>
  <docTitle><text>{safe_title}</text></docTitle>
  <navMap>
    <navPoint id="nav1" playOrder="1">
      <navLabel><text>{safe_title}</text></navLabel>
      <content src="index.xhtml"/>
    </navPoint>
  </navMap>
</ncx>
"""
    xhtml = html
    if "<html" not in xhtml.lower():
        xhtml = f"<html xmlns='http://www.w3.org/1999/xhtml'><body>{html}</body></html>"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", opf)
        archive.writestr("OEBPS/toc.ncx", ncx)
        archive.writestr("OEBPS/index.xhtml", xhtml.encode("utf-8"))
        for name, data in resources.items():
            archive.writestr(f"OEBPS/{name}", data)


def _mime_for(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".svg"):
        return "image/svg+xml"
    if lower.endswith(".css"):
        return "text/css"
    return "application/octet-stream"


def _xml_escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
