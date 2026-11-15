from __future__ import annotations

import hashlib
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from ..core.cache import dumps
from ..domain import CATEGORY_ORDER
from ..schemas import (
    CareerResponse,
    CompareResponse,
    CoverageResponse,
    DirectoryResponse,
    EventInfo,
    MetaResponse,
    OfficerOut,
    OfficerProfileResponse,
    RegionDetailResponse,
    RegionOut,
    RegionTimelineResponse,
    SeatHistoryResponse,
    SnapshotResponse,
)
from ..services.query import NotFoundError, QueryService
from ..services.central import CENTRAL_START, central_service

router = APIRouter()

MIN_DATE = date(2012, 11, 8)


def get_service(request: Request) -> QueryService:
    return request.app.state.service


Service = Annotated[QueryService, Depends(get_service)]


def _ensure_day(day: date) -> date:
    if day < MIN_DATE:
        raise HTTPException(
            status_code=422,
            detail={"code": "date_out_of_range", "message": "时间轴最早支持 2012-11-08（中共十八大）"},
        )
    if day > date.today():
        raise HTTPException(
            status_code=422,
            detail={"code": "date_in_future", "message": "不能查询未来日期"},
        )
    return day


def _ok(payload, request: Request, response: Response, cache_status: str) -> Response:
    body = dumps(payload)
    etag = '"' + hashlib.sha1(body.encode()).hexdigest()[:20] + '"'
    headers = {
        "ETag": etag,
        "X-Cache": cache_status,
        "Cache-Control": "no-cache, max-age=0, must-revalidate",
    }
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type="application/json; charset=utf-8", headers=headers)


def _parse_categories(value: str | None) -> list[str] | None:
    if not value:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in items if item not in CATEGORY_ORDER]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_categories", "message": f"未知分类: {', '.join(unknown)}"},
        )
    return items or None


def _central_day(day: date) -> date:
    if day < CENTRAL_START:
        raise HTTPException(
            status_code=422,
            detail={"code": "central_date_out_of_range",
                    "message": "中央机构数据从 2012-11-08（十八大开幕）开始"},
        )
    return day


@router.get("/central/overview", tags=["central"], summary="中央机构四套班子概览")
def central_overview(
    request: Request,
    response: Response,
    day: Annotated[date | None, Query(alias="date")] = None,
):
    day = _central_day(day or date(2026, 10, 29))
    payload = central_service.overview(day)
    return _ok(payload, request, response, "miss")


@router.get("/central/org", tags=["central"], summary="中央机构组织架构")
def central_org(
    request: Request,
    response: Response,
    team: str = Query("party"),
    day: Annotated[date | None, Query(alias="date")] = None,
):
    day = _central_day(day or date(2026, 10, 29))
    if team not in {"party", "congress", "government", "cppcc", "other"}:
        raise HTTPException(status_code=422, detail={"code": "bad_team", "message": "未知中央板块"})
    return _ok(central_service.org(team, day), request, response, "miss")


@router.get("/central/snapshot", tags=["central"], summary="中央机构时点快照")
def central_snapshot(
    request: Request,
    response: Response,
    team: str = Query("party"),
    day: Annotated[date | None, Query(alias="date")] = None,
):
    day = _central_day(day or date(2026, 10, 29))
    if team not in {"party", "congress", "government", "cppcc", "other"}:
        raise HTTPException(status_code=422, detail={"code": "bad_team", "message": "未知中央板块"})
    payload = {
        "team": team,
        "as_of": day.isoformat(),
        "overview": central_service.overview(day),
        "org": central_service.org(team, day),
    }
    return _ok(payload, request, response, "miss")


@router.get("/central/institutions/{inst_id}", tags=["central"], summary="中央机构详情")
def central_institution(
    inst_id: str,
    request: Request,
    response: Response,
    day: Annotated[date | None, Query(alias="date")] = None,
):
    day = _central_day(day or date(2026, 10, 29))
    if inst_id not in central_service.by_id:
        raise NotFoundError(f"未知中央机构: {inst_id}")
    return _ok(central_service.institution(inst_id, day), request, response, "miss")


@router.get("/central/committee", tags=["central"], summary="官员中央委员身份")
def central_committee(
    request: Request,
    response: Response,
    name: str = Query(...),
    day: Annotated[date | None, Query(alias="date")] = None,
):
    # 中央机构图从二十大开始，但中央委员身份要覆盖十八/十九/二十届，
    # 因此这里只受全局时间轴下限约束。
    day = _ensure_day(day or date(2026, 10, 29))
    return _ok({"name": name, "as_of": day.isoformat(),
                "committee": central_service.committee(name, day),
                "party_roles": central_service.party_roles_for(name)},
               request, response, "miss")

@router.get("/meta", response_model=MetaResponse, tags=["meta"], summary="数据集元信息")
def get_meta(request: Request, response: Response, service: Service):
    payload, status = service.meta()
    return _ok(payload, request, response, status)


@router.get("/events", response_model=list[EventInfo], tags=["meta"], summary="时间轴里程碑")
def get_events(request: Request, response: Response, service: Service):
    return _ok(service.events(), request, response, "STATIC")


@router.get("/regions", response_model=list[RegionOut], tags=["regions"], summary="行政区划列表")
def list_regions(
    request: Request,
    response: Response,
    service: Service,
    level: str | None = Query(None, pattern="^(country|province|prefecture|county)$"),
    parent_code: str | None = None,
):
    regions = service.repo.list_regions(level=level, parent_code=parent_code)
    return _ok(
        [
            {
                "code": region.code,
                "name": region.name,
                "short_name": region.short_name,
                "level": region.level,
                "parent_code": region.parent_code,
                "centroid": list(region.centroid) if region.centroid else None,
                "sort_order": region.sort_order,
            }
            for region in regions
        ],
        request,
        response,
        "MISS",
    )


