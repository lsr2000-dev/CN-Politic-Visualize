from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"

# Last-resort manual review for long-tail officials. Prefer province/city-level
# when a county-level source was not available.
MANUAL = {
    "吉林": ("吉林省吉林市", None),
    "齐同生": ("河北平山", 1952),
    "陈扬勇": ("江西永新", 1963),
    "王超": ("河北", 1963),
    "雷海潮": ("山东", 1968),
    "何厚铧": ("广东番禺", 1955),
    "万立骏": ("辽宁", 1957),
    "刘振立": ("河北栾城", 1964),
    "刘青松": ("山东", 1963),
    "王建武": ("河南", 1958),
    "王强": ("河北", 1963),
    "郑璇": ("福建", 1964),
    "李桥铭": ("河南偃师", 1961),
    "胡中明": ("山东", 1964),
    "郝卫中": ("河北", 1961),
    "陈辉": ("江苏", 1963),
    "张作胜": ("山东", 1964),
    "韩晓东": ("河北", 1963),
    "王立岩": ("辽宁", 1962),
    "王抗平": ("江苏", 1965),
    "高大光": ("辽宁", 1967),
    "王小龙": ("江苏", 1965),
    "赵晓哲": ("江苏常州", 1963),
    "边保民": ("陕西府谷", 1962),
    "孙斌": ("山东", 1965),
    "陈军": ("江苏", 1967),
    "张红兵": ("江苏", 1966),
    "肖天亮": ("湖北", 1962),
    "黎湘": ("湖南", 1967),
    "林上元": ("湖北新洲", 1924),
    "王家瑞": ("河北秦皇岛", 1949),
    "王永红": ("江西", 1969),
    "宋志勇": ("山东", 1965),
    "黄锦生": ("江苏如皋", 1953),
    "王宏志": ("山东", 1969),
    "刘国洪": ("江苏江阴", 1966),
    "董经纬": ("河北石家庄", 1951),
    "易纲": ("北京", 1958),
    "周生贤": ("宁夏中卫", 1949),
    "凌成兴": ("江西", 1957),
    "陆东福": ("江苏丹阳", 1955),
    "李家祥": ("山东枣庄", 1949),
    "李从军": ("安徽", 1949),
    "王伟光": ("山东", 1950),
    "白春礼": ("辽宁岫岩", 1953),
    "郑国光": ("山东昌邑", 1959),
    "付建华": ("辽宁昌图", 1958),
    "李刚": ("陕西三原", 1922),
    "陈奎元": ("河南", 1941),
    "许其亮": ("山东临朐", 1950),
    "马培华": ("江苏", 1949),
    "刘新成": ("河北", 1952),
    "贺军科": ("陕西凤翔", 1969),
    "李飞": ("河北", 1953),
    "陈锡文": ("江苏", 1950),
    "冷溶": ("山东", 1953),
    "林军": ("福建", 1949),
    "高燕": ("河南济源", 1958),
    "王乐泉": ("山东寿光", 1944),
    "孙淦": ("上海", 1946),
    "周伯华": ("湖南", 1948),
    "朱维群": ("江苏", 1947),
    "陈炳德": ("江苏南通", 1941),
    "李继耐": ("山东滕州", 1942),
    "廖锡龙": ("贵州思南", 1940),
    "靖志远": ("山东临沭", 1944),
    "吴胜利": ("河北吴桥", 1945),
    "房峰辉": ("陕西咸阳", 1951),
    "张阳": ("河北武强", 1951),
    "赵克石": ("河北高阳", 1947),
    "马晓天": ("河南巩义", 1949),
}


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    for officer in data["officers"]:
        item = MANUAL.get(officer["name"])
        if not item:
            continue
        native, birth = item
        if not officer.get("native_place"):
            officer["native_place"] = native
        if not officer.get("birth_year") and birth:
            officer["birth_year"] = birth
    DATASET.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    missing_birth = [o for o in data["officers"] if not o.get("birth_year")]
    missing_native = [o for o in data["officers"] if not o.get("native_place")]
    print("remaining birth", len(missing_birth), [o["name"] for o in missing_birth])
    print("remaining native", len(missing_native), [o["name"] for o in missing_native])


if __name__ == "__main__":
    main()
