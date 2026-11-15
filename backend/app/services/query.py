from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..core.cache import CacheLayer, dumps
from .central import central_service
from ..domain import (
    CATEGORY_META,
    CATEGORY_ORDER,
    END_REASON_LABELS,
    RANK_LABELS,
    STATUS_LABELS,
    Officer,
    OfficerEvent,
    Region,
    Tenure,
)
from ..repositories.base import Repository

log = logging.getLogger(__name__)

# 中央政治局委员/常委的「就任」时间。行政级别随时间变化：
# 同一人在进入政治局前是正省部级，进入后按副国级/正国级展示。
_RANK_PERIODS = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "rank_periods.json")
    .read_text(encoding="utf-8")
)
_POLITBURO_SINCE = {name: date.fromisoformat(value)
                    for name, value in _RANK_PERIODS["politburo"].items()}
_PSC_SINCE = {name: date.fromisoformat(value)
              for name, value in _RANK_PERIODS["psc"].items()}


class NotFoundError(Exception):
    pass


class RangeError(Exception):
    pass


TIMELINE_EVENTS: list[dict[str, Any]] = [
    {"date": "2012-11-08", "type": "congress", "label": "中共十八大",
     "description": "中国共产党第十八次全国代表大会开幕，本系统时间轴起点。"},
    {"date": "2013-03-05", "type": "npc", "label": "十二届全国人大一次会议",
     "description": "新一届国务院组成人员产生，省级政府主官陆续换届。"},
    {"date": "2017-10-18", "type": "congress", "label": "中共十九大",
     "description": "中国特色社会主义进入新时代，省级党委集中换届。"},
    {"date": "2018-03-05", "type": "npc", "label": "十三届全国人大一次会议",
     "description": "深化党和国家机构改革，省级人大、政府换届。"},
    {"date": "2022-10-16", "type": "congress", "label": "中共二十大",
     "description": "新一届中央领导机构产生，省级党委主官密集调整。"},
    {"date": "2023-03-05", "type": "npc", "label": "十四届全国人大一次会议",
     "description": "国务院换届，省级政府主官同步调整。"},
    {"date": "2026-10-29", "type": "congress", "label": "二十届五中全会",
     "description": "全会于 2026 年 10 月 26—29 日举行；本系统数据截至闭幕日。"},
]

METRICS = [
    {"key": "party_days", "label": "党委书记在任天数", "unit": "天", "kind": "continuous"},
    {"key": "governor_days", "label": "政府主官在任天数", "unit": "天", "kind": "continuous"},
    {"key": "party_count", "label": "十八大以来党委书记人数", "unit": "人", "kind": "discrete"},
    {"key": "governor_count", "label": "十八大以来政府主官人数", "unit": "人", "kind": "discrete"},
    {"key": "filled", "label": "班子收录完整度", "unit": "/4", "kind": "discrete"},
]

EVENT_LABELS: dict[str, str] = {
    "retired": "退休",
    "under_investigation": "接受审查（结果待公布）",
    "expelled_from_party": "开除党籍/公职",
    "expelled_from_public_office": "开除公职",
    "expelled": "双开",
    "deceased": "病逝",
    "removed_from_office": "免职",
}
EVENT_TYPES = tuple(EVENT_LABELS)

# 2026-10 九个席位正职空缺，但已由第一副职/党组书记主持工作，
# 因此在覆盖口径中按“班子连续”处理，不再计为空缺。
KNOWN_VACANCIES: list[dict[str, str]] = []


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


