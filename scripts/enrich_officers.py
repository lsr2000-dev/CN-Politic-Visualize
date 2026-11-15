import json
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

DATE = re.compile(r"(\d{4})年(?:\s*(\d{1,2})月)?(?:\s*(\d{1,2})日)?")
FIELD = lambda name: re.compile(rf"\|\s*{name}\s*=\s*([^\n|]+)")


def strip_wiki(value: str) -> str:
    value = re.sub(r"<ref.*?</ref>", "", value, flags=re.S)
    value = re.sub(r"<!--.*?-->", "", value, flags=re.S)
    value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), value)
    value = value.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", "", value).strip("，,。;；")


def page_text(client: httpx.Client, title: str) -> str:
    try:
        r = client.get("https://zh.wikipedia.org/w/api.php", params={
            "action": "query", "format": "json", "prop": "revisions",
            "rvprop": "content", "rvslots": "main", "titles": title, "redirects": 1,
        })
        pages = r.json().get("query", {}).get("pages", {})
        for page in pages.values():
            if "missing" in page:
                return ""
            revisions = page.get("revisions") or []
            if revisions:
                return revisions[0]["slots"]["main"]["*"]
    except Exception:
        pass
    return ""


def search_title(client: httpx.Client, name: str) -> str:
    try:
        r = client.get("https://zh.wikipedia.org/w/api.php", params={
            "action": "query", "format": "json", "list": "search",
            "srsearch": f"{name} 中国 政治人物", "srlimit": 5,
        })
        for item in r.json().get("query", {}).get("search", []):
            title = item["title"]
            if name in title or title in name:
                return title
        results = r.json().get("query", {}).get("search", [])
        if results:
            return results[0]["title"]
    except Exception:
        pass
    return ""


def parse(text: str) -> dict:
    out = {}
    if not text:
        return out

    m = re.search(r"birth year and age\s*\|\s*(\d{4})", text) or re.search(r"\{\{bd\|(\d{4})", text)
    if not m:
        m = re.search(r"出生日期\s*=\s*[^\n]*?(\d{4})年", text)
    if not m:
        m = re.search(r"'''[^']{2,8}'''（[^）]*?(\d{4})年", text)
    if m:
        out["birth_year"] = int(m.group(1))

    native = ""
    for key in ("籍贯", "出生地", "birth_place"):
        fm = FIELD(key).search(text)
        if fm:
            native = strip_wiki(fm.group(1))
            if native:
                break
    if native:
        out["native_place"] = native

    gm = FIELD("性别").search(text) or FIELD("sex").search(text)
    if gm:
        raw = strip_wiki(gm.group(1))
        if "女" in raw:
            out["gender"] = "F"
        elif "男" in raw:
            out["gender"] = "M"

    em = FIELD("民族").search(text) or FIELD("ethnicity").search(text)
    if em:
        out["ethnicity"] = strip_wiki(em.group(1))

    pm = FIELD("入党时间").search(text)
    if pm:
        raw = strip_wiki(pm.group(1))
        dm = DATE.search(raw)
        if dm:
            month = dm.group(2) or "01"
            day = dm.group(3) or "01"
            out["party_join_date"] = f"{int(dm.group(1)):04d}-{int(month):02d}-{int(day):02d}"
    if "party_join_date" not in out:
        m = re.search(r"(\d{4})年(?:\s*(\d{1,2})月)?加入中国共产党", text)
        if m:
            month = m.group(2) or "01"
            out["party_join_date"] = f"{int(m.group(1)):04d}-{int(month):02d}-01"

    if "gender" not in out:
        head = text[:3000]
        if re.search(r"'''[^']{2,8}'''（?女", head) or "女，汉族" in head:
            out["gender"] = "F"
        elif re.search(r"'''[^']{2,8}'''（?男", head) or "男，汉族" in head:
            out["gender"] = "M"
    return out


def main() -> None:
    dataset = json.loads((ROOT / "backend/app/data/dataset.json").read_text(encoding="utf-8"))
    missing = [o["name"] for o in dataset["officers"]
               if not o.get("birth_year") or not o.get("native_place")
               or not o.get("gender") or not o.get("ethnicity")
               or not o.get("party_join_date")]
    client = httpx.Client(timeout=30, headers={"User-Agent": "polvis-demo/1.0"})
    result = {}
    for index, name in enumerate(missing, 1):
        text = page_text(client, name)
        if not text:
            title = search_title(client, name)
            if title and title != name:
                text = page_text(client, title)
        if text:
            result[name] = parse(text)
        print(index, name, bool(text), flush=True)
        time.sleep(0.25)
    (ROOT / ".scrape").mkdir(exist_ok=True)
    (ROOT / ".scrape" / "officer_enrichment.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
