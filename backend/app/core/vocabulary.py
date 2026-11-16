from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "vocabulary.json"
VOCABULARY = json.loads(DATA.read_text(encoding="utf-8"))

TERMS = {item["ordinal"]: item for item in VOCABULARY["terms"]}
RANKS = VOCABULARY["ranks"]
PERSON_STATUS = VOCABULARY["person_status"]
TENURE_STATUS = VOCABULARY["tenure_status"]
IDENTITY_STATUS = VOCABULARY["identity_status"]
IDENTITY_TYPES = VOCABULARY["identity_types"]
COMMITTEE_TYPES = VOCABULARY["committee_types"]


def term_label(ordinal: int | str | None) -> str:
    try:
        return TERMS[int(ordinal)]["label"]
    except (KeyError, TypeError, ValueError):
        return f"{ordinal}届" if ordinal is not None else ""


def rank_label(code: str | None) -> str:
    return RANKS.get(code or "", RANKS["unknown"])


def status_label(scope: str, code: str | None) -> str:
    table = {
        "person": PERSON_STATUS,
        "tenure": TENURE_STATUS,
        "identity": IDENTITY_STATUS,
    }.get(scope, {})
    return table.get(code or "", code or "")


def identity_label(
    ordinal: int | str | None,
    role: str,
    status: str = "active",
) -> str:
    role_label = IDENTITY_TYPES.get(role, {}).get("label", role)
    label = f"{term_label(ordinal)}{role_label}"
    return f"原{label}" if status != "active" else label


def committee_label(ordinal: int | str | None, member_type: str, ended: bool = False) -> str:
    kind = COMMITTEE_TYPES.get(member_type, {}).get("label", member_type)
    label = f"{term_label(ordinal)}{kind}"
    return f"原{label}" if ended else label
