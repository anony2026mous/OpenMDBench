"""Candidate grouped observation metrics on authoritative mission snapshots.

No perception, dynamics, world state or terminal logic is implemented here.
Groups are referee-only cohorts with independent observation windows.
"""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json

MODEL_ID = "models.competition-recon-metrics"
MODEL_VERSION = "1.0.0"
MODEL_REF = f"{MODEL_ID}@{MODEL_VERSION}"
KINDS = {"recall", "coverage", "fresh_fraction", "discovery_timeliness",
         "information_freshness", "nonduplicate_effort", "delivered_recall",
         "delivered_fresh_fraction", "delivered_information_freshness"}


def plain(value):
    if isinstance(value, Mapping):
        if set(value) == {"values"} and isinstance(value["values"], Mapping):
            return plain(value["values"])
        return {key: plain(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(child) for child in value]
    return value


def ids(value):
    return isinstance(value, list) and bool(value) and all(isinstance(v, str) and v for v in value) and len(set(value)) == len(value)


class ReconMetricV1:
    def bind_session(self, *, session_id, seed, parameters):
        del session_id, seed
        p = plain(parameters)
        if set(p) != {"metric_id", "kind", "groups", "maximum_age_ticks", "delivery", "unit"}:
            raise ValueError("recon parameters must match the explicit v1 schema")
        if not isinstance(p["kind"], str) or p["kind"] not in KINDS or p["unit"] != "1" or not isinstance(p["metric_id"], str) or not p["metric_id"]:
            raise ValueError("named dimensionless recon metric required")
        if p["kind"].startswith("delivered_"):
            if not isinstance(p["delivery"], dict) or set(p["delivery"]) != {"recipient_entity_id", "recipient_controller_slot"} or not all(isinstance(v, str) and v for v in p["delivery"].values()):
                raise ValueError("delivered evidence requires an explicit recipient and controller slot")
        elif p["delivery"] is not None:
            raise ValueError("organic observation metrics cannot claim delivered evidence")
        if type(p["maximum_age_ticks"]) is not int or p["maximum_age_ticks"] < 0:
            raise ValueError("maximum contact age must be a nonnegative integer")
        if not isinstance(p["groups"], list) or not p["groups"]:
            raise ValueError("at least one observation group required")
        names = []
        for group in p["groups"]:
            if not isinstance(group, dict) or set(group) != {"group_id", "observer_ids", "item_ids", "start_tick", "end_tick"}:
                raise ValueError("observation group schema mismatch")
            if not isinstance(group["group_id"], str) or not group["group_id"] or not ids(group["observer_ids"]) or not ids(group["item_ids"]):
                raise ValueError("unique named groups, observers and items required")
            if any(type(group[k]) is not int or group[k] < 0 for k in ("start_tick", "end_tick")) or group["end_tick"] <= group["start_tick"]:
                raise ValueError("group windows must be nonempty half-open integer intervals")
            names.append(group["group_id"])
        if len(names) != len(set(names)):
            raise ValueError("duplicate observation group")
        self.parameters = deepcopy(p)
        self.last_tick, self.last_input_hash, self.last_value = -1, None, None
        self.contact_history = {}
        self.groups = {g["group_id"]: {"samples": 0, "contributions": 0, "duplicates": 0,
            "items": {i: {"first_seen_tick": None, "last_observed_tick": None, "fresh_samples": 0, "maximum_gap": 0}
                      for i in g["item_ids"]}} for g in p["groups"]}

    def _history(self, snapshot):
        if self.parameters["delivery"] is None:
            return {}
        tick, age = snapshot.tick, self.parameters["maximum_age_ticks"]
        history = {k: v for k, v in self.contact_history.items() if tick-v["observed_tick"] <= age}
        observers = {o for g in self.parameters["groups"] for o in g["observer_ids"]}
        targets = {i for g in self.parameters["groups"] for i in g["item_ids"]}
        for fact in snapshot.contact_facts:
            if (fact.owner_entity_id in observers and fact.target_entity_id in targets
                and snapshot.entity_states.get(fact.owner_entity_id, {}).get("lifecycle") in {"active", "degraded"}
                and fact.is_valid(expected_tick=tick, owner_entity_id=fact.owner_entity_id)
                and tick-fact.observed_tick <= age):
                key = json.dumps([fact.owner_entity_id, fact.evidence_id, fact.observed_tick])
                history.setdefault(key, {"owner_id": fact.owner_entity_id, "evidence_id": fact.evidence_id,
                    "target_id": fact.target_entity_id, "observed_tick": fact.observed_tick, "recorded_tick": tick})
        return history

    def _delivered(self, snapshot, group, history):
        rows = {i: {} for i in group["item_ids"]}
        recipient = self.parameters["delivery"]
        if snapshot.entity_states.get(recipient["recipient_entity_id"], {}).get("lifecycle") not in {"active", "degraded"}:
            return rows
        for message in snapshot.communications:
            if (message.get("transport_status") != "delivered"
                or message.get("sender_entity_id") not in group["observer_ids"]
                or message.get("recipient_entity_id") != recipient["recipient_entity_id"]
                or recipient["recipient_controller_slot"] not in message.get("recipient_controller_slots", ())):
                continue
            times = [message.get(k) for k in ("generated_tick", "delivered_tick", "expiry_tick")]
            if any(type(t) is not int for t in times) or not 0 <= times[0] <= times[1] <= snapshot.tick <= times[2]:
                continue
            try:
                body = json.loads(message.get("payload", ""))
            except (TypeError, ValueError):
                continue
            if not isinstance(body, dict) or set(body) != {"schema_version", "contacts"} or body["schema_version"] != "competition-contact-report@1.0":
                continue
            reports = body["contacts"]
            if not isinstance(reports, list) or len(reports) > 64:
                continue
            for report in reports:
                if not isinstance(report, dict) or set(report) != {"contact_id", "observed_tick"} or not isinstance(report["contact_id"], str) or type(report["observed_tick"]) is not int:
                    continue
                key = json.dumps([message["sender_entity_id"], report["contact_id"], report["observed_tick"]])
                fact = history.get(key)
                if (fact is None or fact["target_id"] not in rows or fact["recorded_tick"] > times[0]
                    or fact["observed_tick"] < group["start_tick"]
                    or snapshot.tick-fact["observed_tick"] > self.parameters["maximum_age_ticks"]):
                    continue
                seen = rows[fact["target_id"]]
                seen[fact["owner_id"]] = max(fact["observed_tick"], seen.get(fact["owner_id"], -1))
        return rows

    def _input(self, snapshot, history):
        result = {}
        zones = self.parameters["kind"] in {"coverage", "nonduplicate_effort"}
        for group in self.parameters["groups"]:
            rows = {i: {} for i in group["item_ids"]}
            if group["start_tick"] <= snapshot.tick < group["end_tick"]:
                if self.parameters["delivery"] is not None:
                    result[group["group_id"]] = self._delivered(snapshot, group, history)
                    continue
                active = {i for i in group["observer_ids"] if snapshot.entity_states.get(i, {}).get("lifecycle") in {"active", "degraded"}}
                if zones:
                    if not set(rows) <= set(snapshot.zone_activation):
                        raise ValueError("required search-zone activation evidence missing")
                    for observer in active:
                        for item in rows:
                            if snapshot.zone_activation[item] and item in snapshot.zone_membership.get(observer, ()):
                                rows[item][observer] = snapshot.tick
                else:
                    for fact in snapshot.contact_facts:
                        if (fact.owner_entity_id in active and fact.target_entity_id in rows
                            and fact.observed_tick >= group["start_tick"]
                            and fact.is_valid(expected_tick=snapshot.tick, owner_entity_id=fact.owner_entity_id)
                            and snapshot.tick-fact.observed_tick <= self.parameters["maximum_age_ticks"]):
                            evidence = rows[fact.target_entity_id]
                            evidence[fact.owner_entity_id] = max(fact.observed_tick, evidence.get(fact.owner_entity_id, -1))
            result[group["group_id"]] = rows
        return result

    def _value(self):
        # Future windows remain unavailable, not silently omitted from a mean.
        if any(row["samples"] == 0 for row in self.groups.values()):
            return None
        kind, values = self.parameters["kind"].removeprefix("delivered_"), []
        for group in self.parameters["groups"]:
            row = self.groups[group["group_id"]]
            items = list(row["items"].values())
            duration = group["end_tick"]-group["start_tick"]
            if kind in {"recall", "coverage"}:
                value = sum(i["first_seen_tick"] is not None for i in items)/len(items)
            elif kind == "fresh_fraction":
                value = min(i["fresh_samples"]/row["samples"] for i in items)
            elif kind == "discovery_timeliness":
                value = min(0. if i["first_seen_tick"] is None else 1-(i["first_seen_tick"]-group["start_tick"])/duration for i in items)
            elif kind == "information_freshness":
                value = min(max(0., 1-i["maximum_gap"]/duration) for i in items)
            else:
                value = 0. if row["contributions"] == 0 else 1-row["duplicates"]/row["contributions"]
            values.append(value)
        return min(values)

    def evaluate(self, snapshot):
        tick = snapshot.tick
        history = self._history(snapshot)
        evidence = self._input(snapshot, history)
        anchor = hashlib.sha256(json.dumps([tick, evidence, history], sort_keys=True).encode()).hexdigest()
        if tick < self.last_tick:
            raise ValueError("recon metric cannot move backward")
        if tick == self.last_tick:
            if anchor != self.last_input_hash:
                raise ValueError("conflicting recon input for the same tick")
            return {self.parameters["metric_id"]: self.last_value}
        first_start = min(g["start_tick"] for g in self.parameters["groups"])
        if (self.last_tick >= 0 and tick != self.last_tick+1) or (self.last_tick < 0 and tick > first_start):
            raise ValueError("recon metrics require every authoritative tick")
        for group in self.parameters["groups"]:
            if not group["start_tick"] <= tick < group["end_tick"]:
                continue
            row = self.groups[group["group_id"]]
            row["samples"] += 1
            for identifier, contributors in evidence[group["group_id"]].items():
                item = row["items"][identifier]
                if contributors:
                    item["fresh_samples"] += 1
                    if item["first_seen_tick"] is None:
                        item["first_seen_tick"] = tick
                    item["last_observed_tick"] = max(max(contributors.values()), item["last_observed_tick"] or 0)
                age = tick-item["last_observed_tick"] if item["last_observed_tick"] is not None else tick-group["start_tick"]+1
                item["maximum_gap"] = max(item["maximum_gap"], age)
                row["contributions"] += len(contributors)
                row["duplicates"] += max(0, len(contributors)-1)
        self.last_tick, self.last_input_hash = tick, anchor
        self.contact_history = history
        self.last_value = self._value()
        return {self.parameters["metric_id"]: self.last_value}

    def snapshot(self):
        return deepcopy({"parameters": self.parameters, "groups": self.groups,
            "contact_history": self.contact_history,
            "last_tick": self.last_tick, "last_input_hash": self.last_input_hash, "last_value": self.last_value})

    def restore(self, state):
        state = plain(state)
        if set(state) != set(self.snapshot()) or state["parameters"] != self.parameters:
            raise ValueError("recon checkpoint schema/parameters mismatch")
        last = state["last_tick"]
        if type(last) is not int or last < -1 or set(state["groups"]) != set(self.groups):
            raise ValueError("invalid recon checkpoint clock/groups")
        anchor = state["last_input_hash"]
        if ((last == -1 and anchor is not None) or (last >= 0 and
            (not isinstance(anchor, str) or len(anchor) != 64 or not set(anchor) <= set("0123456789abcdef")))):
            raise ValueError("invalid recon input fingerprint")
        if state["last_value"] is not None and (type(state["last_value"]) not in (int, float) or not 0 <= state["last_value"] <= 1):
            raise ValueError("invalid recon checkpoint score")
        observers = {o for g in self.parameters["groups"] for o in g["observer_ids"]}
        targets = {i for g in self.parameters["groups"] for i in g["item_ids"]}
        if not isinstance(state["contact_history"], dict) or (self.parameters["delivery"] is None and state["contact_history"]):
            raise ValueError("invalid contact-history checkpoint")
        for key, fact in state["contact_history"].items():
            if (not isinstance(fact, dict) or set(fact) != {"owner_id", "evidence_id", "target_id", "observed_tick", "recorded_tick"}
                or fact["owner_id"] not in observers or fact["target_id"] not in targets
                or not isinstance(fact["evidence_id"], str) or not fact["evidence_id"]
                or type(fact["observed_tick"]) is not int or type(fact["recorded_tick"]) is not int
                or not 0 <= fact["observed_tick"] <= fact["recorded_tick"] <= last
                or last-fact["observed_tick"] > self.parameters["maximum_age_ticks"]
                or key != json.dumps([fact["owner_id"], fact["evidence_id"], fact["observed_tick"]])):
                raise ValueError("invalid provenance in contact-history checkpoint")
        for group in self.parameters["groups"]:
            row = state["groups"][group["group_id"]]
            expected = max(0, min(last, group["end_tick"]-1)-group["start_tick"]+1)
            if set(row) != {"samples", "contributions", "duplicates", "items"} or type(row["samples"]) is not int or row["samples"] != expected or set(row["items"]) != set(group["item_ids"]):
                raise ValueError("invalid recon sample or item history")
            for key in ("contributions", "duplicates"):
                if type(row[key]) is not int or row[key] < 0:
                    raise ValueError("invalid duplicate-observation counters")
            count = 0
            for item in row["items"].values():
                if set(item) != {"first_seen_tick", "last_observed_tick", "fresh_samples", "maximum_gap"}:
                    raise ValueError("invalid observation history schema")
                for key in ("fresh_samples", "maximum_gap"):
                    if type(item[key]) is not int or not 0 <= item[key] <= expected:
                        raise ValueError("invalid observation counters")
                for key in ("first_seen_tick", "last_observed_tick"):
                    if item[key] is not None and (type(item[key]) is not int or not group["start_tick"] <= item[key] <= min(last, group["end_tick"]-1)):
                        raise ValueError("invalid observation timestamps")
                if (item["fresh_samples"] == 0) != (item["first_seen_tick"] is None) or (item["first_seen_tick"] is None) != (item["last_observed_tick"] is None):
                    raise ValueError("observation timestamps disagree with samples")
                if item["first_seen_tick"] is None:
                    if item["maximum_gap"] != expected:
                        raise ValueError("never-observed information age must cover the entire sampled window")
                else:
                    minimum_gap = max(item["first_seen_tick"]-group["start_tick"],
                                      min(last, group["end_tick"]-1)-item["last_observed_tick"])
                    if item["maximum_gap"] < minimum_gap:
                        raise ValueError("information age contradicts observation timestamps")
                count += item["fresh_samples"]
            if (row["contributions"]-row["duplicates"] != count
                or row["contributions"] > expected*len(group["item_ids"])*len(group["observer_ids"])):
                raise ValueError("duplicate effort disagrees with observed samples")
        previous = self.snapshot()
        self.groups = deepcopy(state["groups"])
        if state["last_value"] != self._value():
            self.groups = previous["groups"]
            raise ValueError("recon checkpoint score disagrees with history")
        self.last_tick, self.last_input_hash, self.last_value = last, state["last_input_hash"], state["last_value"]
        self.contact_history = deepcopy(state["contact_history"])

    def close(self):
        pass
