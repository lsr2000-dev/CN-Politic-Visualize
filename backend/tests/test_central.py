from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

client = TestClient(create_app(Settings(data_mode="json", redis_url=None, environment="test")))
CENTRAL = Path(__file__).resolve().parent.parent / "app" / "data" / "central.json"
DATASET = Path(__file__).resolve().parent.parent / "app" / "data" / "dataset.json"


def test_all_positions_have_stable_uid_and_no_overlaps() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    positions = data["positions"]
    assert all(position.get("position_uid") for position in positions)
    assert len({position["position_uid"] for position in positions}) == len(positions)
    by_uid = {position["id"]: position["position_uid"] for position in positions}
    spans: dict[tuple[int, str], list[tuple[date, date | None]]] = {}
    for tenure in data["tenures"]:
        start = date.fromisoformat(tenure["start_date"])
        end = date.fromisoformat(tenure["end_date"]) if tenure.get("end_date") else None
        spans.setdefault((tenure["officer_id"], by_uid[tenure["position_id"]]), []).append((start, end))
    for values in spans.values():
        values.sort()
        for previous, current in zip(values, values[1:]):
            assert previous[1] is not None and current[0] > previous[1]


def test_central_positions_use_stable_seat_keys() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    positions = [p for p in data["positions"] if p.get("seat_key", "").startswith("central:")]
    keys = [p["seat_key"] for p in positions]
    assert len(keys) == len(set(keys))
    assert all(":seat:" in key for key in keys)
    ids = {p["id"] for p in positions}
    tenures = [t for t in data["tenures"] if t["position_id"] in ids]
    tenure_keys = [(t["officer_id"], t["position_id"], t["start_date"]) for t in tenures]
    assert len(tenure_keys) == len(set(tenure_keys))


def test_central_data_has_no_overlapping_or_invalid_tenures() -> None:
    data = json.loads(CENTRAL.read_text(encoding="utf-8"))
    for institution in data["institutions"]:
        seen: dict[tuple[str, str], tuple[date, date | None]] = {}
        for leader in institution.get("leaders", []):
            start = date.fromisoformat(leader["start_date"])
            end = date.fromisoformat(leader["end_date"]) if leader.get("end_date") else None
            assert leader.get("officer_id"), (institution["id"], leader["name"])
            assert leader.get("seat_id"), (institution["id"], leader["name"])
            assert end is None or end >= start, (institution["id"], leader["name"])
            key = (leader["name"], leader["title"])
            previous = seen.get(key)
            assert previous is None or previous[1] is not None and start > previous[1], (
                institution["id"], leader["name"], leader["title"],
            )
            seen[key] = (start, end)


def test_central_overview_and_org() -> None:
    overview = client.get("/api/v1/central/overview", params={"date": "2026-10-29"})
    assert overview.status_code == 200
    body = overview.json()
    assert body["teams"]["party"]["label"] == "党中央"
    assert body["teams"]["government"]["count"] > 0
    assert body["coverage"]["required"] > 0
    assert body["coverage"]["filled"] <= body["coverage"]["required"]
    assert len(body["other"]) == 5

    org = client.get("/api/v1/central/org", params={"team": "government", "date": "2026-10-29"})
    assert org.status_code == 200
    institutions = org.json()["institutions"]
    assert any(item["name"] == "外交部" for item in institutions)
    foreign = next(item for item in institutions if item["name"] == "外交部")
    assert foreign["leader"]["name"] == "王毅"
    assert foreign["leader"]["central_committee"]["label"].endswith("中央委员")


def test_central_committee_status_changes_by_date() -> None:
    active = client.get("/api/v1/central/committee", params={"name": "马兴瑞", "date": "2022-10-16"}).json()
    assert active["committee"]["status"] == "active"
    assert active["committee"]["label"].endswith("中央委员")

    expelled = client.get("/api/v1/central/committee", params={"name": "马兴瑞", "date": "2026-10-29"}).json()
    assert expelled["committee"]["status"] == "expelled"
    assert expelled["committee"]["status_label"] == "已开除"
    assert expelled["committee"]["label"].startswith("原")


