from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
CENTRAL = ROOT / "backend" / "app" / "data" / "central.json"
OUT = ROOT / "scripts" / "state_council_native_places.json"


def clean(value: str) -> str:
    value = re.sub(r"<ref[^>]*>.*?</ref>", "", value, flags=re.S)
    value = re.sub(r"<ref[^>]*/>", "", value)
    value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"\[\[[^|\]]*\|([^\]]+)\]\]", r"\1", value)
    value = re.sub(r"\[\[([^\]]+)\]\]", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    return value.strip(" |\n\t")


def fetch_place(name: str) -> str | None:
    response = httpx.get(
        "https://zh.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "format": "json",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": name,
            "redirects": 1,
        },
        headers={"User-Agent": "polvis-demo/1.0"},
        timeout=8,
    )
    page = next(iter(response.json().get("query", {}).get("pages", {}).values()), {})
    text = page.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("*", "")
    match = re.search(r"birth_place\s*=\s*([^\n]+)", text)
    return clean(match.group(1)) if match else None


central = json.loads(CENTRAL.read_text(encoding="utf-8"))
data = json.loads(DATASET.read_text(encoding="utf-8"))
officers = {officer["name"]: officer for officer in data["officers"]}
names = sorted({
    leader["name"]
    for institution in central["institutions"]
    if institution["team"] == "government"
    and institution["institution_type"] != "group"
    and not institution["institution_type"].endswith("_group")
    for leader in institution.get("leaders", [])
    if not leader.get("native_place")
})
places = {}
for index, name in enumerate(names, 1):
    try:
        place = fetch_place(name)
    except Exception as exc:  # noqa: BLE001
        print("ERR", name, exc, flush=True)
        continue
    if place:
        places[name] = place
        print(index, name, place, flush=True)

OUT.write_text(json.dumps(places, ensure_ascii=False, indent=1), encoding="utf-8")
updated = 0
for name, place in places.items():
    officer = officers.get(name)
    if officer and not officer.get("native_place"):
        officer["native_place"] = place
        updated += 1
DATASET.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("requests", len(names), "places", len(places), "updated", updated, flush=True)
