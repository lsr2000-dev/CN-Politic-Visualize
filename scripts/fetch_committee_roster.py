import json
import re
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parent.parent
DATASET = json.loads((ROOT / "backend/app/data/dataset.json").read_text(encoding="utf-8"))
NAMES = {officer["name"] for officer in DATASET["officers"]}

EXPEL_20 = {"马兴瑞", "蓝天立", "王莉霞", "孙绍骋"}
TERM_DATES = {18: ("2012-11-15", "2017-10-24"), 19: ("2017-10-25", "2022-10-15"), 20: ("2022-10-16", "2026-10-29")}


def links(title: str) -> set[str]:
    text = httpx.get(
        "https://r.jina.ai/http://zh.wikipedia.org/wiki/" + quote(title),
        timeout=60, headers={"User-Agent": "polvis-demo/1.0"},
    ).text
    found = set(re.findall(r"\[([\u4e00-\u9fa5·]{2,6})\]\(https://zh\.wikipedia\.org/wiki/[^ )]+ \"", text))
    return found


def main() -> None:
    result: dict[str, list[dict]] = {}
    for term in (18, 19, 20):
        for kind, suffix in (("member", "委员"), ("alternate", "候补委员")):
            title = f"中国共产党第{'十八' if term == 18 else '十九' if term == 19 else '二十'}届中央委员会{suffix}列表"
            found = links(title) & NAMES
            start, end = TERM_DATES[term]
            for name in found:
                if kind == "alternate" and name in result and any(r["term"] == term and r["type"] == "member" for r in result[name]):
                    continue
                status = "active" if term == 20 and name not in EXPEL_20 else ("expelled" if term == 20 else "term_ended")
                record = {
                    "term": term,
                    "type": kind,
                    "start": start,
                    "end": "2026-10-29" if status == "expelled" else (None if term == 20 else end),
                    "status": status,
                }
                result.setdefault(name, []).append(record)
            print(term, kind, len(found), flush=True)
    (ROOT / "scripts" / "central_committee_roster.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
