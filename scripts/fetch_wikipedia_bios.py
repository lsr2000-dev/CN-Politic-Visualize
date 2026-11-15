import json
import re
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"


def active_missing() -> list[str]:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    active_ids = {t["officer_id"] for t in data["tenures"] if t["end_date"] is None}
    names = []
    for officer in data["officers"]:
        if officer["id"] in active_ids and (not officer.get("birth_year") or not officer.get("native_place")):
            names.append(officer["name"])
    return names


def parse_intro(text: str) -> dict | None:
    if "可以指" in text[:30] or "可以指" in text[:100]:
        return None
    birth = re.search(r"（(19[2-9]\d)年", text)
    if not birth:
        birth = re.search(r"(19[2-9]\d)年(?:\d{1,2}月)?(?:生|出生)", text)
    native = re.search(r"[，,]([\u4e00-\u9fa5]{2,15})人[，,。]", text)
    if not native:
        native = re.search(r"籍贯[：:是为\s]*([\u4e00-\u9fa5]{2,15})", text)
    if not birth:
        return None
    return {
        "birth_year": int(birth.group(1)),
        "native_place": native.group(1) if native else None,
    }


def main() -> None:
    names = active_missing()
    client = httpx.Client(timeout=30, headers={"User-Agent": "polvis-demo/1.0"})
    result: dict[str, dict] = {}
    for start in range(0, len(names), 20):
        batch = names[start:start + 20]
        try:
            response = client.get(
                "https://zh.wikipedia.org/w/api.php",
                params={
                    "action": "query", "format": "json", "prop": "extracts",
                    "exintro": 1, "explaintext": 1, "exlimit": "max",
                    "titles": "|".join(batch), "redirects": 1,
                },
            )
            pages = response.json()["query"]["pages"].values()
        except Exception as exc:
            print("batch fail", start, exc)
            continue
        for page in pages:
            title = page.get("title", "")
            intro = page.get("extract", "")
            if not intro or title not in batch:
                continue
            parsed = parse_intro(intro)
            if parsed:
                result[title] = parsed
    print("found", len(result), "of", len(names))
    (ROOT / ".scrape").mkdir(exist_ok=True)
    (ROOT / ".scrape" / "wiki_bios.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
