"""Public-geometry surface screening, with unchanged selectable weapon policies.

Only own state, own nominal capabilities, protected zones and observed contacts
choose the station. Actual enemy state, wave plans and flight telemetry are never
controller inputs. The range margin and speed fraction are fixed development
settings, not a claim of calibrated hydrodynamic control.
"""
from copy import deepcopy
import math

from .denial_policy import ZoneGuardPolicy
from .salvo_guard_policy import SalvoGuardPolicy

SETTINGS = {"nominal_range_fraction": .9, "navigation_speed_fraction": .8,
            "arrival_radius_m": 50., "settling_seconds": 8.,
            "contact_memory_ticks": 12, "command_lifetime_ticks": 4}


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class ScreenGuardPolicy:
    def __init__(self, brief, defender_id, mode):
        if mode not in {"screen-guard", "screen-salvo"}:
            raise ValueError("screening requires a declared weapon-control mode")
        self.brief, self.defender_id = deepcopy(brief), defender_id
        assets = [a for a in brief["own_assets"] if a["entity_id"] == defender_id]
        if len(assets) != 1:
            raise ValueError("screening requires exactly one public own-asset record")
        self.asset = assets[0]
        self.weapon = (SalvoGuardPolicy(brief, defender_id) if mode == "screen-salvo"
                       else ZoneGuardPolicy(brief, defender_id, "guard"))
        self.centres = sorted(tuple(sum(p[i] for p in z["coordinates_m"])/len(z["coordinates_m"])
                                    for i in (0, 1)) for z in brief["protected_zones"])
        if not self.centres:
            raise ValueError("screening requires declared protected zones")
        self.centre = tuple(sum(p[i] for p in self.centres)/len(self.centres) for i in (0, 1))
        self.axis, self.last_contact_tick = None, None
        self.navigation_log = []

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
        radius = self.asset["nominal_sensor_range_m"]
        cap = self.asset["maximum_navigation_speed_mps"]
        if not finite(radius) or radius <= 0 or not finite(cap) or cap <= 0:
            raise ValueError("screening needs positive published sensor and navigation limits")
        points = []
        for contact in observation.get("organic_contacts", ()):
            when, point = contact.get("observed_tick"), contact.get("estimated_position_m")
            if (type(when) is not int or when < 0 or not 0 <= tick-when <= 2
                or contact.get("observer_entity_id", self.defender_id) != self.defender_id
                or not isinstance(point, (list, tuple)) or len(point) != 3 or not all(finite(v) for v in point)
                or point[2] > 40.):
                continue
            points.append(tuple(point[:2]))
        if points:
            points.sort()
            direction = [sum(p[i] for p in points)/len(points)-self.centre[i] for i in (0, 1)]
            length = math.hypot(*direction)
            if length > 1.:
                self.axis = tuple(x/length for x in direction); self.last_contact_tick = tick
        if self.last_contact_tick is not None and tick-self.last_contact_tick > SETTINGS["contact_memory_ticks"]:
            self.axis = None
        goal = self.centre
        safe_radius = SETTINGS["nominal_range_fraction"]*radius
        centre_covers = all(math.dist(goal, p) <= safe_radius for p in self.centres)
        if self.axis is not None and centre_covers:
            low, high = 0., safe_radius
            for _ in range(24):
                distance = (low+high)/2
                candidate = tuple(self.centre[i]+distance*self.axis[i] for i in (0, 1))
                if all(math.dist(candidate, p) <= safe_radius for p in self.centres): low = distance
                else: high = distance
            goal = tuple(self.centre[i]+low*self.axis[i] for i in (0, 1))
        position = state["position_m"]
        if len(position) != 3 or not all(finite(x) for x in position):
            raise ValueError("own position must contain three finite coordinates")
        distance = math.dist(position[:2], goal)
        velocity = state.get("velocity_mps", [0., 0., 0.])
        if len(velocity) != 3 or not all(finite(x) for x in velocity):
            raise ValueError("own velocity must contain three finite coordinates")
        speed = math.hypot(velocity[0], velocity[1])
        stopping_band = max(SETTINGS["arrival_radius_m"], SETTINGS["settling_seconds"]*speed)
        moving = distance > stopping_band
        payload = {"speed_mps": min(SETTINGS["navigation_speed_fraction"]*cap, distance/8.) if moving else 0.,
            "heading_deg": math.degrees(math.atan2(goal[0]-position[0], goal[1]-position[1])) % 360.
                           if moving else state.get("heading_deg", 0.)}
        self.navigation_log.append({"tick": tick, "goal_m": list(goal), "public_centres_within_nominal_margin": centre_covers,
                                    "last_observed_contact_tick": self.last_contact_tick})
        return {"payload": payload, "valid_until_tick": min(tick+SETTINGS["command_lifetime_ticks"], self.brief["scoring_deadline_tick"])}

    def action(self, observation):
        return self.weapon.action(observation)

    @property
    def decisions(self):
        return {"navigation": self.navigation_log, "weapon_assessments": getattr(self.weapon, "decisions", [])}
