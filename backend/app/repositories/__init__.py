from __future__ import annotations

import logging

from ..core.config import Settings
from .base import Repository
from .json_repo import JsonRepository
from .sql_repo import SqlRepository

log = logging.getLogger(__name__)

__all__ = ["Repository", "JsonRepository", "SqlRepository", "build_repository"]


def build_repository(settings: Settings) -> Repository:
    if settings.data_mode == "postgres":
        log.info("using PostgreSQL repository")
        return SqlRepository(settings.database_url)
    log.info("using bundled JSON dataset: %s", settings.dataset_path)
    return JsonRepository(settings.dataset_path)
