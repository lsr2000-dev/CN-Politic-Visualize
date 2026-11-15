from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["party", "congress", "government", "cppcc", "other"]


class Coverage(BaseModel):
    dataset_id: str
    coverage_start: date
    coverage_end: date
    beyond_coverage: bool
    status: str
    disclaimer: str | None = None


class OfficerBrief(BaseModel):
    id: int
    name: str
    slug: str
    gender: str | None = None
    birth_year: int | None = None


class Member(BaseModel):
    tenure_id: int
    officer: OfficerBrief
    title: str
    category: Category
    seat_key: str
    seat_rank: int
    region_code: str | None = None
    region_name: str | None = None
    region_short_name: str | None = None
    rank_level: str = "unknown"
    rank_label: str = "级别待考"
    is_acting: bool
    is_concurrent: bool
    is_plural: bool = False
    start_date: date
    end_date: date | None = None
    start_precision: str = "month"
    duration_days: int
    is_incumbent: bool
    is_provisional: bool
    is_roster_snapshot: bool = False
    status: str = "unknown"
    status_label: str = "待补充"
    exit_reason: str | None = None
    exit_reason_label: str | None = None
    verified: bool


class Team(BaseModel):
    key: Category
    label: str
    members: list[Member]


class Teams(BaseModel):
    party: Team
    congress: Team
    government: Team
    cppcc: Team


class RegionMetrics(BaseModel):
    party_days: int
    governor_days: int
    party_count: int
    governor_count: int
    filled: int
    acting: int


class RegionSnapshot(BaseModel):
    region_code: str
    region_name: str
    short_name: str
    level: str
    centroid: list[float] | None = None
    teams: Teams
    headline: dict[str, Member | None]
    filled: int
    member_count: int
    acting_count: int
    metrics: RegionMetrics


class SnapshotStats(BaseModel):
    region_count: int
    member_count: int
    acting_count: int
    regions_with_gaps: int


class SnapshotResponse(BaseModel):
    as_of: date
    coverage: Coverage
    stats: SnapshotStats
    regions: list[RegionSnapshot]


class RegionDetailResponse(BaseModel):
    as_of: date
    coverage: Coverage
    region: RegionSnapshot


class CompareResponse(BaseModel):
    as_of: date
    coverage: Coverage
    regions: list[RegionSnapshot]


class RegionOut(BaseModel):
    code: str
    name: str
    short_name: str
    level: str
    parent_code: str | None = None
    centroid: list[float] | None = None
    sort_order: int


class RegionTimelineSpan(Member):
    officer_name: str
    officer_id: int


class OfficerEventOut(BaseModel):
    id: int
    event_type: str
    event_date: date
    title: str
    description: str | None = None
    source_url: str | None = None
    source_title: str | None = None
    verified: bool = False


class CareerContext(BaseModel):
    previous: Member | None = None
    next: Member | None = None
    status: str
    status_label: str


class CareerResponse(BaseModel):
    officer: OfficerOut
    range: CareerRange
    lanes: list[CareerLane]
    events: list[OfficerEventOut] = []
    context: CareerContext | None = None
    summary: CareerSummary
    coverage: Coverage


class RegionTimelineLane(BaseModel):
    key: str
    category: Category
    title: str
    label: str
    rank: int
    spans: list[RegionTimelineSpan]


class RegionTimelineResponse(BaseModel):
    region_code: str
    region_name: str
    from_: date = Field(alias="from")
    to: date
    lanes: list[RegionTimelineLane]

    model_config = ConfigDict(populate_by_name=True)


class SeatSpan(Member):
    officer_name: str
    officer_id: int
    gap_before_days: int | None = None
    is_current: bool
    is_future: bool = False
    event_type: str | None = None
    event_label: str | None = None
    event_date: date | None = None


