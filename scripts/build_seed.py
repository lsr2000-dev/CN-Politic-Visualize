"""Generate the demo dataset (JSON) and PostgreSQL seed SQL from seed_source.py.

Run:  python scripts/build_seed.py
Outputs:
  backend/app/data/dataset.json
  infra/initdb/02_seed.sql
"""

from __future__ import annotations

import calendar
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from seed_source import (  # noqa: E402
    CENTRAL,
    CLOSE_TENURES,
    EVENTS,
    OFFICER_META,
    PROVINCES,
    REVISIONS,
    DEFAULT_SNAPSHOT_START,
    SNAPSHOT_STARTS,
    ACTING_PRINCIPALS,
    FULL_TIMELINES,
    FULL_ACTING,
    FULL_ACTING_TENURES,
    BASELINE_2012,
)
from current_roster import CURRENT_PRINCIPALS  # noqa: E402
from current_bios import CURRENT_BIOS  # noqa: E402
from wiki_bios import WIKI_BIOS  # noqa: E402
from baseline_2013 import BASELINE_2013  # noqa: E402
from officer_enrichment import ENRICHMENT  # noqa: E402

COVERAGE_START = "2012-11-08"

MINORITY = {
    "巴音朝鲁": "蒙古族", "布小林": "蒙古族", "王莉霞": "蒙古族",
    "蓝天立": "壮族", "韦韬": "壮族", "陈武": "壮族", "马飚": "壮族",
    "雪克来提·扎克尔": "维吾尔族", "努尔·白克力": "维吾尔族",
    "艾尔肯·吐尼亚孜": "维吾尔族", "祖木热提·吾布力": "维吾尔族",
    "艾斯海提·克里木拜": "维吾尔族", "努尔兰·阿不都满金": "哈萨克族",
    "帕巴拉·格列朗杰": "藏族", "向巴平措": "藏族", "白玛赤林": "藏族",
    "洛桑江村": "藏族", "齐扎拉": "藏族", "严金海": "藏族",
    "嘎玛泽登": "藏族", "仁青加": "藏族", "多杰热旦": "藏族",
    "公保扎西": "藏族", "王正伟": "回族", "咸辉": "回族", "张雨浦": "回族",
}
COVERAGE_END = "2026-10-29"
DATASET_ID = "2026.10"
PLENUM_DATE = "2026-10-29"

CATEGORY_LABELS = {
    "party": "党委",
    "congress": "人大",
    "government": "政府",
    "cppcc": "政协",
}

CENTRAL_ORDER = {"李强": 1}


def month_start(value: str) -> date:
    year, month = (int(x) for x in value.split("-")[:2])
    return date(year, month, 1)


def month_end(value: str) -> date:
    year, month = (int(x) for x in value.split("-")[:2])
    return date(year, month, calendar.monthrange(year, month)[1])


def role_titles(province: dict) -> dict[str, tuple[str, str]]:
    """Return category -> (title, full_title) for a province."""
    short = province["short"]
    is_municipality = province["name"].endswith("市")
    is_autonomous = province["name"].endswith("自治区")

    if is_municipality:
        party, gov, cong, cppcc = (
            f"{short}市委书记",
            f"{short}市长",
            f"{short}市人大常委会主任",
            f"{short}市政协主席",
        )
    elif is_autonomous:
        base = province["name"].removesuffix("自治区")
        party, gov, cong, cppcc = (
            f"{base}自治区党委书记",
            f"{base}自治区主席",
            f"{base}自治区人大常委会主任",
            f"{base}自治区政协主席",
        )
    else:
        party, gov, cong, cppcc = (
            f"{short}省委书记",
            f"{short}省长",
            f"{short}省人大常委会主任",
            f"{short}省政协主席",
        )
    return {
        "party": (party, f"中共{party}"),
        "government": (gov, gov),
        "congress": (cong, cong),
        "cppcc": (cppcc, cppcc),
    }


def acting_title(category: str, title: str) -> str:
    if category == "government":
        return "代" + title
    if category == "party":
        return "代理" + title
    return "代理" + title


