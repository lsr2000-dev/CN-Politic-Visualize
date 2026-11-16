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
UA = "CN-Politic-Visualize/1.0 (data import; local)"


def fetch(titles: list[str]) -> dict[str, str]:
    params = urllib.parse.urlencode({
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "exintro": "1",
        "exlimit": "max",
        "redirects": "1",
        "format": "json",
        "titles": "|".join(titles),
    })
    request = urllib.request.Request(
        f"https://zh.wikipedia.org/w/api.php?{params}", headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return {
        page.get("title", ""): page.get("extract", "")
        for page in payload.get("query", {}).get("pages", {}).values()
        if page.get("extract")
    }


def parse(text: str) -> tuple[int | None, str | None]:
    birth = re.search(r"[（(]\s*(19\d{2}|20\d{2})\s*年", text)
    native = re.search(r"[，,]\s*([^，。；\n]{2,20}?)人", text)
    return (
        int(birth.group(1)) if birth else None,
        native.group(1).strip() if native else None,
    )


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    existing = {officer["name"] for officer in data["officers"]}
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    bios = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    missing = [name for name in roster if name not in existing]
    missing = [name for name in missing if not (bios.get(name, {}).get("birth_year") and bios.get(name, {}).get("native_place"))]
    print("missing", len(missing))
    for start in range(0, len(missing), 20):
        batch = missing[start:start + 20]
        queries = [name.split("（", 1)[0] for name in batch]
        try:
            pages = fetch(queries)
        except Exception as exc:  # noqa: BLE001
            print("batch error", exc)
            time.sleep(3)
            continue
        for name, query in zip(batch, queries):
            text = pages.get(query)
            if not text:
                continue
            birth, native = parse(text)
            if birth or native:
                bios[name] = {"birth_year": birth, "native_place": native}
                print(name, birth, native)
        time.sleep(1)
    OUT.write_text(json.dumps(bios, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("remaining", [n for n in roster if n not in existing and not (bios.get(n, {}).get("birth_year") and bios.get(n, {}).get("native_place"))])


if __name__ == "__main__":
    main()
