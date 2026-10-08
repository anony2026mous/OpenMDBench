"""Finite-ammunition baseline using public geometry and estimated travel time.

Pending assessments are controller estimates, not privileged missile/hit state.
Neither hidden target roles nor future wave times enter this policy.
"""
import math

from .denial_policy import ZoneGuardPolicy, _inside, _projected_entry


class SalvoGuardPolicy(ZoneGuardPolicy):
    def __init__(self, brief, defender_id, mode="salvo"):
        if mode != "salvo":
            raise ValueError("salvo guard requires its declared mode")
        super().__init__(brief, defender_id, "guard")
        self.pending_until = {}
        self.decisions = []
        self.dt = brief["physics_dt_seconds"]
        if not isinstance(self.dt, (int, float)) or not math.isfinite(self.dt) or self.dt <= 0:
            raise ValueError("positive finite physics tick duration required")

    def action(self, observation):
        profile = self.inventory.get("projectile_profile")
        if self.inventory.get("delivery_model") != "guided_missile":
            return super().action(observation)
        speed = profile["cruise_speed_mps"]
        if not isinstance(speed, (int, float)) or not math.isfinite(speed) or speed <= 0:
            raise ValueError("public projectile speed must be positive and finite")
        entities = observation["own_entities"]
        if not entities:
            return None
        if len(entities) != 1 or entities[0]["entity_id"] != self.defender_id:
            raise ValueError("salvo guard received another controller's observation")
        own, tick = entities[0], observation["tick"]
        if own.get("lifecycle_state", "active") not in {"active", "degraded"}:
            return None
        candidates = []
        cooldown = max(1, self.inventory["cooldown_ticks"])
        for contact in observation["organic_contacts"]:
            observed = contact["observed_tick"]
            position, token = contact["estimated_position_m"], contact["contact_id"]
            if (type(observed) is not int or observed < 0 or not 0 <= tick-observed <= 2
                or len(position) != 3 or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in position)
                or contact.get("observer_entity_id", self.defender_id) != self.defender_id):
                continue
            previous = self.history.get(token)
            if previous is None or observed > previous[0]:
                self.history[token] = (observed, list(position))
            if previous is None or observed <= previous[0] or tick < self.pending_until.get(token, -1):
                continue
            domain = "air" if position[2] > 40 else "surface"
            distance = math.dist(own["position_m"], position)
            if (domain != self.inventory["target_domain"]
                or not self.inventory["minimum_range_m"] <= distance <= self.inventory["maximum_range_m"]):
                continue
            warnings = self.brief["warning_zones"]
            if warnings and not any(_inside(position, zone) for zone in warnings):
                continue
            velocity = [(position[i]-previous[1][i])/(observed-previous[0]) for i in range(2)]
            flight_ticks = min(profile["max_flight_ticks"], math.ceil(distance/(speed*self.dt)))
            horizon = min(self.brief["scoring_deadline_tick"]-tick,
                          max(self.brief["engagement_lookahead_ticks"], flight_ticks+2*cooldown))
            entries = [_projected_entry(position, velocity, zone, horizon) for zone in self.brief["protected_zones"]]
            entries = [entry for entry in entries if entry is not None]
            if not entries:
                continue
            entry = min(entries)
            candidates.append((entry-flight_ticks, entry, distance, tuple(position), token, flight_ticks))
        if (not candidates or self.attempts*self.inventory["rounds_per_action"] >= sum(self.inventory["initial_ammunition"].values())
            or (self.last_attempt_tick is not None and tick-self.last_attempt_tick < cooldown)):
            return None
        slack, entry, distance, _, token, flight_ticks = min(candidates)
        self.last_attempt_tick, self.attempts = tick, self.attempts+1
        self.pending_until[token] = tick+flight_ticks+cooldown
        self.decisions.append({"tick": tick, "contact_id": token, "range_m": distance,
            "predicted_entry_ticks": entry, "estimated_flight_ticks": flight_ticks,
            "assessment_tick": self.pending_until[token], "attempt_number": self.attempts})
        return {"weapon_ref": self.inventory["weapon_ref"], "contact_id": token}
