"""Stable institution-detail contract shared by central and future local bodies.

The existing central payload remains the source for the central adapter.  Local
adapters can return the same envelope without changing the drawer contract.
"""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1
ENTITY_TYPES = {"central", "province", "prefecture", "county", "subordinate"}


def institution_envelope(
    payload: dict[str, Any],
    *,
    entity_type: str,
    children: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"unsupported entity_type: {entity_type}")

    body = dict(payload)
    body["schema_version"] = SCHEMA_VERSION
    body["entity_type"] = entity_type
    body["children"] = children or []

    committee = body.get("committee_members") or {}
    sections = [
        {"key": "overview", "label": "概况", "available": True},
        {"key": "leaders", "label": "领导班子", "available": True},
        {
            "key": "history",
            "label": "机构沿革",
            "available": bool(body.get("history")),
        },
        {
            "key": "roster",
            "label": "中央委员会名单",
            "available": bool(committee.get("members")),
        },
        {
            "key": "children",
            "label": "下属机构",
            "available": bool(body["children"]),
        },
    ]
    body["sections"] = sections
    return body


def child_summary(institution: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id",
        "parent_id",
        "name",
        "short_name",
        "institution_type",
        "institution_rank",
        "level",
        "status",
        "team",
    )
    return {key: institution.get(key) for key in keys if key in institution}
