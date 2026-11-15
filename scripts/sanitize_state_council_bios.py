from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"

OVERRIDES = {
    "李强": (1959, "浙江瑞安"),
    "高翔": (1963, "四川绵阳"),
    "潘岳": (1960, "江苏南京"),
    "李群": (1962, "山东威海"),
    "李利": (1962, None),
    "王小龙": (1965, None),
    "陈一新": (1959, "浙江泰顺"),
    "李小鹏": (1959, "四川成都"),
    "秦刚": (1966, "河北怀来"),
}

data = json.loads(DATASET.read_text(encoding="utf-8"))
for officer in data["officers"]:
    name = officer["name"]
    if name in OVERRIDES:
        year, place = OVERRIDES[name]
        officer["birth_year"] = year
        officer["native_place"] = place
        continue
    year = officer.get("birth_year")
    if year is not None and not (1900 <= year <= 2010):
        officer["birth_year"] = None
    if officer.get("native_place") == "中华人民共和国":
        officer["native_place"] = None

DATASET.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("sanitized")
