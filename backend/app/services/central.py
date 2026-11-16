from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from ..core.vocabulary import committee_label, status_label

DATA = Path(__file__).resolve().parent.parent / "data" / "central.json"
DATASET = Path(__file__).resolve().parent.parent / "data" / "dataset.json"
CENTRAL_START = date(2012, 11, 8)
PSC_ORDER = {
    17: ["胡锦涛", "吴邦国", "温家宝", "贾庆林", "李长春", "习近平", "李克强", "贺国强", "周永康"],
    18: ["习近平", "李克强", "张德江", "俞正声", "刘云山", "王岐山", "张高丽"],
    19: ["习近平", "李克强", "栗战书", "汪洋", "王沪宁", "赵乐际", "韩正"],
    20: ["习近平", "李强", "赵乐际", "王沪宁", "蔡奇", "丁薛祥", "李希"],
}


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
            self.term_composition = dataset.get("central_term_composition", {})
        else:
            self.institutions = self.data["institutions"]
            self.memberships = self.data.get("memberships", {})
            self.party_roles = self.data.get("party_roles", {})
            self.terms = {item["ordinal"]: item for item in self.data["terms"]}
            self.term_composition = self.data.get("term_composition", {})
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
            return {
                "term": rec["term"], "term_label": term["label"], "type": rec["type"],
                "status": "active",
                "label": committee_label(rec["term"], rec["type"]),
                "status_label": status_label("identity", "active"),
            }
        ended = [rec for rec in records if rec.get("end") and rec["end"] <= day.isoformat()]
        if not ended:
            return None
        rec = sorted(ended, key=lambda r: (r["term"], r["end"]))[-1]
        term = self.terms[rec["term"]]
        status = rec.get("status", "term_ended")
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
            "status": status, "label": committee_label(rec["term"], rec["type"], ended=True),
            "status_label": status_label("identity", status), "status_note": note,
        }

    def committee_stats(self, day: date) -> dict:
        term = 20 if day >= date(2022, 10, 23) else (
            19 if day >= date(2017, 10, 25) else (
                18 if day >= date(2012, 11, 15) else 17
            )
        )
        composition = self.term_composition.get(str(term), {})
        records = [
            rec for recs in self.memberships.values() for rec in recs
            if rec.get("term") == term
        ]
        active = [
            rec for rec in records
            if rec.get("start") and rec["start"] <= day.isoformat()
            and (not rec.get("end") or day.isoformat() <= rec["end"])
        ]
        members = [rec for rec in active if rec.get("type") == "member"]
        alternates = [rec for rec in active if rec.get("type") == "alternate"]
        all_members = [rec for rec in records if rec.get("type") == "member"]
        all_alternates = [rec for rec in records if rec.get("type") == "alternate"]
        term_start = {
            17: date(2007, 10, 22),
            18: date(2012, 11, 15),
            19: date(2017, 10, 25),
            20: date(2022, 10, 23),
        }[term]
        at_first_plenum = day == term_start

        def status_at(rec: dict) -> str:
            status = rec.get("status", "active")
            if status not in {"expelled", "under_investigation", "resigned", "deceased", "promoted", "removed"}:
                return status
            status_date = rec.get("status_date") or rec.get("end")
            if status_date and day.isoformat() < status_date:
                review_date = rec.get("review_date")
                if review_date and day.isoformat() >= review_date:
                    return "under_investigation"
                return "active"
            return status

        effective_expelled = {id(rec) for rec in all_members if status_at(rec) == "expelled"}
        effective_review = {id(rec) for rec in all_members if status_at(rec) == "under_investigation"}
        effective_resigned = {id(rec) for rec in all_members if status_at(rec) == "resigned"}
        effective_deceased = {id(rec) for rec in all_members if status_at(rec) == "deceased"}
        if at_first_plenum:
            actual_members = members
            actual_alternates = alternates
            effective_expelled = set()
            effective_review = set()
            effective_resigned = set()
            effective_deceased = set()
        else:
            unavailable = effective_expelled | effective_review | effective_resigned | effective_deceased
            actual_members = [rec for rec in members if id(rec) not in unavailable]
            actual_alternates = [
                rec for rec in alternates
                if rec.get("status") not in {"expelled", "under_investigation", "resigned", "deceased"}
                and status_at(rec) not in {"expelled", "under_investigation", "resigned", "deceased"}
            ]
        current_unavailable = {
            id(rec) for rec in members
            if status_at(rec) in {"expelled", "resigned", "deceased"}
        }
        current_members = len(members) - len(current_unavailable)
        initial_records = [rec for rec in all_members if not rec.get("replacement")]
        initial_departed = [
            rec for rec in initial_records
            if status_at(rec) in {"expelled", "resigned", "deceased"}
        ]
        replacement_records = [
            rec for rec in all_members
            if rec.get("replacement") and (not rec.get("start") or rec["start"] <= day.isoformat())
        ]
        expelled_members = len(effective_expelled)
        alternate_20 = {}
        if term == 20:
            promoted_alternates = sum(1 for rec in all_alternates if status_at(rec) == "promoted")
            expelled_alternates = sum(1 for rec in all_alternates if status_at(rec) == "expelled")
            removed_alternates = sum(1 for rec in all_alternates if status_at(rec) == "removed")
            review_alternates = sum(1 for rec in all_alternates if status_at(rec) == "under_investigation")
            departed_alternates = expelled_alternates + removed_alternates
            current_alternates = len(all_alternates) - promoted_alternates - departed_alternates
            alternate_20 = {
                "initial_alternates": len(all_alternates),
                "departed_alternates": departed_alternates,
                "promoted_alternates": promoted_alternates,
                "current_alternates": current_alternates,
                "under_investigation_alternates": review_alternates,
                "alternate_expelled": expelled_alternates,
                "alternate_removed": removed_alternates,
                "initial_alternates_remaining": current_alternates,
                "actual_alternates": current_alternates - review_alternates,
            }
        term_info = self.terms.get(term, {})
        return {
            "term": term,
            "term_label": term_info.get("label", f"{term}届"),
            "elected_members": composition.get("members"),
            "elected_alternates": composition.get("alternates"),
            "initial_members": len(initial_records),
            "departed_members": len(initial_departed),
            "replacement_members": len(replacement_records),
            "initial_members_remaining": len(initial_records) - len(initial_departed),
            "member_list_collected": len(all_members),
            "alternate_list_collected": len(all_alternates),
            **alternate_20,
            "recorded_members": len(all_members),
            "recorded_alternates": len(all_alternates),
            "active_members": len(members),
            "current_members": current_members,
            "actual_members": len(actual_members),
            "actual_alternates": alternate_20.get("actual_alternates", len(actual_alternates)),
            "actual_total": len(actual_members) + alternate_20.get("actual_alternates", len(actual_alternates)),
            "expelled_members": expelled_members,
            "expelled_alternates": alternate_20.get("alternate_expelled", len(alternates) - len(actual_alternates)),
            "resigned_members": len(effective_resigned),
            "deceased_members": len(effective_deceased),
            "under_investigation": len(effective_review),
            "recorded_total": len(all_members) + len(alternates),
        }

    def committee_members(self, day: date) -> dict:
        stats = self.committee_stats(day)
        term = stats["term"]
        records = [
            (name, rec)
            for name, recs in self.memberships.items() for rec in recs
            if rec.get("term") == term and rec.get("type") == "member"
        ]
        seen: set[str] = set()
        members = []
        for name, rec in records:
            if not name or name in seen:
                continue
            if rec.get("start") and rec["start"] > day.isoformat():
                continue
            seen.add(name)
            person = next(
                (item for item in self._people.values() if item.get("name") == name),
                {},
            )
            officer_id = next(
                (int(pid) for pid, item in self._people.items() if item.get("name") == name),
                person.get("id"),
            )
            status = rec.get("status", "active")
            status_date = rec.get("status_date") or rec.get("end")
            if status in {"expelled", "under_investigation", "resigned", "deceased"} and status_date and day.isoformat() < status_date:
                review_date = rec.get("review_date")
                status = "under_investigation" if review_date and day.isoformat() >= review_date else "active"
            if status == "expelled" and rec.get("end") and rec["end"] > day.isoformat():
                status = "active"
            status_label = {
                "active": "在任",
                "expelled": "已开除",
                "resigned": "已辞职",
                "deceased": "已逝世",
                "term_ended": "任期结束",
                "under_investigation": "审查中",
            }.get(status, status)
            members.append({
                "name": name,
                "type": rec.get("type", "member"),
                "officer_id": officer_id,
                "initial": not bool(rec.get("replacement")),
                "replacement": bool(rec.get("replacement")),
                "status": status,
                "status_label": status_label,
                "birth_year": person.get("birth_year"),
                "native_place": person.get("native_place"),
                "gender": person.get("gender"),
                "ethnicity": person.get("ethnicity"),
                "party_join_date": person.get("party_join_date"),
            })
        members.sort(key=lambda item: item["name"])
        return {
            "term": term,
            "term_label": stats["term_label"],
            "members": members,
        }

    def committee_alternates(self, day: date) -> dict:
        stats = self.committee_stats(day)
        term = stats["term"]
        rows = []
        seen: set[str] = set()
        for name, recs in self.memberships.items():
            for rec in recs:
                if rec.get("term") != term or rec.get("type") != "alternate":
                    continue
                if rec.get("start") and rec["start"] > day.isoformat():
                    continue
                if name in seen:
                    continue
                seen.add(name)
                person = next(
                    (item for item in self._people.values() if item.get("name") == name),
                    {},
                )
                officer_id = next(
                    (int(pid) for pid, item in self._people.items() if item.get("name") == name),
                    person.get("id"),
                )
                status = rec.get("status", "active")
                status_date = rec.get("status_date") or rec.get("end")
                if status in {"expelled", "under_investigation", "removed", "promoted"} and status_date and day.isoformat() < status_date:
                    review_date = rec.get("review_date")
                    status = "under_investigation" if review_date and day.isoformat() >= review_date else "active"
                rows.append({
                    "name": name,
                    "type": "alternate",
                    "officer_id": officer_id,
                    "initial": not bool(rec.get("replacement")),
                    "replacement": bool(rec.get("replacement")),
                    "status": status,
                    "status_label": {
                        "active": "在任",
                        "expelled": "已开除",
                        "resigned": "已辞职",
                        "deceased": "已逝世",
                        "under_investigation": "审查中",
                        "promoted": "已递补",
                        "removed": "已撤职",
                    }.get(status, status),
                    "birth_year": person.get("birth_year"),
                    "native_place": person.get("native_place"),
                    "gender": person.get("gender"),
                    "ethnicity": person.get("ethnicity"),
                    "party_join_date": person.get("party_join_date"),
                })
        rows.sort(key=lambda item: item["name"])
        return {"term": term, "term_label": stats["term_label"], "members": rows}

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
                identity_day = day.isoformat() if day is not None else start
                for identity in self._identities_by_person.get(int(tenure["officer_id"]), []):
                    if identity.get("start_date", "") <= identity_day and (
                        not identity.get("end_date") or identity_day <= identity["end_date"]
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
                else:
                    seen_roles = {(item.get("term"), item.get("role")) for item in identities}
                    for extra in meta.get("party_roles", []):
                        key = (extra.get("term"), extra.get("role"))
                        if key not in seen_roles:
                            identities.append(extra)
                            seen_roles.add(key)
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
        psc_order: dict[str, int] = {}
        if inst["id"] in {"party:politburo_standing", "party:politburo"}:
            for row in rows:
                term = 20 if row["start_date"] >= "2022-10-23" else (
                    19 if row["start_date"] >= "2017-10-25" else (
                        18 if row["start_date"] >= "2012-11-15" else 17
                    )
                )
                psc_order.update({
                    name: index for index, name in enumerate(PSC_ORDER.get(term, []))
                })
        rows.sort(key=lambda row: (
            0 if inst["id"] == "party:politburo_standing" else 1,
            psc_order.get(row["name"], 1000),
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
        elected_members = self._elected_members(inst, day)
        roster_members = self._roster_members(elected_members, leaders)
        composition = self._composition(inst, elected_members, leaders)
        membership_changes = self._membership_changes(
            inst,
            elected_members or [],
            leaders,
        )
        return {
            **inst,
            "leaders": leaders,
            "leader": leaders[0] if leaders else None,
            "status_at": status_at,
            **({"elected_members": elected_members} if elected_members is not None else {}),
            **({"roster_members": roster_members} if roster_members is not None else {}),
            **({"composition": composition} if composition is not None else {}),
            **({"membership_changes": membership_changes} if membership_changes is not None else {}),
        }

    def _composition(
        self,
        inst: dict,
        elected: list[dict] | None,
        current: list[dict],
    ) -> dict | None:
        if inst.get("id") not in {
            "party:politburo_standing",
            "party:politburo",
            "party:secretariat",
        } or not elected:
            return None
        initial = len(elected)
        elected_names = {row.get("name") for row in elected}
        current_names = {row.get("name") for row in current}
        removed = len(elected_names - current_names)
        added = len(current_names - elected_names)
        return {
            "initial": initial,
            "removed": removed,
            "added": added,
            "current": len(current),
            "display": str(len(current)),
        }

    def _roster_members(
        self,
        elected: list[dict] | None,
        current: list[dict],
    ) -> list[dict] | None:
        if elected is None:
            return None
        rows = [dict(row) for row in elected]
        elected_names = {row.get("name") for row in elected}
        for row in current:
            name = row.get("name")
            if name and name not in elected_names:
                rows.append({
                    **row,
                    "member_status": "added",
                    "member_status_label": "新增选",
                })
        return rows

    def _membership_changes(
        self,
        inst: dict,
        elected: list[dict],
        current: list[dict],
    ) -> list[dict] | None:
        if inst.get("id") not in {
            "party:politburo_standing",
            "party:politburo",
            "party:secretariat",
        }:
            return None
        elected_names = {row.get("name") for row in elected}
        current_names = {row.get("name") for row in current}
        removed = elected_names - current_names
        added = current_names - elected_names
        if not removed and not added:
            return []
        event_labels = {
            "2024-07-18": "二十届三中全会",
            "2025-10-23": "二十届四中全会",
            "2026-10-29": "二十届五中全会",
        }
        groups: dict[tuple[str, str], list[str]] = {}
        for name in removed:
            record = next(
                (
                    item for item in self.memberships.get(name, [])
                    if item.get("term") == 20 and item.get("type") == "member"
                ),
                None,
            )
            event_date = (
                (record or {}).get("status_date")
                or (record or {}).get("end")
                or ""
            )
            event = event_labels.get(event_date, event_date or "本届任期内")
            groups.setdefault((event, "removed"), []).append(name)
        current_by_name = {row.get("name"): row for row in current}
        for name in added:
            event_date = (current_by_name.get(name) or {}).get("start_date", "")
            event = event_labels.get(event_date, event_date or "本届任期内")
            groups.setdefault((event, "added"), []).append(name)
        order = {
            "二十届三中全会": 0,
            "二十届四中全会": 1,
            "二十届五中全会": 2,
        }
        result = []
        for (event, change_type), names in groups.items():
            result.append({
                "event": event,
                "change_type": change_type,
                "label": f"{event}{'除名' if change_type == 'removed' else '增选'}",
                "members": sorted(names),
            })
        result.sort(key=lambda item: (
            order.get(item["event"], 99),
            0 if item["change_type"] == "removed" else 1,
        ))
        return result

    def _elected_members(self, inst: dict, day: date) -> list[dict] | None:
        elected_ids = {
            "party:politburo_standing",
            "party:politburo",
            "party:secretariat",
        }
        if inst.get("id") not in elected_ids:
            return None
        rows = [
            row for row in (inst.get("leaders") or self._dataset_leaders(inst))
            if row.get("start_date") == "2022-10-23"
        ]
        result: list[dict] = []
        seen: set[str] = set()
        for row in rows:
            name = row.get("name") or ""
            if not name or name in seen:
                continue
            seen.add(name)
            committee = self.committee(name, day)
            status = committee.get("status") if committee else "active"
            status_label = {
                "expelled": "已开除",
                "resigned": "已辞职",
                "deceased": "已逝世",
                "under_investigation": "审查中",
            }.get(status or "active", "")
            result.append({
                **row,
                "member_status": status or "active",
                "member_status_label": status_label,
            })
        return result

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
            if inst_id == "party:general_secretary":
                seat_title = inst_name
            elif not seat_title.startswith(inst_name):
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
        return {
            **self._decorate(inst, day),
            "history": history,
            "leader_history": inst.get("leaders", []),
            "seats": list(seat_map.values()),
            **({"committee_stats": self.committee_stats(day),
                 "committee_members": self.committee_members(day),
                 "committee_alternates": self.committee_alternates(day)}
               if inst_id == "party:central_committee" else {}),
        }


central_service = CentralService()
