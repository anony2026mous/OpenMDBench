"""Candidate benchmark policies using native own-side observations and actions."""
from copy import deepcopy
import math

from .tracking_policy import ScheduledNavigationPolicy


def _inside(position, zone):
    points = zone["coordinates_m"]
    return all(min(p[i] for p in points) <= position[i] <= max(p[i] for p in points) for i in range(2))


def _projected_entry(position, velocity, zone, horizon):
    points = zone["coordinates_m"]
    first, last = 0., float(horizon)
    for axis in range(2):
        low, high = min(p[axis] for p in points), max(p[axis] for p in points)
        if abs(velocity[axis]) < 1e-9:
            if not low <= position[axis] <= high:
                return None
            continue
        a, b = (low-position[axis])/velocity[axis], (high-position[axis])/velocity[axis]
        first, last = max(first, min(a, b)), min(last, max(a, b))
        if first > last:
            return None
    return first


class WaveNavigationPolicy:
    """Data-driven navigation with delayed activation and no synthetic spawning."""
    def __init__(self, plan):
        if set(plan) != {"schema_version", "faction_id", "status", "segments", "controller_slots"} or plan["schema_version"] != "wave-navigation@1.0":
            raise ValueError("invalid wave navigation schema")
        self.plan = deepcopy(plan)
        if not isinstance(plan["segments"], list) or not plan["segments"]:
            raise ValueError("wave navigation plan must not be empty")
        self.first_ticks = {}
        for segment in plan["segments"]:
            first = segment["start_tick"]
            if type(first) is not int or first < 0:
                raise ValueError("invalid activation tick")
            self.first_ticks[segment["entity_id"]] = min(first, self.first_ticks.get(segment["entity_id"], first))
        if set(plan["controller_slots"]) != set(self.first_ticks) or len(set(plan["controller_slots"].values())) != len(self.first_ticks):
            raise ValueError("each scheduled entity requires its own controller binding")
        normalized = [{**deepcopy(s), "start_tick": s["start_tick"]-self.first_ticks[s["entity_id"]],
                       "end_tick": s["end_tick"]-self.first_ticks[s["entity_id"]]} for s in plan["segments"]]
        ScheduledNavigationPolicy({"schema_version": "scheduled-navigation@1.0",
            "faction_id": plan["faction_id"], "status": plan["status"], "segments": normalized})

    def active_ids(self, tick):
        return tuple(sorted(i for i, first in self.first_ticks.items() if first <= tick))

    def commands(self, tick, observations):
        if set(observations) != set(self.active_ids(tick)):
            raise ValueError("wave observations do not match the released own-side fleet")
        available = set()
        for identifier, observation in observations.items():
            own = observation["own_entities"]
            if own and (len(own) != 1 or own[0]["entity_id"] != identifier):
                raise ValueError("wave controller cannot command another entity")
            if own:
                available.add(identifier)
        return {s["entity_id"]: {"payload": deepcopy(s["payload"]), "valid_until_tick": s["end_tick"]-1}
                for s in self.plan["segments"] if s["start_tick"] == tick and s["entity_id"] in available}


class ZoneGuardPolicy:
    """Small reference policy; no hidden-role, future-wave or target-ID inputs.

Only opaque local contact tokens are passed to fire_weapon. Attempt budgeting is
conservative; actual ammunition/effect outcomes remain native and are audited.
This benchmark baseline is not a calibrated or competition-accepted controller.
"""
    def __init__(self, brief, defender_id, mode):
        if mode not in {"idle", "guard", "indiscriminate"} or defender_id not in brief["defenders"]:
            raise ValueError("invalid defender baseline configuration")
        self.brief, self.defender_id, self.mode = deepcopy(brief), defender_id, mode
        self.inventory = brief["own_inventory"][defender_id]
        self.history = {}
        self.last_attempt_tick, self.attempts = None, 0

    def action(self, observation):
        if self.mode == "idle" or not observation["own_entities"]:
            return None
        own = observation["own_entities"][0]
        if own["entity_id"] != self.defender_id:
            raise ValueError("defender received another controller's observation")
        tick = observation["tick"]
        candidates = []
        for contact in observation["organic_contacts"]:
            if contact["age_ticks"] > 2:
                continue
            token, position, observed = contact["contact_id"], contact["estimated_position_m"], contact["observed_tick"]
            prior = self.history.get(token)
            if prior is None or observed > prior[0]:
                self.history[token] = (observed, list(position))
            distance = math.dist(own["position_m"], position)
            domain = "air" if position[2] > 40 else "surface"
            if domain != self.inventory["target_domain"] or not self.inventory["minimum_range_m"] <= distance <= self.inventory["maximum_range_m"]:
                continue
            if self.mode == "guard":
                if prior is None or observed <= prior[0]:
                    continue
                warning = self.brief["warning_zones"]
                if warning and not any(_inside(position, z) for z in warning):
                    continue
                velocity = [(position[i]-prior[1][i])/(observed-prior[0]) for i in range(2)]
                horizon = min(self.brief["engagement_lookahead_ticks"], self.brief["scoring_deadline_tick"]-tick)
                if not any(_projected_entry(position, velocity, z, horizon) is not None for z in self.brief["protected_zones"]):
                    continue
            candidates.append((distance, token))
        interval = max(1, self.inventory["cooldown_ticks"])
        budget = sum(self.inventory["initial_ammunition"].values())
        if (not candidates or self.attempts*self.inventory["rounds_per_action"] >= budget
                or (self.last_attempt_tick is not None and tick-self.last_attempt_tick < interval)):
            return None
        self.last_attempt_tick, self.attempts = tick, self.attempts+1
        return {"weapon_ref": self.inventory["weapon_ref"], "contact_id": min(candidates)[1]}
