"""Candidate tracking-history model on native mission facts, not an agent oracle.

Scoring is referee-side. It does not expose target IDs or future events to agents,
and it does not replace native perception, communications or terminal rules.
Observer-group transfers measure sensor responsibility, not completed transport.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

MODEL_ID = "models.competition-tracking-metrics"
MODEL_VERSION = "1.0.1"
MODEL_REF = f"{MODEL_ID}@{MODEL_VERSION}"


def _ids(values):
    return (isinstance(values, (tuple, list)) and bool(values)
            and all(isinstance(v, str) and v for v in values) and len(set(values)) == len(values))


class TrackingMetricV1:
    def bind_session(self, *, session_id, seed, parameters):
        del session_id, seed
        p = deepcopy(parameters)
        for field in ("observer_groups", "handover_edges", "reacquisition_events"):
            if isinstance(p.get(field), (tuple, list)):
                p[field] = [r["values"] if isinstance(r, dict) and set(r) == {"values"} else r for r in p[field]]
        if set(p) != {"metric_id", "kind", "observer_ids", "target_ids", "observer_groups",
                      "handover_edges", "reacquisition_events", "start_tick", "end_tick",
                      "maximum_age_ticks", "maximum_gap_ticks", "unit"}:
            raise ValueError("tracking parameters must match the explicit v1 schema")
        if p["kind"] not in {"continuity", "gap_compliance", "handover_fraction", "reacquisition_fraction", "freshness"}:
            raise ValueError("unsupported tracking metric")
        if p["unit"] != "1" or not isinstance(p["metric_id"], str) or not p["metric_id"]:
            raise ValueError("dimensionless named tracking metric required")
        if not _ids(p["observer_ids"]) or not _ids(p["target_ids"]):
            raise ValueError("unique nonempty observer and target IDs required")
        for field in ("start_tick", "end_tick", "maximum_age_ticks", "maximum_gap_ticks"):
            if type(p[field]) is not int or p[field] < 0:
                raise ValueError("tracking windows and limits must be nonnegative integers")
        if p["start_tick"] >= p["end_tick"]:
            raise ValueError("empty tracking score interval")
        groups = p["observer_groups"]
        if not isinstance(groups, list) or not groups or not _ids([g.get("group_id") for g in groups]):
            raise ValueError("named observer groups required")
        members = []
        for g in groups:
            if set(g) != {"group_id", "observer_ids"} or not _ids(g["observer_ids"]):
                raise ValueError("invalid observer group")
            members.extend(g["observer_ids"])
        if set(members) != set(p["observer_ids"]) or len(members) != len(set(members)):
            raise ValueError("observer groups must partition the authorized observers")
        names = {g["group_id"] for g in groups}
        edges = p["handover_edges"]
        if not isinstance(edges, list) or len({(e.get("from_group"), e.get("to_group")) for e in edges}) != len(edges):
            raise ValueError("handover edges must be unique")
        for e in edges:
            if (set(e) != {"from_group", "to_group", "minimum_count"}
                    or e["from_group"] not in names or e["to_group"] not in names
                    or e["from_group"] == e["to_group"]
                    or type(e["minimum_count"]) is not int or e["minimum_count"] < 1):
                raise ValueError("invalid directed handover requirement")
        reacquire = p["reacquisition_events"]
        if not isinstance(reacquire, list):
            raise ValueError("reacquisition events must be a sequence")
        if reacquire and not _ids([e.get("event_id") for e in reacquire]):
            raise ValueError("reacquisition events must be unique")
        for e in reacquire:
            if set(e) != {"event_id", "deadline_ticks"} or type(e["deadline_ticks"]) is not int or e["deadline_ticks"] < 0:
                raise ValueError("invalid reacquisition window")
        if p["kind"] == "handover_fraction" and not edges:
            raise ValueError("handover metric requires actual directed transfers")
        if p["kind"] == "reacquisition_fraction" and not reacquire:
            raise ValueError("reacquisition metric requires actual event windows")
        self.parameters = p
        # Before the declared window there is no measurement. Preserve N/A;
        # a native checkpoint limitation must not turn absence into zero.
        self.last_tick, self.last_input_hash, self.last_value = -1, None, None
        self.samples = 0
        self.targets = {t: {"seen_ticks": 0, "gap_ticks": 0, "longest_gap_ticks": 0,
            "age_total": 0, "owner_group": None, "last_contact_tick": None,
            "handover_counts": {}, "handover_gaps": []} for t in p["target_ids"]}
        self.event_windows = {}

    def evaluate(self, snapshot):
        p, tick = self.parameters, snapshot.tick
        active = {i for i in p["observer_ids"]
                  if snapshot.entity_states.get(i, {}).get("lifecycle") in {"active", "degraded"}}
        fresh = {t: {} for t in p["target_ids"]}
        for fact in snapshot.contact_facts:
            age = tick - fact.observed_tick
            if (fact.owner_entity_id in active and fact.target_entity_id in fresh
                    and 0 <= age <= p["maximum_age_ticks"]
                    and fact.is_valid(expected_tick=tick, owner_entity_id=fact.owner_entity_id)):
                previous = fresh[fact.target_entity_id].get(fact.owner_entity_id, age)
                fresh[fact.target_entity_id][fact.owner_entity_id] = min(previous, age)
        events = sorted(set(snapshot.event_ids) & {e["event_id"] for e in p["reacquisition_events"]})
        anchor = hashlib.sha256(json.dumps([tick, fresh, events], sort_keys=True).encode()).hexdigest()
        if tick < self.last_tick:
            raise ValueError("tracking metric cannot move backwards without restore")
        if tick == self.last_tick:
            if anchor != self.last_input_hash:
                raise ValueError("conflicting tracking evidence at the same tick")
            return {p["metric_id"]: self.last_value}
        first = max(p["start_tick"], self.last_tick + 1)
        if tick > first and first < p["end_tick"]:
            raise ValueError("tracking requires every authoritative scoring tick")
        if p["start_tick"] <= tick < p["end_tick"]:
            self.samples += 1
            for event_id in events:
                self.event_windows.setdefault(event_id, {"start_tick": tick, "reacquired": {}})
            for target, owners in fresh.items():
                state = self.targets[target]
                if not owners:
                    state["gap_ticks"] += 1
                    state["longest_gap_ticks"] = max(state["longest_gap_ticks"], state["gap_ticks"])
                    continue
                groups = [g["group_id"] for g in p["observer_groups"] if set(g["observer_ids"]) & set(owners)]
                current = state["owner_group"] if state["owner_group"] in groups else groups[0]
                previous = state["owner_group"]
                if previous is not None and current != previous:
                    edge = f"{previous}->{current}"
                    state["handover_counts"][edge] = state["handover_counts"].get(edge, 0) + 1
                    state["handover_gaps"].append(state["gap_ticks"])
                state["owner_group"] = current
                state["seen_ticks"] += 1
                state["age_total"] += min(owners.values())
                state["last_contact_tick"] = tick
                state["gap_ticks"] = 0
                for spec in p["reacquisition_events"]:
                    window = self.event_windows.get(spec["event_id"])
                    if window is not None and target not in window["reacquired"]:
                        if tick - window["start_tick"] <= spec["deadline_ticks"]:
                            window["reacquired"][target] = tick - window["start_tick"]
            if p["kind"] == "continuity":
                self.last_value = min(s["seen_ticks"] for s in self.targets.values()) / self.samples
            elif p["kind"] == "gap_compliance":
                self.last_value = float(all(s["longest_gap_ticks"] <= p["maximum_gap_ticks"] for s in self.targets.values()))
            elif p["kind"] == "handover_fraction":
                self.last_value = min(min(1., s["handover_counts"].get(f"{e['from_group']}->{e['to_group']}", 0) / e["minimum_count"])
                                      for s in self.targets.values() for e in p["handover_edges"])
            elif p["kind"] == "reacquisition_fraction":
                self.last_value = sum(len(w["reacquired"]) for w in self.event_windows.values()) / (len(p["reacquisition_events"]) * len(self.targets))
            else:
                self.last_value = min((s["seen_ticks"] - s["age_total"] / (p["maximum_age_ticks"] + 1)) / self.samples for s in self.targets.values())
        self.last_tick, self.last_input_hash = tick, anchor
        return {p["metric_id"]: self.last_value}

    def snapshot(self):
        return deepcopy({k: getattr(self, k) for k in ("parameters", "last_tick",
            "last_input_hash", "last_value", "samples", "targets", "event_windows")})

    def restore(self, state):
        if set(state) != set(self.snapshot()) or state["parameters"] != self.parameters:
            raise ValueError("tracking checkpoint schema or parameters differ")
        p = self.parameters
        if type(state["last_tick"]) is not int or state["last_tick"] < -1:
            raise ValueError("invalid checkpoint tick")
        expected = max(0, min(state["last_tick"], p["end_tick"]-1)-p["start_tick"]+1)
        if type(state["samples"]) is not int or state["samples"] != expected or set(state["targets"]) != set(self.targets):
            raise ValueError("tracking checkpoint samples or target identities differ")
        if expected == 0 and state["last_value"] is not None:
            raise ValueError("unmeasured tracking checkpoint value must remain unavailable")
        if expected > 0 and (type(state["last_value"]) not in (int, float) or not 0 <= state["last_value"] <= 1):
            raise ValueError("measured tracking checkpoint value must be a finite fraction")
        for target, history in state["targets"].items():
            if set(history) != set(self.targets[target]):
                raise ValueError("invalid target history schema")
            for key in ("seen_ticks", "gap_ticks", "longest_gap_ticks"):
                if type(history[key]) is not int or not 0 <= history[key] <= expected:
                    raise ValueError("invalid target history counters")
            if history["gap_ticks"] > history["longest_gap_ticks"] or history["seen_ticks"] + history["gap_ticks"] > expected:
                raise ValueError("inconsistent target history")
        if not set(state["event_windows"]) <= {e["event_id"] for e in p["reacquisition_events"]}:
            raise ValueError("checkpoint contains undeclared reacquisition event")
        for key, value in state.items():
            setattr(self, key, deepcopy(value))

    def close(self):
        pass
