from __future__ import annotations

import json
import re
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
OUT = ROOT / ".scrape" / "wikipedia_all_native.json"
API = "https://zh.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "polvis-data-audit/1.0 (local research)"}
LINK_RE = re.compile(r"\[\[([^|\]]+)(?:\|[^\]]*)?\]\]")
NATIVE_FIELD = re.compile(r"\|\s*(?:籍贯|籍貫|祖籍|native place)\s*=\s*([^\n]+)")
NATIVE_INTRO = re.compile(r"[，,]\s*([\u4e00-\u9fa5]{2,18})人")


def clean(value: str) -> str:
    value = re.sub(r"<ref.*?</ref>|<ref[^>]*/>", "", value, flags=re.S)
    value = LINK_RE.sub(r"\1", value)
    value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"''+", "", value)
    return re.sub(r"\s+", "", value).strip("，。；:：|")


def parse(wikitext: str, extract: str) -> str | None:
    match = NATIVE_FIELD.search(wikitext)
    if match:
        native = clean(match.group(1))
        if native and "中国" not in native:
            return native
    first = extract.split("。")[0]
    match = NATIVE_INTRO.search(first)
    if match:
        native = match.group(1)
        if "中国" not in native and native not in {"人民", "汉族"}:
            return native
    return None


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    names = [officer["name"] for officer in data["officers"]]
    rows = []
    client = httpx.Client(headers=HEADERS, timeout=45)
    for start in range(0, len(names), 20):
        batch = names[start:start + 20]
        for attempt in range(5):
            try:
                response = client.get(API, params={
                    "action": "query", "prop": "revisions|extracts",
                    "rvprop": "content", "rvslots": "main",
                    "explaintext": 1, "exintro": 1, "exlimit": "max",
                    "titles": "|".join(batch), "redirects": 1, "format": "json",
                })
                response.raise_for_status()
                pages = response.json().get("query", {}).get("pages", {})
                by_title = {page.get("title"): page for page in pages.values()}
                for name in batch:
                    page = by_title.get(name)
                    if not page or "missing" in page:
                        rows.append({"name": name, "status": "no_page"})
                        continue
                    wikitext = page.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("*", "")
                    extract = page.get("extract", "")
                    rows.append({
                        "name": name, "status": "ok", "title": page.get("title"),
                        "native_place": parse(wikitext, extract),
                        "extract": extract[:300],
                    })
                break
            except Exception as exc:  # noqa: BLE001
                print("retry", start, exc, flush=True)
                time.sleep(15 + attempt * 15)
        else:
            for name in batch:
                rows.append({"name": name, "status": "error"})
        print(f"batch {start // 20 + 1}: {len(rows)}", flush=True)
        time.sleep(1.5)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
