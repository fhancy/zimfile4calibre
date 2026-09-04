from collections import defaultdict

from zim_import.gutenberg_catalog import BOOK_HTML, COVER_HTML
from zim_import.zim_reader import ZimArchive

ids = {50075, 51418, 44822, 21374, 9996}
hits: dict[int, list[tuple[str, str, bool]]] = defaultdict(list)

with ZimArchive(r"E:\Downloads\gutenberg_en_all_2021-12.zim") as zim:
    for entry in zim.iter_entries():
        if entry.namespace != "A" or entry.mime != "text/html":
            continue
        match = BOOK_HTML.match(entry.url)
        if not match:
            continue
        gid = int(match.group("id"))
        if gid in ids:
            hits[gid].append(
                (entry.url, entry.title, bool(COVER_HTML.match(entry.url)))
            )

for gid in sorted(hits):
    print("===", gid, "count", len(hits[gid]))
    for url, title, cover in hits[gid]:
        kind = "cover" if cover else "page"
        print(f"  {kind:5} title={title[:80]!r}")
        print(f"        url={url[:100]!r}")
