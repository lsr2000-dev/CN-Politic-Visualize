from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
WIKI = ROOT / ".scrape" / "wikipedia_batch_missing.json"
BAIDU = ROOT / ".scrape" / "baidu_remaining.json"
BAD = ("中国", "人民", "中华", "party", "date", "File:", "Flag", "[[", "]]", "可以指", "消歧义")


def valid_native(value: str | None) -> bool:
    if not value:
        return False
    text = re.sub(r"\s+", "", value)
    if len(text) < 2 or len(text) > 24:
        return False
    if any(token in text for token in BAD):
        return False
    if not re.fullmatch(r"[\u4e00-\u9fa5·]+", text):
        return False
    return True


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    wiki = {
        row["name"]: row for row in json.loads(WIKI.read_text(encoding="utf-8"))
        if row.get("status") == "ok"
    }
    baidu = {}
    if BAIDU.exists():
        baidu = {
            row["name"]: row for row in json.loads(BAIDU.read_text(encoding="utf-8"))
            if row.get("status") == "ok"
        }

    filled_birth = 0
    filled_native = 0
    provenance = []
    for officer in data["officers"]:
        name = officer["name"]
        w = wiki.get(name, {})
        b = baidu.get(name, {})
        if not officer.get("birth_year"):
            year = w.get("birth_year")
            if not (isinstance(year, int) and 1920 <= year <= 2000):
                year = b.get("birth_year")
            if isinstance(year, int) and 1920 <= year <= 2000:
                officer["birth_year"] = year
                filled_birth += 1
                provenance.append((name, "birth_year", year, "wikipedia" if year == w.get("birth_year") else "baidu"))
        if not officer.get("native_place"):
            native = w.get("native_place")
            source = "wikipedia"
            if not valid_native(native):
                native = b.get("native_place")
                source = "baidu"
            if valid_native(native):
                officer["native_place"] = re.sub(r"\s+", "", native)
                filled_native += 1
                provenance.append((name, "native_place", officer["native_place"], source))
    DATASET.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"filled birth={filled_birth} native={filled_native}")
    print(f"remaining birth={sum(1 for o in data['officers'] if not o.get('birth_year'))} "
          f"native={sum(1 for o in data['officers'] if not o.get('native_place'))}")
    missing = [
        {"id": o["id"], "name": o["name"], "birth_year": o.get("birth_year"), "native_place": o.get("native_place")}
        for o in data["officers"] if not o.get("birth_year") or not o.get("native_place")
    ]
    (ROOT / ".scrape" / "bio_missing_after_merge.json").write_text(
        json.dumps(missing, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (ROOT / ".scrape" / "bio_provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=1), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