def test_central_snapshot_returns_as_of_tree() -> None:
    snapshot = client.get(
        "/api/v1/central/snapshot",
        params={"team": "congress", "date": "2018-04-01"},
    )
    assert snapshot.status_code == 200
    assert snapshot.headers.get("X-Data-Version")
    body = snapshot.json()
    assert body["as_of"] == "2018-04-01"
    assert body["team"] == "congress"
    assert any(item["id"] == "congress:npc" for item in body["org"]["institutions"])


def test_central_rejects_before_congress() -> None:
    response = client.get("/api/v1/central/overview", params={"date": "2012-11-07"})
    assert response.status_code == 422


def test_directory_exposes_central_committee() -> None:
    rows = client.get(
        "/api/v1/directory", params={"date": "2026-10-29", "q": "尹力"}
    ).json()["items"]
    assert rows[0]["central_committee"]["label"] == "二十届中央委员"


def test_party_taxonomy_has_work_orgs_and_aliases() -> None:
    org = client.get(
        "/api/v1/central/org", params={"team": "party", "date": "2026-10-29"}
    ).json()
    by_id = {item["id"]: item for item in org["institutions"]}
    assert len([item for item in by_id.values() if item["institution_type"] != "group"
                and not item["institution_type"].endswith("_group")]) >= 40
    assert by_id["party:guangming"]["party_category"] == "affiliate"
    assert by_id["party:archives"]["party_category"] == "subordinate"
    assert "国务院台湾事务办公室" in by_id["party:taiwan"]["aliases"]
    assert by_id["party:taiwan"]["verification_status"] == "provisional"


def test_central_institution_history() -> None:
    detail = client.get(
        "/api/v1/central/institutions/government:foreign", params={"date": "2026-10-29"}
    )
    assert detail.status_code == 200
    body = detail.json()
    names = [item["name"] for item in body["history"]]
    assert "秦刚" in names
    assert "王毅" in names
    wang = next(item for item in body["leaders"] if item["name"] == "王毅")
    assert wang["birth_year"] == 1953
    assert wang["native_place"] == "北京市"
    assert any(seat["id"].startswith("government:foreign:seat:") for seat in body["seats"])
    assert any(seat["title"] == "外交部部长" for seat in body["seats"])


def test_central_lifecycle_and_team_coverage() -> None:
    overview = client.get("/api/v1/central/overview", params={"date": "2012-11-08"}).json()
    assert overview["team_coverage"]["government"]["start"] == "2012-11-08"
    assert overview["team_coverage"]["party"]["start"] == "2012-11-08"
    detail = client.get(
        "/api/v1/central/institutions/government:data", params={"date": "2012-11-08"}
    ).json()
    assert detail["status_at"] == "not_yet"
    assert detail["created_at"] == "2023-10-25"


def test_2018_legislature_and_cppcc_are_complete() -> None:
    for team in ("congress", "cppcc"):
        org = client.get(
            "/api/v1/central/org", params={"team": team, "date": "2018-04-01"}
        ).json()
        missing = [
            item["name"] for item in org["institutions"]
            if item["institution_type"] != "group"
            and not item["institution_type"].endswith("_group")
            and not item["leaders"]
        ]
        assert missing == [], (team, missing)


def test_party_and_legislature_history() -> None:
    standing = client.get(
        "/api/v1/central/institutions/party:politburo_standing", params={"date": "2018-04-01"}
    ).json()
    assert {item["name"] for item in standing["leaders"]} == {
        "习近平", "李克强", "栗战书", "汪洋", "王沪宁", "赵乐际", "韩正",
    }
    npc = client.get(
        "/api/v1/central/institutions/congress:npc", params={"date": "2018-04-01"}
    ).json()
    assert npc["leader"]["name"] == "栗战书"
    cppcc = client.get(
        "/api/v1/central/institutions/cppcc:committee", params={"date": "2018-04-01"}
    ).json()
    assert cppcc["leader"]["name"] == "汪洋"
    politburo = client.get(
        "/api/v1/central/institutions/party:politburo", params={"date": "2018-04-01"}
    ).json()
    xuexiang = next(item for item in politburo["leaders"] if item["name"] == "丁薛祥")
    assert any(role["term"] == 19 for role in xuexiang["party_roles"])
    assert all(role["term"] != 20 for role in xuexiang["party_roles"])


