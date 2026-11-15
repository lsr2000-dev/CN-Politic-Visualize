import asyncio
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

DATE = re.compile(r"(\d{4})年(?:\s*(\d{1,2})月)?")


def parse(text: str) -> dict:
    out: dict = {}
    m = re.search(r"(\d{4})年(?:\s*(\d{1,2})月)?加入中国共产党", text)
    if not m:
        m = re.search(r"(\d{4})年(?:\s*(\d{1,2})月)?入党", text)
    if m:
        out["party_join_date"] = f"{int(m.group(1)):04d}-{int(m.group(2) or 1):02d}-01"

    # 首段：姓名（1962年6月—），男，汉族，广东惠州人
    m = re.search(r"（\s*(\d{4})年(?:\s*(\d{1,2})月)?", text)
    if m:
        out["birth_year"] = int(m.group(1))

    m = re.search(r"(?:男|女)[，,]\s*(?:汉族|[\u4e00-\u9fa5]{1,6}族)[，,]\s*([\u4e00-\u9fa5]{2,20}?)人", text)
    if m:
        out["native_place"] = m.group(1)
    return out


async def fetch(client: httpx.AsyncClient, sem: asyncio.Semaphore, name: str) -> str:
    async with sem:
        url = "https://r.jina.ai/http://zh.wikipedia.org/wiki/" + quote(name)
        for attempt in range(3):
            try:
                r = await client.get(url, timeout=60)
                if r.status_code == 200:
                    return r.text
            except Exception:
                pass
            await asyncio.sleep(1 + attempt)
    return ""


async def main() -> None:
    dataset = json.loads((ROOT / "backend/app/data/dataset.json").read_text(encoding="utf-8"))
    merged_path = ROOT / ".scrape" / "officer_enrichment_merged.json"
    merged = json.loads(merged_path.read_text(encoding="utf-8")) if merged_path.exists() else {}
    names = [o["name"] for o in dataset["officers"]
             if not merged.get(o["name"], {}).get("party_join_date")
             or not merged.get(o["name"], {}).get("native_place")
             or not merged.get(o["name"], {}).get("birth_year")]
    sem = asyncio.Semaphore(4)
    async with httpx.AsyncClient(headers={"User-Agent": "polvis-demo/1.0"}) as client:
        tasks = [fetch(client, sem, name) for name in names]
        for name, text in zip(names, await asyncio.gather(*tasks)):
            if text:
                fields = parse(text)
                target = merged.setdefault(name, {})
                for key, value in fields.items():
                    if value and not target.get(key):
                        target[key] = value
            print(name, len(text), flush=True)
    merged_path.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
