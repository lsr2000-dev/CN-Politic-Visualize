from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"

data = json.loads(DATASET.read_text(encoding="utf-8"))
officers = {item["id"]: item for item in data["officers"]}
positions = {item["id"]: item for item in data["positions"]}
source_ids = {item["id"] for item in data.get("sources", [])}
position_uids = {item.get("position_uid") for item in positions.values()}
problems: list[str] = []

uids = [item.get("position_uid") for item in positions.values()]
if any(not uid for uid in uids):
    problems.append("position without position_uid")
if len(uids) != len(set(uids)):
    problems.append("duplicate position_uid")

seen: dict[tuple[int, str], list[tuple[date, date | None]]] = defaultdict(list)
for item in data["tenures"]:
    if item["officer_id"] not in officers:
        problems.append(f"orphan officer: {item['id']}")
    if item.get("source_id") not in source_ids:
        problems.append(f"orphan source: {item['id']}")
    position = positions.get(item["position_id"])
    if position is None:
        problems.append(f"orphan position: {item['id']}")
        continue
    start = date.fromisoformat(item["start_date"])
    end = date.fromisoformat(item["end_date"]) if item.get("end_date") else None
    if end and end < start:
        problems.append(f"invalid tenure: {item['id']}")
    seen[(item["officer_id"], position["position_uid"])].append((start, end))

for key, spans in seen.items():
    spans.sort(key=lambda span: span[0])
    for previous, current in zip(spans, spans[1:]):
        if previous[1] is None or current[0] <= previous[1]:
            problems.append(f"overlap: {key[0]} {key[1]}")

for item in data.get("position_equivalences", []):
    if item.get("position_uid") not in position_uids or item.get("equivalent_uid") not in position_uids:
        problems.append(f"bad position equivalence: {item}")

by_title: dict[tuple[int, str], list[tuple[str, str | None, str]]] = defaultdict(list)
for item in data["tenures"]:
    position = positions[item["position_id"]]
    by_title[(item["officer_id"], position["title"])].append(
        (item["start_date"], item.get("end_date"), position["position_uid"])
    )
for key, spans in by_title.items():
    spans.sort()
    for previous, current in zip(spans, spans[1:]):
        if previous[1] is None or current[0] <= previous[1]:
            if previous[2] != current[2]:
                problems.append(f"semantic overlap: {key[0]} {key[1]}")

print("officers", len(officers), "positions", len(positions), "tenures", len(data["tenures"]))
print("problems", len(problems))
for problem in problems[:30]:
    print(" -", problem)
