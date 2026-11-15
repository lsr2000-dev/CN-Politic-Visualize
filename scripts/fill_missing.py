import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def parse(text: str) -> dict:
    out: dict = {}
    m = re.search(r"(\d{4})年(?:\s*(\d{1,2})月)?加入中国共产党", text)
    if m:
        out["party_join_date"] = f"{int(m.group(1)):04d}-{int(m.group(2) or 1):02d}-01"
    m = re.search(r"出生日期[^\d]{0,10}(\d{4})年(?:\s*(\d{1,2})月)?", text)
    if not m:
        m = re.search(r"(\d{4})年(?:\s*(\d{1,2})月)生", text)
    if m:
        out["birth_year"] = int(m.group(1))
    for pat in (
        r"籍贯[^\u4e00-\u9fa5]{0,10}([\u4e00-\u9fa5]{2,20})",
        r"(?:生|出生)[，,]\s*([\u4e00-\u9fa5]{2,20}?)人",
        r"(?:男|女)[，,]\s*(?:汉族|[\u4e00-\u9fa5]{1,6}族)[，,]\s*([\u4e00-\u9fa5]{2,20}?)人",
    ):
        m = re.search(pat, text)
        if m:
            out["native_place"] = m.group(1).strip()
            break
    return out


def main() -> None:
    dataset = json.loads((ROOT / "backend/app/data/dataset.json").read_text(encoding="utf-8"))
    path = ROOT / ".scrape" / "officer_enrichment_merged.json"
    merged = json.loads(path.read_text(encoding="utf-8"))
    names = []
    for officer in dataset["officers"]:
        name = officer["name"]
        fields = merged.get(name, {})
        if not fields.get("party_join_date") or not fields.get("native_place") or not fields.get("birth_year"):
            names.append(name)
    client = httpx.Client(timeout=60, headers={"User-Agent": "polvis-demo/1.0"})
    for index, name in enumerate(names, 1):
        text = ""
        for attempt in range(3):
            try:
                r = client.get("https://r.jina.ai/http://baike.baidu.com/item/" + quote(name))
                if r.status_code == 200:
                    text = r.text
                    break
            except Exception:
                pass
            time.sleep(1 + attempt)
        if text:
            fields = parse(text)
            target = merged.setdefault(name, {})
            for key, value in fields.items():
                if value and not target.get(key):
                    target[key] = value
        print(index, name, len(text), flush=True)
        time.sleep(0.4)
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
