from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
OUT = ROOT / ".scrape" / "wikipedia_missing.json"
API = "https://zh.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "polvis-data-audit/1.0 (local research)"}
YEAR_RE = re.compile(r"(19[2-9]\d|200\d)年")
BIRTH_RE = re.compile(r"(?:出生|生于)[^。\n]{0,30}?(19[2-9]\d|200\d)年")
NATIVE_RE = re.compile(r"(?:籍贯|籍貫|祖籍)[：:\s]*([^\n，。；、|]{2,20})")
INFO_NATIVE_RE = re.compile(r"\|\s*(?:籍贯|籍貫|祖籍)\s*=\s*([^\n|]+)")
INFO_BIRTH_RE = re.compile(r"\|\s*(?:出生日期|出生日期|出生)\s*=\s*([^\n|]+)")


def clean(value: str) -> str:
    value = re.sub(r"<ref.*?</ref>|<ref[^>]*/>", "", value, flags=re.S)
    value = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", value)
    value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"''+", "", value)
    return re.sub(r"\s+", " ", value).strip(" ，。；:：|")


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    names = [
        officer["name"] for officer in data["officers"]
        if not officer.get("birth_year") or not officer.get("native_place")
    ]

    def fetch(name: str) -> dict:
        try:
            search = httpx.get(API, params={
                "action": "query", "list": "search", "srsearch": name,
                "format": "json", "srlimit": 5,
            }, headers=HEADERS, timeout=20)
            search.raise_for_status()
            hits = search.json().get("query", {}).get("search", [])
            titles = [hit["title"] for hit in hits if name in hit["title"]]
            if not titles:
                titles = [hit["title"] for hit in hits[:2]]
            if not titles:
                return {"name": name, "status": "no_page"}
            title = titles[0]
            page = httpx.get(API, params={
                "action": "query", "prop": "revisions|extracts",
                "rvprop": "content", "rvslots": "main",
                "explaintext": 1, "exintro": 1,
                "titles": title, "redirects": 1, "format": "json",
            }, headers=HEADERS, timeout=25)
            page.raise_for_status()
            pages = page.json().get("query", {}).get("pages", {})
            payload = next(iter(pages.values()))
            wikitext = (
                payload.get("revisions", [{}])[0]
                .get("slots", {}).get("main", {}).get("*", "")
            )
            extract = payload.get("extract", "")
            birth_year = None
            for pattern, text in ((INFO_BIRTH_RE, wikitext), (BIRTH_RE, extract), (YEAR_RE, extract)):
                match = pattern.search(text)
                if match:
                    year_match = re.search(r"(19[2-9]\d|200\d)", match.group(0))
                    if year_match:
                        birth_year = int(year_match.group(1))
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
            return {
                "name": name, "status": "ok", "title": title,
                "birth_year": birth_year, "native_place": native,
                "extract": extract[:500],
            }
        except Exception as exc:  # noqa: BLE001
            return {"name": name, "status": "error", "error": str(exc)}

    rows = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(fetch, name) for name in names]
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 40 == 0:
                print(f"fetched {index}/{len(names)}", flush=True)
    rows.sort(key=lambda row: names.index(row["name"]))
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for row in rows if row["status"] == "ok")
    print(f"wrote {OUT} ok={ok} failed={len(rows) - ok}")


if __name__ == "__main__":
    main()
