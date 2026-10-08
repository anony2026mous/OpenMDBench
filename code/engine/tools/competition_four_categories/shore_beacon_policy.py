"""Actual shore-to-mobile binding publication, never self-credit at the score sink."""
from copy import deepcopy
import json

from .allocated_tracking_policy import _point
from .identity_tracking_policy import (IdentityTrackPolicy, IdentityReportingPolicy,
    PEER_PROTOCOL, PEER_INTERVAL, INITIAL_SAMPLE_LIMIT, inside_polygon)


class BeaconIdentityTrackPolicy(IdentityTrackPolicy):
    def _peer_samples(self, observation):
        return super()._peer_samples(observation, allowed_senders=self.brief["observers"])


class BeaconIdentityReportingPolicy(IdentityReportingPolicy):
    def __init__(self, brief, observer_id, mode="honest"):
        super().__init__(brief, observer_id, mode)
        self.tracker = BeaconIdentityTrackPolicy(brief, observer_id)


class ShoreBindingPolicy:
    """Stationary observer publishes only its own measured contact bindings.

It is not an official reporter, never navigates and never emits track-report.
Only unambiguous initial public regions establish labels. Later positions use
the same opaque native contact token. No private opponent state is consulted.
"""
    def __init__(self, brief, observer_id):
        if (observer_id not in brief["observers"] or brief["observer_domains"].get(observer_id) != "shore"
                or observer_id in brief["track_reporting"]["reporter_ids"]):
            raise ValueError("declared non-reporting shore observer required")
        self.brief, self.identifier = deepcopy(brief), observer_id
        self.labels = [r["id"] for r in brief["initial_designation_regions"]]
        self.bindings, self.label_tokens, self.binding_events = {}, {}, []

    def decide(self, observation):
        own = observation["own_entities"]
        if not own:
            return {"navigation": None, "messages": []}
        if len(own) != 1 or own[0]["entity_id"] != self.identifier:
            raise ValueError("shore publisher received another controller scope")
        tick = observation["tick"]
        if type(tick) is not int or tick < 0:
            raise ValueError("nonnegative native observation tick required")
        rows = []
        for item in observation.get("organic_contacts", ()):
            if (item.get("observer_entity_id") != self.identifier or type(item.get("observed_tick")) is not int
                    or not 0 <= item["observed_tick"] <= tick or item.get("confidence", 0) <= 0
                    or not isinstance(item.get("contact_id"), str) or not item["contact_id"]):
                continue
            rows.append({**item, "estimated_position_m": _point(item["estimated_position_m"])})
        candidates = {}
        for row in rows:
            token = row["contact_id"]
            if token in self.bindings or row["observed_tick"] > INITIAL_SAMPLE_LIMIT:
                continue
            indices = [i for i, region in enumerate(self.brief["initial_designation_regions"])
                       if inside_polygon(row["estimated_position_m"], region["coordinates_m"])]
            if len(indices) == 1:
                candidates.setdefault(indices[0], set()).add(token)
        for index, tokens in candidates.items():
            if len(tokens) == 1 and index not in self.label_tokens:
                token = next(iter(tokens))
                self.bindings[token] = index; self.label_tokens[index] = token
                self.binding_events.append({"tick": tick, "contact_id": token, "track_id": self.labels[index],
                                            "reason": "own_organic_initial_public_region"})
        if tick % PEER_INTERVAL:
            return {"navigation": None, "messages": []}
        bindings = []
        for row in rows:
            index = self.bindings.get(row["contact_id"])
            if index is not None and tick-row["observed_tick"] <= self.brief["track_reporting"]["maximum_age_ticks"]:
                bindings.append({"track_id": self.labels[index], "contact_id": row["contact_id"],
                    "observed_tick": row["observed_tick"], "estimated_position_m": row["estimated_position_m"]})
        if not bindings:
            return {"navigation": None, "messages": []}
        bindings.sort(key=lambda row: self.labels.index(row["track_id"]))
        body = {"schema_version": PEER_PROTOCOL, "issued_tick": tick, "bindings": bindings}
        return {"navigation": None, "messages": [{"message_id": f"shore-binding-{self.identifier}-{tick}",
            "sender_id": self.identifier,
            "recipient_controller_slots": [f"slot.{i}" for i in self.brief["track_reporting"]["reporter_ids"]],
            "message": json.dumps(body, sort_keys=True)}]}
