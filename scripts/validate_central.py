from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "backend" / "app" / "data" / "central.json"

data = json.loads(DATA.read_text(encoding="utf-8"))
institutions = data["institutions"]
ids = {item["id"] for item in institutions}
problems: list[str] = []

for item in institutions:
    if item.get("parent_id") and item["parent_id"] not in ids:
        problems.append(f"missing parent: {item['id']} -> {item['parent_id']}")
    if item.get("valid_from") and item.get("valid_to") and item["valid_from"] > item["valid_to"]:
        problems.append(f"invalid lifecycle: {item['id']}")

for item in institutions:
    seen: dict[tuple[str, str], tuple[date, date | None]] = {}
    seat_ids: set[str] = set()
    for leader in item.get("leaders", []):
        start = date.fromisoformat(leader["start_date"])
        end = date.fromisoformat(leader["end_date"]) if leader.get("end_date") else None
        if end and end < start:
            problems.append(f"invalid tenure: {item['id']} {leader['name']} {leader['title']}")
        if not leader.get("seat_id"):
            problems.append(f"missing seat_id: {item['id']} {leader['name']} {leader['title']}")
        elif leader["seat_id"] in seat_ids:
            pass
        else:
            seat_ids.add(leader["seat_id"])
        key = (leader["name"], leader.get("seat_id") or leader["title"])
        if key in seen:
            previous = seen[key]
            if previous[1] is None or start <= previous[1]:
                problems.append(f"overlapping tenure: {item['id']} {leader['name']} {leader['title']}")
        seen[key] = (start, end)

by_team = defaultdict(int)
for item in institutions:
    if item["institution_type"] != "group" and not item["institution_type"].endswith("_group"):
        by_team[item["team"]] += 1
print("nodes", len(institutions), "real", dict(by_team))
print("problems", len(problems))
for problem in problems[:30]:
    print(" -", problem)
