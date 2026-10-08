"""Candidate generic dispatch metrics on native mission facts, never a simulator.

Arrival is a navigation proxy, NOT rescue. Request release and hazard activation
consume applied native event IDs; future event contents are never agent inputs.
Registration is local opt-in pending independent review and competition gates.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re

MODEL_ID = "models.competition-dispatch-metrics"
MODEL_VERSION = "1.0.0"
MODEL_REF = f"{MODEL_ID}@{MODEL_VERSION}"


def _ids(value, name):
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{name} must contain IDs")
    if any(not isinstance(v, str) or not v for v in value) or len(set(value)) != len(value):
        raise ValueError(f"{name} must contain unique nonempty IDs")


class DispatchMetricV1:
    """Weighted on-time arrival, normalized timeliness, or strict route safety.

    One capable observer must dwell continuously for the configured request time.
    Different observers cannot splice partial dwell times into a completed arrival.
    Requests released in the future stay in the denominator: no early success.
    Physical event effects, observations and terminal adjudication remain native.
    """

    def bind_session(self, *, session_id, seed, parameters):
        del session_id, seed
        parameters = deepcopy(parameters)
        # Native _plain serializes nested _FrozenRecordV2 dataclasses as
        # {"values": {...}}. Unwrap only the two explicitly typed record lists,
        # not arbitrary keys or user data; the strict schema below still applies.
        for key in ("requests", "hazards"):
            if isinstance(parameters.get(key), (list, tuple)):
                parameters[key] = [record["values"] if isinstance(record, dict)
                                   and set(record) == {"values"} else record
                                   for record in parameters[key]]
        required = {"metric_id", "kind", "observer_ids", "requests",
                    "hazards", "start_tick", "end_tick", "unit"}
        if set(parameters) != required or parameters["unit"] != "1":
            raise ValueError("dispatch parameters must match the v1 schema")
        if parameters["kind"] not in {"arrival_fraction", "timeliness", "route_safety"}:
            raise ValueError("unsupported dispatch metric")
        if not isinstance(parameters["metric_id"], str) or not parameters["metric_id"]:
            raise ValueError("metric_id is required")
        _ids(parameters["observer_ids"], "observer_ids")
        start, end = parameters["start_tick"], parameters["end_tick"]
        if type(start) is not int or type(end) is not int or not 0 <= start < end:
            raise ValueError("invalid half-open scoring window")
        requests = parameters["requests"]
        if not isinstance(requests, (list, tuple)) or not requests:
            raise ValueError("at least one request is required")
        _ids([r["request_id"] for r in requests], "request IDs")
        for r in requests:
            if set(r) != {"request_id", "zone_id", "release_event_id", "deadline_tick",
                          "weight", "dwell_ticks", "observer_ids"}:
                raise ValueError("invalid request schema")
            _ids(r["observer_ids"], "request observer IDs")
            if not set(r["observer_ids"]) <= set(parameters["observer_ids"]):
                raise ValueError("request observers must belong to the declared fleet")
            if not isinstance(r["zone_id"], str) or not r["zone_id"]:
                raise ValueError("request zone required")
            if r["release_event_id"] is not None and (not isinstance(r["release_event_id"], str) or not r["release_event_id"]):
                raise ValueError("release must name an event or be null")
            if type(r["deadline_tick"]) is not int or not start <= r["deadline_tick"] < end:
                raise ValueError("request deadline must lie inside the score window")
            if type(r["dwell_ticks"]) is not int or r["dwell_ticks"] < 1:
                raise ValueError("positive dwell ticks required")
            if type(r["weight"]) not in (int, float) or not math.isfinite(r["weight"]) or r["weight"] <= 0:
                raise ValueError("finite positive request weight required")
        if not isinstance(parameters["hazards"], (list, tuple)):
            raise ValueError("hazards must be a sequence")
        for h in parameters["hazards"]:
            if set(h) != {"zone_id", "activation_event_id"}:
                raise ValueError("invalid hazard schema")
            if not isinstance(h["zone_id"], str) or not h["zone_id"]:
                raise ValueError("hazard zone required")
            if h["activation_event_id"] is not None and (not isinstance(h["activation_event_id"], str) or not h["activation_event_id"]):
                raise ValueError("hazard activation must name an event or be null")
        if len({h["zone_id"] for h in parameters["hazards"]}) != len(parameters["hazards"]):
            raise ValueError("hazard zones must be unique")
        self.parameters = deepcopy(parameters)
        self.last_tick = -1
        self.last_input_hash = None
        self.released = {}
        self.arrivals = {}
        self.dwell = {r["request_id"]: {} for r in requests}
        self.exposure_entity_ticks = 0
        self.samples = 0
        self.last_value = None

    def evaluate(self, snapshot):
        p, tick = self.parameters, snapshot.tick
        active = sorted(i for i in p["observer_ids"]
                        if snapshot.entity_states.get(i, {}).get("lifecycle") in {"active", "degraded"})
        zones = {i: sorted(z for z in snapshot.zone_membership.get(i, ())
                           if snapshot.zone_activation.get(z, True)) for i in active}
        events = set(snapshot.event_ids)
        anchor = hashlib.sha256(json.dumps([tick, active, zones, sorted(events)],
                                         sort_keys=True).encode()).hexdigest()
        if tick < self.last_tick:
            raise ValueError("backward metric tick requires checkpoint restoration")
        if tick == self.last_tick:
            if anchor != self.last_input_hash:
                raise ValueError("conflicting authoritative facts at the same tick")
            return {p["metric_id"]: self.last_value}
        first_required = max(p["start_tick"], self.last_tick + 1)
        if tick > first_required and first_required < p["end_tick"]:
            raise ValueError("every scoring tick is required")
        if p["start_tick"] <= tick < p["end_tick"]:
            self.samples += 1
            hazards = {h["zone_id"] for h in p["hazards"]
                       if h["activation_event_id"] is None or h["activation_event_id"] in events}
            self.exposure_entity_ticks += sum(bool(set(zs) & hazards) for zs in zones.values())
            for r in p["requests"]:
                rid = r["request_id"]
                if rid not in self.released and (r["release_event_id"] is None or r["release_event_id"] in events):
                    self.released[rid] = tick
                if rid not in self.released or rid in self.arrivals or tick > r["deadline_tick"]:
                    continue
                present = {i for i in r["observer_ids"] if r["zone_id"] in zones.get(i, ())}
                self.dwell[rid] = {i: self.dwell[rid].get(i, 0) + 1 for i in present}
                finished = sorted(i for i, count in self.dwell[rid].items() if count >= r["dwell_ticks"])
                if finished:
                    self.arrivals[rid] = {"tick": tick, "observer_id": finished[0],
                                          "latency_ticks": tick - self.released[rid]}
            total = sum(r["weight"] for r in p["requests"])
            if p["kind"] == "route_safety":
                self.last_value = float(self.exposure_entity_ticks == 0)
            elif p["kind"] == "arrival_fraction":
                self.last_value = sum(r["weight"] for r in p["requests"] if r["request_id"] in self.arrivals) / total
            else:
                value = 0.0
                for r in p["requests"]:
                    rid = r["request_id"]
                    if rid in self.arrivals:
                        budget = max(1, r["deadline_tick"] - self.released[rid] + 1)
                        value += r["weight"] * (1 - self.arrivals[rid]["latency_ticks"] / budget)
                self.last_value = value / total
        self.last_tick, self.last_input_hash = tick, anchor
        return {p["metric_id"]: self.last_value}

    def snapshot(self):
        return deepcopy({k: getattr(self, k) for k in ("parameters", "last_tick",
            "last_input_hash", "released", "arrivals", "dwell",
            "exposure_entity_ticks", "samples", "last_value")})

    def restore(self, state):
        expected = set(self.snapshot())
        if set(state) != expected or state["parameters"] != self.parameters:
            raise ValueError("checkpoint schema/parameters mismatch")
        request_ids = {r["request_id"] for r in self.parameters["requests"]}
        if set(state["dwell"]) != request_ids or not set(state["arrivals"]) <= set(state["released"]) <= request_ids:
            raise ValueError("checkpoint request identities mismatch")
        for key in ("samples", "exposure_entity_ticks"):
            if type(state[key]) is not int or state[key] < 0:
                raise ValueError("invalid checkpoint counters")
        p = self.parameters
        last = state["last_tick"]
        if type(last) is not int or last < -1:
            raise ValueError("invalid checkpoint last tick")
        expected_samples = max(0, min(last, p["end_tick"]-1) - p["start_tick"] + 1)
        if state["samples"] != expected_samples or state["exposure_entity_ticks"] > expected_samples * len(p["observer_ids"]):
            raise ValueError("checkpoint counters disagree with the scoring window")
        if (last == -1 and state["last_input_hash"] is not None) or (last >= 0 and
                (not isinstance(state["last_input_hash"], str) or not re.fullmatch(r"[0-9a-f]{64}", state["last_input_hash"]))):
            raise ValueError("invalid checkpoint authoritative input hash")
        for r in p["requests"]:
            rid = r["request_id"]
            release = state["released"].get(rid)
            if release is not None and (type(release) is not int or not p["start_tick"] <= release <= min(last, p["end_tick"]-1)):
                raise ValueError("checkpoint release tick outside observed scoring history")
            dwell = state["dwell"][rid]
            if not isinstance(dwell, dict) or not set(dwell) <= set(r["observer_ids"]):
                raise ValueError("checkpoint dwell observer identities differ")
            if any(type(count) is not int or not 1 <= count <= expected_samples for count in dwell.values()):
                raise ValueError("invalid checkpoint dwell counters")
            if release is None and dwell:
                raise ValueError("unreleased request cannot have dwell progress")
            if rid in state["arrivals"]:
                arrival = state["arrivals"][rid]
                if set(arrival) != {"tick", "observer_id", "latency_ticks"}:
                    raise ValueError("invalid checkpoint arrival schema")
                if (type(arrival["tick"]) is not int or type(arrival["latency_ticks"]) is not int
                        or release is None or not release <= arrival["tick"] <= min(last, r["deadline_tick"])
                        or arrival["latency_ticks"] != arrival["tick"] - release
                        or arrival["observer_id"] not in r["observer_ids"]
                        or dwell.get(arrival["observer_id"], 0) < r["dwell_ticks"]
                        or arrival["latency_ticks"] + 1 < r["dwell_ticks"]):
                    raise ValueError("checkpoint arrival contradicts observed dwell history")
        if state["last_value"] is not None and (type(state["last_value"]) not in (int, float) or not math.isfinite(state["last_value"]) or not 0 <= state["last_value"] <= 1):
            raise ValueError("invalid checkpoint metric value")
        if (expected_samples == 0) != (state["last_value"] is None):
            raise ValueError("checkpoint availability disagrees with scoring samples")
        for key, value in state.items():
            setattr(self, key, deepcopy(value))

    def close(self):
        pass
