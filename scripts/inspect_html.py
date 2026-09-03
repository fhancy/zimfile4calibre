from zim_import.zim_reader import ZimArchive

needle = ".9996.html"
with ZimArchive(r"E:\Downloads\gutenberg_en_all_2021-12.zim") as zim:
    for entry in zim.iter_entries():
        if not entry.url.endswith(needle):
            continue
        print("NS", entry.namespace, "MIME", entry.mime, "URL", entry.url[:120])
        print("TITLE", entry.title[:80] if entry.title else "")
        if entry.namespace == "A" and entry.mime == "text/html" and "_cover." not in entry.url:
            html = zim.read_content(entry)
            text = html.decode("utf-8", "replace")
            print("HTML_BYTES", len(html))
            print("--- HEAD ---")
            print(text[:2500])
            print("--- LINKS ---")
            for line in text.splitlines():
                low = line.lower()
                if "src=" in low or "href=" in low or "url(" in low:
                    print(line.strip()[:200])
            break
