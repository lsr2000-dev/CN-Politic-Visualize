from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
WIKI = ROOT / ".scrape" / "wikipedia_batch_missing.json"
BAD_NATIVE = ("中国", "人民", "中华", "party", "[[", "]]", "可以指", "消歧义")


def valid_native(value: str | None) -> bool:
    if not value:
        return False
    text = re.sub(r"\s+", "", value)
    if len(text) < 2 or len(text) > 24:
        return False
    if any(token in text for token in BAD_NATIVE):
        return False
    return bool(re.fullmatch(r"[\u4e00-\u9fa5·]+", text))


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    candidates = {
        row["name"]: row for row in json.loads(WIKI.read_text(encoding="utf-8"))
        if row.get("status") == "ok"
    }
    filled_birth = 0
    filled_native = 0
    rejected = []
    for officer in data["officers"]:
        row = candidates.get(officer["name"])
        if not row:
            continue
        if not officer.get("birth_year") and row.get("birth_year"):
            year = int(row["birth_year"])
            if 1920 <= year <= 2005:
                officer["birth_year"] = year
                filled_birth += 1
        if not officer.get("native_place") and valid_native(row.get("native_place")):
            officer["native_place"] = row["native_place"]
            filled_native += 1
        elif not officer.get("native_place") and row.get("native_place"):
            rejected.append((officer["name"], row["native_place"]))
    DATASET.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"filled birth={filled_birth} native={filled_native}")
    print(f"remaining birth={sum(1 for o in data['officers'] if not o.get('birth_year'))} "
          f"native={sum(1 for o in data['officers'] if not o.get('native_place'))}")
    print("rejected native:", rejected[:20])


if __name__ == "__main__":
    main()
