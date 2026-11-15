from __future__ import annotations

from datetime import date
from typing import Any, Protocol, Sequence

from ..domain import Officer, OfficerEvent, Region, Tenure


class Repository(Protocol):
    """Storage-agnostic read model used by the API layer.

    Two implementations ship with the project:
      * JsonRepository  — bundled demo snapshot, zero infrastructure
      * SqlRepository   — PostgreSQL + PostGIS, production path
    Both must return identical shapes so the API contract is stable.
    """

    dataset_id: str
    meta: dict[str, Any]

    def list_regions(self, level: str | None = None,
                     parent_code: str | None = None) -> list[Region]: ...

    def get_region(self, code: str) -> Region | None: ...

    def list_officers(self, query: str | None = None, limit: int = 20) -> list[Officer]: ...

    def get_officer(self, officer_id: int) -> Officer | None: ...

    def tenures_at(self, day: date,
                   region_codes: Sequence[str] | None = None,
                   categories: Sequence[str] | None = None) -> list[Tenure]: ...

    def tenures_for_region(self, region_code: str,
                           start: date, end: date) -> list[Tenure]: ...

    def tenures_in_range(self, start: date, end: date,
                         region_codes: Sequence[str] | None = None) -> list[Tenure]: ...

    def tenures_for_officer(self, officer_id: int) -> list[Tenure]: ...

    def all_tenures(self) -> list[Tenure]: ...

    def list_officer_events(self, officer_id: int) -> list[OfficerEvent]: ...

    def all_events(self) -> list[OfficerEvent]: ...

    def seat_history(self, region_code: str, seat_key: str) -> list[Tenure]: ...

    def seat_catalog(self) -> list[dict[str, Any]]: ...

    def health(self) -> dict[str, Any]: ...
