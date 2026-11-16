from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
VOCABULARY = ROOT / "backend" / "app" / "data" / "vocabulary.json"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

REQUIRED_SECTIONS = [
    "officers", "organizations", "positions", "tenures",
    "identities", "sources", "position_equivalences", "regions",
]
PROVINCES = (
    "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
    "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海",
    "内蒙古", "广西", "西藏", "宁夏", "新疆", "香港", "澳门", "台湾",
)


def main() -> int:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    errors: list[str] = []

    for section in REQUIRED_SECTIONS:
        if not isinstance(data.get(section), list):
            errors.append(f"missing or invalid section: {section}")

    if not isinstance(data.get("officers"), list):
        print("\n".join(errors))
        return 1

    for key in ("id", "slug"):
        values = [item.get(key) for item in data["officers"]]
        if len(values) != len(set(values)):
            errors.append(f"duplicate officer {key}")
        if any(value in (None, "") for value in values):
            errors.append(f"empty officer {key}")

    for item in data["officers"]:
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            errors.append(f"officer without name: {item.get('id')}")
        birth = item.get("birth_year")
        if not isinstance(birth, int) or not 1920 <= birth <= 2000:
            errors.append(f"officer without valid birth_year: {item.get('id')}")
        native = item.get("native_place")
        if not isinstance(native, str) or not native.strip():
            errors.append(f"officer without native_place: {item.get('id')}")
        elif not native.startswith(PROVINCES):
            errors.append(f"officer native_place has no province prefix: {item.get('id')}")

    position_uids = [item.get("position_uid") for item in data["positions"]]
    if any(not value for value in position_uids):
        errors.append("position without position_uid")
    if len(position_uids) != len(set(position_uids)):
        errors.append("duplicate position_uid")

    for section, key in (("positions", "id"), ("tenures", "id"), ("identities", "id"), ("sources", "id")):
        values = [item.get(key) for item in data[section]]
        if len(values) != len(set(values)):
            errors.append(f"duplicate {section}.{key}")

    for item in data["positions"]:
        if not item.get("organization_id") and not item.get("region_code"):
            errors.append(f"position missing organization/region: {item.get('id')}")
        if not item.get("code") and not item.get("seat_key"):
            errors.append(f"position missing code/seat_key: {item.get('id')}")
        for key in ("title", "position_uid"):
            if not item.get(key):
                errors.append(f"position missing {key}: {item.get('id')}")

    for item in data["tenures"]:
        if not item.get("officer_id") or not item.get("position_id"):
            errors.append(f"tenure missing officer/position: {item.get('id')}")
        if not item.get("source_id"):
            errors.append(f"tenure missing source_id: {item.get('id')}")
        start = str(item.get("start_date", ""))
        end = item.get("end_date")
        if not DATE.match(start):
            errors.append(f"bad start_date: {item.get('id')}")
        if end and not DATE.match(str(end)):
            errors.append(f"bad end_date: {item.get('id')}")
        if end and start > str(end):
            errors.append(f"start after end: {item.get('id')}")

    for item in data["identities"]:
        if not item.get("person_id") or not item.get("role") or not item.get("term"):
            errors.append(f"identity missing person/term/role: {item.get('id')}")
        if not item.get("source_id"):
            errors.append(f"identity missing source_id: {item.get('id')}")

    term_ids = {item["ordinal"] for item in data.get("central_terms", [])}
    if term_ids:
        for item in data["identities"]:
            if item.get("term") not in term_ids:
                errors.append(f"identity has unknown term: {item.get('id')}")

    vocabulary = json.loads(VOCABULARY.read_text(encoding="utf-8"))
    identity_types = {key: value["label"] for key, value in vocabulary["identity_types"].items()}
    term_labels = {item["ordinal"]: item["label"] for item in vocabulary["terms"]}
    for item in data["identities"]:
        role = item.get("role")
        term = item.get("term")
        if role not in identity_types:
            errors.append(f"identity has unknown role: {item.get('id')}")
            continue
        expected = f"{term_labels.get(term, '')}{identity_types[role]}"
        if item.get("label") not in (expected, f"原{expected}"):
            errors.append(f"identity label drift: {item.get('id')}")

    print(f"sections: {', '.join(REQUIRED_SECTIONS)}")
    print(f"officers: {len(data['officers'])} positions: {len(data['positions'])} "
          f"tenures: {len(data['tenures'])} identities: {len(data['identities'])}")
    print(f"schema_errors: {len(errors)}")
    for error in errors[:30]:
        print(" -", error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
