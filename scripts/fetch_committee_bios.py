from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
ROSTER = ROOT / "scripts" / "central_committee_roster.json"
OUT = ROOT / "scripts" / "committee_bios.json"

UA = "CN-Politic-Visualize/1.0 (data import; contact: local)"


def wiki_extract(name: str) -> str | None:
    params = urllib.parse.urlencode({
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "redirects": "1",
        "format": "json",
        "titles": name,
    })
    url = f"https://zh.wikipedia.org/w/api.php?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    pages = payload.get("query", {}).get("pages", {})
    for page in pages.values():
        extract = page.get("extract")
        if extract:
            return extract
    return None


def parse_bio(extract: str) -> tuple[int | None, str | None]:
    birth = re.search(r"[（(]\s*(19\d{2}|20\d{2})\s*年", extract)
    birth_year = int(birth.group(1)) if birth else None
    native = re.search(r"[，,]\s*([^，。；\n]{2,20}?)人", extract)
    native_place = native.group(1).strip() if native else None
    if native_place:
        native_place = re.sub(r"^(籍贯|出生于)", "", native_place).strip()
    return birth_year, native_place


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    existing = {officer["name"] for officer in data["officers"]}
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    missing = [name for name in roster if name not in existing]
    result: dict[str, dict[str, object]] = {}
    failures: list[str] = []
    for index, name in enumerate(missing, 1):
        query = name.split("（", 1)[0]
        try:
            extract = wiki_extract(query)
        except Exception as exc:  # noqa: BLE001
            print(f"{index}/{len(missing)} {name}: {exc}")
            failures.append(name)
            continue
        if not extract:
            failures.append(name)
            continue
        birth, native = parse_bio(extract)
        result[name] = {"birth_year": birth, "native_place": native}
        print(f"{index}/{len(missing)} {name}: {birth} {native}")
        time.sleep(0.15)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("saved", len(result), "failures", len(failures), failures)


if __name__ == "__main__":
    main()