class Builder:
    def __init__(self) -> None:
        self.regions: list[dict] = []
        self.officers: list[dict] = []
        self.officer_index: dict[str, dict] = {}
        self.positions: list[dict] = []
        self.position_index: dict[tuple, dict] = {}
        self.tenures: list[dict] = []
        self.events: list[dict] = []
        self.warnings: list[str] = []

    # -- officers -----------------------------------------------------
    def officer(self, name: str) -> dict:
        if name in self.officer_index:
            return self.officer_index[name]
        meta = dict(OFFICER_META.get(name, {}))
        for bios in (WIKI_BIOS.get(name, {}), CURRENT_BIOS.get(name, {})):
            if bios.get("birth_year") is not None and not meta.get("birth_year"):
                meta["birth_year"] = bios["birth_year"]
            if bios.get("native_place") and not meta.get("native"):
                meta["native"] = bios["native_place"]
        officer = {
            "id": len(self.officers) + 1,
            "slug": f"p{len(self.officers) + 1:03d}",
            "name": name,
            "gender": meta.get("gender"),
            "birth_year": meta.get("birth_year"),
            "native_place": meta.get("native"),
            "ethnicity": meta.get("ethnicity"),
            "party_join_date": month_start(meta["party_join"]).isoformat() if meta.get("party_join") else None,
            "work_start_date": month_start(meta["work_start"]).isoformat() if meta.get("work_start") else None,
            "education": meta.get("education"),
            "degree": meta.get("degree"),
            "school": meta.get("school"),
            "bio": meta.get("bio"),
            "portrait_url": None,
            "is_deceased": False,
        }
        self.officers.append(officer)
        self.officer_index[name] = officer
        return officer

    # -- positions ----------------------------------------------------
    def position(self, region_code: str | None, category: str, seat_key: str,
                 title: str, rank: int, full_title: str | None = None,
                 org_name: str | None = None,
                 rank_level: str = "provincial_principal",
                 team_group: str | None = None,
                 is_singular: bool = True) -> dict:
        key = (region_code, seat_key, title)
        if key in self.position_index:
            return self.position_index[key]
        position = {
            "id": len(self.positions) + 1,
            "region_code": region_code,
            "category": category,
            "seat_key": seat_key,
            "title": title,
            "full_title": full_title or title,
            "rank": rank,
            "rank_level": rank_level,
            "team_group": team_group,
            "is_singular": is_singular,
            "is_leader": is_singular and rank <= 4,
            "org_name": org_name,
        }
        self.positions.append(position)
        self.position_index[key] = position
        return position

    # -- tenures ------------------------------------------------------
    def add_seat(self, officer_name: str, region_code: str | None, category: str,
                 seat_key: str, title: str, rank: int, start: str,
                 end: str | None, acting: bool, org_name: str | None = None,
                 full_title: str | None = None,
                 rank_level: str = "provincial_principal",
                 team_group: str | None = None,
                 is_plural: bool = False,
                 start_precision: str = "month",
                 end_reason: str | None = None,
                 notes: str | None = None) -> None:
        officer = self.officer(officer_name)
        position = self.position(
            region_code, category, seat_key, title, rank,
            full_title=full_title, org_name=org_name,
            rank_level=rank_level, team_group=team_group,
            is_singular=not is_plural,
        )
        title_snapshot = acting_title(category, title) if acting else title
        if start_precision == "snapshot":
            start_date = date.fromisoformat(start)
        else:
            start_date = month_start(start)
        self.tenures.append({
            "officer_id": officer["id"],
            "position_id": position["id"],
            "region_code": region_code,
            "category": category,
            "title": title_snapshot,
            "start_date": start_date.isoformat(),
            "end_date": month_end(end).isoformat() if end else None,
            "_start_month": start,
            "_end_month": end,
            "start_precision": start_precision,
            "end_precision": "month" if end else None,
            "is_acting": acting,
            "is_concurrent": False,
            "is_plural": is_plural,
            "rank_level": rank_level,
            "end_reason": end_reason,
            "end_reason_detail": None,
            "appointment_basis": None,
            "verified": False,
            "notes": notes or "演示数据；日期为月份级精度",
            "seat_key": seat_key,
        })

    def add_event(self, officer_name: str, event_type: str, event_date: str,
                  title: str, description: str | None = None,
                  source_url: str | None = None,
                  source_title: str | None = None,
                  verified: bool = False) -> None:
        officer = self.officer(officer_name)
        self.events.append({
            "id": len(self.events) + 1,
            "officer_id": officer["id"],
            "event_type": event_type,
            "event_date": event_date,
            "title": title,
            "description": description,
            "source_url": source_url,
            "source_title": source_title,
            "verified": verified,
        })

    def normalize(self) -> None:
        """Close gaps/overlaps between adjacent records of the same seat."""
        groups: dict[int, list[dict]] = {}
        for tenure in self.tenures:
            groups.setdefault(tenure["position_id"], []).append(tenure)

        for group in groups.values():
            group.sort(key=lambda t: t["start_date"])
            for current, nxt in zip(group, group[1:]):
                if current["end_date"] is None:
                    self.warnings.append(
                        f"open tenure {current['officer_id']} at position {current['position_id']} closed before successor"
                    )
                    current["end_date"] = (
                        date.fromisoformat(nxt["start_date"]) - timedelta(days=1)
                    ).isoformat()
                elif current["end_date"] >= nxt["start_date"]:
                    current["end_date"] = (
                        date.fromisoformat(nxt["start_date"]) - timedelta(days=1)
                    ).isoformat()
            for tenure in group:
                if tenure["end_date"] and tenure["end_date"] < tenure["start_date"]:
                    tenure["end_date"] = tenure["start_date"]
                    self.warnings.append(f"collapsed negative tenure for {tenure['officer_id']}")

    def build(self) -> dict:
        self.regions.append({
            "code": "100000", "name": "中华人民共和国", "short_name": "全国",
            "level": "country", "parent_code": None,
            "centroid": [104.1954, 35.8617], "sort_order": 0,
        })
        for index, province in enumerate(PROVINCES, start=1):
            self.regions.append({
                "code": province["code"],
                "name": province["name"],
                "short_name": province["short"],
                "level": "province",
                "parent_code": "100000",
                "centroid": [province["lon"], province["lat"]],
                "sort_order": index,
            })

        for province in PROVINCES:
            titles = role_titles(province)
            entries = {category: list(province[category]) for category in
                       ("party", "government", "congress", "cppcc")}
            for category, extra in REVISIONS.get(province["code"], {}).items():
                entries.setdefault(category, []).extend(extra)
            for category, rank in (("party", 1), ("government", 2),
                                   ("congress", 3), ("cppcc", 4)):
                seat_key = {"party": "party_secretary", "government": "governor",
                            "congress": "congress_chair", "cppcc": "cppcc_chair"}[category]
                title, full_title = titles[category]
                for name, start, end, acting in entries[category]:
                    self.add_seat(name, province["code"], category, seat_key,
                                  title, rank, start, end, acting,
                                  full_title=full_title,
                                  rank_level="provincial_principal",
                                  team_group=f"{category}_principal")
            for name, start, end, acting in province.get("deputies", []):
                self.add_seat(name, province["code"], "party", "party_deputy_secretary",
                              f"{province['short']}省委副书记", 5, start, end, acting,
                              rank_level="provincial_deputy",
                              team_group="party_deputy", is_plural=True)

        for name, roles in CENTRAL.items():
            for index, (title, start, end, category, org) in enumerate(roles, start=1):
                # Central roles are not exclusive seats (e.g. all PSC members
                # hold the same office concurrently), so key by person.
                seat_key = f"central_{re.sub(r'[^0-9]', '', start)}_{index}_{name}"
                if any(key in title for key in ("政治局常委", "国务院总理", "中央书记处", "纪律检查")):
                    rank_level = "national_leader"
                elif any(key in title for key in ("国务院副总理", "国务委员", "最高人民法院院长",
                                                  "最高人民检察院检察长")):
                    rank_level = "vice_national_leader"
                elif "副书记" in title:
                    rank_level = "provincial_deputy"
                else:
                    rank_level = "ministerial"
                self.add_seat(name, None, category, seat_key, title, 9,
                              start, end, False, org_name=org,
                              full_title=org + title, rank_level=rank_level,
                              team_group="central",
                              is_plural="副书记" in title)

        # 2013 年省级两会换届基线：补全 2013–2022 年人大/政协正职，
        # 避免只有 2012 年零散记录和 2023 年现任快照、中间整段空白。
        for province in PROVINCES:
            titles = role_titles(province)
            for category in ("congress", "cppcc"):
                baseline_name = BASELINE_2013.get(province["code"], {}).get(category)
                if not baseline_name:
                    continue
                current = CURRENT_PRINCIPALS.get(province["code"], {}).get(category)
                current_name = current[0] if current else None
                if (current_name and baseline_name
                        and current_name.replace("·", "").replace(" ", "")
                        == baseline_name.replace("·", "").replace(" ", "")
                        and (province["code"], category) == ("540000", "cppcc")):
                    # 帕巴拉·格列朗杰自 1993 年起长期连任，当前快照已覆盖
                    continue
                seat_key = "congress_chair" if category == "congress" else "cppcc_chair"
                title, full_title = titles[category]
                position = self.position(
                    province["code"], category, seat_key, title, 3 if category == "congress" else 4,
                    full_title=full_title, rank_level="provincial_principal",
                    team_group=f"{category}_principal",
                )
                covered = any(
                    t["position_id"] == position["id"]
                    and t["start_date"] <= "2013-01-01"
                    and (t["end_date"] is None or t["end_date"] >= "2013-01-01")
                    for t in self.tenures
                )
                if covered:
                    continue
                self.add_seat(
                    baseline_name, province["code"], category, seat_key, title,
                    3 if category == "congress" else 4,
                    "2013-01-01", "2022-12-31", False, full_title=full_title,
                    rank_level="provincial_principal",
                    team_group=f"{category}_principal",
                    start_precision="month",
                    notes="2013 年省级两会换届基线（新华网/新浪 2013-02-01 名单）",
                )

        # 2026-10-29 现任名册：名称来自中国经济网省级领导人物库。
        # 若现有开放任职已是对应人物则保留；否则新增一条 snapshot 精度记录，
        # 由 normalize 关闭前任（具体到任日待考）。
        for province in PROVINCES:
            titles = role_titles(province)
            for category, rank in (("party", 1), ("government", 2),
                                   ("congress", 3), ("cppcc", 4)):
                current = CURRENT_PRINCIPALS.get(province["code"], {}).get(category)
                if not current or not current[0]:
                    continue
                name, source_url = current
                seat_key = {"party": "party_secretary", "government": "governor",
                            "congress": "congress_chair", "cppcc": "cppcc_chair"}[category]
                title, full_title = titles[category]
                position = self.position(
                    province["code"], category, seat_key, title, rank,
                    full_title=full_title, rank_level="provincial_principal",
                    team_group=f"{category}_principal",
                )
                open_rows = [t for t in self.tenures
                             if t["position_id"] == position["id"] and t["end_date"] is None]
                if any(t["officer_id"] == self.officer(name)["id"] for t in open_rows):
                    continue
                start_month = SNAPSHOT_STARTS.get(
                    (province["code"], category),
                    DEFAULT_SNAPSHOT_START[category],
                )
                start_date = f"{start_month}-01"
                self.add_seat(
                    name, province["code"], category, seat_key, title, rank,
                    start_date, None, False, full_title=full_title,
                    rank_level="provincial_principal",
                    team_group=f"{category}_principal",
                    start_precision="snapshot",
                    notes=(f"截至 {COVERAGE_END} 现任；起始按公开报道/届次推定为 "
                           f"{start_month}（具体到日待考）；来源：{source_url}"),
                )

        # 已核对省份：用完整时间线整体替换基线/快照/主持工作占位。
        province_by_code = {province["code"]: province for province in PROVINCES}
        for code, categories in FULL_TIMELINES.items():
            self.tenures = [
                tenure for tenure in self.tenures
                if not (tenure["region_code"] == code and tenure["category"] in categories)
            ]
            province = province_by_code[code]
            titles = role_titles(province)
            for category, rows in categories.items():
                seat_key = {"party": "party_secretary", "government": "governor",
                            "congress": "congress_chair", "cppcc": "cppcc_chair"}[category]
                title, full_title = titles[category]
                self.position(
                    code, category, seat_key, title,
                    {"party": 1, "government": 2, "congress": 3, "cppcc": 4}[category],
                    full_title=full_title, rank_level="provincial_principal",
                    team_group=f"{category}_principal",
                )
                for name, start, end in rows:
                    presiding = (code, category, name) in FULL_ACTING
                    acting = (code, category, name, start) in FULL_ACTING_TENURES
                    self.add_seat(
                        name, code, category, seat_key, title,
                        {"party": 1, "government": 2, "congress": 3, "cppcc": 4}[category],
                        start, end, acting,
                        full_title=full_title,
                        rank_level="provincial_principal",
                        team_group=f"{category}_principal",
                        start_precision="day",
                        notes=("维基百科机构页 + 中国经济网现任交叉；逐节点 A 级来源待补"
                               + ("；正职空缺，由第一副职主持工作" if presiding else "")),
                    )
                    if presiding:
                        self.tenures[-1]["title"] = f"{title}（主持工作）"

        # 2012 年 11 月至 12 月的上一届四套正职，避免 2012 检查点整体缺失。
        for code, names in BASELINE_2012.items():
            province = province_by_code[code]
            titles = role_titles(province)
            for category, name in zip(("party", "congress", "government", "cppcc"), names):
                if not name:
                    continue
                covered = any(
                    t["region_code"] == code and t["category"] == category
                    and t["start_date"] <= "2012-11-15"
                    and (not t["end_date"] or t["end_date"] >= "2012-12-15")
                    for t in self.tenures
                )
                if covered:
                    continue
                seat_key = {"party": "party_secretary", "government": "governor",
                            "congress": "congress_chair", "cppcc": "cppcc_chair"}[category]
                title, full_title = titles[category]
                self.add_seat(
                    name, code, category, seat_key, title,
                    {"party": 1, "government": 2, "congress": 3, "cppcc": 4}[category],
                    "2012-11-08", "2012-12-31", False,
                    full_title=full_title, rank_level="provincial_principal",
                    team_group=f"{category}_principal", start_precision="day",
                    notes="2012 年 2 月省级两会后正职（华夏时报/中新网表）",
                )

        # 正职空缺时，由第一副职/党组书记主持工作，保持班子连续可查询。
        province_by_code = {province["code"]: province for province in PROVINCES}
        for code, category, name in ACTING_PRINCIPALS:
            if code in FULL_TIMELINES:
                continue
            province = province_by_code[code]
            titles = role_titles(province)
            seat_key = "congress_chair" if category == "congress" else "cppcc_chair"
            title, full_title = titles[category]
            position = self.position(
                code, category, seat_key, title, 3 if category == "congress" else 4,
                full_title=full_title, rank_level="provincial_principal",
                team_group=f"{category}_principal",
            )
            open_rows = [t for t in self.tenures
                         if t["position_id"] == position["id"] and t["end_date"] is None]
            if open_rows:
                continue
            start_month = SNAPSHOT_STARTS.get((code, category), "2026-10")
            self.add_seat(
                name, code, category, seat_key, title,
                3 if category == "congress" else 4,
                f"{start_month}-01", None, False,
                full_title=full_title,
                rank_level="provincial_principal",
                team_group=f"{category}_principal",
                start_precision="month",
                notes=(f"正职空缺，由第一副职/党组书记主持工作；"
                       f"截至 {COVERAGE_END}；起始月份按公开报道推定"),
            )
            self.tenures[-1]["title"] = f"{title}（主持工作）"

        # 对已经离任但没有继任者的记录，显式收口并写明原因
        for officer_name, end_date, reason in CLOSE_TENURES:
            officer = self.officer_index.get(officer_name)
            if officer is None:
                continue
            for tenure in self.tenures:
                if tenure["officer_id"] == officer["id"] and tenure["end_date"] is None:
                    tenure["end_date"] = end_date
                    tenure["end_reason"] = reason
                    tenure["notes"] = "离任原因依据公开通报；具体交接日待考"

        for event in EVENTS:
            self.add_event(
                event["officer"], event["type"], event["date"], event["title"],
                description=event.get("description"),
                source_url=event.get("source_url"),
                source_title=event.get("source_title"),
                verified=event.get("verified", False),
            )

        self.normalize()
        for index, tenure in enumerate(self.tenures, start=1):
            tenure["id"] = index
            tenure.pop("_start_month", None)
            tenure.pop("_end_month", None)
            tenure.pop("seat_key", None)

        # 补全官员基础字段；缺失性别/民族按公开履历的绝对多数处理，
        # 已识别的少数民族按 MINORITY 覆盖。
        for officer in self.officers:
            fields = ENRICHMENT.get(officer["name"], {})
            for key in ("birth_year", "native_place", "gender", "ethnicity", "party_join_date"):
                if not officer.get(key) and fields.get(key):
                    officer[key] = fields[key]
            if not officer.get("gender"):
                officer["gender"] = "M"
            if not officer.get("ethnicity"):
                officer["ethnicity"] = MINORITY.get(officer["name"], "汉族")

        meta = {
            "id": DATASET_ID,
            "coverage_start": COVERAGE_START,
            "coverage_end": COVERAGE_END,
            "curated_at": COVERAGE_END,
            "status": "demo",
            "disclaimer": (
                "本项目内置数据为产品演示用样例，月份级精度，部分日期依据公开报道推定，"
                "不构成权威人事档案。用于生产前须逐条核对官方来源并在 sources 表中留痕。"
            ),
            "counts": {
                "regions": len(self.regions),
                "officers": len(self.officers),
                "positions": len(self.positions),
                "tenures": len(self.tenures),
                "events": len(self.events),
            },
            "plenum_date": PLENUM_DATE,
        }
        return {
            "meta": meta,
            "regions": self.regions,
            "officers": self.officers,
            "positions": self.positions,
            "tenures": self.tenures,
            "events": self.events,
        }