def test_politburo_roles_and_primary_posts() -> None:
    org = client.get("/api/v1/central/org", params={"team": "party", "date": "2026-10-29"}).json()
    standing = next(i for i in org["institutions"] if i["id"] == "party:politburo_standing")
    leader = standing["leaders"][0]
    assert leader["name"] == "习近平"
    assert leader["party_roles"][0]["role"] == "politburo_standing"
    assert "总书记" in (leader["primary_post"] or "")


def test_state_council_every_principal_page_is_available() -> None:
    org = client.get("/api/v1/central/org", params={"team": "government", "date": "2026-10-29"}).json()
    institutions = [
        item for item in org["institutions"]
        if item["institution_type"] != "group"
        and not item["institution_type"].endswith("_group")
    ]
    assert len(institutions) >= 50
    for institution in institutions:
        detail = client.get(
            f"/api/v1/central/institutions/{institution['id']}",
            params={"date": "2026-10-29"},
        )
        assert detail.status_code == 200, institution["id"]
        if institution["leaders"]:
            assert detail.json()["history"], institution["id"]


def test_separate_party_secretary_seats() -> None:
    foreign = client.get(
        "/api/v1/central/institutions/government:foreign",
        params={"date": "2026-10-29"},
    ).json()
    assert [(item["name"], item["title"]) for item in foreign["leaders"]] == [
        ("王毅", "部长"),
        ("齐玉", "党委书记"),
    ]
    environment = client.get(
        "/api/v1/central/institutions/government:environment",
        params={"date": "2026-10-29"},
    ).json()
    assert [(item["name"], item["title"]) for item in environment["leaders"]] == [
        ("黄润秋", "部长"),
        ("孙金龙", "党组书记"),
    ]

def test_20th_central_committee_status_accounting() -> None:
    detail = client.get(
        "/api/v1/central/institutions/party:central_committee", params={"date": "2026-11-16"}
    ).json()
    stats = detail["committee_stats"]
    assert stats["elected_members"] == 205
    assert stats["current_members"] == 191
    assert stats["actual_members"] == 183
    assert stats["expelled_members"] == 36
    assert stats["resigned_members"] == 1
    assert stats["deceased_members"] == 1
    assert stats["under_investigation"] == 8
    assert len(detail["committee_members"]["members"]) == 229
    assert (
        stats["actual_members"]
        + stats["expelled_members"]
        + stats["resigned_members"]
        + stats["deceased_members"]
        + stats["under_investigation"]
        == stats["recorded_members"]
    )

def test_20th_body_baseline_snapshots() -> None:
    expected = {
        "2022-10-23": (205, 0, 0, 205, 0, 171, 0, 0, 171, 0, 171),
        "2024-07-18": (205, 3, 3, 205, 1, 171, 1, 3, 167, 0, 167),
        "2025-10-23": (205, 14, 14, 205, 1, 171, 5, 14, 152, 0, 152),
        "2026-10-29": (205, 38, 24, 191, 7, 171, 15, 24, 132, 5, 127),
    }
    for day, values in expected.items():
        detail = client.get(
            "/api/v1/central/institutions/party:central_committee", params={"date": day}
        ).json()
        stats = detail["committee_stats"]
        assert (
            stats["elected_members"],
            stats["departed_members"],
            stats["replacement_members"],
            stats["current_members"],
            stats["under_investigation"],
            stats["initial_alternates"],
            stats["departed_alternates"],
            stats["promoted_alternates"],
            stats["current_alternates"],
            stats["under_investigation_alternates"],
            stats["actual_alternates"],
        ) == values
        members = detail["committee_members"]["members"]
        alternates = detail["committee_alternates"]["members"]
        assert len(members) == {
            "2022-10-23": 205,
            "2024-07-18": 208,
            "2025-10-23": 219,
            "2026-10-29": 229,
        }[day]
        assert len(alternates) == 171
        assert all(item["birth_year"] and item["native_place"] for item in members + alternates)

    detail = client.get(
        "/api/v1/central/institutions/party:central_committee", params={"date": "2026-10-29"}
    ).json()
    unique = {item["name"].replace("凱", "凯") for item in detail["committee_members"]["members"]}
    unique |= {item["name"].replace("凱", "凯") for item in detail["committee_alternates"]["members"]}
    assert len(unique) == 376

