from __future__ import annotations

import json
import re
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
OUT = ROOT / ".scrape" / "wikidata_sparql_missing.json"
ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "polvis-data-audit/1.0 (local research)", "Accept": "application/sparql-results+json"}
DATE_RE = re.compile(r"^(\d{4})-")


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    names = [
        officer["name"] for officer in data["officers"]
        if not officer.get("birth_year") or not officer.get("native_place")
    ]
    rows: list[dict] = []
    errors: list[str] = []
    for start in range(0, len(names), 50):
        batch = names[start:start + 50]
        values = " ".join(json.dumps(name, ensure_ascii=False) + "@zh" for name in batch)
        query = f"""
SELECT ?name ?person ?personLabel ?birth ?placeLabel ?description WHERE {{
  VALUES ?name {{ {values} }}
  ?person rdfs:label ?name .
  OPTIONAL {{ ?person wdt:P569 ?birth . }}
  OPTIONAL {{ ?person wdt:P19 ?place . }}
  OPTIONAL {{ ?person schema:description ?description . FILTER(LANG(?description) = "zh") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en". }}
}}
"""
        for attempt in range(3):
            try:
                response = httpx.get(ENDPOINT, params={"query": query, "format": "json"}, headers=HEADERS, timeout=60)
                response.raise_for_status()
                payload = response.json()
                for binding in payload["results"]["bindings"]:
                    birth = binding.get("birth", {}).get("value", "")
                    rows.append({
                        "name": binding.get("name", {}).get("value", ""),
                        "qid": binding.get("person", {}).get("value", "").rsplit("/", 1)[-1],
                        "person": binding.get("personLabel", {}).get("value", ""),
                        "birth": birth,
                        "birth_year": int(match.group(1)) if (match := DATE_RE.match(birth)) else None,
                        "place": binding.get("placeLabel", {}).get("value", ""),
                        "description": binding.get("description", {}).get("value", ""),
                    })
                print(f"batch {start // 50 + 1}: {len(batch)} names, {len(rows)} rows", flush=True)
                break
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                print("retry", start, exc, flush=True)
                time.sleep(5 + attempt * 5)
        time.sleep(1.5)
    OUT.write_text(json.dumps({"rows": rows, "errors": errors}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT} rows={len(rows)} errors={len(errors)}")


if __name__ == "__main__":
    main()
