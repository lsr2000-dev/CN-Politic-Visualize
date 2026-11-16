from __future__ import annotations

import json
import re
from pathlib import Path

import cpca

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
PROVINCES = [
    "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
    "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海",
    "内蒙古", "广西", "西藏", "宁夏", "新疆", "香港", "澳门", "台湾",
]
MUNICIPAL = {"北京", "天津", "上海", "重庆"}
TRAD = str.maketrans({"東": "东", "蘇": "苏", "貴": "贵", "內": "内", "遼": "辽", "龍": "龙", "灣": "湾"})


def clean(value: str) -> str:
    value = (value or "").translate(TRAD).strip()
    value = re.sub(r"^曾任", "", value)
    value = value.replace("中華民國大陸時期", "")
    return value


def province_prefix(value: str) -> str | None:
    for province in PROVINCES:
        if value.startswith(province):
            return province
    return None


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    changed = 0
    for officer in data["officers"]:
        value = clean(officer.get("native_place"))
        if not value:
            continue
        province = province_prefix(value)
        if province:
            # Already starts with a province/municipality; keep its detail.
            if value != officer.get("native_place"):
                officer["native_place"] = value
                changed += 1
            continue
        try:
            row = cpca.transform([value]).to_dict("records")[0]
            p, c, a = row.get("省"), row.get("市"), row.get("区")
        except Exception:
            p = c = a = None
        if p:
            if p[:2] in MUNICIPAL:
                normalized = p + (a or "")
            else:
                normalized = p + (c or "") + (a or "")
            if normalized and normalized != value:
                officer["native_place"] = normalized
                changed += 1
    DATASET.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("changed", changed)
    province_only = []
    invalid = []
    for officer in data["officers"]:
        value = clean(officer.get("native_place"))
        p = province_prefix(value)
        if not p:
            invalid.append((officer["name"], value))
            continue
        if len(value) <= (3 if p in {"内蒙古", "黑龙江"} else 2) + (1 if value[len(p):].startswith(("省", "市", "区", "县")) else 0):
            province_only.append((officer["name"], value))
    print("province_only", len(province_only), province_only[:50])
    print("invalid", len(invalid), invalid[:30])


if __name__ == "__main__":
    main()
