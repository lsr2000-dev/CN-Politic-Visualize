from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from ..domain import Officer, OfficerEvent, Region, Tenure, parse_date

log = logging.getLogger(__name__)


class JsonRepository:
    """Loads the curated demo dataset once and serves it from memory.

    This is the zero-infrastructure path (`POLVIS_DATA_MODE=json`), used by
    the frontend demo and the test-suite. Query semantics mirror the SQL
    functions in infra/initdb/01_schema.sql.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self.dataset_version = self._path.stat().st_mtime_ns
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        self.meta = raw["meta"]
        self.dataset_id = raw["meta"]["id"]
        self._regions = {
            item["code"]: Region(
                code=item["code"],
                name=item["name"],
                short_name=item["short_name"] or item["name"],
                level=item["level"],
                parent_code=item.get("parent_code"),
                centroid=tuple(item["centroid"]) if item.get("centroid") else None,
                sort_order=item.get("sort_order", 0),
            )
            for item in raw["regions"]
        }
        self._officers = {
            item["id"]: Officer(
                id=item["id"],
                slug=item["slug"],
                name=item["name"],
                gender=item.get("gender"),
                birth_year=item.get("birth_year"),
                native_place=item.get("native_place"),
                ethnicity=item.get("ethnicity"),
                party_join_date=parse_date(item.get("party_join_date")),
                work_start_date=parse_date(item.get("work_start_date")),
                education=item.get("education"),
                degree=item.get("degree"),
                school=item.get("school"),
                bio=item.get("bio"),
                portrait_url=item.get("portrait_url"),
                is_deceased=item.get("is_deceased", False),
            )
            for item in raw["officers"]
        }
        self._positions = {item["id"]: item for item in raw["positions"]}
        self._tenures: list[Tenure] = []
        for item in raw["tenures"]:
            position = self._positions[item["position_id"]]
            officer = self._officers[item["officer_id"]]
            region = self._regions.get(item.get("region_code") or "")
            self._tenures.append(
                Tenure(
                    id=item["id"],
                    officer_id=item["officer_id"],
                    position_id=item["position_id"],
                    region_code=item.get("region_code"),
                    region_name=region.name if region else None,
                    region_short_name=region.short_name if region else None,
                    category=item["category"],
                    title=item["title"],
                    seat_key=position["seat_key"],
                    position_uid=position.get("position_uid", ""),
                    seat_rank=position["rank"],
                    is_leader=position["is_leader"],
                    start_date=parse_date(item["start_date"]),  # type: ignore[arg-type]
                    end_date=parse_date(item.get("end_date")),
                    start_precision=item.get("start_precision", "month"),
                    end_precision=item.get("end_precision"),
                    is_acting=item.get("is_acting", False),
                    is_concurrent=item.get("is_concurrent", False),
                    is_plural=item.get("is_plural", False),
                    rank_level=item.get("rank_level", "provincial_deputy"),
                    end_reason=item.get("end_reason"),
                    end_reason_detail=item.get("end_reason_detail"),
                    verified=item.get("verified", False),
                    officer_name=officer.name,
                    officer_slug=officer.slug,
                    gender=officer.gender,
                    birth_year=officer.birth_year,
                    org_name=position.get("org_name"),
                    notes=item.get("notes"),
                )
            )
        self._by_officer: dict[int, list[Tenure]] = {}
        self._by_region: dict[str, list[Tenure]] = {}
        for tenure in self._tenures:
            self._by_officer.setdefault(tenure.officer_id, []).append(tenure)
            if tenure.region_code:
                self._by_region.setdefault(tenure.region_code, []).append(tenure)
        for rows in (*self._by_officer.values(), *self._by_region.values()):
            rows.sort(key=lambda t: t.start_date)
        self._events: list[OfficerEvent] = []
        for item in raw.get("events", []):
            self._events.append(OfficerEvent(
                id=item["id"],
                officer_id=item["officer_id"],
                event_type=item["event_type"],
                event_date=parse_date(item["event_date"]),  # type: ignore[arg-type]
                title=item["title"],
                description=item.get("description"),
                source_url=item.get("source_url"),
                source_title=item.get("source_title"),
                verified=item.get("verified", False),
            ))
        self._events_by_officer: dict[int, list[OfficerEvent]] = {}
        for event in self._events:
            self._events_by_officer.setdefault(event.officer_id, []).append(event)
        for rows in self._events_by_officer.values():
            rows.sort(key=lambda e: e.event_date)
        log.info(
            "json repository loaded: %s regions, %s officers, %s tenures, %s events",
            len(self._regions), len(self._officers), len(self._tenures), len(self._events),
        )

    def reload_if_changed(self) -> bool:
        """Atomically reload the in-memory snapshot when the JSON file changes."""
        version = self._path.stat().st_mtime_ns
        if version == self.dataset_version:
            return False
        fresh = JsonRepository(self._path)
        self.__dict__.update(fresh.__dict__)
        log.info("json repository hot-reloaded: version %s", version)
        return True

    # -- regions ------------------------------------------------------
    def list_regions(self, level: str | None = None,
                     parent_code: str | None = None) -> list[Region]:
        items = sorted(self._regions.values(), key=lambda r: (r.sort_order, r.code))
        if level:
            items = [r for r in items if r.level == level]
        if parent_code:
            items = [r for r in items if r.parent_code == parent_code]
        return items

    def get_region(self, code: str) -> Region | None:
        return self._regions.get(code)

    # -- officers -----------------------------------------------------
    def list_officers(self, query: str | None = None, limit: int = 20) -> list[Officer]:
        items = sorted(self._officers.values(), key=lambda o: o.name)
        if query:
            needle = query.strip()
            items = [o for o in items if needle in o.name or needle in (o.native_place or "")]
        return items[:limit]

    def get_officer(self, officer_id: int) -> Officer | None:
        return self._officers.get(officer_id)

    # -- tenures ------------------------------------------------------
    def tenures_at(self, day: date, region_codes: Sequence[str] | None = None,
                   categories: Sequence[str] | None = None) -> list[Tenure]:
        allowed = set(region_codes) if region_codes else None
        cats = set(categories) if categories else None
        result = []
        for tenure in self._tenures:
            if allowed is not None and tenure.region_code not in allowed:
                continue
            if cats is not None and tenure.category not in cats:
                continue
            if tenure.start_date <= day and (tenure.end_date is None or tenure.end_date >= day):
                result.append(tenure)
        return result

    def tenures_for_region(self, region_code: str, start: date, end: date) -> list[Tenure]:
        return [
            t for t in self._by_region.get(region_code, [])
            if t.start_date <= end and (t.end_date is None or t.end_date >= start)
        ]

    def tenures_in_range(self, start: date, end: date,
                         region_codes: Sequence[str] | None = None) -> list[Tenure]:
        allowed = set(region_codes) if region_codes else None
        return [
            t for t in self._tenures
            if (allowed is None or t.region_code in allowed)
            and t.start_date <= end
            and (t.end_date is None or t.end_date >= start)
        ]

    def tenures_for_officer(self, officer_id: int) -> list[Tenure]:
        return list(self._by_officer.get(officer_id, []))

    def all_tenures(self) -> list[Tenure]:
        return list(self._tenures)

    def list_officer_events(self, officer_id: int) -> list[OfficerEvent]:
        return list(self._events_by_officer.get(officer_id, []))

    def all_events(self) -> list[OfficerEvent]:
        return list(self._events)

    def seat_history(self, region_code: str, seat_key: str) -> list[Tenure]:
        return [
            t for t in self._by_region.get(region_code, [])
            if t.seat_key == seat_key
        ]

    def seat_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "id": p["id"],
                "region_code": p["region_code"],
                "seat_key": p["seat_key"],
                "category": p["category"],
                "title": p["title"],
                "rank": p["rank"],
            }
            for p in self._positions.values()
        ]

    def health(self) -> dict[str, Any]:
        return {
            "backend": "json",
            "dataset_id": self.dataset_id,
            "regions": len(self._regions),
            "officers": len(self._officers),
            "tenures": len(self._tenures),
            "events": len(self._events),
        }
