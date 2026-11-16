from __future__ import annotations

import json
import re
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
MISSING = ROOT / ".scrape" / "bio_missing_after_merge.json"
OUT = ROOT / ".scrape" / "baidu_final.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; polvis-data-audit/1.0)"}
DATE_RE = re.compile(r"(19[2-9]\d|200\d)年")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")


def clean(text: str) -> str:
    text = LINK_RE.sub(r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text)


def parse(text: str, name: str) -> tuple[int | None, str | None]:
    plain = clean(text)
    index = plain.find(name)
    window = plain[index:index + 1600] if index >= 0 else plain[:4000]
    birth = None
    for sentence in re.split(r"[。\n]", window):
        if "19" not in sentence and "20" not in sentence:
            continue
        match = DATE_RE.search(sentence)
        if match:
            birth = int(match.group(1))
            break
    native = None
    # "1955年3月出生于澳门，广东番禺人" / "1964年9月生，河南洛阳人"
    for match in re.finditer(r"(?:19[2-9]\d|200\d)年[^。\n]{0,80}", window):
        tail = match.group(0)
        if "人" not in tail:
            continue
        native_match = re.search(r"[，,、]\s*([\u4e00-\u9fa5]{2,18})人", tail)
        if native_match:
            native = native_match.group(1)
            break
    if not native:
        for match in re.finditer(r"[，,、]\s*([\u4e00-\u9fa5]{2,18})人", window):
            native = match.group(1)
            break
    if native:
        native = re.sub(r"^(?:男|女|汉族|中共|出生于|生于)", "", native)
        if "中国" in native or native in {"人民", "中华人民共和国"}:
            native = None
    return birth, native


def main() -> None:
    rows = json.loads(MISSING.read_text(encoding="utf-8"))
    names = [row["name"] for row in rows]
    out = []
    for index, name in enumerate(names, 1):
        from urllib.parse import quote
        url = "https://r.jina.ai/http://baike.baidu.com/item/" + quote(name)
        last = ""
        result = {"name": name, "status": "error", "error": last}
        for attempt in range(4):
            try:
                response = httpx.get(url, headers=HEADERS, timeout=90)
                if response.status_code == 429:
                    time.sleep(15 + attempt * 15)
                    continue
                response.raise_for_status()
                birth, native = parse(response.text, name)
                result = {
                    "name": name, "status": "ok", "birth_year": birth,
                    "native_place": native, "chars": len(response.text),
                }
                break
            except Exception as exc:  # noqa: BLE001
                last = str(exc)
                result["error"] = last
                time.sleep(5 + attempt * 5)
        out.append(result)
        if index % 10 == 0:
            OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{index}/{len(names)}", flush=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("done", len(out))


if __name__ == "__main__":
    main()
