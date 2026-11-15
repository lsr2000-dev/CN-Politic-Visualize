import json
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def parse(text: str) -> dict:
    out: dict = {}
    m = re.search(r"(\d{4})年(?:\s*(\d{1,2})月)?加入中国共产党", text)
    if m:
        out["party_join_date"] = f"{int(m.group(1)):04d}-{int(m.group(2) or 1):02d}-01"
    m = re.search(r"（\s*(\d{4})年(?:\s*(\d{1,2})月)?", text)
    if m:
        out["birth_year"] = int(m.group(1))
    for pat in (
        r"(?:生|出生)[，,]\s*([\u4e00-\u9fa5]{2,20}?)人",
        r"[，,]\s*([\u4e00-\u9fa5]{2,20}?)人[，,。]",
    ):
        m = re.search(pat, text[:800])
        if m:
            out["native_place"] = m.group(1)
            break
    return out


def main() -> None:
    dataset = json.loads((ROOT / "backend/app/data/dataset.json").read_text(encoding="utf-8"))
    path = ROOT / ".scrape" / "officer_enrichment_merged.json"
    merged = json.loads(path.read_text(encoding="utf-8"))
    names = []
    for officer in dataset["officers"]:
        fields = merged.get(officer["name"], {})
        if not fields.get("party_join_date") or not fields.get("native_place") or not fields.get("birth_year"):
            names.append(officer["name"])
    client = httpx.Client(timeout=30, headers={"User-Agent": "polvis-demo/1.0"})
    for index, name in enumerate(names, 1):
        text = ""
        for attempt in range(3):
            try:
                r = client.get("https://zh.wikipedia.org/w/api.php", params={
                    "action": "query", "format": "json", "prop": "extracts",
                    "explaintext": 1, "titles": name, "redirects": 1,
                })
                if r.status_code == 200:
                    for page in r.json().get("query", {}).get("pages", {}).values():
                        text = page.get("extract", "")
                        if text:
                            break
                if text:
                    break
            except Exception:
                pass
            time.sleep(2)
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
