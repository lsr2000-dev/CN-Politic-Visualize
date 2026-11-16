from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRAPE = ROOT / ".scrape"
ROSTER = ROOT / "scripts" / "central_committee_roster.json"
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"

TERMS = {
    18: ("2012-11-15", "2017-10-24", "term_ended"),
    19: ("2017-10-25", "2022-10-22", "term_ended"),
    20: ("2022-10-23", None, "active"),
}

ETHNIC = [
    "壮", "回", "满", "蒙古", "藏", "维吾尔", "苗", "土家", "朝鲜", "哈萨克",
    "锡伯", "白", "傣", "黎", "彝", "侗", "瑶", "布依", "傈僳", "佤", "畲",
    "高山", "拉祜", "水", "东乡", "纳西", "景颇", "柯尔克孜", "土", "达斡尔",
    "仫佬", "羌", "布朗", "撒拉", "毛南", "仡佬", "阿昌", "普米", "塔吉克",
    "怒", "乌孜别克", "俄罗斯", "鄂温克", "德昂", "保安", "裕固", "京",
    "塔塔尔", "独龙", "鄂伦春", "赫哲", "门巴", "珞巴", "基诺",
]


def list_text(term: int) -> str:
    source = (SCRAPE / f"cc{term}.html").read_text(encoding="utf-8", errors="ignore")
    source = re.sub(r"<script.*?</script>", "", source, flags=re.S | re.I)
    source = re.sub(r"<style.*?</style>", "", source, flags=re.S | re.I)
    source = re.sub(r"<[^>]+>", " ", source)
    source = html.unescape(source)
    source = re.sub(r"\\+", "", source)
    source = re.sub(r"\s+", " ", source)
    return source.translate(str.maketrans("０１２３４５６７８９", "0123456789"))


def parse_names(term: int) -> list[str]:
    source = list_text(term)
    match = re.search(r"[（(]\s*(?:205|204)\s*名\s*[）)]", source)
    if not match:
        raise ValueError(f"{term}: member count not found")
    tail = source[match.end():]
    start = tail.find("按姓氏笔画")
    end = tail.find("）", start)
    if end < 0:
        end = tail.find(")", start)
    tail = tail[end + 1:]
    for stop in ("上一页", "责任编辑", "扫一扫", "相关稿件", "【"):
        cut = tail.find(stop)
        if cut > 0:
            tail = tail[:cut]
    names: list[str] = []
    for token in re.findall(r"[\u4e00-\u9fff·]+(?:（[^）]*）)?", tail):
        match = re.match(r"^([\u4e00-\u9fff·]+)(?:（([^）]*)）)?$", token)
        if not match:
            continue
        base, note = match.group(1), match.group(2) or ""
        parts = [part for part in re.split("[，,、]", note) if part]
        descriptor = all(any(ethnic in part for ethnic in ETHNIC) or part in ("女", "男") for part in parts)
        name = base if (not note or descriptor) else f"{base}（{note}）"
        if name not in names:
            names.append(name)
    return names


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    existing = {officer["name"] for officer in data["officers"]}
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    all_names: dict[str, list[int]] = {}
    for term in (18, 19, 20):
        names = parse_names(term)
        assert len(names) == (204 if term == 19 else 205), (term, len(names))
        for name in names:
            base = name.split("（", 1)[0]
            if (
                name not in existing
                and base in existing
                and not name.endswith("（解放军）")
            ):
                name = base
            all_names.setdefault(name, []).append(term)
            records = roster.setdefault(name, [])
            if any(record.get("term") == term and record.get("type") == "member" for record in records):
                continue
            start, end, status = TERMS[term]
            records.append({
                "term": term,
                "type": "member",
                "start": start,
                "end": end,
                "status": status,
            })
    # Remove roster entries that are not in the official term list.  This also
    # clears stale placeholder records that were added before the complete list
    # was available.
    for name, records in list(roster.items()):
        kept = []
        for record in records:
            term = record.get("term")
            if record.get("type") == "member" and term in (18, 19, 20) and name not in all_names:
                continue
            if record.get("type") == "member" and term in TERMS:
                start, end, status = TERMS[term]
                record["start"] = start
                record["end"] = end
                if record.get("status") != "expelled":
                    record["status"] = status
            kept.append(record)
        if kept:
            roster[name] = kept
        else:
            roster.pop(name, None)
    ROSTER.write_text(json.dumps(roster, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    missing = [name for name in all_names if name not in existing]
    print("members unique:", len(all_names), "missing officers:", len(missing))
    for name in missing:
        print(name, all_names[name])


if __name__ == "__main__":
    main()
