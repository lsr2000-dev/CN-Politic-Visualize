from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parent.parent / "data" / "central.json"
DATASET = Path(__file__).resolve().parent.parent / "data" / "dataset.json"
CENTRAL_START = date(2012, 11, 8)


class CentralService:
    def __init__(self) -> None:
        self._central_mtime = 0.0
        self._load_structure()
        self._people_mtime = 0.0
        self._people: dict[int, dict] = {}
        self._positions_by_inst: dict[str, list[dict]] = {}
        self._tenures_by_position: dict[int, list[dict]] = {}
        self._positions_by_id: dict[int, dict] = {}
        self._identities_by_person: dict[int, list[dict]] = {}

    def _load_structure(self) -> None:
        self.data = json.loads(DATA.read_text(encoding="utf-8"))
        dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        organizations = dataset.get("organizations")
        if organizations:
            self.institutions: list[dict[str, Any]] = organizations
            self.memberships = dataset.get("central_memberships", {})
            self.party_roles = dataset.get("central_party_roles", {})
            self.terms = {item["ordinal"]: item for item in dataset.get("central_terms", [])}
        else:
            self.institutions = self.data["institutions"]
            self.memberships = self.data.get("memberships", {})
            self.party_roles = self.data.get("party_roles", {})
            self.terms = {item["ordinal"]: item for item in self.data["terms"]}
        self.by_id = {item["id"]: item for item in self.institutions}
        self._central_mtime = max(DATA.stat().st_mtime, DATASET.stat().st_mtime)

    def _reload_structure(self) -> None:
        if max(DATA.stat().st_mtime, DATASET.stat().st_mtime) != self._central_mtime:
            self._load_structure()

    def _reload_dataset(self) -> None:
        mtime = DATASET.stat().st_mtime
        if mtime == self._people_mtime:
            return
        data = json.loads(DATASET.read_text(encoding="utf-8"))
        self._people = {int(officer["id"]): officer for officer in data.get("officers", [])}
        self._positions_by_id = {
            int(position["id"]): position for position in data.get("positions", [])
        }
        self._positions_by_inst = {}
        for position in self._positions_by_id.values():
            seat_key = str(position.get("seat_key", ""))
            if not seat_key.startswith("central:"):
                continue
            seat = seat_key[len("central:"):]
            inst_id = seat.rsplit(":seat:", 1)[0].rstrip(":")
            if inst_id:
                self._positions_by_inst.setdefault(inst_id, []).append(position)
        self._tenures_by_position = {}
        for tenure in data.get("tenures", []):
            self._tenures_by_position.setdefault(int(tenure["position_id"]), []).append(tenure)
        self._identities_by_person = {}
        for identity in data.get("identities", []):
            self._identities_by_person.setdefault(int(identity["person_id"]), []).append(identity)
        self._people_mtime = mtime

    def _canonical_people(self) -> dict[int, dict]:
        self._reload_dataset()
        return self._people

    def _person_fields(self, leader: dict) -> dict:
        person = self._canonical_people().get(int(leader.get("officer_id") or 0))
        if not person:
            return leader
        return {
            **leader,
            "name": person.get("name", leader.get("name")),
            "birth_year": person.get("birth_year"),
            "native_place": person.get("native_place"),
            "gender": person.get("gender"),
            "ethnicity": person.get("ethnicity"),
            "bio": person.get("bio"),
        }

    def _active(self, item: dict, day: date) -> bool:
        start = item.get("start_date")
        end = item.get("end_date")
        return bool(start and start <= day.isoformat() and (not end or day.isoformat() <= end))

    def party_roles_for(self, name: str) -> list[dict]:
        return list(self.party_roles.get(name, []))

    def committee(self, name: str, day: date) -> dict | None:
        records = self.memberships.get(name) or []
        if not records:
            return None
        active = [
            rec for rec in records
            if rec.get("start") and rec["start"] <= day.isoformat()
            and (not rec.get("end") or day.isoformat() < rec["end"])
        ]
        if active:
            rec = sorted(active, key=lambda r: r["term"])[-1]
            term = self.terms[rec["term"]]
            kind = "候补委员" if rec["type"] == "alternate" else "委员"
            return {
                "term": rec["term"], "term_label": term["label"], "type": rec["type"],
                "status": "active", "label": f"{term['label']}中央{kind}", "status_label": "在任",
            }
        ended = [rec for rec in records if rec.get("end") and rec["end"] <= day.isoformat()]
        if not ended:
            return None
        rec = sorted(ended, key=lambda r: (r["term"], r["end"]))[-1]
        term = self.terms[rec["term"]]
        kind = "候补委员" if rec["type"] == "alternate" else "委员"
        status = rec.get("status", "term_ended")
        labels = {"expelled": "已开除", "retired": "已退休", "deceased": "已故",
                  "term_ended": "任期结束", "resigned": "已辞职"}
        term_end = term.get("end")
        if status == "expelled":
            note = "因严重违纪违法被开除党籍，其中央委员/候补委员资格终止。"
        elif status == "term_ended":
            note = (
                f"{term['label']}中央委员会任期至 {term_end}，所选时点已超过该届任期，"
                "因此显示为“原…”，不是被开除。"
            )
        elif status == "retired":
            note = "该官员已退休，所选时点不再担任本届中央委员/候补委员。"
        elif status == "deceased":
            note = "该官员已故，所选时点不再担任本届中央委员/候补委员。"
        else:
            note = "所选时点该官员已不再担任本届中央委员/候补委员。"
        return {
            "term": rec["term"], "term_label": term["label"], "type": rec["type"],
            "status": status, "label": f"原{term['label']}中央{kind}",
            "status_label": labels.get(status, "已离任"), "status_note": note,
        }

    def _metadata(self, inst: dict) -> dict[tuple[str, str, str], dict]:
        metadata: dict[tuple[str, str, str], dict] = {}
        for leader in inst.get("leaders", []):
            seat_id = leader.get("seat_id")
            if seat_id:
                metadata[(seat_id, leader.get("start_date", ""), leader.get("name", ""))] = leader
        return metadata

    def _metadata_by_name(self, inst: dict) -> dict[tuple[str, str], dict]:
        metadata: dict[tuple[str, str], dict] = {}
        for leader in inst.get("leaders", []):
            seat_id = leader.get("seat_id")
            name = leader.get("name")
            if seat_id and name:
                previous = metadata.get((seat_id, name))
                if previous is None or leader.get("start_date", "") >= previous.get("start_date", ""):
                    metadata[(seat_id, name)] = leader
        return metadata

    def _dataset_leaders(self, inst: dict, day: date | None = None) -> list[dict]:
        self._reload_dataset()
        positions = self._positions_by_inst.get(inst["id"], [])
        if not positions:
            return []
        metadata = self._metadata(inst)
        metadata_by_name = self._metadata_by_name(inst)
        metadata_order: dict[tuple[str, str], int] = {}
        for index, leader in enumerate(inst.get("leaders", [])):
            seat_id = leader.get("seat_id")
            if seat_id:
                metadata_order[(seat_id, leader.get("name", ""))] = index
        rows: list[dict] = []
        for position in positions:
            seat_key = str(position.get("seat_key", ""))
            seat_id = seat_key[len("central:"):] if seat_key.startswith("central:") else seat_key
            for tenure in self._tenures_by_position.get(int(position["id"]), []):
                start = str(tenure.get("start_date") or "")
                end = str(tenure["end_date"]) if tenure.get("end_date") else None
                if day is not None and not self._active(tenure, day):
                    continue
                person = self._people.get(int(tenure["officer_id"]), {})
                meta = (
                    metadata.get((seat_id, start, person.get("name", "")))
                    or metadata_by_name.get((seat_id, person.get("name", "")))
                    or {}
                )
                identities = []
                for identity in self._identities_by_person.get(int(tenure["officer_id"]), []):
                    if identity.get("start_date", "") <= start and (
                        not identity.get("end_date") or start <= identity["end_date"]
                    ):
                        term = identity.get("term")
                        identities.append({
                            "term": term,
                            "term_label": identity.get("term_label") or f"{term}届",
                            "role": identity.get("role"),
                            "label": identity.get("label"),
                            "status": "active",
                        })
                if not identities:
                    identities = meta.get("party_roles", [])
                title = meta.get("title") or position.get("title") or position.get("full_title", "")
                if not meta and title.startswith(inst.get("name", "")):
                    title = title[len(inst.get("name", "")):] or title
                rows.append({
                    "name": person.get("name", meta.get("name", "")),
                    "title": title,
                    "seat_id": seat_id,
                    "position_uid": position.get("position_uid", seat_id),
                    "start_date": start,
                    "end_date": end,
                    "seat_type": meta.get("seat_type") or "principal",
                    "officer_id": int(tenure["officer_id"]),
                    "birth_year": person.get("birth_year"),
                    "native_place": person.get("native_place"),
                    "gender": person.get("gender"),
                    "ethnicity": person.get("ethnicity"),
                    "bio": person.get("bio"),
                    "party_roles": identities,
                    "primary_post": meta.get("primary_post"),
                    "concurrent_titles": meta.get("concurrent_titles", []),
                    "rank_override": meta.get("rank_override"),
                })
        rows.sort(key=lambda row: (
            metadata_order.get((row["seat_id"], row["name"]), 10_000),
            row["start_date"],
            row["name"],
        ))
        if day is None:
            merged: list[dict] = []
            for row in rows:
                previous = merged[-1] if merged else None
                if (
                    previous
                    and previous["seat_id"] == row["seat_id"]
                    and previous["name"] == row["name"]
                    and previous.get("end_date")
                ):
                    previous_end = date.fromisoformat(previous["end_date"])
                    current_start = date.fromisoformat(row["start_date"])
                    if (current_start - previous_end).days <= 1:
                        previous["end_date"] = row.get("end_date")
                        continue
                merged.append(row)
            rows = merged
        return rows

    def _leaders(self, inst: dict, day: date) -> list[dict]:
        out = self._dataset_leaders(inst, day)
        for leader in out:
            leader["central_committee"] = self.committee(leader["name"], day)
        return out

    def _decorate(self, inst: dict, day: date) -> dict:
        leaders = self._leaders(inst, day)
        valid_from = inst.get("valid_from")
        valid_to = inst.get("valid_to")
        status_at = "active"
        if valid_from and day.isoformat() < valid_from:
            status_at = "not_yet"
        elif valid_to and day.isoformat() > valid_to:
            status_at = "abolished"
        return {
            **inst,
            "leaders": leaders,
            "leader": leaders[0] if leaders else None,
            "status_at": status_at,
        }

    def _is_real(self, inst: dict) -> bool:
        kind = inst.get("institution_type", "")
        return kind != "group" and not kind.endswith("_group")

    def _exists(self, inst: dict, day: date) -> bool:
        valid_from = inst.get("valid_from")
        valid_to = inst.get("valid_to")
        return (not valid_from or valid_from <= day.isoformat()) and (
            not valid_to or day.isoformat() <= valid_to
        )

    def overview(self, day: date) -> dict:
        self._reload_structure()
        teams: dict[str, dict] = {}
        roots = {
            "party": "party:central_committee",
            "congress": "congress:npc",
            "government": "government:state_council",
            "cppcc": "cppcc:committee",
        }
        for team, root_id in roots.items():
            meta = self.data["teams"][team]
            root = self._decorate(self.by_id[root_id], day)
            items = [i for i in self.institutions if i["team"] == team and self._is_real(i)]
            teams[team] = {
                "key": team, "label": meta["label"], "short": meta["short"],
                "color": meta["color"], "count": len(items),
                "leader": root.get("leader"),
            }
        others = []
        for key, label in (("judicial", "两高"), ("mass", "群团"), ("military", "军委"),
                           ("supervision", "纪委监委"), ("deliberative", "议事协调")):
            items = [i for i in self.institutions if i["team"] == "other"
                     and i["group_type"] == key and self._is_real(i)]
            others.append({"key": key, "label": label, "count": len(items),
                           "color": self.data["teams"]["other"]["color"]})
        required = [
            self._decorate(i, day) for i in self.institutions
            if self._is_real(i) and i.get("principal_required", True) and self._exists(i, day)
        ]
        filled = [i for i in required if i.get("leader")]
        return {
            "as_of": day.isoformat(),
            "coverage_start": self.data["coverage_start"],
            "team_coverage": self.data.get("team_coverage", {}),
            "teams": teams,
            "other": others,
            "coverage": {
                "required": len(required),
                "filled": len(filled),
                "missing": len(required) - len(filled),
                "ratio": round(len(filled) / len(required), 4) if required else 1.0,
            },
        }

    def org(self, team: str, day: date) -> dict:
        self._reload_structure()
        if team not in {"party", "congress", "government", "cppcc", "other"}:
            raise KeyError(team)
        items = [
            self._decorate(inst, day)
            for inst in self.institutions
            if inst["team"] == team
        ]
        items.sort(key=lambda i: (i["sort_order"], i["name"]))
        return {"team": team, "as_of": day.isoformat(), "institutions": items}

    def institution(self, inst_id: str, day: date) -> dict:
        self._reload_structure()
        inst = self.by_id[inst_id]
        history = self._dataset_leaders(inst)
        for leader in history:
            leader["central_committee"] = self.committee(
                leader["name"],
                date.fromisoformat(leader["end_date"]) if leader.get("end_date") else day,
            )
        seat_map: dict[str, dict] = {}
        for leader in history:
            inst_name = inst.get("name", "")
            seat_title = leader["title"]
            if not seat_title.startswith(inst_name):
                seat_title = f"{inst_name}{seat_title}"
            seat_key = leader.get("seat_id") or seat_title
            seat = seat_map.setdefault(seat_key, {
                "id": seat_key,
                "title": seat_title,
                "is_principal": leader.get("seat_type") in {"principal", "minister"},
                "leaders": [],
                "history": [],
            })
            seat["history"].append(leader)
            if self._active(leader, day):
                seat["leaders"].append(leader)
        return {**self._decorate(inst, day), "history": history, "seats": list(seat_map.values())}


central_service = CentralService()
