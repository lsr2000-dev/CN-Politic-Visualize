from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
WIKI = ROOT / ".scrape" / "wikipedia_batch_missing.json"
OUT = ROOT / ".scrape" / "baidu_missing.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; polvis-data-audit/1.0)"}
DATE_RE = re.compile(r"(19[2-9]\d|200\d)年")
NATIVE_AFTER_BIRTH = re.compile(
    r"(?:19[2-9]\d|200\d)年(?:\d{1,2}月)?(?:生|出生)?[，,、\s]*"
    r"([\u4e00-\u9fa5]{2,20}?)人"
)
NATIVE_FIELD = re.compile(r"(?:籍贯|籍貫|祖籍)[：:\s]*([^\n，。；]{2,20})")


def parse(text: str) -> tuple[int | None, str | None]:
    birth = None
    match = DATE_RE.search(text)
    if match:
        birth = int(match.group(1))
    native = None
    match = NATIVE_FIELD.search(text)
    if match:
        native = match.group(1).strip()
    if not native:
        match = NATIVE_AFTER_BIRTH.search(text)
        if match:
            native = match.group(1).strip()
    if native:
        native = re.sub(r"^(?:男|女|汉族|中共)", "", native).strip()
        native = re.sub(r"(?:省|市|县|区)$", "", native) if len(native) > 6 else native
        if native in {"中国", "人民", "中华人民共和国"} or "中国" in native:
            native = None
    return birth, native


def fetch(name: str) -> dict:
    from urllib.parse import quote
    url = "https://r.jina.ai/http://baike.baidu.com/item/" + quote(name)
    for attempt in range(4):
        try:
            response = httpx.get(url, headers=HEADERS, timeout=90)
            if response.status_code == 429:
                time.sleep(20 + attempt * 20)
                continue
            response.raise_for_status()
            text = response.text
            birth, native = parse(text)
            return {
                "name": name, "status": "ok", "title": text.splitlines()[0][:80],
                "birth_year": birth, "native_place": native,
            }
        except Exception as exc:  # noqa: BLE001
            time.sleep(5 + attempt * 5)
            last = str(exc)
    return {"name": name, "status": "error", "error": last}


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    wiki = {
        item["name"]: item
        for item in json.loads(WIKI.read_text(encoding="utf-8"))
        if item.get("status") == "ok"
    }
    names = []
    for officer in data["officers"]:
        name = officer["name"]
        if officer.get("birth_year") and officer.get("native_place"):
            continue
        wiki_item = wiki.get(name, {})
        native = wiki_item.get("native_place")
        if native and ("中国" in native or native in {"人民", "中华人民共和国"} or native.startswith("[[")):
            native = None
        if native and officer.get("birth_year") and officer.get("native_place"):
            continue
        names.append(name)

    rows = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(fetch, name): name for name in names}
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 20 == 0:
                print(f"fetched {index}/{len(names)}", flush=True)
    rows.sort(key=lambda row: names.index(row["name"]))
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ok={sum(1 for r in rows if r['status'] == 'ok')}")


if __name__ == "__main__":
    main()
