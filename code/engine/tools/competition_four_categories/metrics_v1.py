"""Generic, checkpointable metrics consuming authoritative MissionEvaluationSnapshotV2.

This is a candidate versioned model plugin, NOT a separate simulation or adjudicator.
No scenario IDs, side colours, hidden roles, or privileged actions are encoded here.
Production registration requires the competition acceptance/review gates.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any


MODEL_ID = "models.competition-observation-metrics"
MODEL_VERSION = "1.0.0"
MODEL_REF = f"{MODEL_ID}@{MODEL_VERSION}"


class ObservationMetricV1:
    """Parameter-driven unique contact recall, zone visits, or tracking continuity."""

    def bind_session(self, *, session_id: str, seed: int, parameters: dict) -> None:
        del session_id, seed  # The metric itself has no RNG.
        required = {"metric_id", "kind", "observer_ids", "item_ids",
                    "start_tick", "end_tick", "maximum_age_ticks", "unit"}
        if set(parameters) != required:
            raise ValueError("metric parameters must match the explicit v1 schema")
        if parameters["kind"] not in {"contact_recall", "zone_visits", "contact_fraction"}:
            raise ValueError("unsupported metric kind")
        for key in ("observer_ids", "item_ids"):
            values = parameters[key]
            if not isinstance(values, (list, tuple)) or not values:
                raise ValueError(f"{key} must contain at least one ID")
            if any(not isinstance(x, str) or not x for x in values) or len(set(values)) != len(values):
                raise ValueError(f"{key} must contain unique nonempty IDs")
        for key in ("start_tick", "end_tick", "maximum_age_ticks"):
            if type(parameters[key]) is not int or parameters[key] < 0:
                raise ValueError(f"{key} must be a nonnegative integer")
        if parameters["end_tick"] <= parameters["start_tick"]:
            raise ValueError("the score interval is [start_tick, end_tick) and must be nonempty")
        if parameters["unit"] != "1" or not isinstance(parameters["metric_id"], str) or not parameters["metric_id"]:
            raise ValueError("a metric ID and dimensionless unit are required")
        self.parameters = deepcopy(parameters)
        self.last_tick = -1
        self.last_input_hash = None
        self.seen: set[str] = set()
        self.counts = {identifier: 0 for identifier in parameters["item_ids"]}
        self.samples = 0
        self.last_value = None

    def _present(self, snapshot: Any) -> set[str]:
        p = self.parameters
        observers = set(p["observer_ids"])
        allowed = set(p["item_ids"])
        active = {i for i in observers if snapshot.entity_states.get(i, {}).get("lifecycle")
                  not in {None, "scheduled", "destroyed", "despawned", "disabled"}}
        if p["kind"] == "zone_visits":
            return {zone for entity in active for zone in snapshot.zone_membership.get(entity, ())
                    if zone in allowed and snapshot.zone_activation.get(zone, True)}
        return {fact.target_entity_id for fact in snapshot.contact_facts
                if fact.owner_entity_id in active and fact.target_entity_id in allowed
                and fact.is_valid(expected_tick=snapshot.tick, owner_entity_id=fact.owner_entity_id)
                and snapshot.tick - fact.observed_tick <= p["maximum_age_ticks"]}

    def evaluate(self, snapshot: Any) -> dict[str, float | None]:
        tick = snapshot.tick
        present = self._present(snapshot)
        anchor = hashlib.sha256(json.dumps([tick, sorted(present)]).encode()).hexdigest()
        if tick < self.last_tick:
            raise ValueError("metric cannot move backwards without checkpoint restoration")
        if tick == self.last_tick:
            if anchor != self.last_input_hash:
                raise ValueError("same metric tick has conflicting authoritative inputs")
            return {self.parameters["metric_id"]: self.last_value}
        p = self.parameters
        # Refuse skipped scoring ticks: otherwise continuity can be inflated by sparse sampling.
        first_required = max(p["start_tick"], self.last_tick + 1)
        if tick > first_required and first_required < p["end_tick"]:
            raise ValueError("metric interval requires every authoritative tick")
        if p["start_tick"] <= tick < p["end_tick"]:
            self.samples += 1
            self.seen.update(present)
            for item in present:
                self.counts[item] += 1
        self.last_tick, self.last_input_hash = tick, anchor
        if self.samples:
            self.last_value = (min(self.counts.values()) / self.samples
                               if p["kind"] == "contact_fraction"
                               else len(self.seen) / len(p["item_ids"]))
        return {p["metric_id"]: self.last_value}

    def snapshot(self) -> dict:
        return {"parameters": deepcopy(self.parameters), "last_tick": self.last_tick,
                "last_input_hash": self.last_input_hash, "seen": sorted(self.seen),
                "counts": dict(self.counts), "samples": self.samples, "last_value": self.last_value}

    def restore(self, state: dict) -> None:
        if state["parameters"] != self.parameters:
            raise ValueError("checkpoint parameters differ from the resolved metric")
        if set(state["counts"]) != set(self.counts) or not set(state["seen"]) <= set(self.counts):
            raise ValueError("checkpoint item identities differ")
        self.last_tick = state["last_tick"]
        self.last_input_hash = state["last_input_hash"]
        self.seen = set(state["seen"])
        self.counts = dict(state["counts"])
        self.samples = state["samples"]
        self.last_value = state["last_value"]

    def close(self) -> None:
        pass
