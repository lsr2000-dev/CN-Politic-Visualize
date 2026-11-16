from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".scrape" / "baidu_36.json"
NAMES = [line.split("\t")[0] for line in (ROOT / "scripts" / "prov_only_clean.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; polvis-data-audit/1.0)"}
DATE_RE = re.compile(r"(19[2-9]\d|200\d)年")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
NATIVE_RE = re.compile(r"[，,、]\s*([\u4e00-\u9fa5]{2,18})人")


def clean(text: str) -> str:
    text = LINK_RE.sub(r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text)


def parse(text: str, name: str) -> tuple[int | None, str | None]:
    plain = clean(text)
    anchor = re.search(re.escape(name) + r"[，,]\s*(?:男|女)", plain)
    window = plain[anchor.start():anchor.start() + 900] if anchor else plain[:5000]
    birth = None
    match = DATE_RE.search(window)
    if match:
        birth = int(match.group(1))
    native = None
    for match in re.finditer(r"(?:19[2-9]\d|200\d)年[^。\n]{0,100}", window):
        native_match = NATIVE_RE.search(match.group(0))
        if native_match:
            native = native_match.group(1)
            break
    if not native:
        native_match = NATIVE_RE.search(window)
        if native_match:
            native = native_match.group(1)
    if native:
        native = re.sub(r"^(?:男|女|汉族|中共|出生于|生于)", "", native)
        if "中国" in native or native in {"人民", "中华人民共和国"}:
            native = None
    return birth, native


rows = []
for index, name in enumerate(NAMES, 1):
    url = "https://r.jina.ai/http://baike.baidu.com/item/" + quote(name)
    result = {"name": name, "status": "error"}
    for attempt in range(4):
        try:
            response = httpx.get(url, headers=HEADERS, timeout=90)
            if response.status_code == 429:
                time.sleep(15 + attempt * 15)
                continue
            response.raise_for_status()
            birth, native = parse(response.text, name)
            result = {"name": name, "status": "ok", "birth_year": birth, "native_place": native}
            break
        except Exception as exc:  # noqa: BLE001
            result["error"] = str(exc)
            time.sleep(5 + attempt * 5)
    rows.append(result)
    if index % 5 == 0:
        OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{index}/{len(NAMES)}", flush=True)
OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("done")
