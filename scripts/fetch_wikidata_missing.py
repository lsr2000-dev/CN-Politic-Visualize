from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
OUT = ROOT / ".scrape" / "wikidata_missing.json"
API = "https://www.wikidata.org/w/api.php"
HEADERS = {"User-Agent": "polvis-data-audit/1.0 (local research)"}
DATE_RE = re.compile(r"^\+?(\d{4})-")


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    names = [
        officer["name"] for officer in data["officers"]
        if not officer.get("birth_year") or not officer.get("native_place")
    ]

    def search(name: str) -> tuple[str, list[dict]]:
        try:
            response = httpx.get(API, params={
                "action": "wbsearchentities", "search": name,
                "language": "zh", "uselang": "zh", "type": "item",
                "limit": 8, "format": "json",
            }, headers=HEADERS, timeout=20)
            response.raise_for_status()
            return name, response.json().get("search", [])
        except Exception as exc:  # noqa: BLE001
            return name, [{"error": str(exc)}]

    candidates: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(search, name) for name in names]
        for index, future in enumerate(as_completed(futures), 1):
            name, results = future.result()
            candidates[name] = results
            if index % 50 == 0:
                print(f"searched {index}/{len(names)}", flush=True)

    all_ids = sorted({
        item["id"] for results in candidates.values() for item in results
        if item.get("id", "").startswith("Q")
    })
    entities: dict[str, dict] = {}
    for start in range(0, len(all_ids), 50):
        batch = all_ids[start:start + 50]
        try:
            response = httpx.get(API, params={
                "action": "wbgetentities", "ids": "|".join(batch),
                "props": "labels|descriptions|claims", "languages": "zh|en",
                "format": "json",
            }, headers=HEADERS, timeout=40)
            response.raise_for_status()
            entities.update(response.json().get("entities", {}))
            print(f"entities {min(start + 50, len(all_ids))}/{len(all_ids)}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print("entity batch failed", exc, flush=True)

    def claim_value(entity: dict, prop: str) -> str | None:
        for claim in entity.get("claims", {}).get(prop, []):
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
            if isinstance(value, dict) and value.get("id"):
                return value["id"]
        return None

    def label(entity: dict) -> str:
        labels = entity.get("labels", {})
        return labels.get("zh", labels.get("en", {})).get("value", "")

    rows = []
    for name, results in candidates.items():
        selected = None
        for item in results:
            entity = entities.get(item.get("id", ""))
            if not entity:
                continue
            instance = entity.get("claims", {}).get("P31", [])
            is_human = any(
                c.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id") == "Q5"
                for c in instance
            )
            if not is_human:
                continue
            selected = entity
            break
        if not selected:
            rows.append({"name": name, "status": "missing"})
            continue
        birth_entity = claim_value(selected, "P569")
        place_entity = claim_value(selected, "P19")
        birth = entities.get(birth_entity, {}).get("labels", {}).get("zh", {}).get("value", "")
        place = entities.get(place_entity, {}).get("labels", {}).get("zh", {}).get("value", "")
        rows.append({
            "name": name,
            "status": "ok",
            "qid": selected.get("id"),
            "description": selected.get("descriptions", {}).get("zh", {}).get("value", ""),
            "birth": birth,
            "birth_year": int(match.group(1)) if (match := DATE_RE.match(birth)) else None,
            "place": place,
        })

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for row in rows if row["status"] == "ok")
    print(f"wrote {OUT} ok={ok} missing={len(rows) - ok}")


if __name__ == "__main__":
    main()
