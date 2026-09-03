"""Build a minimal uncompressed OpenZIM v5 file for unit tests."""

from __future__ import annotations

import hashlib
import os
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path

from zim_import.zim_reader import COMP_NONE, HEADER_SIZE, MIME_REDIRECT, ZIM_MAGIC

_HEADER_STRUCT = struct.Struct("<IHH16sIIQQQQIIQ")


@dataclass(frozen=True)
class TestEntry:
    namespace: str
    mime: str
    url: str
    title: str = ""
    redirect_url: str | None = None
    content: bytes | None = None


def build_zim_v5(entries: list[TestEntry]) -> bytes:
    """Return a complete ZIM v5 blob whose dirents match *entries*."""
    if not entries:
        raise ValueError("Need at least one entry")

    sorted_entries = sorted(entries, key=lambda e: (e.namespace, e.url))
    mimes: list[str] = []
    for entry in sorted_entries:
        if entry.redirect_url is None and entry.mime not in mimes:
            mimes.append(entry.mime)

    mime_bytes = b"".join(m.encode("utf-8") + b"\x00" for m in mimes) + b"\x00"
    url_to_index = {
        (entry.namespace, entry.url): index for index, entry in enumerate(sorted_entries)
    }

    blobs: list[bytes] = []
    blob_ids: dict[tuple[str, str], int] = {}
    include_cluster = any(entry.content is not None for entry in sorted_entries)
    if include_cluster:
        for entry in sorted_entries:
            if entry.redirect_url is not None:
                continue
            blob_ids[(entry.namespace, entry.url)] = len(blobs)
            blobs.append(entry.content or b"")
        cluster_blob = _encode_uncompressed_cluster(blobs)
    else:
        cluster_blob = b""

    dirents: list[bytes] = []
    for entry in sorted_entries:
        if entry.redirect_url is not None:
            target = url_to_index[(entry.namespace, entry.redirect_url)]
            dirents.append(_encode_redirect(entry, target))
        elif include_cluster:
            dirents.append(
                _encode_article(
                    entry,
                    mimes.index(entry.mime),
                    cluster=0,
                    blob=blob_ids[(entry.namespace, entry.url)],
                )
            )
        else:
            dirents.append(_encode_article(entry, mimes.index(entry.mime)))

    dirent_blob = b"".join(dirents)
    mime_list_pos = HEADER_SIZE
    cluster_start = mime_list_pos + len(mime_bytes)
    dirent_start = cluster_start + len(cluster_blob)
    offsets: list[int] = []
    cursor = dirent_start
    for dirent in dirents:
        offsets.append(cursor)
        cursor += len(dirent)

    n = len(sorted_entries)
    url_ptr_pos = cursor
    url_ptrs = struct.pack(f"<{n}Q", *offsets)
    title_ptr_pos = url_ptr_pos + len(url_ptrs)
    title_order = sorted(range(n), key=lambda i: (sorted_entries[i].title, i))
    title_ptrs = struct.pack(f"<{n}I", *title_order)
    cluster_ptr_pos = title_ptr_pos + len(title_ptrs)
    cluster_count = 1 if include_cluster else 0
    cluster_ptrs = struct.pack("<Q", cluster_start) if include_cluster else b""
    checksum_pos = cluster_ptr_pos + len(cluster_ptrs)

    header = _HEADER_STRUCT.pack(
        ZIM_MAGIC,
        5,
        0,
        b"\x00" * 16,
        n,
        cluster_count,
        url_ptr_pos,
        title_ptr_pos,
        cluster_ptr_pos,
        mime_list_pos,
        0xFFFFFFFF,
        0xFFFFFFFF,
        checksum_pos,
    )
    body = header + mime_bytes + cluster_blob + dirent_blob + url_ptrs + title_ptrs + cluster_ptrs
    return body + hashlib.md5(body).digest()


def write_zim_v5(entries: list[TestEntry]) -> Path:
    fd, name = tempfile.mkstemp(suffix=".zim")
    os.close(fd)
    path = Path(name)
    path.write_bytes(build_zim_v5(entries))
    return path


def _encode_uncompressed_cluster(blobs: list[bytes]) -> bytes:
    offset_count = len(blobs) + 1
    header_size = 4 * offset_count
    offsets = [header_size]
    for blob in blobs:
        offsets.append(offsets[-1] + len(blob))
    table = struct.pack(f"<{offset_count}I", *offsets)
    return bytes([COMP_NONE]) + table + b"".join(blobs)


def _encode_article(
    entry: TestEntry, mime_index: int, cluster: int = 0, blob: int = 0
) -> bytes:
    return b"".join(
        (
            struct.pack("<HBcI", mime_index, 0, entry.namespace.encode("ascii"), 0),
            struct.pack("<II", cluster, blob),
            entry.url.encode("utf-8") + b"\x00",
            entry.title.encode("utf-8") + b"\x00",
        )
    )


def _encode_redirect(entry: TestEntry, target_index: int) -> bytes:
    return b"".join(
        (
            struct.pack("<HBcI", MIME_REDIRECT, 0, entry.namespace.encode("ascii"), 0),
            struct.pack("<I", target_index),
            entry.url.encode("utf-8") + b"\x00",
            entry.title.encode("utf-8") + b"\x00",
        )
    )
