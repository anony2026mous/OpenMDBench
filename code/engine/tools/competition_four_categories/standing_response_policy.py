"""Delivered-task response plus explicitly published standing surveillance.

Uses only authenticated tasks already accepted by ResponsePolicy, public mission
geometry and native sensor estimates. It does not read scenario/event schedules.
"""
import math

from .response_policy import ResponsePolicy, center, inside, crosses

SETTINGS = {"watch_altitude_m": 60.0, "watch_lane_height_m": 20.0,
            "watch_lateral_spacing_m": 50.0, "memory_ticks": 30,
            "maximum_speed_mps": 22.0, "arrival_radius_m": 20.0}


class StandingResponsePolicy(ResponsePolicy):
    def __init__(self, brief, identifier, mode="watch-coordinated"):
        if mode != "watch-coordinated":
            raise ValueError("standing response requires its declared mode")
        super().__init__(brief, identifier, "coordinated")
        self.standing = brief.get("standing_missions", [])
        self.initial_ids = {task["request_id"] for task in brief["initial_requests"]}
        self.watch_contact = None
        self.watch_route, self.watch_key = [], None
        self.phase = "initial_or_incident"

    def command(self, observation):
        # Preserve the original authentication, versioning and real dwell logic.
        default = super().command(observation)
        if not self.standing or not observation["own_entities"] or observation["tick"] >= self.brief["scoring_deadline_tick"]:
            return default
        tick = observation["tick"]
        position = observation["own_entities"][0]["position_m"]
        watch = self.standing[0]
        samples = []
        for contact in observation.get("organic_contacts", []):
            point, when = contact.get("estimated_position_m"), contact.get("observed_tick")
            if (type(when) is not int or when < 0 or not 0 <= tick-when <= 2
                or contact.get("observer_entity_id", self.identifier) != self.identifier
                or not isinstance(point, (list, tuple)) or len(point) != 3
                or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in point)
                or not inside(point, watch["search_region"])):
                continue
            samples.append((math.dist(position, point), tuple(point), when))
        if samples:
            _, point, when = min(samples)
            self.watch_contact = (point, when)
        outstanding_initial = [r for key, r in self.tasks.items() if key in self.initial_ids
                               and key not in self.completed and tick <= r["deadline_tick"]]
        if outstanding_initial:
            self.phase = "initial"
            return default
        # Include completed tasks in the assignment list: finishing one request
        # must not silently swap both responders onto each other's tasks.
        incidents = sorted((r for key, r in self.tasks.items() if key not in self.initial_ids
                            and r["status"] == "confirmed" and tick <= r["deadline_tick"]),
                           key=lambda r: (-r["priority"], r["request_id"]))
        assigned = []
        for index, task in enumerate(incidents):
            eligible = [i for i in self.brief["responders"] if i in task["observer_ids"]]
            if eligible and eligible[index % len(eligible)] == self.identifier and task["request_id"] not in self.completed:
                assigned.append(task)
        rank = self.brief["responders"].index(self.identifier)
        if assigned:
            self.phase = "incident"
            task = assigned[0]
            goal = list(center(task["destination"]))
            goal[1] += (rank-(len(self.brief["responders"])-1)/2)*SETTINGS["watch_lateral_spacing_m"]
            return self._navigate(position, goal, 100., ("incident", task["request_id"]))
        self.phase = "standing_watch"
        if self.watch_contact is not None and tick-self.watch_contact[1] <= SETTINGS["memory_ticks"]:
            goal = list(self.watch_contact[0][:2])
        elif incidents:
            # A known high-priority incident site is a search hint, not a true
            # target coordinate or evidence that the surveillance objective passed.
            goal = list(center(incidents[0]["destination"]))
        else:
            goal = list(center(watch["search_region"]))
        goal[1] += (rank-(len(self.brief["responders"])-1)/2)*SETTINGS["watch_lateral_spacing_m"]
        altitude = SETTINGS["watch_altitude_m"] + rank*SETTINGS["watch_lane_height_m"]
        return self._navigate(position, goal, altitude, ("watch", tuple(goal)))

    def _navigate(self, position, goal, altitude, key):
        if self.watch_key != key:
            obstacles = [r for r in self.brief["risk_regions"] if crosses(position, goal, r)]
            self.watch_route = []
            if obstacles:
                floor = min(p[1] for r in obstacles for p in r["coordinates_m"])-160.
                self.watch_route.extend([(position[0], floor), (goal[0], floor)])
            self.watch_route.append(tuple(goal)); self.watch_key = key
        x, y = self.watch_route[0]
        if math.hypot(x-position[0], y-position[1]) < 45. and len(self.watch_route) > 1:
            self.watch_route.pop(0); x, y = self.watch_route[0]
        distance = math.hypot(x-position[0], y-position[1])
        return {"speed_mps": 0. if distance < SETTINGS["arrival_radius_m"] else min(SETTINGS["maximum_speed_mps"], max(3., distance/3)),
                "heading_deg": math.degrees(math.atan2(x-position[0], y-position[1])) % 360., "altitude_m": altitude}
