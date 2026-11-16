from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parent.parent
MISSING = ROOT / ".scrape" / "bio_missing_after_merge.json"
OUT = ROOT / ".scrape" / "baidu_anchor.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; polvis-data-audit/1.0)"}
DATE_RE = re.compile(r"(19[2-9]\d|200\d)年")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
NATIVE_AFTER = re.compile(r"[，,、]\s*([\u4e00-\u9fa5]{2,18})人")


def clean(text: str) -> str:
    text = LINK_RE.sub(r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text)


def parse(text: str, name: str) -> tuple[int | None, str | None]:
    plain = clean(text)
    anchor = re.search(re.escape(name) + r"[，,]\s*(?:男|女)", plain)
    window = plain[anchor.start():anchor.start() + 800] if anchor else plain[:5000]
    birth = None
    match = DATE_RE.search(window)
    if match:
        birth = int(match.group(1))
    native = None
    # Prefer a place immediately after birth: "1957年7月生，辽宁鞍山人"
    for match in re.finditer(r"(?:19[2-9]\d|200\d)年[^。\n]{0,80}", window):
        tail = match.group(0)
        native_match = NATIVE_AFTER.search(tail)
        if native_match:
            native = native_match.group(1)
            break
    if not native:
        native_match = NATIVE_AFTER.search(window)
        if native_match:
            native = native_match.group(1)
    if native:
        native = re.sub(r"^(?:男|女|汉族|中共|出生于|生于)", "", native)
        if "中国" in native or native in {"人民", "中华人民共和国"}:
            native = None
    return birth, native


def fetch(name: str) -> dict:
    url = "https://r.jina.ai/http://baike.baidu.com/item/" + quote(name)
    last = ""
    for attempt in range(4):
        try:
            response = httpx.get(url, headers=HEADERS, timeout=90)
            if response.status_code == 429:
                time.sleep(15 + attempt * 15)
                continue
            response.raise_for_status()
            birth, native = parse(response.text, name)
            return {
                "name": name, "status": "ok", "birth_year": birth,
                "native_place": native, "anchor": bool(re.search(re.escape(name) + r"[，,]\s*(?:男|女)", response.text)),
            }
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
            time.sleep(4 + attempt * 4)
    return {"name": name, "status": "error", "error": last}


def main() -> None:
    names = [row["name"] for row in json.loads(MISSING.read_text(encoding="utf-8"))]
    rows = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(fetch, name): name for name in names}
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 10 == 0:
                OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"{index}/{len(names)}", flush=True)
    rows.sort(key=lambda row: names.index(row["name"]))
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main()
