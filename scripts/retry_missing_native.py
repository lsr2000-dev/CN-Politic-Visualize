from __future__ import annotations

import json
import re
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
MISSING = ROOT / "scripts" / "state_council_missing_bios.json"
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
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
    for attempt in range(3):
        try:
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
                timeout=12,
            )
            if response.status_code == 429:
                time.sleep(3 + attempt * 2)
                continue
            response.raise_for_status()
            page = next(iter(response.json().get("query", {}).get("pages", {}).values()), {})
            text = page.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("*", "")
            match = re.search(r"birth_place\s*=\s*([^\n]+)", text)
            return clean(match.group(1)) if match else None
        except Exception as exc:  # noqa: BLE001
            print("ERR", name, attempt, exc, flush=True)
            time.sleep(2)
    return None


rows = json.loads(MISSING.read_text(encoding="utf-8"))
data = json.loads(DATASET.read_text(encoding="utf-8"))
officers = {officer["name"]: officer for officer in data["officers"]}
found = {}
for index, (name, _, _) in enumerate(rows, 1):
    place = fetch_place(name)
    if place:
        found[name] = place
        print(index, name, place, flush=True)
    time.sleep(1.1)

OUT.write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")
updated = 0
for name, place in found.items():
    officer = officers.get(name)
    if officer and not officer.get("native_place"):
        officer["native_place"] = place
        updated += 1
DATASET.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("found", len(found), "updated", updated, flush=True)
