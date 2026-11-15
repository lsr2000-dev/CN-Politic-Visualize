from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
CENTRAL = ROOT / "backend" / "app" / "data" / "central.json"
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
OUT = ROOT / "scripts" / "state_council_bios.json"


def clean(value: str) -> str:
    value = re.sub(r"<ref[^>]*>.*?</ref>", "", value, flags=re.S)
    value = re.sub(r"<ref[^>]*/>", "", value)
    value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"\[\[[^|\]]*\|([^\]]+)\]\]", r"\1", value)
    value = re.sub(r"\[\[([^\]]+)\]\]", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    return value.strip(" |\n\t")


def fetch(name: str) -> dict:
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
    pages = response.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    text = page.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("*", "")
    if not text:
        return {}
    year_match = re.search(
        r"birth_date\s*=\s*\{\{\s*[Bb]irth (?:date and age|year and age)\s*\|\s*(\d{4})",
        text,
    ) or re.search(r"birth_date\s*=\s*[^\n]*?(\d{4})", text)
    place_match = re.search(r"birth_place\s*=\s*([^\n]+)", text)
    result = {}
    if year_match:
        result["birth_year"] = int(year_match.group(1))
    if place_match:
        place = clean(place_match.group(1))
        if place:
            result["native_place"] = place
    return result


def main() -> None:
    central = json.loads(CENTRAL.read_text(encoding="utf-8"))
    names = sorted({
        leader["name"]
        for institution in central["institutions"]
        if institution["team"] == "government"
        and institution["institution_type"] != "group"
        and not institution["institution_type"].endswith("_group")
        for leader in institution.get("leaders", [])
    })
    bios = {}
    for index, name in enumerate(names, 1):
        try:
            info = fetch(name)
        except Exception as exc:  # noqa: BLE001
            print("ERR", name, exc)
            info = {}
        if info:
            bios[name] = info
            print(index, name, info)
        time.sleep(0.08)
    OUT.write_text(json.dumps(bios, ensure_ascii=False, indent=1), encoding="utf-8")

    data = json.loads(DATASET.read_text(encoding="utf-8"))
    updated = 0
    for officer in data["officers"]:
        info = bios.get(officer["name"])
        if not info:
            continue
        changed = False
        if not officer.get("birth_year") and info.get("birth_year"):
            officer["birth_year"] = info["birth_year"]
            changed = True
        if not officer.get("native_place") and info.get("native_place"):
            officer["native_place"] = info["native_place"]
            changed = True
        updated += int(changed)
    DATASET.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("names", len(names), "matched", len(bios), "officers_updated", updated)


if __name__ == "__main__":
    main()