class SeatHistoryResponse(BaseModel):
    region_code: str
    region_name: str
    seat_key: str
    title: str
    category: Category
    as_of: date
    spans: list[SeatSpan]
    holder_count: int
    acting_count: int
    incumbent: Member | None = None


class OfficerOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

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


class OfficerProfileResponse(BaseModel):
    officer: OfficerOut
    current: list[Member]
    previous: Member | None = None
    next: Member | None = None
    events: list[OfficerEventOut] = []
    status: str
    status_label: str
    stats: dict[str, Any]
    as_of: date
    coverage: Coverage


class CareerSpan(Member):
    lane_key: str
    officer_name: str
    officer_id: int
    org_name: str | None = None
    clipped_start: date


class CareerLane(BaseModel):
    key: str
    label: str
    full_label: str
    order: int
    spans: list[CareerSpan]


class CareerRange(BaseModel):
    from_: date = Field(alias="from")
    to: date
    coverage_end: date
    requested_to: date | None = None

    model_config = ConfigDict(populate_by_name=True)


class CareerSummary(BaseModel):
    span_count: int
    province_count: int
    acting_count: int
    total_days: int


class DirectoryItem(BaseModel):
    officer_id: int
    name: str
    gender: str | None = None
    birth_year: int | None = None
    native_place: str | None = None
    current_title: str | None = None
    region_code: str | None = None
    region_name: str | None = None
    category: Category | None = None
    rank_level: str
    rank_label: str
    start_date: date | None = None
    end_date: date | None = None
    start_precision: str | None = None
    status: str
    status_label: str
    status_date: date | None = None
    status_title: str | None = None
    previous_title: str | None = None
    previous_rank_label: str | None = None
    next_title: str | None = None
    next_rank_label: str | None = None
    central_committee: dict | None = None
    party_roles: list[dict] = Field(default_factory=list)
    source_count: int = 0
    verified: bool = False
    updated_at: str


class CoverageCategory(BaseModel):
    provinces: int
    total: int
    ratio: float


class CoverageRegion(BaseModel):
    region_code: str
    region_name: str
    short_name: str
    filled: int
    principal_complete: bool
    categories: dict[str, bool]
    member_count: int
    roster_snapshots: int


class CoverageCheckpoint(BaseModel):
    date: date
    provinces_complete: int
    principal_coverage: float


class CoverageVacancy(BaseModel):
    region_code: str
    region_name: str
    category: Category
    reason: str
    date: date


class CoverageResponse(BaseModel):
    as_of: date
    dataset_version: str
    plenum_date: date
    provinces_total: int
    provinces_complete: int
    provinces_accounted: int
    principal_coverage: float
    checkpoints: list[CoverageCheckpoint] = []
    vacancies: list[CoverageVacancy] = []
    category_coverage: dict[str, CoverageCategory]
    principal_slots: int
    principal_slots_filled: int
    tenures: int
    officers: int
    events: int
    verified_tenures: int
    verified_ratio: float
    roster_snapshots: int
    regions: list[CoverageRegion]


class DirectoryResponse(BaseModel):
    items: list[DirectoryItem]
    total: int
    page: int
    page_size: int
    as_of: date
    dataset_version: str
    coverage: CoverageResponse
    updated_at: str


class CategoryInfo(BaseModel):
    key: Category
    label: str
    order: int
    accent: str


class MetricInfo(BaseModel):
    key: str
    label: str
    unit: str
    kind: str


class EventInfo(BaseModel):
    date: date
    type: str
    label: str
    description: str


class DatasetInfo(BaseModel):
    id: str
    coverage_start: date
    coverage_end: date
    plenum_date: date | None = None
    status: str
    disclaimer: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)


class GeoInfo(BaseModel):
    geojson: str
    adcode_property: str
    name_property: str


class MetaResponse(BaseModel):
    dataset: DatasetInfo
    categories: list[CategoryInfo]
    metrics: list[MetricInfo]
    events: list[EventInfo]
    geo: GeoInfo
    timezone: str
    generated_at: str


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
