"""API contract tests — run against the bundled demo dataset."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def build_client() -> TestClient:
    settings = Settings(data_mode="json", redis_url=None, environment="test")
    return TestClient(create_app(settings))


client = build_client()


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["repository"]["backend"] == "json"
    assert body["repository"]["tenures"] > 300


def test_meta() -> None:
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["dataset"]["id"] == "2026.10"
    assert body["dataset"]["coverage_end"] == "2026-10-29"
    assert len(body["categories"]) == 4
    assert body["events"][0]["date"] == "2012-11-15"
    assert any(event["date"] == "2026-10-29" for event in body["events"])


def test_snapshot_2017() -> None:
    response = client.get("/api/v1/map/snapshot", params={"date": "2017-10-25"})
    assert response.status_code == 200
    body = response.json()
    assert body["as_of"] == "2017-10-25"
    assert body["stats"]["region_count"] == 31
    beijing = next(item for item in body["regions"] if item["region_code"] == "110000")
    assert beijing["teams"]["party"]["members"][0]["officer"]["name"] == "蔡奇"
    assert beijing["teams"]["government"]["members"][0]["officer"]["name"] == "陈吉宁"
    assert beijing["metrics"]["party_count"] >= 2


def test_snapshot_cache_and_etag() -> None:
    first = client.get("/api/v1/map/snapshot", params={"date": "2020-01-01"})
    second = client.get("/api/v1/map/snapshot", params={"date": "2020-01-01"})
    assert first.status_code == second.status_code == 200
    assert second.headers["x-cache"] == "HIT"
    etag = second.headers["etag"]
    third = client.get(
        "/api/v1/map/snapshot",
        params={"date": "2020-01-01"},
        headers={"If-None-Match": etag},
    )
    assert third.status_code == 304


def test_region_leaders() -> None:
    response = client.get("/api/v1/regions/310000/leaders", params={"date": "2015-06-01"})
    assert response.status_code == 200
    body = response.json()
    assert body["region"]["region_name"] == "上海市"
    assert body["region"]["teams"]["party"]["members"][0]["officer"]["name"] == "韩正"
    assert body["region"]["teams"]["government"]["members"][0]["officer"]["name"] == "杨雄"
    assert body["region"]["teams"]["congress"]["members"][0]["officer"]["name"] == "殷一璀"


def test_seat_history_includes_acting() -> None:
    response = client.get("/api/v1/regions/110000/seats/governor/history")
    assert response.status_code == 200
    body = response.json()
    names = [span["officer_name"] for span in body["spans"]]
    assert "陈吉宁" in names
    assert "殷勇" in names
    acting = [span for span in body["spans"] if span["is_acting"]]
    assert any(span["officer_name"] == "陈吉宁" for span in acting)
    assert body["spans"] == sorted(body["spans"], key=lambda span: span["start_date"])


def test_seat_history_uses_full_tenure_duration() -> None:
    """Regression: at a historical date, closed tenures must show their full
    length, not the time elapsed at the selected date; successors who have not
    taken office yet are marked is_future instead of showing '不足 1 天'."""
    response = client.get("/api/v1/regions/440000/seats/party_secretary/history",
                          params={"date": "2017-10-25"})
    assert response.status_code == 200
    body = response.json()
    spans = {span["officer_name"]: span for span in body["spans"]}
    assert spans["李希"]["duration_days"] > 1800
    assert spans["李希"]["is_current"] is True
    assert spans["黄坤明"]["is_future"] is True
    assert spans["黄坤明"]["is_current"] is False
    assert body["holder_count"] == 3
    assert body["incumbent"]["officer"]["name"] == "李希"


def test_officer_career_cross_region() -> None:
    search = client.get("/api/v1/officers", params={"q": "李强"}).json()
    officer = next(item for item in search if item["name"] == "李强")
    response = client.get(f"/api/v1/officers/{officer['id']}/career")
    assert response.status_code == 200
    body = response.json()
    lanes = {lane["key"]: lane for lane in body["lanes"]}
    assert {"330000", "320000", "310000", "central"} <= set(lanes)
    assert any(span["title"] == "国务院总理" for span in lanes["central"]["spans"])
    assert body["summary"]["province_count"] >= 3


def test_snapshot_duration_stops_at_as_of() -> None:
    response = client.get("/api/v1/map/snapshot", params={"date": "2017-10-25",
                                                          "regions": "310000"})
    region = response.json()["regions"][0]
    secretary = region["teams"]["party"]["members"][0]
    assert secretary["officer"]["name"] == "李强"
    assert secretary["duration_days"] == 25


def test_region_timeline() -> None:
    response = client.get("/api/v1/regions/310000/timeline")
    assert response.status_code == 200
    body = response.json()
    assert body["region_name"] == "上海市"
    lanes = {lane["category"]: lane for lane in body["lanes"]}
    assert set(lanes) == {"party", "congress", "government", "cppcc"}
    party_names = [span["officer_name"] for span in lanes["party"]["spans"]]
    assert party_names[:2] == ["韩正", "李强"]
    assert lanes["party"]["spans"][0]["duration_days"] > 1000


def test_compare() -> None:
    response = client.get("/api/v1/compare", params={"date": "2024-06-01",
                                                     "regions": "110000,310000,440000"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["regions"]) == 3
    assert [item["region_code"] for item in body["regions"]] == ["110000", "310000", "440000"]


def test_coverage_report() -> None:
    response = client.get("/api/v1/coverage")
    assert response.status_code == 200
    body = response.json()
    assert body["as_of"] == "2026-10-29"
    assert body["provinces_total"] == 31
    assert body["principal_slots"] == 124
    assert body["provinces_complete"] == 31
    assert body["provinces_accounted"] == 31
    assert len(body["vacancies"]) == 0
    assert 0 < body["principal_coverage"] <= 1
    assert len(body["regions"]) == 31


def test_directory_and_filters() -> None:
    response = client.get("/api/v1/directory", params={"page_size": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 200
    assert len(body["items"]) == 5
    assert body["coverage"]["provinces_total"] == 31
    statuses = {item["status"] for item in body["items"]}
    assert statuses

    shanghai = client.get("/api/v1/directory", params={"region": "310000", "page_size": 50})
    assert shanghai.status_code == 200
    assert all(item["region_code"] == "310000" for item in shanghai.json()["items"])


def test_current_roster_snapshot() -> None:
    response = client.get("/api/v1/map/snapshot", params={"date": "2026-10-29",
                                                          "regions": "310000"})
    assert response.status_code == 200
    teams = response.json()["regions"][0]["teams"]
    assert teams["party"]["members"][0]["officer"]["name"] == "陈吉宁"
    governor = teams["government"]["members"][0]
    assert governor["officer"]["name"] == "朱忠明"
    assert governor["is_incumbent"] is True
    assert governor["start_precision"] in {"day", "month", "snapshot"}
    assert governor["rank_label"] == "正省部级"


def test_status_event_expelled() -> None:
    search = client.get("/api/v1/officers", params={"q": "马兴瑞"}).json()
    person = next(item for item in search if item["name"] == "马兴瑞")
    profile = client.get(f"/api/v1/officers/{person['id']}", params={"date": "2026-10-29"})
    assert profile.status_code == 200
    body = profile.json()
    assert body["status"] == "expelled"
    assert any(event["event_type"] == "expelled_from_party" for event in body["events"])


def test_politburo_rank_is_date_aware() -> None:
    """Politburo members are 副国级 even when their post is a provincial
    secretary; the same person is 正省部级 before entering the Politburo."""
    shanghai = client.get("/api/v1/map/snapshot",
                          params={"date": "2026-10-29", "regions": "310000"}).json()
    party = shanghai["regions"][0]["teams"]["party"]["members"][0]
    assert party["officer"]["name"] == "陈吉宁"
    assert party["rank_label"] == "副国级"

    beijing_2019 = client.get("/api/v1/map/snapshot",
                              params={"date": "2019-01-01", "regions": "110000"}).json()
    mayor = beijing_2019["regions"][0]["teams"]["government"]["members"][0]
    assert mayor["officer"]["name"] == "陈吉宁"
    assert mayor["rank_label"] == "正省部级"

    guangdong_2019 = client.get("/api/v1/map/snapshot",
                                params={"date": "2019-01-01", "regions": "440000"}).json()
    li_xi = guangdong_2019["regions"][0]["teams"]["party"]["members"][0]
    assert li_xi["officer"]["name"] == "李希"
    assert li_xi["rank_label"] == "副国级"

    directory = client.get("/api/v1/directory", params={"q": "李希"}).json()
    li_xi_row = next(item for item in directory["items"] if item["name"] == "李希")
    assert li_xi_row["rank_label"] == "正国级"


def test_seat_history_shows_person_status_event() -> None:
    """Expulsion is a person-level event, not the end reason of a tenure that
    ended years earlier. It must still be visible on every seat row."""
    response = client.get("/api/v1/regions/440000/seats/governor/history",
                          params={"date": "2026-10-29"})
    assert response.status_code == 200
    ma = next(span for span in response.json()["spans"]
              if span["officer_name"] == "马兴瑞" and span["start_date"] == "2017-01-01")
    assert ma["event_type"] == "expelled_from_party"
    assert ma["event_label"] == "开除党籍/公职"
    assert ma["event_date"] == "2026-10-29"


def test_date_validation() -> None:
    early = client.get("/api/v1/map/snapshot", params={"date": "2010-01-01"})
    assert early.status_code == 422
    future = client.get("/api/v1/map/snapshot", params={"date": "2999-01-01"})
    assert future.status_code == 422


def test_unknown_region() -> None:
    response = client.get("/api/v1/regions/999999/leaders", params={"date": "2020-01-01"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
