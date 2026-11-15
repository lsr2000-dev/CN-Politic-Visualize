from __future__ import annotations

import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / "scripts" / "state_council_bios_status.json"
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
OUT = ROOT / "scripts" / "state_council_bios_sparql.json"


def main() -> None:
    rows = json.loads(STATUS.read_text(encoding="utf-8"))
    names = sorted({row[1] for row in rows})
    values = " ".join(json.dumps(name, ensure_ascii=False) + "@zh" for name in names)
    query = f"""
SELECT ?name ?dob ?placeLabel WHERE {{
  VALUES ?name {{ {values} }}
  ?item rdfs:label ?name.
  OPTIONAL {{ ?item wdt:P569 ?dob. }}
  OPTIONAL {{ ?item wdt:P19 ?place. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh". }}
}}
"""
    response = httpx.get(
        "https://query.wikidata.org/sparql",
        params={"query": query, "format": "json"},
        headers={"User-Agent": "polvis-demo/1.0"},
        timeout=60,
    )
    response.raise_for_status()
    bindings = response.json()["results"]["bindings"]
    candidates: dict[str, list[dict]] = {}
    for item in bindings:
        name = item["name"]["value"]
        entry = {
            "birth_year": int(item["dob"]["value"][:4]) if "dob" in item else None,
            "native_place": item.get("placeLabel", {}).get("value"),
        }
        if entry["birth_year"] or entry["native_place"]:
            candidates.setdefault(name, []).append(entry)
    # Prefer a candidate that has both fields, then the earliest birth year.
    bios: dict[str, dict] = {}
    for name, options in candidates.items():
        options.sort(key=lambda x: (x["birth_year"] is None, x["native_place"] is None, x["birth_year"] or 9999))
        bios[name] = options[0]
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
