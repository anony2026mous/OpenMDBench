"""Screen against measured incoming velocity, not the current contact centroid.

This candidate controller uses two fresh organic samples and public zone/capability
metadata. It never reads opponent routes, target identity, missile state or RNG.
Weapon selection, ammunition reservations and all navigation limits are inherited
unchanged from the original screening/salvo controls.
"""
import math

from .denial_policy import _projected_entry
from .screen_guard_policy import ScreenGuardPolicy, SETTINGS, finite


class ApproachScreenPolicy(ScreenGuardPolicy):
    def __init__(self, brief, defender_id, mode="approach-salvo"):
        if mode != "approach-salvo":
            raise ValueError("approach screening requires its declared comparison mode")
        super().__init__(brief, defender_id, "screen-salvo")
        self.approach_history = {}

    def navigation(self, observation):
        own = observation["own_entities"]
        if not own:
            return None
        if len(own) != 1 or own[0]["entity_id"] != self.defender_id:
            raise ValueError("screening received another controller's observation")
        state, tick = own[0], observation["tick"]
        if (not self.asset["mobile"] or self.asset["domain"] != "surface"
                or tick >= self.brief["scoring_deadline_tick"]
                or state.get("lifecycle_state", "active") not in {"active", "degraded"}):
            return None
        radius, cap = self.asset["nominal_sensor_range_m"], self.asset["maximum_navigation_speed_mps"]
        if not finite(radius) or radius <= 0 or not finite(cap) or cap <= 0:
            raise ValueError("screening needs positive published sensor and navigation limits")
        directions = []
        for contact in observation.get("organic_contacts", ()):
            when, point, token = (contact.get("observed_tick"),
                                  contact.get("estimated_position_m"), contact.get("contact_id"))
            if (type(when) is not int or when < 0 or not 0 <= tick - when <= 2
                    or not isinstance(token, str) or not token
                    or contact.get("observer_entity_id", self.defender_id) != self.defender_id
                    or not isinstance(point, (list, tuple)) or len(point) != 3
                    or not all(finite(v) for v in point) or point[2] > 40.):
                continue
            previous = self.approach_history.get(token)
            if previous is not None and when <= previous[0]:
                continue
            self.approach_history[token] = (when, tuple(point))
            if previous is None or when - previous[0] > SETTINGS["contact_memory_ticks"]:
                continue
            velocity = tuple((point[i] - previous[1][i]) / (when - previous[0]) for i in (0, 1))
            speed = math.hypot(*velocity)
            if speed < 1e-6:
                continue
            horizon = self.brief["scoring_deadline_tick"] - tick
            if any(_projected_entry(point, velocity, z, horizon) is not None
                   for z in self.brief["protected_zones"]):
                directions.append(tuple(-v / speed for v in velocity))
        if directions:
            directions.sort()
            direction = tuple(math.fsum(d[i] for d in directions) for i in (0, 1))
            length = math.hypot(*direction)
            if length > 1e-6:
                self.axis = tuple(v / length for v in direction)
                self.last_contact_tick = tick
        if self.last_contact_tick is not None and tick - self.last_contact_tick > SETTINGS["contact_memory_ticks"]:
            self.axis = None
        self.approach_history = {k: v for k, v in self.approach_history.items()
                                 if tick - v[0] <= SETTINGS["contact_memory_ticks"]}
        goal = self.centre
        safe_radius = SETTINGS["nominal_range_fraction"] * radius
        centre_covers = all(math.dist(goal, p) <= safe_radius for p in self.centres)
        if self.axis is not None and centre_covers:
            low, high = 0., safe_radius
            for _ in range(24):
                distance = (low + high) / 2
                candidate = tuple(self.centre[i] + distance * self.axis[i] for i in (0, 1))
                if all(math.dist(candidate, p) <= safe_radius for p in self.centres):
                    low = distance
                else:
                    high = distance
            goal = tuple(self.centre[i] + low * self.axis[i] for i in (0, 1))
        position, velocity = state["position_m"], state.get("velocity_mps", [0., 0., 0.])
        if any(len(v) != 3 or not all(finite(x) for x in v) for v in (position, velocity)):
            raise ValueError("own position and velocity must contain finite coordinates")
        distance = math.dist(position[:2], goal)
        stopping_band = max(SETTINGS["arrival_radius_m"], SETTINGS["settling_seconds"] * math.hypot(*velocity[:2]))
        moving = distance > stopping_band
        payload = {"speed_mps": min(SETTINGS["navigation_speed_fraction"] * cap, distance / 8.) if moving else 0.,
                   "heading_deg": math.degrees(math.atan2(goal[0] - position[0], goal[1] - position[1])) % 360.
                   if moving else state.get("heading_deg", 0.)}
        self.navigation_log.append({"tick": tick, "goal_m": list(goal),
                                    "public_centres_within_nominal_margin": centre_covers,
                                    "last_observed_contact_tick": self.last_contact_tick,
                                    "incoming_velocity_sample_count": len(directions),
                                    "estimated_approach_axis": list(self.axis) if self.axis else None})
        return {"payload": payload, "valid_until_tick": min(tick + SETTINGS["command_lifetime_ticks"],
                                                            self.brief["scoring_deadline_tick"])}
