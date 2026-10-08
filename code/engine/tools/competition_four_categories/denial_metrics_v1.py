"""Candidate generic protected-zone metrics on native authoritative facts.

This is not a combat engine. Native movement, zone transitions, damage and
lifecycle produce all inputs. Hidden evaluation cohorts remain referee-side.
Protected integrity is all-cause health preservation, not damage attribution.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import math

MODEL_ID = "models.competition-denial-metrics"
MODEL_VERSION = "1.0.0"
MODEL_REF = f"{MODEL_ID}@{MODEL_VERSION}"


def _ids(values):
    return isinstance(values, (tuple, list)) and bool(values) and all(isinstance(v, str) and v for v in values) and len(set(values)) == len(values)


class DenialMetricV1:
    def bind_session(self, *, session_id, seed, parameters):
        del session_id, seed
        p = deepcopy(parameters)
        if isinstance(p.get("protected_entities"), (tuple, list)):
            p["protected_entities"] = [r["values"] if isinstance(r, dict) and set(r) == {"values"} else r for r in p["protected_entities"]]
        if set(p) != {"metric_id", "kind", "zone_ids", "intruder_ids", "protected_entities",
                      "start_tick", "end_tick", "maximum_breaches_per_zone", "unit"}:
            raise ValueError("denial parameters must match the explicit v1 schema")
        if p["kind"] not in {"protection_fraction", "breach_free", "protected_integrity"}:
            raise ValueError("unsupported denial metric")
        if p["unit"] != "1" or not isinstance(p["metric_id"], str) or not p["metric_id"]:
            raise ValueError("named dimensionless denial metric required")
        if not _ids(p["zone_ids"]) or not _ids(p["intruder_ids"]):
            raise ValueError("unique nonempty zone and intruder IDs required")
        for key in ("start_tick", "end_tick", "maximum_breaches_per_zone"):
            if type(p[key]) is not int or p[key] < 0:
                raise ValueError("denial windows and breach limits must be nonnegative integers")
        if p["end_tick"] <= p["start_tick"]:
            raise ValueError("empty denial scoring window")
        protected = p["protected_entities"]
        if not isinstance(protected, list) or (protected and not _ids([r.get("entity_id") for r in protected])):
            raise ValueError("invalid protected cohort")
        for row in protected:
            if (set(row) != {"entity_id", "initial_health"} or type(row["initial_health"]) not in (int, float)
                    or not math.isfinite(row["initial_health"]) or row["initial_health"] <= 0):
                raise ValueError("protected entities require finite positive initial health")
        if {r["entity_id"] for r in protected} & set(p["intruder_ids"]):
            raise ValueError("protected and intruder cohorts must be disjoint")
        if p["kind"] == "protected_integrity" and not protected:
            raise ValueError("protected integrity requires a real protected cohort")
        self.parameters = p
        self.last_tick, self.last_input_hash, self.last_value = -1, None, None
        self.samples = 0
        self.zones = {z: {"safe_ticks": 0, "breaches": 0, "first_breach_tick": None,
                          "last_breach_tick": None, "inside": [], "ever_inactive": False} for z in p["zone_ids"]}
        self.transition_ids = set()
        self.minimum_health = {r["entity_id"]: r["initial_health"] for r in protected}

    def evaluate(self, snapshot):
        p, tick = self.parameters, snapshot.tick
        active = {i for i in p["intruder_ids"] if snapshot.entity_states.get(i, {}).get("lifecycle") in {"active", "degraded"}}
        if not set(p["zone_ids"]) <= set(snapshot.zone_activation):
            raise ValueError("required protection-zone activation facts are missing")
        occupied = {z: sorted(i for i in active if z in snapshot.zone_membership.get(i, ())) for z in p["zone_ids"]}
        transitions = sorted((t.evidence_hash, t.entity_id, t.zone_id, t.transition, t.tick)
                             for t in snapshot.zone_transitions
                             if t.entity_id in p["intruder_ids"] and t.zone_id in self.zones
                             and p["start_tick"] <= t.tick <= tick)
        health = {}
        for row in p["protected_entities"]:
            identifier = row["entity_id"]
            state = snapshot.entity_states.get(identifier)
            if state is None:
                raise ValueError("required protected entity state is missing")
            if state.get("lifecycle") in {"destroyed", "despawned"}:
                health[identifier] = 0.
            else:
                value = state.get("health")
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    raise ValueError("required protected health fact is missing or invalid")
                health[identifier] = float(value)
        activation = {z: bool(snapshot.zone_activation[z]) for z in p["zone_ids"]}
        anchor = hashlib.sha256(json.dumps([tick, occupied, transitions, health, activation], sort_keys=True).encode()).hexdigest()
        if tick < self.last_tick:
            raise ValueError("denial metric cannot move backwards without restore")
        if tick == self.last_tick:
            if anchor != self.last_input_hash:
                raise ValueError("conflicting denial facts at the same tick")
            return {p["metric_id"]: self.last_value}
        first = max(p["start_tick"], self.last_tick+1)
        if tick > first and first < p["end_tick"]:
            raise ValueError("denial scoring requires every authoritative tick")
        if p["start_tick"] <= tick < p["end_tick"]:
            self.samples += 1
            entered = {z: set() for z in self.zones}
            for evidence, identifier, zone, transition, _ in transitions:
                if evidence not in self.transition_ids:
                    self.transition_ids.add(evidence)
                    if transition == "entered":
                        entered[zone].add(identifier)
            for zone, history in self.zones.items():
                # End-of-tick membership also covers an initially occupied zone.
                # Native transition evidence catches enter+exit within one tick,
                # including an intruder destroyed later in that same tick.
                new_entries = entered[zone] | (set(occupied[zone]) - set(history["inside"]))
                if new_entries:
                    history["breaches"] += len(new_entries)
                    history["first_breach_tick"] = tick if history["first_breach_tick"] is None else history["first_breach_tick"]
                    history["last_breach_tick"] = tick
                if activation[zone] and not occupied[zone] and not entered[zone]:
                    history["safe_ticks"] += 1
                history["ever_inactive"] = history["ever_inactive"] or not activation[zone]
                history["inside"] = occupied[zone]
            for identifier, value in health.items():
                self.minimum_health[identifier] = min(self.minimum_health[identifier], value)
            if p["kind"] == "protection_fraction":
                self.last_value = min(z["safe_ticks"] for z in self.zones.values()) / self.samples
            elif p["kind"] == "breach_free":
                self.last_value = float(all(z["breaches"] <= p["maximum_breaches_per_zone"] and not z["ever_inactive"] for z in self.zones.values()))
            else:
                self.last_value = min(self.minimum_health[r["entity_id"]] / r["initial_health"] for r in p["protected_entities"])
        self.last_tick, self.last_input_hash = tick, anchor
        return {p["metric_id"]: self.last_value}

    def snapshot(self):
        return deepcopy({"parameters": self.parameters, "last_tick": self.last_tick,
            "last_input_hash": self.last_input_hash, "last_value": self.last_value,
            "samples": self.samples, "zones": self.zones,
            "transition_ids": sorted(self.transition_ids), "minimum_health": self.minimum_health})

    def restore(self, state):
        if set(state) != set(self.snapshot()) or state["parameters"] != self.parameters:
            raise ValueError("denial checkpoint schema or parameters differ")
        p, last = self.parameters, state["last_tick"]
        if type(last) is not int or last < -1:
            raise ValueError("invalid denial checkpoint tick")
        count = max(0, min(last, p["end_tick"]-1) - p["start_tick"]+1)
        if type(state["samples"]) is not int or state["samples"] != count or set(state["zones"]) != set(self.zones):
            raise ValueError("denial checkpoint sample count or zones differ")
        for zone, row in state["zones"].items():
            if set(row) != set(self.zones[zone]) or type(row["safe_ticks"]) is not int or not 0 <= row["safe_ticks"] <= count:
                raise ValueError("invalid zone history")
            if type(row["breaches"]) is not int or row["breaches"] < 0 or not set(row["inside"]) <= set(p["intruder_ids"]):
                raise ValueError("invalid breach history")
        if set(state["minimum_health"]) != set(self.minimum_health):
            raise ValueError("checkpoint protected identities differ")
        for r in p["protected_entities"]:
            value = state["minimum_health"][r["entity_id"]]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= r["initial_health"]:
                raise ValueError("invalid protected health history")
        for key, value in state.items():
            if key != "transition_ids":
                setattr(self, key, deepcopy(value))
        self.transition_ids = set(state["transition_ids"])

    def close(self):
        pass
