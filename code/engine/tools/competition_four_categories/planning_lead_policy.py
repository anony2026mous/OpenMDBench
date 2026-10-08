"""Candidate reference control with a public-capability planning-time budget.

The existing receipt-aware target selection, navigation and ammunition accounting
remain in use. This heuristic reserves time to observe a result and potentially
retry; it neither guarantees success nor reads referee state/future events.
"""
from copy import deepcopy
import math

from .receipt_aware_screen_policy import ReceiptAwareSalvoPolicy, ReceiptAwareScreenPolicy
from .screen_guard_policy import finite

PROFILE = {"version": "public-service-time-lead@1.0", "service_cycles": 2, "cooldown_cycles": 2}


class PlanningLeadSalvoPolicy(ReceiptAwareSalvoPolicy):
    def __init__(self, brief, defender_id):
        planned = deepcopy(brief)
        original = planned["engagement_lookahead_ticks"]
        deadline, dt = planned["scoring_deadline_tick"], planned["physics_dt_seconds"]
        if type(original) is not int or original <= 0 or type(deadline) is not int or deadline <= 0:
            raise ValueError("public planning limits must be positive integer ticks")
        if not finite(dt) or dt <= 0:
            raise ValueError("public tick duration must be positive and finite")
        inventory = planned["own_inventory"][defender_id]
        travel_ticks = None
        if inventory.get("delivery_model") == "guided_missile":
            assets = [a for a in planned["own_assets"] if a["entity_id"] == defender_id]
            if len(assets) != 1:
                raise ValueError("planning requires one public own-capability record")
            radius = assets[0]["nominal_sensor_range_m"]
            maximum_range = inventory["maximum_range_m"]
            profile = inventory["projectile_profile"]
            speed, lifetime = profile["cruise_speed_mps"], profile["max_flight_ticks"]
            cooldown = inventory["cooldown_ticks"]
            if any(not finite(x) or x <= 0 for x in (radius, maximum_range, speed)):
                raise ValueError("planning requires positive finite public range and speed")
            if type(lifetime) is not int or lifetime <= 0 or type(cooldown) is not int or cooldown < 0:
                raise ValueError("planning requires valid public lifetime and cooldown ticks")
            travel_ticks = min(lifetime, math.ceil(min(radius, maximum_range) / (speed * dt)))
            planned["engagement_lookahead_ticks"] = min(deadline, max(
                original, PROFILE["service_cycles"] * travel_ticks + PROFILE["cooldown_cycles"] * cooldown))
        super().__init__(planned, defender_id)
        self.planning = {"profile": dict(PROFILE), "original_lookahead_ticks": original,
                         "controller_lookahead_ticks": planned["engagement_lookahead_ticks"],
                         "nominal_range_travel_ticks": travel_ticks,
                         "basis": "own published sensor/range/speed/lifetime/cooldown only; no hit probability or future wave input"}


class PlanningLeadScreenPolicy(ReceiptAwareScreenPolicy):
    def __init__(self, brief, defender_id, mode="planning-lead-salvo"):
        if mode != "planning-lead-salvo":
            raise ValueError("planning-lead control requires its declared mode")
        super().__init__(brief, defender_id)
        self.weapon = PlanningLeadSalvoPolicy(brief, defender_id)

    @property
    def decisions(self):
        return {**super().decisions, "planning_lead": self.weapon.planning}
