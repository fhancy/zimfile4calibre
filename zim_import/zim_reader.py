"""Read-only OpenZIM v5/v6 directory and cluster blobs."""

from __future__ import annotations

import struct
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

ZIM_MAGIC = 72173914
HEADER_SIZE = 80
SUPPORTED_MAJOR = frozenset({5, 6})
MIME_REDIRECT = 0xFFFF
MIME_LINKTARGET = 0xFFFE
MIME_DELETED = 0xFFFD

COMP_NONE = 1
COMP_ZLIB = 2
COMP_BZIP2 = 3
COMP_LZMA = 4
COMP_ZSTD = 5

_HEADER_STRUCT = struct.Struct("<IHH16sIIQQQQIIQ")


class ZimError(Exception):
    """Raised when a ZIM file is missing, truncated, or unsupported."""


@dataclass(frozen=True)
class ZimHeader:
    major: int
    minor: int
    uuid: bytes
    entry_count: int
    cluster_count: int
    url_ptr_pos: int
    title_ptr_pos: int
    cluster_ptr_pos: int
    mime_list_pos: int
    main_page: int
    layout_page: int
    checksum_pos: int


@dataclass(frozen=True)
class ZimEntry:
    index: int
    namespace: str
    mime: str
    url: str
    title: str
    is_redirect: bool
    cluster: int | None = None
    blob: int | None = None
    redirect_index: int | None = None