@router.get(
    "/map/snapshot",
    response_model=SnapshotResponse,
    tags=["map"],
    summary="按日期获取 31 省四套班子快照",
)
def map_snapshot(
    request: Request,
    response: Response,
    service: Service,
    as_of: date | None = Query(None, alias="date", description="YYYY-MM-DD，默认今天"),
    regions: str | None = Query(None, description="逗号分隔的省级行政区划代码"),
    categories: str | None = Query(None, description="party,congress,government,cppcc"),
):
    day = _ensure_day(as_of or date.today())
    codes = [code.strip() for code in regions.split(",") if code.strip()] if regions else None
    payload, status = service.snapshot(day, codes, _parse_categories(categories))
    return _ok(payload, request, response, status)


@router.get(
    "/regions/{region_code}/leaders",
    response_model=RegionDetailResponse,
    tags=["map"],
    summary="某省某日四套班子详情",
)
def region_leaders(
    region_code: str,
    request: Request,
    response: Response,
    service: Service,
    as_of: date | None = Query(None, alias="date"),
):
    day = _ensure_day(as_of or date.today())
    payload, status = service.region_detail(region_code, day)
    return _ok(payload, request, response, status)


@router.get(
    "/regions/{region_code}/timeline",
    response_model=RegionTimelineResponse,
    tags=["map"],
    summary="某省四套班子席位更替时间线",
)
def region_timeline(
    region_code: str,
    request: Request,
    response: Response,
    service: Service,
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
):
    start = _ensure_day(from_date or MIN_DATE)
    end = _ensure_day(to_date or date.today())
    payload, status = service.region_timeline(region_code, start, end)
    return _ok(payload, request, response, status)


@router.get(
    "/regions/{region_code}/seats/{seat_key}/history",
    response_model=SeatHistoryResponse,
    tags=["seats"],
    summary="单个席位自十八大以来的完整任职史",
)
def seat_history(
    region_code: str,
    seat_key: str,
    request: Request,
    response: Response,
    service: Service,
    as_of: date | None = Query(None, alias="date"),
):
    day = _ensure_day(as_of or date.today())
    payload, status = service.seat_history(region_code, seat_key, day)
    return _ok(payload, request, response, status)


@router.get("/officers", response_model=list[OfficerOut], tags=["officers"], summary="按姓名搜索官员")
def search_officers(
    request: Request,
    response: Response,
    service: Service,
    q: str = Query("", max_length=32),
    limit: int = Query(20, ge=1, le=50),
):
    payload = service.search_officers(q, limit)
    return _ok(payload, request, response, "MISS")


@router.get("/directory", response_model=DirectoryResponse, tags=["directory"],
            summary="官员名册（人类可读表格数据）")
def directory(
    request: Request,
    response: Response,
    service: Service,
    q: str = Query("", max_length=64),
    region: str | None = Query(None, description="省级行政区划代码"),
    category: str | None = Query(None, pattern="^(party|congress|government|cppcc|other)$"),
    status: str | None = Query(None, pattern="^(active|retired|under_investigation|expelled|deceased|left|unknown)$"),
    rank: str | None = Query(None, description="行政级别 key"),
    as_of: date | None = Query(None, alias="date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    day = _ensure_day(as_of) if as_of else service.coverage_end
    payload, cache_status = service.directory(
        query=q, region=region, category=category, status=status,
        rank_level=rank, as_of=day, page=page, page_size=page_size,
    )
    return _ok(payload, request, response, cache_status)


@router.get("/coverage", response_model=CoverageResponse, tags=["meta"],
            summary="数据覆盖率与完整率报告")
def coverage(
    request: Request,
    response: Response,
    service: Service,
    as_of: date | None = Query(None, alias="date"),
):
    day = _ensure_day(as_of) if as_of else service.coverage_end
    payload, cache_status = service.coverage(day)
    return _ok(payload, request, response, cache_status)


@router.get("/officers/{officer_id}", response_model=OfficerProfileResponse,
            tags=["officers"], summary="官员档案与当前职务")
def officer_profile(
    officer_id: int,
    request: Request,
    response: Response,
    service: Service,
    as_of: date | None = Query(None, alias="date"),
):
    day = _ensure_day(as_of or date.today())
    payload = service.officer_profile(officer_id, day)
    return _ok(payload, request, response, "MISS")


@router.get(
    "/officers/{officer_id}/career",
    response_model=CareerResponse,
    tags=["officers"],
    summary="官员履历甘特图数据",
)
def officer_career(
    officer_id: int,
    request: Request,
    response: Response,
    service: Service,
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
):
    start = _ensure_day(from_date or MIN_DATE)
    end = _ensure_day(to_date or date.today())
    payload, status = service.career(officer_id, start, end)
    return _ok(payload, request, response, status)


@router.get("/compare", response_model=CompareResponse, tags=["compare"],
            summary="多省班子对比")
def compare(
    request: Request,
    response: Response,
    service: Service,
    regions: str = Query(..., description="逗号分隔，最多 6 个省"),
    as_of: date | None = Query(None, alias="date"),
):
    day = _ensure_day(as_of or date.today())
    codes = [code.strip() for code in regions.split(",") if code.strip()]
    if not codes:
        raise HTTPException(status_code=422, detail={"code": "empty_regions", "message": "至少选择 1 个省"})
    payload, status = service.compare(day, codes)
    return _ok(payload, request, response, status)


@router.get("/health", tags=["meta"], summary="健康检查")
def health(request: Request):
    service: QueryService = request.app.state.service
    return {
        "status": "ok",
        "repository": service.repo.health(),
        "cache": service.cache.stats(),
    }
