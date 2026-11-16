from __future__ import annotations

import json
import re
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
OUT = ROOT / ".scrape" / "wikipedia_batch_missing.json"
API = "https://zh.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "polvis-data-audit/1.0 (local research)"}
YEAR_RE = re.compile(r"(19[2-9]\d|200\d)")
BIRTH_RE = re.compile(r"(?:出生|生于)[^。\n]{0,30}?(19[2-9]\d|200\d)年")
NATIVE_RE = re.compile(r"(?:籍贯|籍貫|祖籍)[：:\s]*([^\n，。；|]{2,20})")
INFO_NATIVE_RE = re.compile(r"\|\s*(?:籍贯|籍貫|祖籍|native place|place of birth)\s*=\s*([^\n]+)")
INFO_BIRTH_RE = re.compile(r"\|\s*(?:出生日期|出生|birth date)\s*=\s*([^\n|]+)")


def clean(value: str) -> str:
    value = re.sub(r"<ref.*?</ref>|<ref[^>]*/>", "", value, flags=re.S)
    value = re.sub(r"\[\[([^|\]]+)(?:\|[^\]]*)?\]\]", r"\1", value)
    value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"''+", "", value)
    return re.sub(r"\s+", " ", value).strip(" ，。；:：|")


def parse(wikitext: str, extract: str) -> tuple[int | None, str | None]:
    birth_year = None
    for pattern, text in ((INFO_BIRTH_RE, wikitext), (BIRTH_RE, extract), (YEAR_RE, extract)):
        match = pattern.search(text)
        if match:
            year = re.search(r"(19[2-9]\d|200\d)", match.group(0))
            if year:
                birth_year = int(year.group(1))
                break
    native = None
    for pattern, text in ((INFO_NATIVE_RE, wikitext), (NATIVE_RE, extract)):
        match = pattern.search(text)
        if match:
            native = clean(match.group(1)).split(" ")[0]
            if native:
                break
    if not native:
        match = re.search(r"([\u4e00-\u9fa5]{2,15}(?:省|市|县))[\u4e00-\u9fa5]{0,8}人", extract)
        if match:
            native = match.group(1)
    return birth_year, native


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    names = [
        officer["name"] for officer in data["officers"]
        if not officer.get("birth_year") or not officer.get("native_place")
    ]
    rows: list[dict] = []
    client = httpx.Client(headers=HEADERS, timeout=45)
    for start in range(0, len(names), 20):
        batch = names[start:start + 20]
        for attempt in range(5):
            try:
                response = client.get(API, params={
                    "action": "query", "prop": "revisions|extracts",
                    "rvprop": "content", "rvslots": "main",
                    "explaintext": 1, "exintro": 1,
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
                    wikitext = (
                        page.get("revisions", [{}])[0]
                        .get("slots", {}).get("main", {}).get("*", "")
                    )
                    extract = page.get("extract", "")
                    birth, native = parse(wikitext, extract)
                    rows.append({
                        "name": name, "status": "ok", "title": page.get("title"),
                        "birth_year": birth, "native_place": native,
                        "extract": extract[:400],
                    })
                break
            except Exception as exc:  # noqa: BLE001
                print("retry", start, exc, flush=True)
                time.sleep(15 + attempt * 15)
        else:
            for name in batch:
                rows.append({"name": name, "status": "error"})
        print(f"batch {start // 20 + 1}: total {len(rows)}", flush=True)
        time.sleep(2)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ok={sum(1 for r in rows if r['status'] == 'ok')}")


if __name__ == "__main__":
    main()
