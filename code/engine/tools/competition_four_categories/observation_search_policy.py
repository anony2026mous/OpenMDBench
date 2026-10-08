"""Public-observation search baseline; never reads the scenario or opponent plan.

Patrol and adaptive modes have identical fixed speed/altitude envelopes. The
adaptive mode may pursue measured contacts only after visiting its public cells.
These are controller settings, not changes to platform physics or score rules.
"""
from copy import deepcopy
import math

from .recon_policy import SearchPolicy

SETTINGS = {
    "air_speed_mps": 12.0,
    "surface_speed_mps": 8.0,
    "arrival_radius_m": 80.0,
    "maximum_contact_age_ticks": 2,
    "pursuit_memory_ticks": 8,
    "range_hold_fraction": 0.25,
    "minimum_altitude_m": 60.0,
    "maximum_altitude_m": 300.0,
}


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class ObservationSearchPolicy:
    def __init__(self, brief, entity_id, mode):
        if mode not in {"patrol", "adaptive"}:
            raise ValueError("observation search requires patrol or adaptive mode")
        self.search = SearchPolicy(brief, entity_id, "coordinated")
        self.entity_id, self.mode = entity_id, mode
        self.settings = deepcopy(SETTINGS)
        self.visited = set()
        self.last_contact = None
        self.phase = "survey"

    def _contact(self, observation, position):
        candidates = []
        tick = observation["tick"]
        for contact in observation.get("organic_contacts", ()):
            when = contact.get("observed_tick")
            point, confidence = contact.get("estimated_position_m"), contact.get("confidence")
            if (type(when) is not int or when < 0 or not 0 <= tick-when <= self.settings["maximum_contact_age_ticks"]
                or contact.get("observer_entity_id", self.entity_id) != self.entity_id
                or not _finite(confidence) or not 0 < confidence <= 1
                or not isinstance(point, (list, tuple)) or len(point) != 3
                or not all(_finite(x) for x in point)):
                continue
            # Neither contact-token spelling nor input list order breaks ties.
            candidates.append((math.dist(position, point), -when, -confidence, tuple(point), when))
        if candidates:
            selected = min(candidates)
            self.last_contact = {"position_m": selected[3], "observed_tick": selected[4]}
        if self.last_contact is None:
            return None
        age = tick-self.last_contact["observed_tick"]
        if not 0 <= age <= self.settings["pursuit_memory_ticks"]:
            self.last_contact = None
            return None
        # Remembered positions are navigation hints, never fresh sensor samples
        # or reported contacts. Report generation still consumes the real DTO.
        return self.last_contact["position_m"]

    def navigation(self, observation):
        own = self.search._own(observation)
        tick, asset = observation["tick"], self.search.asset
        if (own is None or own.get("lifecycle_state", "active") not in {"active", "degraded"}
            or asset["domain"] == "shore" or not self.search.waypoints
            or tick >= self.search.brief["scoring_deadline_tick"]):
            return None
        position = own["position_m"]
        if len(position) != 3 or not all(_finite(x) for x in position):
            raise ValueError("own position must contain three finite coordinates")
        for index, point in enumerate(self.search.waypoints):
            if math.dist(position[:2], point) <= self.settings["arrival_radius_m"]:
                self.visited.add(index)
        speed = self.settings[f"{asset['domain']}_speed_mps"]
        goal = self._contact(observation, position) if self.mode == "adaptive" else None
        if goal is not None and len(self.visited) == len(self.search.waypoints):
            self.phase = "observe"
            dx, dy = goal[0]-position[0], goal[1]-position[1]
            hold = max(40.0, asset["sensor_range_m"]*self.settings["range_hold_fraction"])
            moving = math.hypot(dx, dy) > hold
            payload = {"speed_mps": speed if moving else 0.0,
                "heading_deg": math.degrees(math.atan2(dx, dy)) % 360.0 if moving else own.get("heading_deg", 0.0)}
            if asset["domain"] == "air":
                payload["altitude_m"] = max(self.settings["minimum_altitude_m"],
                    min(self.settings["maximum_altitude_m"], goal[2]))
            return {"payload": payload, "valid_until_tick": min(tick+4, self.search.brief["scoring_deadline_tick"])}
        self.phase = "survey" if len(self.visited) < len(self.search.waypoints) else "reacquire"
        command = self.search.navigation(observation)
        if command is not None and command["payload"]["speed_mps"] > 0:
            command["payload"]["speed_mps"] = speed
        if command is not None and asset["domain"] == "air":
            command["payload"]["altitude_m"] = max(self.settings["minimum_altitude_m"],
                min(self.settings["maximum_altitude_m"], command["payload"]["altitude_m"]))
        return command

    def report(self, observation):
        return self.search.report(observation)

    def diagnostics(self):
        return {"phase": self.phase, "visited_cell_indices": sorted(self.visited),
                "assigned_cell_count": len(self.search.waypoints),
                "remembered_observed_tick": None if self.last_contact is None else self.last_contact["observed_tick"]}
