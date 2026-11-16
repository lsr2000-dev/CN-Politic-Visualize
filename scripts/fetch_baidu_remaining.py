from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
OUT = ROOT / ".scrape" / "baidu_remaining.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; polvis-data-audit/1.0)"}
DATE_RE = re.compile(r"(19[2-9]\d|200\d)年")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
BIRTH_NATIVE_RE = re.compile(
    r"(?:19[2-9]\d|200\d)年(?:\d{1,2}月)?(?:生|出生)[，,、\s]*"
    r"([\u4e00-\u9fa5]{2,24}?)人"
)


def clean(text: str) -> str:
    text = LINK_RE.sub(r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text)


def parse(text: str, name: str) -> tuple[int | None, str | None]:
    plain = clean(text)
    anchor = re.search(re.escape(name) + r"[，,]\s*(?:男|女)", plain)
    window = plain[anchor.start():anchor.start() + 600] if anchor else plain[:4000]
    birth = None
    match = DATE_RE.search(window)
    if match:
        birth = int(match.group(1))
    native = None
    match = BIRTH_NATIVE_RE.search(window)
    if match:
        native = match.group(1).strip()
    if not native:
        match = re.search(r"(?:籍贯|祖籍)[：:\s]*([^\n，。；]{2,20})", window)
        if match:
            native = match.group(1).strip()
    if native:
        native = re.sub(r"^(?:男|女|汉族|中共)", "", native).strip()
        if "中国" in native or native in {"人民", "中华人民共和国"}:
            native = None
    return birth, native


def fetch(name: str) -> dict:
    url = "https://r.jina.ai/http://baike.baidu.com/item/" + quote(name)
    last = ""
    for attempt in range(5):
        try:
            response = httpx.get(url, headers=HEADERS, timeout=90)
            if response.status_code == 429:
                time.sleep(15 + attempt * 20)
                continue
            response.raise_for_status()
            birth, native = parse(response.text, name)
            return {
                "name": name, "status": "ok", "birth_year": birth,
                "native_place": native, "chars": len(response.text),
            }
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
            time.sleep(5 + attempt * 5)
    return {"name": name, "status": "error", "error": last}


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    names = [
        officer["name"] for officer in data["officers"]
        if not officer.get("birth_year") or not officer.get("native_place")
    ]
    rows = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(fetch, name): name for name in names}
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 10 == 0:
                OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"fetched {index}/{len(names)}", flush=True)
    rows.sort(key=lambda row: names.index(row["name"]))
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ok={sum(1 for r in rows if r['status'] == 'ok')}")


if __name__ == "__main__":
    main()
