from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from .core.vocabulary import PERSON_STATUS, RANKS

CATEGORY_META: dict[str, dict[str, Any]] = {
    "party": {"label": "党委", "order": 1, "accent": "#c0392b"},
    "congress": {"label": "人大", "order": 2, "accent": "#2c5f8a"},
    "government": {"label": "政府", "order": 3, "accent": "#b7791f"},
    "cppcc": {"label": "政协", "order": 4, "accent": "#4a6b52"},
    "other": {"label": "其他", "order": 9, "accent": "#6b7280"},
}
CATEGORY_ORDER = ["party", "congress", "government", "cppcc"]

RANK_LABELS: dict[str, str] = dict(RANKS)

STATUS_LABELS: dict[str, str] = dict(PERSON_STATUS)

END_REASON_LABELS: dict[str, str] = {
    "promotion": "提拔",
    "transfer": "调任",
    "retirement": "退休",
    "term_end": "任期结束",
    "removed": "免职",
    "investigation": "接受审查",
    "expulsion": "开除党籍/公职",
    "death": "病逝",
    "acting_end": "代理结束",
    "restructure": "机构调整",
    "unknown": "原因待考",
}


@dataclass(slots=True)
class Region:
    code: str
    name: str
    short_name: str
    level: str
    parent_code: str | None
    centroid: tuple[float, float] | None
    sort_order: int


@dataclass(slots=True)
class Officer:
    id: int
    slug: str
    name: str
    gender: str | None = None
    birth_year: int | None = None
    native_place: str | None = None
    ethnicity: str | None = None
    party_join_date: date | None = None
    work_start_date: date | None = None
    education: str | None = None
    degree: str | None = None
    school: str | None = None
    bio: str | None = None
    portrait_url: str | None = None
    is_deceased: bool = False


@dataclass(slots=True)
class Tenure:
    id: int
    officer_id: int
    position_id: int
    region_code: str | None
    region_name: str | None
    region_short_name: str | None
    category: str
    title: str
    seat_key: str
    seat_rank: int
    is_leader: bool
    start_date: date
    end_date: date | None
    position_uid: str = ""
    start_precision: str = "month"
    end_precision: str | None = None
    is_acting: bool = False
    is_concurrent: bool = False
    is_plural: bool = False
    verified: bool = False
    rank_level: str = "provincial_deputy"
    end_reason: str | None = None
    end_reason_detail: str | None = None
    officer_name: str = ""
    officer_slug: str = ""
    gender: str | None = None
    birth_year: int | None = None
    org_name: str | None = None
    notes: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def is_incumbent(self) -> bool:
        return self.end_date is None

    def duration_days(self, as_of: date) -> int:
        """Days served as of a given date.

        For a snapshot this must stop at `as_of` even if the tenure is
        already closed with a later end date; for career/seat views the
        caller passes the coverage end, which yields the full span.
        """
        end = min(self.end_date, as_of) if self.end_date else as_of
        if end < self.start_date:
            return 0
        return (end - self.start_date).days + 1

    def officer_brief(self) -> dict[str, Any]:
        return {
            "id": self.officer_id,
            "name": self.officer_name,
            "slug": self.officer_slug,
            "gender": self.gender,
            "birth_year": self.birth_year,
        }

    def rank_label(self) -> str:
        return RANK_LABELS.get(self.rank_level, "级别待考")


@dataclass(slots=True)
class OfficerEvent:
    id: int
    officer_id: int
    event_type: str
    event_date: date
    title: str
    description: str | None = None
    source_url: str | None = None
    source_title: str | None = None
    verified: bool = False


def parse_date(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    text = str(value)
    if len(text) == 7:
        text += "-01"
    return date.fromisoformat(text)


def clamp_date(value: date, lower: date, upper: date) -> date:
    return max(lower, min(upper, value))


def overlaps(start: date, end: date | None, range_start: date, range_end: date) -> bool:
    effective_end = end or date.max
    return start <= range_end and effective_end >= range_start


def add_days(value: date, days: int) -> date:
    return value + timedelta(days=days)
