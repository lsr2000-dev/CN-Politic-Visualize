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
        "action": "query", "prop": "extracts", "explaintext": "1",
        "exintro": "1", "redirects": "1", "format": "json", "titles": name,
    })
    request = urllib.request.Request(
        f"https://zh.wikipedia.org/w/api.php?{params}", headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.loads(response.read().decode("utf-8"))
    for page in payload.get("query", {}).get("pages", {}).values():
        extract = page.get("extract")
        if extract:
            return extract
    return None


def parse(extract: str) -> tuple[int | None, str | None]:
    birth = re.search(r"[（(]\s*(19\d{2}|20\d{2})\s*年", extract)
    native = re.search(r"[，,]\s*([^，。；\n]{2,20}?)人", extract)
    return (
        int(birth.group(1)) if birth else None,
        native.group(1).strip() if native else None,
    )


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    existing = {o["name"] for o in data["officers"]}
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    bios = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    missing = [n for n in roster if n not in existing and n not in bios]
    for n in missing:
        clean = n.split("（", 1)[0]
        try:
            text = wiki_extract(clean)
            if text:
                birth, native = parse(text)
                bios[n] = {"birth_year": birth, "native_place": native}
                print(n, birth, native)
        except Exception as exc:  # noqa: BLE001
            print(n, "ERR", exc)
        time.sleep(1.2)
    OUT.write_text(json.dumps(bios, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("missing still", [n for n in roster if n not in existing and not bios.get(n, {}).get("birth_year")])


if __name__ == "__main__":
    main()
