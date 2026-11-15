from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.v1 import router as v1_router
from .core.cache import CacheLayer
from .core.config import Settings, get_settings
from .repositories import build_repository
from .services.query import NotFoundError, QueryService, RangeError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    repository = build_repository(settings)
    cache = CacheLayer(settings)
    service = QueryService(repository, cache, settings)

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "十八大以来中国地方政治人事时空可视化系统的读取 API。\n\n"
            "所有时点查询共享同一语义：`as_of` 时刻仍在任的记录，"
            "包含代理（acting）与兼任（concurrent），并返回任期天数与数据覆盖范围。\n\n"
            "内置数据为演示样例，生产使用前请替换为经复核的数据源。"
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["ETag", "X-Cache"],
    )

    app.state.settings = settings
    app.state.repository = repository
    app.state.cache = cache
    app.state.service = service

    @app.middleware("http")
    async def data_version_header(request: Request, call_next):
        repository = request.app.state.repository
        reload = getattr(repository, "reload_if_changed", None)
        if callable(reload):
            reload()
        response = await call_next(request)
        version = getattr(repository, "dataset_version", None)
        if version is not None:
            response.headers["X-Data-Version"] = str(version)
        return response

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "not_found", "message": str(exc)}},
        )

    @app.exception_handler(RangeError)
    async def _range_error(_: Request, exc: RangeError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "invalid_range", "message": str(exc)}},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "请求参数不合法",
                    "details": exc.errors(),
                }
            },
        )

    app.include_router(v1_router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False)
    def index() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "docs": "/docs",
            "api": settings.api_prefix,
            "mode": settings.data_mode,
        }

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
