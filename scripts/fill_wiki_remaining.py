import asyncio
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def clean(value: str) -> str:
    value = re.sub(r"<ref.*?</ref>", "", value or "", flags=re.S)
    value = re.sub(r"\[\]|\[\[|\]\]", "", value or "")
    value = re.sub(r"\([^)]*\)", "", value)
    value = value.replace("中华人民共和国", "").replace("东北大行政区", "")
    return re.sub(r"\s+", "", value).strip("，,。;；")


def parse(text: str) -> dict:
    out: dict = {}
    m = re.search(r"(\d{4})年(?:\s*(\d{1,2})月)?加入中国共产党", text)
    if not m:
        m = re.search(r"入党时间[^\d]{0,10}(\d{4})年(?:\s*(\d{1,2})月)?", text)
    if m:
        out["party_join_date"] = f"{int(m.group(1)):04d}-{int(m.group(2) or 1):02d}-01"

    m = re.search(r"出生日期\s*=\s*[^\n]*?(\d{4})年", text)
    if m:
        out["birth_year"] = int(m.group(1))

    for pat in (
        r"\|\s*籍贯\s*=\s*([^\n]+)",
        r"\|\s*出生地\s*=\s*([^\n]+)",
    ):
        m = re.search(pat, text)
        if m:
            value = clean(m.group(1))
            if value:
                out["native_place"] = value
                break
    if "native_place" not in out:
        m = re.search(r"(?:生|出生)[，,]\s*([\u4e00-\u9fa5]{2,20}?)人", text)
        if m:
            out["native_place"] = m.group(1)
    return out


async def fetch(client, sem, url):
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=60)
                if r.status_code == 200:
                    return r.text
            except Exception:
                pass
            await asyncio.sleep(1)
    return ""


async def main() -> None:
    dataset = json.loads((ROOT / "backend/app/data/dataset.json").read_text(encoding="utf-8"))
    path = ROOT / ".scrape" / "officer_enrichment_merged.json"
    merged = json.loads(path.read_text(encoding="utf-8"))
    names = []
    for officer in dataset["officers"]:
        name = officer["name"]
        fields = merged.get(name, {})
        if not fields.get("party_join_date") or not fields.get("native_place") or not fields.get("birth_year"):
            names.append(name)
    sem = asyncio.Semaphore(2)
    async with httpx.AsyncClient(headers={"User-Agent": "polvis-demo/1.0"}) as client:
        tasks = []
        for name in names:
            tasks.append(fetch(client, sem, "https://r.jina.ai/http://baike.baidu.com/item/" + quote(name)))
        for name, text in zip(names, await asyncio.gather(*tasks)):
            if text:
                fields = parse(text)
                target = merged.setdefault(name, {})
                for key, value in fields.items():
                    if value and not target.get(key):
                        target[key] = value
            print(name, len(text), flush=True)
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
