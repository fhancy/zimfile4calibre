import re

from zim_import.zim_reader import ZimArchive

with ZimArchive(r"E:\Downloads\gutenberg_en_all_2021-12.zim") as zim:
    for entry in zim.iter_entries():
        if (
            entry.namespace == "A"
            and entry.url.endswith(".65318.html")
            and "_cover." not in entry.url
        ):
            html = zim.read_content(entry).decode("utf-8", "replace")
            urls = re.findall(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", html, re.I)
            print("count", len(html), "urls", len(urls), "unique", len(set(urls)))
            for url in list(dict.fromkeys(urls))[:40]:
                print(url)
            break