class ZimArchive:
    """Open a ZIM v5/v6 file, list dirents, and extract selected blobs."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        try:
            self._file: BinaryIO = self.path.open("rb")
        except OSError as exc:
            raise ZimError(f"Cannot open ZIM file: {self.path}") from exc
        try:
            self.header = self._read_header()
            self._mimes = self._read_mime_list()
            self._url_ptrs: tuple[int, ...] | None = None
            self._cluster_ptrs: tuple[int, ...] | None = None
            self._cluster_cache: dict[int, tuple[bytes, bool]] = {}
            self._dirent_blob: bytes | None = None
            self._dirent_base: int | None = None
        except Exception:
            self._file.close()
            raise

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> ZimArchive:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @property
    def mimes(self) -> tuple[str, ...]:
        return self._mimes

    def iter_entries(self) -> Iterator[ZimEntry]:
        ptrs = self._url_pointer_table()
        if not ptrs:
            return
        blob, base = self._read_dirent_blob(ptrs)
        for index, offset in enumerate(ptrs):
            yield self._parse_dirent(blob, offset - base, index)

    def read_content(self, entry: ZimEntry) -> bytes:
        hops = 0
        current = entry
        while current.is_redirect:
            if current.redirect_index is None:
                raise ZimError(f"Redirect {current.url!r} has no target")
            hops += 1
            if hops > 8:
                raise ZimError(f"Redirect loop at {entry.url!r}")
            current = self.entry_by_index(current.redirect_index)
        if current.cluster is None or current.blob is None:
            raise ZimError(f"Entry {current.url!r} has no content blob")
        return self.read_blob(current.cluster, current.blob)

    def entry_by_index(self, index: int) -> ZimEntry:
        ptrs = self._url_pointer_table()
        if index < 0 or index >= len(ptrs):
            raise ZimError(f"Entry index {index} out of range")
        blob, base = self._read_dirent_blob(ptrs)
        return self._parse_dirent(blob, ptrs[index] - base, index)

    def get_entry(self, namespace: str, url: str) -> ZimEntry | None:
        ptrs = self._url_pointer_table()
        if not ptrs:
            return None
        blob, base = self._read_dirent_blob(ptrs)
        key = (namespace, url)
        lo, hi = 0, len(ptrs)
        while lo < hi:
            mid = (lo + hi) // 2
            mid_entry = self._parse_dirent(blob, ptrs[mid] - base, mid)
            if (mid_entry.namespace, mid_entry.url) < key:
                lo = mid + 1
            else:
                hi = mid
        if lo >= len(ptrs):
            return None
        entry = self._parse_dirent(blob, ptrs[lo] - base, lo)
        if (entry.namespace, entry.url) == key:
            return entry
        return None

    def read_blob(self, cluster_index: int, blob_index: int) -> bytes:
        data, extended = self._uncompressed_cluster(cluster_index)
        return _slice_blob(data, blob_index, extended)

    def _read_header(self) -> ZimHeader:
        raw = self._file.read(HEADER_SIZE)
        if len(raw) != HEADER_SIZE:
            raise ZimError("Truncated ZIM header")
        (
            magic,
            major,
            minor,
            uuid,
            entry_count,
            cluster_count,
            url_ptr_pos,
            title_ptr_pos,
            cluster_ptr_pos,
            mime_list_pos,
            main_page,
            layout_page,
            checksum_pos,
        ) = _HEADER_STRUCT.unpack(raw)
        if magic != ZIM_MAGIC:
            raise ZimError(f"Not a ZIM file (magic={magic:#x})")
        if major not in SUPPORTED_MAJOR:
            raise ZimError(
                f"Unsupported ZIM version {major}.{minor}; "
                f"this reader supports {', '.join(f'v{v}' for v in sorted(SUPPORTED_MAJOR))}"
            )
        return ZimHeader(
            major=major,
            minor=minor,
            uuid=uuid,
            entry_count=entry_count,
            cluster_count=cluster_count,
            url_ptr_pos=url_ptr_pos,
            title_ptr_pos=title_ptr_pos,
            cluster_ptr_pos=cluster_ptr_pos,
            mime_list_pos=mime_list_pos,
            main_page=main_page,
            layout_page=layout_page,
            checksum_pos=checksum_pos,
        )

    def _read_mime_list(self) -> tuple[str, ...]:
        self._file.seek(self.header.mime_list_pos)
        mimes: list[str] = []
        while True:
            value = self._read_cstring_from_file()
            if value == "":
                break
            mimes.append(value)
        return tuple(mimes)

    def _read_cstring_from_file(self) -> str:
        chunks: list[bytes] = []
        while True:
            byte = self._file.read(1)
            if not byte:
                raise ZimError("Truncated MIME list")
            if byte == b"\x00":
                break
            chunks.append(byte)
        return b"".join(chunks).decode("utf-8", "replace")

    def _url_pointer_table(self) -> tuple[int, ...]:
        if self._url_ptrs is None:
            count = self.header.entry_count
            self._file.seek(self.header.url_ptr_pos)
            raw = self._file.read(8 * count)
            if len(raw) != 8 * count:
                raise ZimError("Truncated URL pointer table")
            self._url_ptrs = struct.unpack(f"<{count}Q", raw) if count else ()
        return self._url_ptrs

    def _cluster_pointer_table(self) -> tuple[int, ...]:
        if self._cluster_ptrs is None:
            count = self.header.cluster_count
            self._file.seek(self.header.cluster_ptr_pos)
            raw = self._file.read(8 * count)
            if len(raw) != 8 * count:
                raise ZimError("Truncated cluster pointer table")
            self._cluster_ptrs = struct.unpack(f"<{count}Q", raw) if count else ()
        return self._cluster_ptrs

    def _read_dirent_blob(self, ptrs: tuple[int, ...]) -> tuple[bytes, int]:
        if self._dirent_blob is not None and self._dirent_base is not None:
            return self._dirent_blob, self._dirent_base
        lo = min(ptrs)
        hi = max(ptrs)
        end = max(self.header.url_ptr_pos, hi + 65536)
        if self.header.checksum_pos and end > self.header.checksum_pos:
            end = self.header.checksum_pos
        if end <= lo:
            end = hi + 65536
        self._file.seek(lo)
        blob = self._file.read(end - lo)
        if not blob:
            raise ZimError("Empty directory blob")
        self._dirent_blob = blob
        self._dirent_base = lo
        return blob, lo

    def _parse_dirent(self, blob: bytes, offset: int, index: int) -> ZimEntry:
        if offset + 8 > len(blob):
            raise ZimError(f"Dirent {index} starts past directory blob")
        mime_idx, param_len, ns_byte = struct.unpack_from("<HBc", blob, offset)
        pos = offset + 8
        is_redirect = mime_idx == MIME_REDIRECT
        cluster: int | None = None
        blob_index: int | None = None
        redirect_index: int | None = None
        if is_redirect:
            redirect_index = struct.unpack_from("<I", blob, pos)[0]
            pos += 4
            mime = "REDIRECT"
        elif mime_idx in (MIME_LINKTARGET, MIME_DELETED):
            mime = "LINKTARGET" if mime_idx == MIME_LINKTARGET else "DELETED"
        else:
            cluster, blob_index = struct.unpack_from("<II", blob, pos)
            pos += 8
            if mime_idx < len(self._mimes):
                mime = self._mimes[mime_idx]
            else:
                mime = f"mime:{mime_idx}"
        url, pos = _cstring_at(blob, pos)
        title, pos = _cstring_at(blob, pos)
        namespace = ns_byte.decode("ascii", "replace")
        return ZimEntry(
            index=index,
            namespace=namespace,
            mime=mime,
            url=url,
            title=title,
            is_redirect=is_redirect,
            cluster=cluster,
            blob=blob_index,
            redirect_index=redirect_index,
        )

    def _uncompressed_cluster(self, cluster_index: int) -> tuple[bytes, bool]:
        cached = self._cluster_cache.get(cluster_index)
        if cached is not None:
            return cached
        ptrs = self._cluster_pointer_table()
        if cluster_index < 0 or cluster_index >= len(ptrs):
            raise ZimError(f"Cluster {cluster_index} out of range")
        start = ptrs[cluster_index]
        if cluster_index + 1 < len(ptrs):
            end = ptrs[cluster_index + 1]
        else:
            end = min(self.header.url_ptr_pos, self.header.checksum_pos)
            url_ptrs = self._url_pointer_table()
            if url_ptrs:
                end = min(end, min(url_ptrs))
        if end <= start:
            raise ZimError(f"Invalid cluster span {cluster_index}")
        self._file.seek(start)
        raw = self._file.read(end - start)
        if not raw:
            raise ZimError(f"Empty cluster {cluster_index}")
        extended = bool(raw[0] & 0x10)
        data = _decompress_cluster(raw)
        decoded = (data, extended)
        if len(self._cluster_cache) >= 8:
            self._cluster_cache.pop(next(iter(self._cluster_cache)))
        self._cluster_cache[cluster_index] = decoded
        return decoded


def _cstring_at(blob: bytes, offset: int) -> tuple[str, int]:
    end = blob.find(b"\x00", offset)
    if end < 0:
        raise ZimError("Truncated dirent string")
    return blob[offset:end].decode("utf-8", "replace"), end + 1


def _decompress_cluster(raw: bytes) -> bytes:
    info = raw[0]
    payload = raw[1:]
    compression = info & 0x0F
    if compression == COMP_NONE:
        return payload
    if compression == COMP_ZLIB:
        import zlib

        return zlib.decompress(payload)
    if compression == COMP_LZMA:
        import lzma

        try:
            return lzma.decompress(payload)
        except lzma.LZMAError:
            filters = [{"id": lzma.FILTER_LZMA2}]
            return lzma.decompress(payload, format=lzma.FORMAT_RAW, filters=filters)
    if compression == COMP_ZSTD:
        return _decompress_zstd(payload)
    raise ZimError(f"Unsupported cluster compression {compression}")


def _decompress_zstd(payload: bytes) -> bytes:
    try:
        import zstandard
        import io

        reader = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(payload))
        return reader.read()
    except ImportError:
        pass
    try:
        import pyzstd

        return pyzstd.decompress(payload)
    except ImportError:
        pass
    try:
        from compression import zstd

        return zstd.decompress(payload)
    except ImportError as exc:
        raise ZimError(
            "Cluster uses zstd; install zstandard or pyzstd "
            "(Calibre 8 already bundles pyzstd)"
        ) from exc


def _slice_blob(cluster_data: bytes, blob_index: int, extended: bool) -> bytes:
    width = 8 if extended else 4
    if len(cluster_data) < width:
        raise ZimError("Cluster too small to contain blob offsets")
    fmt_one = "<Q" if extended else "<I"
    first = struct.unpack_from(fmt_one, cluster_data, 0)[0]
    if first % width:
        raise ZimError("Invalid cluster offset table")
    offset_count = first // width
    table_bytes = offset_count * width
    if table_bytes > len(cluster_data) or blob_index + 1 >= offset_count:
        raise ZimError(f"Blob {blob_index} out of range")
    offsets = struct.unpack_from(
        f"<{offset_count}{'Q' if extended else 'I'}", cluster_data, 0
    )
    start, end = offsets[blob_index], offsets[blob_index + 1]
    if start > end or end > len(cluster_data):
        raise ZimError("Invalid blob offsets")
    return cluster_data[start:end]
