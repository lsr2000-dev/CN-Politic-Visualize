import json
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

DATE = re.compile(r"(\d{4})年(?:\s*(\d{1,2})月)?(?:\s*(\d{1,2})日)?")


def field(text: str, name: str) -> str:
    m = re.search(rf"\|\s*{name}\s*=\s*([^\n]+)", text)
    return m.group(1) if m else ""


def clean(value: str) -> str:
    value = re.sub(r"<ref.*?</ref>", "", value, flags=re.S)
    value = re.sub(r"<!--.*?-->", "", value, flags=re.S)
    value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), value)
    value = value.replace("'''", "").replace("''", "")
    value = re.sub(r"\[\[|\]\]", "", value)
    return re.sub(r"\s+", "", value).strip("，,。;；")


def parse(text: str) -> dict:
    out: dict = {}
    m = re.search(r"birth year and age\s*\|\s*(\d{4})", text) or re.search(r"\{\{bd\|(\d{4})", text)
    if not m:
        m = re.search(r"出生日期\s*=\s*[^\n]*?(\d{4})年", text)
    if m:
        out["birth_year"] = int(m.group(1))

    for key in ("籍贯", "出生地", "birth_place"):
        value = clean(field(text, key))
        if value:
            out["native_place"] = value
            break

    value = clean(field(text, "性别")) or clean(field(text, "sex"))
    if "女" in value:
        out["gender"] = "F"
    elif "男" in value:
        out["gender"] = "M"

    value = clean(field(text, "民族")) or clean(field(text, "ethnicity"))
    if value:
        out["ethnicity"] = value

    value = clean(field(text, "入党时间"))
    if value:
        dm = DATE.search(value)
        if dm:
            out["party_join_date"] = f"{int(dm.group(1)):04d}-{int(dm.group(2) or 1):02d}-01"
    if "party_join_date" not in out:
        m = re.search(r"(\d{4})年(?:\s*(\d{1,2})月)?加入中国共产党", text)
        if not m:
            m = re.search(r"(\d{4})年(?:\s*(\d{1,2})月)?入党", text)
        if m:
            out["party_join_date"] = f"{int(m.group(1)):04d}-{int(m.group(2) or 1):02d}-01"

    if "gender" not in out:
        head = text[:2500]
        if re.search(r"'''[^']{2,8}'''（?女", head) or "女，汉族" in head:
            out["gender"] = "F"
        elif re.search(r"'''[^']{2,8}'''（?男", head) or "男，汉族" in head:
            out["gender"] = "M"
    return out


def fetch(client: httpx.Client, name: str) -> str:
    for attempt in range(4):
        try:
            r = client.get("https://zh.wikipedia.org/w/api.php", params={
                "action": "query", "format": "json", "prop": "revisions",
                "rvprop": "content", "rvslots": "main", "titles": name, "redirects": 1,
            }, timeout=30)
            if r.status_code == 200:
                for page in r.json().get("query", {}).get("pages", {}).values():
                    revs = page.get("revisions") or []
                    if revs:
                        return revs[0]["slots"]["main"]["*"]
            if r.status_code == 429:
                time.sleep(5 + attempt * 5)
        except Exception:
            time.sleep(2)
    return ""


def main() -> None:
    dataset = json.loads((ROOT / "backend/app/data/dataset.json").read_text(encoding="utf-8"))
    merged_path = ROOT / ".scrape" / "officer_enrichment_merged.json"
    merged = json.loads(merged_path.read_text(encoding="utf-8")) if merged_path.exists() else {}
    names = [o["name"] for o in dataset["officers"]]
    client = httpx.Client(timeout=30, headers={"User-Agent": "polvis-demo/1.0"})
    for i, name in enumerate(names, 1):
        current = merged.get(name, {})
        if all(current.get(k) for k in ("birth_year", "native_place", "gender", "ethnicity", "party_join_date")):
            continue
        text = fetch(client, name)
        if text:
            parsed = parse(text)
            target = merged.setdefault(name, {})
            for key, value in parsed.items():
                if value and not target.get(key):
                    target[key] = value
        print(i, name, bool(text), flush=True)
        time.sleep(0.35)
    merged_path.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
