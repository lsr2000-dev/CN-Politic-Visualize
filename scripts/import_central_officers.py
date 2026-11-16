"""Import central-institution leaders into the unified officer dataset.

This is intentionally idempotent: rerunning it only adds missing people,
positions and tenures. It gives central organisations the same officer
profile / career plumbing as provincial four-team seats.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "backend" / "app" / "data" / "dataset.json"
CENTRAL = ROOT / "backend" / "app" / "data" / "central.json"


def canonical_title(institution: dict, title: str) -> str:
    inst_id = institution["id"]
    name = institution["name"]
    if name.endswith(title):
        return name
    if title.startswith(name):
        return title
    if inst_id in {"party:politburo_standing", "party:politburo"}:
        return f"中央{title}"
    if inst_id == "party:secretariat":
        if title == "书记处书记":
            return "中央书记处书记"
        return f"中央书记处{title}" if not title.startswith("中央") else title
    if inst_id == "party:discipline":
        return f"中央纪委{title}" if not title.startswith("中央") else title
    if inst_id == "government:state_council":
        return f"国务院{title}" if not title.startswith("国务院") else title
    if inst_id == "government:vice_premiers":
        return "国务院副总理"
    if inst_id == "government:state_councillors":
        return "国务委员"
    if inst_id == "government:secretary":
        return "国务院秘书长"
    if inst_id == "government:state_office":
        return "国务院秘书长" if title == "秘书长" else f"国务院办公厅{title}"
    if inst_id == "party:central_committee":
        return title
    return f"{name}{title}"


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    central = json.loads(CENTRAL.read_text(encoding="utf-8"))
    officers = data["officers"]
    positions = data["positions"]
    tenures = data["tenures"]

    # Rebuild all central positions/tenures from the canonical central snapshot.
    central_position_ids = {
        position["id"] for position in positions
        if str(position.get("seat_key", "")).startswith("central:")
        or position.get("team_group") == "central"
    }
    positions = [position for position in positions if position["id"] not in central_position_ids]
    tenures = [tenure for tenure in tenures if tenure["position_id"] not in central_position_ids]
    data["positions"] = positions
    data["tenures"] = tenures

    by_name = {officer["name"]: officer for officer in officers}
    positions_by_key = {position["seat_key"]: position for position in positions}
    tenure_keys = {
        (t["officer_id"], t["position_id"], t.get("start_date"))
        for t in tenures
    }

    next_officer_id = max((officer["id"] for officer in officers), default=0) + 1
    next_position_id = max((position["id"] for position in positions), default=0) + 1
    next_tenure_id = max((tenure["id"] for tenure in tenures), default=0) + 1

    added_officers = 0
    added_positions = 0
    added_tenures = 0

    for institution in central["institutions"]:
        if institution.get("institution_type", "").endswith("group"):
            continue
        for leader in institution.get("leaders", []):
            name = leader["name"]
            officer = by_name.get(name)
            if not officer:
                officer = {
                    "id": next_officer_id,
                    "slug": f"c{next_officer_id:04d}",
                    "name": name,
                    "gender": None,
                    "birth_year": None,
                    "native_place": None,
                    "ethnicity": None,
                    "party_join_date": None,
                    "work_start_date": None,
                    "education": None,
                    "degree": None,
                    "school": None,
                    "bio": None,
                    "portrait_url": None,
                    "is_deceased": False,
                }
                next_officer_id += 1
                officers.append(officer)
                by_name[name] = officer
                added_officers += 1

            seat_key = f"central:{leader.get('seat_id') or institution['id'] + ':' + leader.get('seat_type', 'principal')}"
            full_title = canonical_title(institution, leader["title"])
            position = positions_by_key.get(seat_key)
            if not position:
                position = {
                    "id": next_position_id,
                    "region_code": None,
                    "organization_id": institution["id"],
                    "code": leader.get("seat_id") or seat_key,
                    "category": "other",
                    "seat_key": seat_key,
                    "position_uid": seat_key,
                    "title": full_title,
                    "full_title": full_title,
                    "rank": 1,
                    "rank_level": institution.get("institution_rank") or "ministerial",
                    "team_group": "central_principal",
                    "is_singular": True,
                    "is_leader": True,
                    "org_name": institution["name"],
                }
                next_position_id += 1
                positions.append(position)
                positions_by_key[seat_key] = position
                added_positions += 1
            else:
                position["title"] = full_title
                position["full_title"] = full_title

            for existing_tenure in tenures:
                if existing_tenure["position_id"] == position["id"]:
                    existing_tenure["title"] = full_title

            key = (officer["id"], position["id"], leader.get("start_date"))
            if key in tenure_keys:
                continue
            tenures.append({
                "officer_id": officer["id"],
                "position_id": position["id"],
                "region_code": None,
                "category": "other",
                "title": full_title,
                "start_date": leader["start_date"],
                "end_date": leader.get("end_date"),
                "start_precision": "day",
                "end_precision": "day" if leader.get("end_date") else None,
                "is_acting": False,
                "is_concurrent": False,
                "is_plural": False,
                "rank_level": institution.get("institution_rank") or "ministerial",
                "end_reason": None,
                "end_reason_detail": None,
                "appointment_basis": None,
                "verified": False,
                "source_id": 1,
                "notes": "中央机构试点导入",
                "id": next_tenure_id,
            })
            next_tenure_id += 1
            tenure_keys.add(key)
            added_tenures += 1

    # Collapse the same role imported from two institutional aliases,
    # for example 国务院秘书长 (国务院秘书长 / 国务院办公厅).
    position_by_id = {position["id"]: position for position in positions}
    unique_tenures = []
    seen_roles: set[tuple[int, str, str, str | None]] = set()
    for tenure in tenures:
        position = position_by_id.get(tenure["position_id"], {})
        key = (
            tenure["officer_id"],
            position.get("title", ""),
            tenure["start_date"],
            tenure.get("end_date"),
        )
        if key in seen_roles:
            continue
        seen_roles.add(key)
        unique_tenures.append(tenure)
    tenures = unique_tenures

    used_position_ids = {tenure["position_id"] for tenure in tenures}
    positions = [
        position for position in positions
        if position["id"] in used_position_ids
        or not str(position.get("seat_key", "")).startswith("central:")
    ]
    data["positions"] = positions
    data["tenures"] = tenures

    identities = [
        item for item in data.get("identities", [])
        if item.get("source") not in {"central_import", "central_import_implied"}
    ]
    identity_keys = {
        (item["person_id"], item["term"], item["role"], item.get("start_date"))
        for item in identities
    }
    next_identity_id = max((item["id"] for item in identities), default=0) + 1
    for institution in central["institutions"]:
        identity_institution = {
            "party:politburo_standing": "politburo_standing",
            "party:politburo": "politburo_member",
            "party:secretariat": "secretariat_member",
            "party:discipline": "discipline_secretary",
        }.get(institution["id"])
        if not identity_institution:
            continue
        for leader in institution.get("leaders", []):
            if identity_institution == "discipline_secretary":
                officer_id = leader.get("officer_id")
                start = leader.get("start_date") or ""
                term = 17 if start < "2012-11-15" else (
                    18 if start < "2017-10-25" else (19 if start < "2022-10-23" else 20)
                )
                term_label = {17: "十七届", 18: "十八届", 19: "十九届", 20: "二十届"}.get(term, f"{term}届")
                key = (officer_id, term, "discipline_secretary", start)
                if officer_id and key not in identity_keys:
                    identities.append({
                        "id": next_identity_id,
                        "person_id": officer_id,
                        "term": term,
                        "term_label": term_label,
                        "role": "discipline_secretary",
                        "label": f"{term_label}中央纪委书记",
                        "start_date": start,
                        "end_date": leader.get("end_date"),
                        "source": "central_import",
                        "source_id": 1,
                    })
                    identity_keys.add(key)
                    next_identity_id += 1
                continue
            for role in leader.get("party_roles", []):
                if role.get("role") != identity_institution:
                    continue
                key = (
                    leader.get("officer_id"), role.get("term"), role.get("role"),
                    leader.get("start_date"),
                )
                if not key[0] or key in identity_keys:
                    continue
                identities.append({
                    "id": next_identity_id,
                    "person_id": key[0],
                    "term": role.get("term"),
                    "term_label": role.get("term_label"),
                    "role": role.get("role"),
                    "label": role.get("label"),
                    "start_date": leader.get("start_date"),
                    "end_date": leader.get("end_date"),
                    "source": "central_import",
                    "source_id": 1,
                })
                identity_keys.add(key)
                next_identity_id += 1
    implied_keys = set(identity_keys)
    for item in list(identities):
        if item.get("role") != "politburo_standing":
            continue
        key = (item["person_id"], item["term"], "politburo_member", item.get("start_date"))
        if key in implied_keys:
            continue
        identities.append({
            "id": next_identity_id,
            "person_id": item["person_id"],
            "term": item["term"],
            "term_label": item.get("term_label"),
            "role": "politburo_member",
            "label": f"{item.get('term_label') or ''}中央政治局委员",
            "start_date": item.get("start_date"),
            "end_date": item.get("end_date"),
            "source": "central_import_implied",
            "source_id": 1,
        })
        implied_keys.add(key)
        next_identity_id += 1
    consolidated: dict[tuple[int, int, str], dict] = {}
    for item in identities:
        key = (item["person_id"], item["term"], item["role"])
        previous = consolidated.get(key)
        if previous is None:
            consolidated[key] = item
            continue
        previous["start_date"] = min(previous["start_date"], item["start_date"])
        if previous.get("end_date") is None or item.get("end_date") is None:
            previous["end_date"] = None
        else:
            previous["end_date"] = max(previous["end_date"], item["end_date"])
    identities = list(consolidated.values())
    data["identities"] = identities
    data["organizations"] = central["institutions"]
    data["central_memberships"] = central.get("memberships", {})
    data["central_party_roles"] = central.get("party_roles", {})
    data["central_terms"] = central.get("terms", [])
    data["central_term_composition"] = central.get("term_composition", {})

    DATASET.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"officers +{added_officers} (total {len(officers)}), "
        f"positions +{added_positions} (total {len(positions)}), "
        f"tenures +{added_tenures} (total {len(tenures)})"
    )


if __name__ == "__main__":
    main()