def test_institution_contract_endpoint() -> None:
    detail = client.get(
        "/api/v1/institutions/central/party:central_committee",
        params={"date": "2026-10-29"},
    ).json()
    assert detail["schema_version"] == 1
    assert detail["entity_type"] == "central"
    assert detail["name"] == "中国共产党中央委员会"
    assert detail["committee_stats"]["actual_members"] == 184
    assert any(
        section["key"] == "roster" and section["available"]
        for section in detail["sections"]
    )
    assert detail["children"]

    assert client.get(
        "/api/v1/institutions/not-a-type/party:central_committee"
    ).status_code == 422
    assert client.get(
        "/api/v1/institutions/province/party:central_committee"
    ).status_code == 404

def test_politburo_rank_is_vice_national() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    ranks = {
        org["id"]: org.get("institution_rank")
        for org in data["organizations"]
    }
    assert ranks["party:politburo"] == "vice_national_leader"
    assert ranks["party:politburo_standing"] == "national_leader"
    assert ranks["party:secretariat"] == "vice_national_leader"

def test_expelled_politburo_members_are_not_current() -> None:
    detail = client.get(
        "/api/v1/institutions/central/party:politburo",
        params={"date": "2026-10-29"},
    ).json()
    names = {leader["name"] for leader in detail["leaders"]}
    assert "何卫东" not in names
    assert "张又侠" not in names
    assert "马兴瑞" not in names
    assert "张升民" in names
    assert len(detail["leaders"]) == 22

def test_elected_politburo_members_keep_expelled_labels() -> None:
    org = client.get(
        "/api/v1/central/org",
        params={"team": "party", "date": "2026-10-29"},
    ).json()
    politburo = next(
        item for item in org["institutions"] if item["id"] == "party:politburo"
    )
    elected = {member["name"]: member for member in politburo["elected_members"]}
    assert len(elected) == 24
    for name in ["何卫东", "张又侠", "马兴瑞"]:
        assert elected[name]["member_status"] == "expelled"
        assert elected[name]["member_status_label"] == "已开除"
    assert "张升民" not in elected
    assert len(politburo["leaders"]) == 22

def test_politburo_membership_change_lines() -> None:
    org = client.get(
        "/api/v1/central/org",
        params={"team": "party", "date": "2026-10-29"},
    ).json()
    politburo = next(
        item for item in org["institutions"] if item["id"] == "party:politburo"
    )
    changes = politburo["membership_changes"]
    labels = [item["label"] for item in changes]
    assert labels == [
        "二十届四中全会除名",
        "二十届五中全会除名",
        "二十届五中全会增选",
    ]
    assert changes[0]["members"] == ["何卫东"]
    assert set(changes[1]["members"]) == {"张又侠", "马兴瑞"}
    assert changes[2]["members"] == ["张升民"]

def test_politburo_roster_contains_added_member() -> None:
    org = client.get(
        "/api/v1/central/org",
        params={"team": "party", "date": "2026-10-29"},
    ).json()
    politburo = next(
        item for item in org["institutions"] if item["id"] == "party:politburo"
    )
    roster = {member["name"]: member for member in politburo["roster_members"]}
    assert len(roster) == 25
    assert roster["张升民"]["member_status"] == "added"
    assert roster["张升民"]["member_status_label"] == "新增选"
    assert "二十届中央军委委员" in {
        role["label"] for role in roster["张升民"]["party_roles"]
    }

def test_collegial_body_composition_display() -> None:
    org = client.get(
        "/api/v1/central/org",
        params={"team": "party", "date": "2026-10-29"},
    ).json()
    by_id = {item["id"]: item for item in org["institutions"]}
    assert by_id["party:politburo_standing"]["composition"]["display"] == "7"
    assert by_id["party:secretariat"]["composition"]["display"] == "7"
    assert by_id["party:politburo"]["composition"] == {
        "initial": 24,
        "removed": 3,
        "added": 1,
        "current": 22,
        "display": "22",
    }
