import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

BATCH = 50


def sparql(client: httpx.Client, names: list[str]) -> list[dict]:
    values = " ".join(json.dumps(n, ensure_ascii=False) + "@zh" for n in names)
    query = f"""
SELECT ?name ?person ?birth ?birthplaceLabel ?genderLabel ?ethnicLabel ?partyLabel ?start WHERE {{
  VALUES ?name {{ {values} }}
  ?person rdfs:label ?name .
  OPTIONAL {{ ?person wdt:P569 ?birth . }}
  OPTIONAL {{ ?person wdt:P19 ?bp . ?bp rdfs:label ?birthplaceLabel . FILTER(LANG(?birthplaceLabel)="zh") }}
  OPTIONAL {{ ?person wdt:P21 ?gender . ?gender rdfs:label ?genderLabel . FILTER(LANG(?genderLabel)="zh") }}
  OPTIONAL {{ ?person wdt:P172 ?ethnic . ?ethnic rdfs:label ?ethnicLabel . FILTER(LANG(?ethnicLabel)="zh") }}
  OPTIONAL {{ ?person p:P102 ?st . ?st ps:P102 ?party . ?party rdfs:label ?partyLabel . FILTER(LANG(?partyLabel)="zh") OPTIONAL {{ ?st pq:P580 ?start }} }}
}}"""
    r = client.get("https://query.wikidata.org/sparql", params={"query": query, "format": "json"}, timeout=90)
    r.raise_for_status()
    return r.json()["results"]["bindings"]


def value(row: dict, key: str) -> str:
    return row.get(key, {}).get("value", "")


def main() -> None:
    dataset = json.loads((ROOT / "backend/app/data/dataset.json").read_text(encoding="utf-8"))
    names = [o["name"] for o in dataset["officers"]]
    client = httpx.Client(timeout=90, headers={"User-Agent": "polvis-demo/1.0"})
    merged: dict[str, dict] = {}
    for start in range(0, len(names), BATCH):
        batch = names[start:start + BATCH]
        try:
            bindings = sparql(client, batch)
        except Exception as exc:
            print("batch failed", start, exc)
            continue
        for row in bindings:
            name = value(row, "name")
            item = merged.setdefault(name, {})
            birth = value(row, "birth")
            if birth:
                item["birth_year"] = int(birth[:4])
            place = value(row, "birthplaceLabel")
            if place and not item.get("native_place"):
                item["native_place"] = place
            gender = value(row, "genderLabel")
            if gender:
                item["gender"] = "F" if "女" in gender else "M"
            ethnic = value(row, "ethnicLabel")
            if ethnic:
                item["ethnicity"] = ethnic
            party = value(row, "partyLabel")
            when = value(row, "start")
            if "中国共产党" in party and when and not item.get("party_join_date"):
                item["party_join_date"] = when[:10]
        print(start, len(batch), len(merged), flush=True)

    # merge with Wikipedia-derived candidates; keep existing values first
    old_path = ROOT / ".scrape" / "officer_enrichment.json"
    old = json.loads(old_path.read_text(encoding="utf-8")) if old_path.exists() else {}
    for name, fields in old.items():
        target = merged.setdefault(name, {})
        for key, val in fields.items():
            if val and not target.get(key):
                target[key] = val

    (ROOT / ".scrape" / "officer_enrichment_merged.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
