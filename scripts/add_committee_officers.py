from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
ROSTER = ROOT / "scripts" / "central_committee_roster.json"
BIOS = ROOT / "scripts" / "committee_bios.json"


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    bios = json.loads(BIOS.read_text(encoding="utf-8")) if BIOS.exists() else {}
    by_name = {officer["name"] for officer in data["officers"]}
    next_id = max((officer["id"] for officer in data["officers"]), default=0) + 1
    slugs = {officer["slug"] for officer in data["officers"]}
    added = 0
    missing_bio: list[str] = []
    for name in roster:
        if name in by_name:
            continue
        info = bios.get(name) or {}
        birth = info.get("birth_year")
        native = info.get("native_place")
        if not birth or not native:
            missing_bio.append(name)
            continue
        while f"p{next_id:03d}" in slugs:
            next_id += 1
        officer = {
            "id": next_id,
            "slug": f"p{next_id:03d}",
            "name": name,
            "gender": "M",
            "birth_year": birth,
            "native_place": native,
            "ethnicity": "汉族",
            "party_join_date": None,
            "work_start_date": None,
            "education": None,
            "degree": None,
            "school": None,
            "bio": None,
            "portrait_url": None,
            "is_deceased": False,
        }
        data["officers"].append(officer)
        by_name.add(name)
        slugs.add(officer["slug"])
        next_id += 1
        added += 1
    DATASET.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("added", added, "missing bio", len(missing_bio), missing_bio)


if __name__ == "__main__":
    main()