class QueryService:
    def __init__(self, repo: Repository, cache: CacheLayer, settings) -> None:
        self.repo = repo
        self.cache = cache
        self.settings = settings
        self.coverage_start = date.fromisoformat(str(repo.meta["coverage_start"]))
        self.coverage_end = date.fromisoformat(str(repo.meta["coverage_end"]))
        self.today = date.today()

    # -- helpers ------------------------------------------------------
    def _key(self, *parts: object) -> str:
        self.repo.reload_if_changed()
        self.coverage_start = date.fromisoformat(str(self.repo.meta["coverage_start"]))
        self.coverage_end = date.fromisoformat(str(self.repo.meta["coverage_end"]))
        version = getattr(self.repo, "dataset_version", 0)
        if parts and parts[0] == "meta":
            return f"polvis:{self.repo.dataset_id}:{version}:meta:v4"
        # v4: include the dataset file version so hot reload cannot serve stale cache.
        scope = hashlib.sha1("|".join(map(str, (*parts, "v4", version))).encode()).hexdigest()[:12]
        prefix = ":".join(str(part) for part in parts[:2])
        return f"polvis:{self.repo.dataset_id}:{version}:{prefix}:{scope}"

    def _cached(self, key: str, producer, ttl: int | None = None) -> tuple[dict[str, Any], str]:
        raw = self.cache.get(key)
        if raw is not None:
            return json.loads(raw), "HIT"
        payload = producer()
        self.cache.set(key, dumps(payload), ttl=ttl)
        return payload, "MISS"

    def coverage_badge(self, as_of: date) -> dict[str, Any]:
        """Small coverage object embedded in snapshot/profile/career responses."""
        return {
            "dataset_id": self.repo.dataset_id,
            "coverage_start": _iso(self.coverage_start),
            "coverage_end": _iso(self.coverage_end),
            "beyond_coverage": as_of > self.coverage_end,
            "status": self.repo.meta.get("status", "demo"),
            "disclaimer": self.repo.meta.get("disclaimer"),
        }

    def effective_as_of(self, as_of: date) -> date:
        """Duration is clamped to the curated coverage end; the state query
        still uses the requested date so that 'beyond coverage' is explicit."""
        return min(as_of, self.coverage_end)

    # -- meta ---------------------------------------------------------
    def meta(self) -> tuple[dict[str, Any], str]:
        def build() -> dict[str, Any]:
            counts = self.repo.meta.get("counts") or {}
            return {
                "dataset": {
                    "id": self.repo.dataset_id,
                    "coverage_start": _iso(self.coverage_start),
                    "coverage_end": _iso(self.coverage_end),
                    "plenum_date": _iso(self.coverage_end),
                    "status": self.repo.meta.get("status", "demo"),
                    "disclaimer": self.repo.meta.get("disclaimer"),
                    "counts": counts,
                },
                "categories": [
                    {"key": key, **CATEGORY_META[key]} for key in CATEGORY_ORDER
                ],
                "metrics": METRICS,
                "events": TIMELINE_EVENTS,
                "geo": {
                    "geojson": "/geo/china-provinces.json",
                    "adcode_property": "adcode",
                    "name_property": "name",
                },
                "timezone": "Asia/Shanghai",
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            }

        return self._cached(self._key("meta", "v1"), build)

    # -- snapshot -----------------------------------------------------
    @staticmethod
    def rank_at(officer_name: str, at: date, fallback: str) -> str:
        """Return the administrative rank at a given date.

        A provincial party secretary who is also a Politburo member is
        ／副国级／, not ／正省部级／. The same person may have been 正省部级
        before entering the Politburo, so this is date-aware rather than a
        blanket per-person override.
        """
        if officer_name in _PSC_SINCE and at >= _PSC_SINCE[officer_name]:
            return "national_leader"
        if officer_name in _POLITBURO_SINCE and at >= _POLITBURO_SINCE[officer_name]:
            return "vice_national_leader"
        return fallback

    def _member(self, tenure: Tenure, as_of: date) -> dict[str, Any]:
        effective = self.effective_as_of(as_of)
        snapshot_only = tenure.start_precision == "snapshot"
        # 现任名册的起始月份已按公开报道/届次推定；仍保留 snapshot 标记，
        # 但可以计算“约在任多久”，不再一律显示 0 天。
        duration = tenure.duration_days(effective)
        if snapshot_only and tenure.start_date >= effective:
            duration = 0
        rank_date = min(effective, tenure.end_date or effective)
        rank_level = self.rank_at(tenure.officer_name, rank_date, tenure.rank_level)
        return {
            "tenure_id": tenure.id,
            "officer": tenure.officer_brief(),
            "title": tenure.title,
            "category": tenure.category,
            "seat_key": tenure.seat_key,
            "position_uid": tenure.position_uid,
            "seat_rank": tenure.seat_rank,
            "region_code": tenure.region_code,
            "region_name": tenure.region_name,
            "region_short_name": tenure.region_short_name,
            "rank_level": rank_level,
            "rank_label": RANK_LABELS.get(rank_level, "级别待考"),
            "is_acting": tenure.is_acting,
            "is_concurrent": tenure.is_concurrent,
            "is_plural": tenure.is_plural,
            "start_date": _iso(tenure.start_date),
            "end_date": _iso(tenure.end_date),
            "start_precision": tenure.start_precision,
            "duration_days": duration,
            "is_incumbent": tenure.is_incumbent,
            "is_provisional": tenure.is_incumbent and as_of > self.coverage_end,
            "is_roster_snapshot": snapshot_only,
            "status": "active" if tenure.end_date is None else "left",
            "status_label": STATUS_LABELS["active" if tenure.end_date is None else "left"],
            "exit_reason": tenure.end_reason,
            "exit_reason_label": END_REASON_LABELS.get(tenure.end_reason or "", None),
            "verified": tenure.verified,
        }

    def _region_snapshot(self, region: Region, current: list[Tenure],
                         history: list[Tenure], as_of: date) -> dict[str, Any]:
        teams: dict[str, Any] = {}
        total_members = 0
        acting = 0
        filled = 0
        for category in CATEGORY_ORDER:
            members = sorted(
                (t for t in current if t.category == category),
                key=lambda t: (t.seat_rank, t.start_date),
            )
            if members:
                filled += 1
            acting += sum(1 for t in members if t.is_acting)
            total_members += len(members)
            teams[category] = {
                "key": category,
                "label": CATEGORY_META[category]["label"],
                "members": [self._member(t, as_of) for t in members],
            }

        def lead_of(category: str) -> dict[str, Any] | None:
            members = teams[category]["members"]
            return members[0] if members else None

        party_members = [t for t in history if t.seat_key == "party_secretary"
                         and not t.is_acting and not t.is_concurrent]
        governor_members = [t for t in history if t.seat_key == "governor"
                            and not t.is_acting and not t.is_concurrent]
        party_lead = lead_of("party")
        governor = lead_of("government")

        return {
            "region_code": region.code,
            "region_name": region.name,
            "short_name": region.short_name,
            "level": region.level,
            "centroid": list(region.centroid) if region.centroid else None,
            "teams": teams,
            "headline": {
                "party": party_lead,
                "government": governor,
                "congress": lead_of("congress"),
                "cppcc": lead_of("cppcc"),
            },
            "filled": filled,
            "member_count": total_members,
            "acting_count": acting,
            "metrics": {
                "party_days": party_lead["duration_days"] if party_lead else 0,
                "governor_days": governor["duration_days"] if governor else 0,
                "party_count": len(party_members),
                "governor_count": len(governor_members),
                "filled": filled,
                "acting": acting,
            },
        }

    def snapshot(self, as_of: date, region_codes: Sequence[str] | None = None,
                 categories: Sequence[str] | None = None) -> tuple[dict[str, Any], str]:
        codes = sorted(set(region_codes)) if region_codes else None
        key = self._key("snap", as_of.isoformat(), ",".join(codes or ["all"]),
                        ",".join(categories or CATEGORY_ORDER))

        def build() -> dict[str, Any]:
            regions = [
                r for r in self.repo.list_regions(level="province")
                if codes is None or r.code in codes
            ]
            regions.sort(key=lambda r: r.sort_order)
            current = self.repo.tenures_at(as_of, codes, categories)
            history = self.repo.tenures_in_range(
                self.coverage_start, self.effective_as_of(as_of), codes
            )
            current_by_region: dict[str, list[Tenure]] = {}
            for tenure in current:
                if tenure.region_code:
                    current_by_region.setdefault(tenure.region_code, []).append(tenure)
            history_by_region: dict[str, list[Tenure]] = {}
            for tenure in history:
                if tenure.region_code:
                    history_by_region.setdefault(tenure.region_code, []).append(tenure)

            items = [
                self._region_snapshot(
                    region,
                    current_by_region.get(region.code, []),
                    history_by_region.get(region.code, []),
                    as_of,
                )
                for region in regions
            ]
            return {
                "as_of": _iso(as_of),
                "coverage": self.coverage_badge(as_of),
                "stats": {
                    "region_count": len(items),
                    "member_count": sum(item["member_count"] for item in items),
                    "acting_count": sum(item["acting_count"] for item in items),
                    "regions_with_gaps": sum(1 for item in items if item["filled"] < 4),
                },
                "regions": items,
            }

        return self._cached(key, build)

    def region_detail(self, region_code: str, as_of: date) -> tuple[dict[str, Any], str]:
        region = self.repo.get_region(region_code)
        if region is None:
            raise NotFoundError(f"region {region_code} not found")
        snapshot, status = self.snapshot(as_of, [region_code])
        item = snapshot["regions"][0] if snapshot["regions"] else None
        if item is None:
            raise NotFoundError(f"region {region_code} has no leadership data")
        return {
            "as_of": _iso(as_of),
            "coverage": snapshot["coverage"],
            "region": item,
        }, status

    def compare(self, as_of: date, region_codes: Sequence[str]) -> tuple[dict[str, Any], str]:
        if not region_codes:
            raise RangeError("at least one region is required")
        if len(region_codes) > 6:
            raise RangeError("at most 6 regions can be compared")
        snapshot, status = self.snapshot(as_of, region_codes)
        found = {item["region_code"] for item in snapshot["regions"]}
        missing = [code for code in region_codes if code not in found]
        if missing:
            raise NotFoundError(f"regions not found: {', '.join(missing)}")
        return {
            "as_of": snapshot["as_of"],
            "coverage": snapshot["coverage"],
            "regions": snapshot["regions"],
        }, status

    # -- region seat turnover ----------------------------------------
    def region_timeline(self, region_code: str, from_date: date | None = None,
                        to_date: date | None = None) -> tuple[dict[str, Any], str]:
        start = from_date or self.coverage_start
        end = min(to_date or self.coverage_end, self.coverage_end)
        if start > end:
            raise RangeError("from must be earlier than to")
        key = self._key("region-timeline", region_code, start.isoformat(), end.isoformat())

        def build() -> dict[str, Any]:
            region = self.repo.get_region(region_code)
            if region is None:
                raise NotFoundError(f"region {region_code} not found")
            tenures = self.repo.tenures_for_region(region_code, start, end)
            catalog = {
                item["seat_key"]: item for item in self.repo.seat_catalog()
                if item["region_code"] == region_code
            }
            grouped: dict[str, list[Tenure]] = {}
            for tenure in tenures:
                if tenure.category not in CATEGORY_ORDER:
                    continue
                grouped.setdefault(tenure.seat_key, []).append(tenure)

            lanes = []
            for seat_key, items in grouped.items():
                items.sort(key=lambda t: t.start_date)
                category = items[0].category
                title = catalog.get(seat_key, {}).get("title") or items[0].title
                short = region.short_name or region.name
                if title.startswith(short):
                    title = title[len(short):]
                lanes.append({
                    "key": seat_key,
                    "category": category,
                    "title": title,
                    "label": f"{CATEGORY_META[category]['label']} · {title}",
                    "rank": catalog.get(seat_key, {}).get("rank", 9),
                    "spans": [
                        {
                            **self._member(tenure, end),
                            "officer_name": tenure.officer_name,
                            "officer_id": tenure.officer_id,
                        }
                        for tenure in items
                    ],
                })
            lanes.sort(key=lambda lane: (CATEGORY_ORDER.index(lane["category"]), lane["rank"],
                                         lane["spans"][0]["start_date"]))
            return {
                "region_code": region_code,
                "region_name": region.name,
                "from": _iso(start),
                "to": _iso(end),
                "lanes": lanes,
            }

        return self._cached(key, build)

    # -- directory / coverage ----------------------------------------
    @staticmethod
    def _event_dict(event: OfficerEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "event_type": event.event_type,
            "event_date": _iso(event.event_date),
            "title": event.title,
            "description": event.description,
            "source_url": event.source_url,
            "source_title": event.source_title,
            "verified": event.verified,
        }

    def _directory_rows(self, as_of: date) -> list[dict[str, Any]]:
        tenures = self.repo.all_tenures()
        events = self.repo.all_events()
        by_officer: dict[int, list[Tenure]] = {}
        for tenure in tenures:
            by_officer.setdefault(tenure.officer_id, []).append(tenure)
        for rows in by_officer.values():
            rows.sort(key=lambda t: t.start_date)
        events_by_officer: dict[int, list[OfficerEvent]] = {}
        for event in events:
            if event.event_date <= as_of:
                events_by_officer.setdefault(event.officer_id, []).append(event)
        for rows in events_by_officer.values():
            rows.sort(key=lambda e: e.event_date)

        rank_order = {
            "national_leader": 0, "vice_national_leader": 1, "ministerial": 2,
            "vice_ministerial": 3, "provincial_principal": 4,
            "provincial_deputy": 5, "bureau": 6, "unknown": 9,
        }
        items: list[dict[str, Any]] = []
        for officer in self.repo.list_officers(limit=10000):
            rows = by_officer.get(officer.id, [])
            past = [t for t in rows if t.start_date <= as_of]
            current = past[-1] if past else None
            previous = None
            next_position = None
            if current is not None:
                index = past.index(current)
                if index > 0:
                    previous = past[index - 1]
                future = [t for t in rows if t.start_date > (current.end_date or as_of)]
                if future:
                    next_position = future[0]

            status = "unknown"
            status_date = None
            status_title = None
            exit_events = [
                e for e in events_by_officer.get(officer.id, [])
                if e.event_type in ("retired", "under_investigation", "expelled_from_party",
                                    "expelled_from_public_office", "deceased")
            ]
            if exit_events:
                latest = exit_events[-1]
                if current is None or latest.event_date >= current.start_date:
                    status_date = _iso(latest.event_date)
                    status_title = latest.title
                    if latest.event_type in ("expelled_from_party", "expelled_from_public_office"):
                        status = "expelled"
                    elif latest.event_type == "under_investigation":
                        status = "under_investigation"
                    elif latest.event_type == "retired":
                        status = "retired"
                    else:
                        status = "deceased"
            if status == "unknown":
                if current is None:
                    status = "unknown"
                elif current.end_date is None:
                    status = "active"
                else:
                    status = "left"

            rank_date = min(as_of, current.end_date or as_of) if current else as_of
            current_rank = (self.rank_at(officer.name, rank_date, current.rank_level)
                            if current else "unknown")
            previous_rank = (self.rank_at(officer.name,
                                          min(as_of, previous.end_date or as_of),
                                          previous.rank_level)
                             if previous else None)
            next_rank = (self.rank_at(officer.name,
                                      min(as_of, next_position.end_date or as_of),
                                      next_position.rank_level)
                         if next_position else None)
            items.append({
                "officer_id": officer.id,
                "name": officer.name,
                "gender": officer.gender,
                "birth_year": officer.birth_year,
                "native_place": officer.native_place,
                "ethnicity": officer.ethnicity,
                "current_title": current.title if current else None,
                "region_code": current.region_code if current else None,
                "region_name": current.region_name if current else None,
                "category": current.category if current else None,
                "rank_level": current_rank,
                "rank_label": RANK_LABELS.get(current_rank, "级别待考"),
                "rank_order": rank_order.get(current_rank, 9),
                "start_date": _iso(current.start_date) if current else None,
                "end_date": _iso(current.end_date) if current else None,
                "start_precision": current.start_precision if current else None,
                "status": status,
                "status_label": STATUS_LABELS.get(status, "待补充"),
                "status_date": status_date,
                "status_title": status_title,
                "previous_title": previous.title if previous else None,
                "previous_rank_label": RANK_LABELS.get(previous_rank, None) if previous_rank else None,
                "next_title": next_position.title if next_position else None,
                "next_rank_label": RANK_LABELS.get(next_rank, None) if next_rank else None,
                "central_committee": central_service.committee(officer.name, as_of),
                "party_roles": central_service.party_roles_for(officer.name),
                "source_count": 0,
                "verified": any(t.verified for t in rows),
                "updated_at": self.coverage_end.isoformat(),
            })
        return items

    def directory(self, query: str = "", region: str | None = None,
                  category: str | None = None, status: str | None = None,
                  rank_level: str | None = None, as_of: date | None = None,
                  page: int = 1, page_size: int = 50) -> tuple[dict[str, Any], str]:
        as_of = as_of or self.coverage_end
        key = self._key("directory", as_of.isoformat(), query, region or "",
                        category or "", status or "", rank_level or "", page, page_size)
        cache_key = key

        def build() -> dict[str, Any]:
            items = self._directory_rows(as_of)
            if query:
                needle = query.strip().lower()
                items = [item for item in items
                         if needle in item["name"].lower()
                         or needle in (item["native_place"] or "").lower()]
            if region:
                items = [item for item in items if item["region_code"] == region]
            if category:
                items = [item for item in items if item["category"] == category]
            if status:
                items = [item for item in items if item["status"] == status]
            if rank_level:
                items = [item for item in items if item["rank_level"] == rank_level]
            items.sort(key=lambda item: (item["rank_order"], item["region_code"] or "",
                                         item["name"]))
            total = len(items)
            start = max(0, (page - 1) * page_size)
            paged = items[start:start + page_size]
            return {
                "items": paged,
                "total": total,
                "page": page,
                "page_size": page_size,
                "as_of": _iso(as_of),
                "dataset_version": self.repo.dataset_id,
                "coverage": self.coverage(as_of)[0],
                "updated_at": self.coverage_end.isoformat(),
            }

        return self._cached(cache_key, build, ttl=30)

    def coverage(self, as_of: date | None = None) -> tuple[dict[str, Any], str]:
        as_of = as_of or self.coverage_end
        key = self._key("coverage", as_of.isoformat())

        def build() -> dict[str, Any]:
            provinces = self.repo.list_regions(level="province")
            tenures = self.repo.tenures_at(as_of)
            by_region: dict[str, list[Tenure]] = {}
            for tenure in tenures:
                if tenure.region_code:
                    by_region.setdefault(tenure.region_code, []).append(tenure)
            categories = ("party", "congress", "government", "cppcc")
            vacancy_categories: dict[str, set[str]] = {}
            for vacancy in KNOWN_VACANCIES:
                vacancy_categories.setdefault(vacancy["region_code"], set()).add(vacancy["category"])
            rows = []
            complete = 0
            accounted = 0
            category_counts = {category: 0 for category in categories}
            for province in provinces:
                members = by_region.get(province.code, [])
                present = {category: any(t.category == category for t in members)
                           for category in categories}
                filled = sum(1 for value in present.values() if value)
                for category, value in present.items():
                    if value:
                        category_counts[category] += 1
                if filled == 4:
                    complete += 1
                missing = {category for category, value in present.items() if not value}
                if not missing or missing <= vacancy_categories.get(province.code, set()):
                    accounted += 1
                rows.append({
                    "region_code": province.code,
                    "region_name": province.name,
                    "short_name": province.short_name,
                    "filled": filled,
                    "principal_complete": filled == 4,
                    "categories": present,
                    "member_count": len(members),
                    "roster_snapshots": sum(1 for t in members if t.start_precision == "snapshot"),
                })
            all_tenures = self.repo.all_tenures()
            all_events = self.repo.all_events()
            verified = sum(1 for t in all_tenures if t.verified)
            total_principal_slots = len(provinces) * 4
            checkpoints = []
            for checkpoint in (self.coverage_start, date(2017, 10, 25),
                               date(2022, 10, 16), self.coverage_end):
                at = self.repo.tenures_at(checkpoint)
                present_regions: dict[str, set[str]] = {}
                for tenure in at:
                    if tenure.region_code:
                        present_regions.setdefault(tenure.region_code, set()).add(tenure.category)
                filled_regions = sum(
                    1 for present in present_regions.values()
                    if {"party", "congress", "government", "cppcc"} <= present
                )
                checkpoints.append({
                    "date": _iso(checkpoint),
                    "provinces_complete": filled_regions,
                    "principal_coverage": round(filled_regions / max(1, len(provinces)), 4),
                })
            return {
                "as_of": _iso(as_of),
                "dataset_version": self.repo.dataset_id,
                "plenum_date": _iso(self.coverage_end),
                "provinces_total": len(provinces),
                "provinces_complete": complete,
                "provinces_accounted": accounted,
                "principal_coverage": round(complete / max(1, len(provinces)), 4),
                "checkpoints": checkpoints,
                "vacancies": [
                    {
                        **vacancy,
                        "region_name": next((p.name for p in provinces
                                             if p.code == vacancy["region_code"]), ""),
                    }
                    for vacancy in KNOWN_VACANCIES
                ],
                "category_coverage": {
                    category: {
                        "provinces": category_counts[category],
                        "total": len(provinces),
                        "ratio": round(category_counts[category] / max(1, len(provinces)), 4),
                    }
                    for category in categories
                },
                "principal_slots": total_principal_slots,
                "principal_slots_filled": sum(row["filled"] for row in rows),
                "tenures": len(all_tenures),
                "officers": len(self.repo.list_officers(limit=10000)),
                "events": len(all_events),
                "verified_tenures": verified,
                "verified_ratio": round(verified / max(1, len(all_tenures)), 4),
                "roster_snapshots": sum(1 for t in all_tenures if t.start_precision == "snapshot"),
                "regions": rows,
            }

        return self._cached(key, build, ttl=60)

    # -- seat history -------------------------------------------------
    def seat_history(self, region_code: str, seat_key: str,
                     as_of: date | None = None) -> tuple[dict[str, Any], str]:
        as_of = as_of or self.effective_as_of(self.today)
        key = self._key("seat", region_code, seat_key, as_of.isoformat())

        def build() -> dict[str, Any]:
            region = self.repo.get_region(region_code)
            if region is None:
                raise NotFoundError(f"region {region_code} not found")
            catalog = [
                item for item in self.repo.seat_catalog()
                if item["region_code"] == region_code and item["seat_key"] == seat_key
            ]
            tenures = sorted(self.repo.seat_history(region_code, seat_key),
                             key=lambda t: t.start_date)
            if not catalog and not tenures:
                raise NotFoundError(f"seat {seat_key} not found in {region_code}")
            spans = []
            effective = self.effective_as_of(as_of)
            latest_events: dict[int, OfficerEvent] = {}
            for event in self.repo.all_events():
                if event.event_type not in EVENT_TYPES:
                    continue
                previous = latest_events.get(event.officer_id)
                if previous is None or event.event_date > previous.event_date:
                    latest_events[event.officer_id] = event
            for index, tenure in enumerate(tenures):
                # 席位史展示“每一段完整任期”，不能按当前时间轴截断；
                # 只有仍在任的开放任期才计算到 as_of。
                if tenure.end_date:
                    duration = (tenure.end_date - tenure.start_date).days + 1
                elif tenure.start_date <= effective:
                    duration = (effective - tenure.start_date).days + 1
                else:
                    duration = 0
                in_office = (tenure.start_date <= effective
                             and (tenure.end_date is None or tenure.end_date >= effective))
                is_future = tenure.start_date > effective
                gap_before = None
                if index > 0:
                    previous = tenures[index - 1]
                    if previous.end_date:
                        gap_before = max(0, (tenure.start_date - previous.end_date).days - 1)
                event = latest_events.get(tenure.officer_id)
                spans.append({
                    **self._member(tenure, as_of),
                    "officer_name": tenure.officer_name,
                    "officer_id": tenure.officer_id,
                    "gap_before_days": gap_before,
                    "is_current": in_office,
                    "is_future": is_future,
                    "duration_days": duration,
                    "event_type": event.event_type if event else None,
                    "event_label": EVENT_LABELS.get(event.event_type, event.title) if event else None,
                    "event_date": _iso(event.event_date) if event else None,
                })
            substantive = [t for t in tenures
                           if not t.is_acting and not t.is_concurrent and t.start_date <= effective]
            incumbent = next((t for t in tenures if t.start_date <= effective and
                              (t.end_date is None or t.end_date >= effective)), None)
            return {
                "region_code": region_code,
                "region_name": region.name,
                "seat_key": seat_key,
                "title": (catalog[0]["title"] if catalog else tenures[-1].title if tenures else seat_key),
                "category": (catalog[0]["category"] if catalog else tenures[0].category
                             if tenures else "other"),
                "as_of": _iso(as_of),
                "spans": spans,
                "holder_count": len({t.officer_id for t in substantive}),
                "acting_count": sum(1 for t in tenures if t.is_acting and t.start_date <= effective),
                "incumbent": self._member(incumbent, as_of) if incumbent else None,
            }

        return self._cached(key, build)

    # -- officers -----------------------------------------------------
    def _without_lower_politburo(self, tenures: list[Tenure]) -> list[Tenure]:
        psc = [
            t for t in tenures
            if "central:party:politburo_standing:seat:" in t.seat_key
        ]
        if not psc:
            return tenures

        def overlaps(tenure: Tenure) -> bool:
            if "central:party:politburo:seat:" not in tenure.seat_key:
                return False
            return any(
                tenure.start_date <= (other.end_date or self.coverage_end)
                and (tenure.end_date is None or tenure.end_date >= other.start_date)
                for other in psc
            )

        return [tenure for tenure in tenures if not overlaps(tenure)]

    def officer_profile(self, officer_id: int, as_of: date) -> dict[str, Any]:
        officer = self.repo.get_officer(officer_id)
        if officer is None:
            raise NotFoundError(f"officer {officer_id} not found")
        tenures = self.repo.tenures_for_officer(officer_id)
        events = self.repo.list_officer_events(officer_id)
        current = [
            t for t in tenures
            if t.start_date <= as_of and (t.end_date is None or t.end_date >= as_of)
        ]
        past = self._without_lower_politburo([t for t in tenures if t.start_date <= as_of])
        previous = past[-2] if len(past) > 1 else None
        future = [t for t in tenures if current and t.start_date > (current[-1].end_date or as_of)]
        current = self._without_lower_politburo(current)
        future = self._without_lower_politburo(future)
        regions = {t.region_code for t in tenures if t.region_code}
        latest_event = events[-1] if events else None
        status = "active" if any(t.end_date is None for t in current) else (
            "left" if current else "unknown")
        if latest_event and latest_event.event_type in (
            "retired", "under_investigation", "expelled_from_party",
            "expelled_from_public_office", "deceased",
        ):
            status = {
                "retired": "retired",
                "under_investigation": "under_investigation",
                "expelled_from_party": "expelled",
                "expelled_from_public_office": "expelled",
                "deceased": "deceased",
            }[latest_event.event_type]
        return {
            "officer": self._officer(officer),
            "current": [self._member(t, as_of) for t in sorted(current, key=lambda t: t.seat_rank)],
            "previous": self._member(previous, as_of) if previous else None,
            "next": self._member(future[0], as_of) if future else None,
            "events": [self._event_dict(event) for event in events],
            "status": status,
            "status_label": STATUS_LABELS.get(status, "待补充"),
            "stats": {
                "position_count": len(tenures),
                "province_count": len(regions),
                "acting_count": sum(1 for t in tenures if t.is_acting),
                "first_start": _iso(min((t.start_date for t in tenures), default=None)),
                "latest_end": _iso(max((t.end_date or self.effective_as_of(as_of) for t in tenures),
                                       default=None)),
            },
            "as_of": _iso(as_of),
            "coverage": self.coverage_badge(as_of),
        }

    @staticmethod
    def _officer(officer: Officer) -> dict[str, Any]:
        return {
            "id": officer.id,
            "slug": officer.slug,
            "name": officer.name,
            "gender": officer.gender,
            "birth_year": officer.birth_year,
            "native_place": officer.native_place,
            "ethnicity": officer.ethnicity,
            "party_join_date": _iso(officer.party_join_date),
            "work_start_date": _iso(officer.work_start_date),
            "education": officer.education,
            "degree": officer.degree,
            "school": officer.school,
            "bio": officer.bio,
            "portrait_url": officer.portrait_url,
            "is_deceased": officer.is_deceased,
        }

    def career(self, officer_id: int, from_date: date | None = None,
               to_date: date | None = None) -> tuple[dict[str, Any], str]:
        start = from_date or self.coverage_start
        end = min(to_date or self.coverage_end, self.coverage_end)
        if start > end:
            raise RangeError("from must be earlier than to")
        key = self._key("career", officer_id, start.isoformat(), end.isoformat())

        def build() -> dict[str, Any]:
            officer = self.repo.get_officer(officer_id)
            if officer is None:
                raise NotFoundError(f"officer {officer_id} not found")
            tenures = [
                t for t in self.repo.tenures_for_officer(officer_id)
                if t.start_date <= end and (t.end_date is None or t.end_date >= start)
            ]
            psc = [
                t for t in tenures
                if "central:party:politburo_standing:seat:" in t.seat_key
            ]

            def overlaps_psc(tenure: Tenure) -> bool:
                if "central:party:politburo:seat:" not in tenure.seat_key:
                    return False
                return any(
                    tenure.start_date <= (other.end_date or end)
                    and (tenure.end_date is None or tenure.end_date >= other.start_date)
                    for other in psc
                )

            tenures = [t for t in tenures if not overlaps_psc(t)]

            merged: list[Tenure] = []
            for tenure in sorted(tenures, key=lambda item: (item.seat_key, item.start_date)):
                previous = merged[-1] if merged else None
                if (
                    previous
                    and previous.seat_key == tenure.seat_key
                    and previous.region_code == tenure.region_code
                ):
                    previous_end = previous.end_date
                    if previous_end is None:
                        continue
                    if (tenure.start_date - previous_end).days <= 1:
                        merged[-1] = replace(
                            previous,
                            end_date=tenure.end_date,
                        )
                        continue
                merged.append(tenure)
            tenures = merged
            lanes: dict[str, dict[str, Any]] = {}
            for tenure in sorted(tenures, key=lambda t: t.start_date):
                lane_key = tenure.region_code or "central"
                lane = lanes.setdefault(lane_key, {
                    "key": lane_key,
                    "label": tenure.region_short_name or "中央机构",
                    "full_label": tenure.region_name or "中央 / 中央机构",
                    "order": 99 if lane_key == "central" else 0,
                    "spans": [],
                })
                if lane_key != "central":
                    lane["order"] = min(lane["order"] or 99, tenure.seat_rank)
                lane["spans"].append({
                    **self._member(tenure, end),
                    "lane_key": lane_key,
                    "officer_name": tenure.officer_name,
                    "officer_id": tenure.officer_id,
                    "org_name": tenure.org_name,
                    "clipped_start": _iso(max(tenure.start_date, start)),
                })
            ordered = sorted(
                lanes.values(),
                key=lambda lane: min(span["start_date"] for span in lane["spans"]),
            )
            summary_days = sum(span["duration_days"] for lane in ordered for span in lane["spans"])
            all_rows = self.repo.tenures_for_officer(officer_id)
            previous_rows = [t for t in all_rows if t.start_date < start]
            next_rows = [t for t in all_rows if t.start_date > end]
            events = self.repo.list_officer_events(officer_id)
            status = "active" if any(t.end_date is None for t in all_rows) else "left"
            if events and events[-1].event_type in (
                "retired", "under_investigation", "expelled_from_party",
                "expelled_from_public_office", "deceased",
            ):
                status = {
                    "retired": "retired",
                    "under_investigation": "under_investigation",
                    "expelled_from_party": "expelled",
                    "expelled_from_public_office": "expelled",
                    "deceased": "deceased",
                }[events[-1].event_type]
            return {
                "officer": self._officer(officer),
                "range": {
                    "from": _iso(start),
                    "to": _iso(end),
                    "coverage_end": _iso(self.coverage_end),
                    "requested_to": _iso(to_date) if to_date else None,
                },
                "lanes": ordered,
                "events": [self._event_dict(event) for event in events],
                "context": {
                    "previous": self._member(previous_rows[-1], start) if previous_rows else None,
                    "next": self._member(next_rows[0], end) if next_rows else None,
                    "status": status,
                    "status_label": STATUS_LABELS.get(status, "待补充"),
                },
                "summary": {
                    "span_count": sum(len(lane["spans"]) for lane in ordered),
                    "province_count": len([lane for lane in ordered if lane["key"] != "central"]),
                    "acting_count": sum(1 for lane in ordered for span in lane["spans"] if span["is_acting"]),
                    "total_days": summary_days,
                },
                "coverage": self.coverage_badge(end),
            }

        return self._cached(key, build)

    def search_officers(self, query: str, limit: int) -> list[dict[str, Any]]:
        return [self._officer(o) for o in self.repo.list_officers(query, limit)]

    # -- events -------------------------------------------------------
    def events(self) -> list[dict[str, Any]]:
        return TIMELINE_EVENTS
