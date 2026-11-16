from __future__ import annotations

import json
import re
from pathlib import Path

import cpca

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
CANDIDATES = ROOT / ".scrape" / "wikipedia_all_native.json"
OUT = ROOT / ".scrape" / "native_remaining.json"

TRAD = str.maketrans({"東": "东", "蘇": "苏", "貴": "贵", "內": "内", "遼": "辽", "龍": "龙", "灣": "湾"})


def components(value: str | None) -> tuple[str | None, str | None, str | None]:
    value = (value or "").translate(TRAD).strip()
    value = re.sub(r"^曾任", "", value)
    value = value.replace("中華民國大陸時期", "")
    if not value:
        return None, None, None
    try:
        row = cpca.transform([value]).to_dict("records")[0]
        return row.get("省"), row.get("市"), row.get("区")
    except Exception:
        return None, None, None


def score(value: str | None) -> int:
    province, city, area = components(value)
    return 3 if area else (2 if city else (1 if province else 0))


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    candidates = {
        row["name"]: row.get("native_place")
        for row in json.loads(CANDIDATES.read_text(encoding="utf-8"))
        if row.get("status") == "ok"
    }
    changed = 0
    for officer in data["officers"]:
        current = officer.get("native_place")
        candidate = candidates.get(officer["name"])
        if candidate and score(candidate) > score(current):
            officer["native_place"] = candidate.translate(TRAD)
            changed += 1
    DATASET.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    remaining = []
    counts = {"area": 0, "city": 0, "prov": 0, "none": 0}
    for officer in data["officers"]:
        province, city, area = components(officer.get("native_place"))
        if area:
            counts["area"] += 1
        elif city:
            counts["city"] += 1
            remaining.append({"name": officer["name"], "native": officer.get("native_place"), "level": "city"})
        elif province:
            counts["prov"] += 1
            remaining.append({"name": officer["name"], "native": officer.get("native_place"), "level": "province"})
        else:
            counts["none"] += 1
            remaining.append({"name": officer["name"], "native": officer.get("native_place"), "level": "invalid"})
    OUT.write_text(json.dumps(remaining, ensure_ascii=False, indent=1), encoding="utf-8")
    print("changed", changed, counts)


if __name__ == "__main__":
    main()
