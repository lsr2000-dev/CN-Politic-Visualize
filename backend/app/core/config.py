from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_prefix="POLVIS_", extra="ignore"
    )

    app_name: str = "地方政治人事时空可视化系统 API"
    api_prefix: str = "/api/v1"
    environment: Literal["dev", "test", "prod"] = "dev"

    # json: 内置样例数据（零依赖启动）；postgres: 生产数据源
    data_mode: Literal["json", "postgres"] = "json"
    dataset_path: Path = BASE_DIR / "app" / "data" / "dataset.json"
    database_url: str = "postgresql+psycopg://polvis:polvis@localhost:5432/polvis"

    redis_url: str | None = None
    cache_ttl_seconds: int = 900
    cache_max_items: int = 512
    memory_cache_ttl_seconds: int = 60

    # 逗号分隔；不使用 list[str]，避免 pydantic-settings 把环境变量当 JSON 解析
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"
    )

    coverage_start_fallback: str = "2012-11-08"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