def sql_escape(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def write_sql(dataset: dict, path: Path) -> None:
    lines: list[str] = [
        "-- AUTO-GENERATED by scripts/build_seed.py — do not edit by hand.",
        "-- Demo data: month-level precision, unverified. See docs/data-governance.md.",
        "SET search_path = polvis, public;",
        "BEGIN;",
        "TRUNCATE polvis.tenure_sources, polvis.officer_events, polvis.change_log,"
        " polvis.tenures, polvis.positions, polvis.officers, polvis.regions,"
        " polvis.dataset_versions RESTART IDENTITY CASCADE;",
        "",
        "INSERT INTO polvis.dataset_versions (id, coverage_start, coverage_end, status, notes, published_at)",
        f"VALUES ({sql_escape(dataset['meta']['id'])}, {sql_escape(dataset['meta']['coverage_start'])},"
        f" {sql_escape(dataset['meta']['coverage_end'])}, 'published',"
        f" {sql_escape(dataset['meta']['disclaimer'])}, now());",
        "",
        "INSERT INTO polvis.regions (code, name, short_name, level, parent_code, sort_order) VALUES",
    ]
    rows = []
    for region in dataset["regions"]:
        rows.append(
            f"({sql_escape(region['code'])}, {sql_escape(region['name'])},"
            f" {sql_escape(region['short_name'])}, {sql_escape(region['level'])},"
            f" {sql_escape(region['parent_code'])}, {region['sort_order']})"
        )
    lines.append(",\n".join(rows) + ";")

    lines.append("")
    lines.append("INSERT INTO polvis.officers (id, slug, name, gender, birth_year, native_place,"
                 " ethnicity, party_join_date, work_start_date, education, degree, school, bio,"
                 " portrait_url, is_deceased) OVERRIDING SYSTEM VALUE VALUES")
    rows = []
    for officer in dataset["officers"]:
        rows.append(
            "(" + ", ".join([
                str(officer["id"]), sql_escape(officer["slug"]), sql_escape(officer["name"]),
                sql_escape(officer["gender"]), sql_escape(officer["birth_year"]),
                sql_escape(officer["native_place"]), sql_escape(officer["ethnicity"]),
                sql_escape(officer["party_join_date"]), sql_escape(officer["work_start_date"]),
                sql_escape(officer["education"]), sql_escape(officer["degree"]),
                sql_escape(officer["school"]), sql_escape(officer["bio"]),
                "NULL", sql_escape(officer["is_deceased"]),
            ]) + ")"
        )
    lines.append(",\n".join(rows) + ";")

    lines.append("")
    lines.append("INSERT INTO polvis.positions (id, seat_key, region_code, category, title,"
                 " full_title, rank, rank_level, team_group, is_singular, is_leader,"
                 " org_name) OVERRIDING SYSTEM VALUE VALUES")
    rows = []
    for position in dataset["positions"]:
        rows.append(
            "(" + ", ".join([
                str(position["id"]), sql_escape(position["seat_key"]),
                sql_escape(position["region_code"]), sql_escape(position["category"]),
                sql_escape(position["title"]), sql_escape(position["full_title"]),
                str(position["rank"]), sql_escape(position["rank_level"]),
                sql_escape(position["team_group"]), sql_escape(position["is_singular"]),
                sql_escape(position["is_leader"]), sql_escape(position["org_name"]),
            ]) + ")"
        )
    lines.append(",\n".join(rows) + ";")

    lines.append("")
    lines.append("INSERT INTO polvis.tenures (id, officer_id, position_id, region_code, category,"
                 " title, start_date, end_date, start_precision, end_precision, is_acting,"
                 " is_concurrent, is_plural, rank_level_snapshot, end_reason,"
                 " end_reason_detail, verified, notes, dataset_version)"
                 " OVERRIDING SYSTEM VALUE VALUES")
    rows = []
    for tenure in dataset["tenures"]:
        rows.append(
            "(" + ", ".join([
                str(tenure["id"]), str(tenure["officer_id"]), str(tenure["position_id"]),
                sql_escape(tenure["region_code"]), sql_escape(tenure["category"]),
                sql_escape(tenure["title"]), sql_escape(tenure["start_date"]),
                sql_escape(tenure["end_date"]), sql_escape(tenure["start_precision"]),
                sql_escape(tenure["end_precision"]), sql_escape(tenure["is_acting"]),
                sql_escape(tenure["is_concurrent"]), sql_escape(tenure.get("is_plural", False)),
                sql_escape(tenure.get("rank_level", "provincial_deputy")),
                sql_escape(tenure.get("end_reason")),
                sql_escape(tenure.get("end_reason_detail")),
                sql_escape(tenure["verified"]),
                sql_escape(tenure["notes"]), sql_escape(dataset["meta"]["id"]),
            ]) + ")"
        )
    lines.append(",\n".join(rows) + ";")

    lines.append("")
    lines.append("INSERT INTO polvis.officer_events (id, officer_id, event_type, event_date,"
                 " title, description, source_url, source_title, verified)"
                 " OVERRIDING SYSTEM VALUE VALUES")
    rows = []
    for event in dataset.get("events", []):
        rows.append(
            "(" + ", ".join([
                str(event["id"]), str(event["officer_id"]),
                sql_escape(event["event_type"]), sql_escape(event["event_date"]),
                sql_escape(event["title"]), sql_escape(event.get("description")),
                sql_escape(event.get("source_url")), sql_escape(event.get("source_title")),
                sql_escape(event.get("verified", False)),
            ]) + ")"
        )
    if rows:
        lines.append(",\n".join(rows) + ";")

    for table in ("officers", "positions", "tenures", "officer_events"):
        lines.append(
            f"SELECT setval(pg_get_serial_sequence('polvis.{table}', 'id'),"
            f" COALESCE((SELECT MAX(id) FROM polvis.{table}), 1));"
        )
    lines += ["", "COMMIT;", "", "ANALYZE polvis.tenures;", "ANALYZE polvis.positions;"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    dataset = Builder().build()
    data_path = ROOT / "backend" / "app" / "data" / "dataset.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(
        json.dumps(dataset, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    write_sql(dataset, ROOT / "infra" / "initdb" / "02_seed.sql")
    counts = dataset["meta"]["counts"]
    print(f"dataset: {counts}")
    print(f"wrote {data_path}")
    print(f"wrote {ROOT / 'infra' / 'initdb' / '02_seed.sql'}")


if __name__ == "__main__":
    main()
