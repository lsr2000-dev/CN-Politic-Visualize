from __future__ import annotations

import logging
from datetime import date
from typing import Any, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, RowMapping

from ..domain import Officer, OfficerEvent, Region, Tenure, parse_date

log = logging.getLogger(__name__)

_TENURE_COLUMNS = """
    v.tenure_id, v.officer_id, v.officer_name, v.officer_slug, v.gender, v.birth_year,
    v.position_id, v.seat_key, v.seat_rank, v.is_leader, v.region_code, v.region_name,
    v.region_short_name, v.category, v.title, v.org_name, v.start_date, v.end_date,
    v.start_precision, v.end_precision, v.is_acting, v.is_concurrent, v.is_plural,
    v.rank_level_snapshot, v.end_reason, v.end_reason_detail, v.verified, v.notes
"""


def _to_tenure(row: RowMapping) -> Tenure:
    return Tenure(
        id=row["tenure_id"],
        officer_id=row["officer_id"],
        position_id=row["position_id"],
        region_code=row["region_code"],
        region_name=row["region_name"],
        region_short_name=row["region_short_name"],
        category=row["category"],
        title=row["title"],
        seat_key=row["seat_key"],
        seat_rank=row["seat_rank"],
        is_leader=row["is_leader"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        start_precision=row["start_precision"],
        end_precision=row["end_precision"],
        is_acting=row["is_acting"],
        is_concurrent=row["is_concurrent"],
        is_plural=row["is_plural"],
        rank_level=row["rank_level_snapshot"],
        end_reason=row["end_reason"],
        end_reason_detail=row["end_reason_detail"],
        verified=row["verified"],
        officer_name=row["officer_name"],
        officer_slug=row["officer_slug"],
        gender=row["gender"],
        birth_year=row["birth_year"],
        org_name=row["org_name"],
        notes=row["notes"],
    )


class SqlRepository:
    """PostgreSQL / PostGIS read model.

    All temporal predicates run against the generated `period daterange`
    column, which is backed by a GiST index (see 01_schema.sql).
    """

    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(
            database_url, pool_pre_ping=True, pool_size=8, max_overflow=4, future=True
        )
        self.meta = self._load_meta()
        self.dataset_id = self.meta["id"]
        log.info("postgres repository ready: dataset=%s", self.dataset_id)

    def _load_meta(self) -> dict[str, Any]:
        with self.engine.connect() as conn:
            row = conn.execute(text(
                "SELECT id, coverage_start, coverage_end, status, notes, published_at "
                "FROM polvis.dataset_versions WHERE status = 'published' "
                "ORDER BY published_at DESC NULLS LAST LIMIT 1"
            )).mappings().first()
            counts = conn.execute(text(
                "SELECT (SELECT count(*) FROM polvis.regions) AS regions,"
                "       (SELECT count(*) FROM polvis.officers) AS officers,"
                "       (SELECT count(*) FROM polvis.positions) AS positions,"
                "       (SELECT count(*) FROM polvis.tenures) AS tenures"
            )).mappings().one()
        if row is None:
            raise RuntimeError("no published dataset_version found; run the seed import first")
        return {
            "id": row["id"],
            "coverage_start": str(row["coverage_start"]),
            "coverage_end": str(row["coverage_end"]),
            "status": row["status"],
            "disclaimer": row["notes"],
            "curated_at": str(row["coverage_end"]),
            "counts": dict(counts),
        }

    # -- regions ------------------------------------------------------
    def list_regions(self, level: str | None = None,
                     parent_code: str | None = None) -> list[Region]:
        sql = (
            "SELECT code, name, short_name, level, parent_code, "
            "       CASE WHEN centroid IS NULL THEN NULL ELSE ST_X(centroid) END AS lon, "
            "       CASE WHEN centroid IS NULL THEN NULL ELSE ST_Y(centroid) END AS lat, "
            "       sort_order "
            "FROM polvis.regions WHERE 1 = 1"
        )
        params: dict[str, Any] = {}
        if level:
            sql += " AND level = :level"
            params["level"] = level
        if parent_code:
            sql += " AND parent_code = :parent"
            params["parent"] = parent_code
        sql += " ORDER BY sort_order, code"
        with self.engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [
            Region(
                code=r["code"], name=r["name"], short_name=r["short_name"] or r["name"],
                level=r["level"], parent_code=r["parent_code"],
                centroid=(r["lon"], r["lat"]) if r["lon"] is not None else None,
                sort_order=r["sort_order"],
            )
            for r in rows
        ]

    def get_region(self, code: str) -> Region | None:
        items = [r for r in self.list_regions() if r.code == code]
        return items[0] if items else None

    # -- officers -----------------------------------------------------
    def list_officers(self, query: str | None = None, limit: int = 20) -> list[Officer]:
        sql = (
            "SELECT id, slug, name, gender, birth_year, native_place, ethnicity, "
            "       party_join_date, work_start_date, education, degree, school, bio, "
            "       portrait_url, is_deceased "
            "FROM polvis.officers"
        )
        params: dict[str, Any] = {"limit": limit}
        if query:
            sql += " WHERE name ILIKE :q OR native_place ILIKE :q"
            params["q"] = f"%{query.strip()}%"
        sql += " ORDER BY name LIMIT :limit"
        with self.engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [self._to_officer(r) for r in rows]

    def get_officer(self, officer_id: int) -> Officer | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT id, slug, name, gender, birth_year, native_place, ethnicity, "
                    "       party_join_date, work_start_date, education, degree, school, bio, "
                    "       portrait_url, is_deceased "
                    "FROM polvis.officers WHERE id = :id"
                ),
                {"id": officer_id},
            ).mappings().first()
        return self._to_officer(row) if row else None

    @staticmethod
    def _to_officer(row: RowMapping) -> Officer:
        return Officer(
            id=row["id"], slug=row["slug"], name=row["name"], gender=row["gender"],
            birth_year=row["birth_year"], native_place=row["native_place"],
            ethnicity=row["ethnicity"],
            party_join_date=parse_date(row["party_join_date"]),
            work_start_date=parse_date(row["work_start_date"]),
            education=row["education"], degree=row["degree"], school=row["school"],
            bio=row["bio"], portrait_url=row["portrait_url"],
            is_deceased=row["is_deceased"],
        )

    # -- tenures ------------------------------------------------------
    def tenures_at(self, day: date, region_codes: Sequence[str] | None = None,
                   categories: Sequence[str] | None = None) -> list[Tenure]:
        sql = f"SELECT {_TENURE_COLUMNS} FROM polvis.v_tenure_expanded v WHERE v.period @> :day"
        params: dict[str, Any] = {"day": day}
        if region_codes:
            sql += " AND v.region_code = ANY(:codes)"
            params["codes"] = list(region_codes)
        if categories:
            sql += " AND v.category::text = ANY(:cats)"
            params["cats"] = list(categories)
        sql += " ORDER BY v.region_code, v.category, v.seat_rank, v.start_date"
        with self.engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [_to_tenure(r) for r in rows]

    def tenures_for_region(self, region_code: str, start: date, end: date) -> list[Tenure]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT {_TENURE_COLUMNS} FROM polvis.v_tenure_expanded v "
                    "WHERE v.region_code = :code "
                    "AND v.period && daterange(:start, :end + 1, '[)') "
                    "ORDER BY v.start_date"
                ),
                {"code": region_code, "start": start, "end": end},
            ).mappings().all()
        return [_to_tenure(r) for r in rows]

    def tenures_in_range(self, start: date, end: date,
                         region_codes: Sequence[str] | None = None) -> list[Tenure]:
        sql = (
            f"SELECT {_TENURE_COLUMNS} FROM polvis.v_tenure_expanded v "
            "WHERE v.period && daterange(:start, :end + 1, '[)')"
        )
        params: dict[str, Any] = {"start": start, "end": end}
        if region_codes:
            sql += " AND v.region_code = ANY(:codes)"
            params["codes"] = list(region_codes)
        sql += " ORDER BY v.region_code, v.start_date"
        with self.engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [_to_tenure(r) for r in rows]

    def tenures_for_officer(self, officer_id: int) -> list[Tenure]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT {_TENURE_COLUMNS} FROM polvis.v_tenure_expanded v "
                    "WHERE v.officer_id = :id ORDER BY v.start_date"
                ),
                {"id": officer_id},
            ).mappings().all()
        return [_to_tenure(r) for r in rows]

    def all_tenures(self) -> list[Tenure]:
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                f"SELECT {_TENURE_COLUMNS} FROM polvis.v_tenure_expanded v "
                "ORDER BY v.officer_id, v.start_date"
            )).mappings().all()
        return [_to_tenure(r) for r in rows]

    def list_officer_events(self, officer_id: int) -> list[OfficerEvent]:
        return [event for event in self.all_events() if event.officer_id == officer_id]

    def all_events(self) -> list[OfficerEvent]:
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, officer_id, event_type, event_date, title, description,"
                "       source_url, source_title, verified "
                "FROM polvis.officer_events ORDER BY officer_id, event_date"
            )).mappings().all()
        return [
            OfficerEvent(
                id=row["id"], officer_id=row["officer_id"],
                event_type=row["event_type"], event_date=row["event_date"],
                title=row["title"], description=row["description"],
                source_url=row["source_url"], source_title=row["source_title"],
                verified=row["verified"],
            )
            for row in rows
        ]

    def seat_history(self, region_code: str, seat_key: str) -> list[Tenure]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT {_TENURE_COLUMNS} FROM polvis.v_tenure_expanded v "
                    "WHERE v.region_code = :code AND v.seat_key = :seat "
                    "ORDER BY v.start_date"
                ),
                {"code": region_code, "seat": seat_key},
            ).mappings().all()
        return [_to_tenure(r) for r in rows]

    def seat_catalog(self) -> list[dict[str, Any]]:
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, region_code, seat_key, category, title, rank "
                "FROM polvis.positions ORDER BY region_code, category, rank"
            )).mappings().all()
        return [dict(r) for r in rows]

    def health(self) -> dict[str, Any]:
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "backend": "postgres",
            "dataset_id": self.dataset_id,
            "counts": self.meta.get("counts", {}),
        }
