"""Candidate opponent and observer agents using only explicit input contracts."""
from copy import deepcopy
import math


class ScheduledNavigationPolicy:
    """Execute a versioned own-side plan through the normal authorized Action API."""

    def __init__(self, plan):
        if set(plan) != {"schema_version", "faction_id", "status", "segments"} or plan["schema_version"] != "scheduled-navigation@1.0":
            raise ValueError("invalid scheduled navigation schema")
        if not isinstance(plan["segments"], list) or not plan["segments"]:
            raise ValueError("navigation plan must not be empty")
        ends = {}
        for segment in sorted(plan["segments"], key=lambda s: (s["entity_id"], s["start_tick"])):
            if set(segment) != {"entity_id", "start_tick", "end_tick", "payload"}:
                raise ValueError("invalid scheduled segment schema")
            first, last = segment["start_tick"], segment["end_tick"]
            if type(first) is not int or type(last) is not int or not 0 <= first < last:
                raise ValueError("segment must have a positive half-open tick interval")
            if first != ends.get(segment["entity_id"], 0):
                raise ValueError("scheduled segments must be contiguous and nonoverlapping")
            ends[segment["entity_id"]] = last
            payload = segment["payload"]
            if set(payload) not in ({"speed_mps", "heading_deg"}, {"speed_mps", "heading_deg", "altitude_m"}):
                raise ValueError("navigation payload contains unsupported fields")
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in payload.values()):
                raise ValueError("navigation controls must be finite numbers")
            if payload["speed_mps"] < 0 or not 0 <= payload["heading_deg"] < 360 or payload.get("altitude_m", 0) < 0:
                raise ValueError("navigation controls outside valid range")
        self.plan = deepcopy(plan)
        self.entity_ids = tuple(sorted(ends))

    def commands(self, tick, observations):
        if set(observations) != set(self.entity_ids):
            raise ValueError("opponent observations must match its own declared fleet")
        available = set()
        for identifier, observation in observations.items():
            own = observation["own_entities"]
            if not own:
                continue
            if len(own) != 1 or own[0]["entity_id"] != identifier:
                raise ValueError("opponent plan cannot command an unowned entity")
            available.add(identifier)
        return {s["entity_id"]: {"payload": deepcopy(s["payload"]), "valid_until_tick": s["end_tick"]-1}
                for s in self.plan["segments"] if s["start_tick"] == tick and s["entity_id"] in available}


class ContactFollowPolicy:
    """Simple per-controller association; no cross-controller truth pooling.

The policy deliberately does not parse an entity ID from a contact token.
Contact identifiers are treated as opaque tokens and are checked against native
sensing/transport evidence by the external audit. Identity-switch scoring remains separate.
"""

    def __init__(self, brief, observer_id):
        if observer_id not in brief["mobile_observers"]:
            raise ValueError("a mobile observer is required")
        self.brief, self.observer_id = deepcopy(brief), observer_id
        index = brief["mobile_observers"].index(observer_id)
        cue = brief["initial_designation_regions"][index % len(brief["initial_designation_regions"])]
        points = cue["coordinates_m"]
        self.last_position = [sum(p[i] for p in points)/len(points) for i in range(2)]
        self.last_observed_tick = None
        self.velocity = [0., 0.]

    def command(self, observation):
        rows = observation["own_entities"]
        if not rows:
            return None
        own = rows[0]
        if len(rows) != 1 or own["entity_id"] != self.observer_id:
            raise ValueError("follow policy received a different controller scope")
        contacts = [c for c in observation["organic_contacts"] if c["age_ticks"] <= 2]
        tick = observation["tick"]
        dt = 0 if self.last_observed_tick is None else min(8, max(0, tick-self.last_observed_tick))
        predicted = [self.last_position[i] + dt*self.velocity[i] for i in range(2)]
        if contacts:
            contact = min(contacts, key=lambda c: (math.hypot(c["estimated_position_m"][0]-predicted[0],
                                                              c["estimated_position_m"][1]-predicted[1]), c["contact_id"]))
            position = contact["estimated_position_m"][:2]
            observed = contact["observed_tick"]
            if math.hypot(position[0]-predicted[0], position[1]-predicted[1]) < 400:
                if self.last_observed_tick is not None and observed > self.last_observed_tick:
                    self.velocity = [(position[i]-self.last_position[i])/(observed-self.last_observed_tick) for i in range(2)]
                self.last_position, self.last_observed_tick = position, observed
                predicted = position
        x, y, altitude = own["position_m"]
        distance = math.hypot(predicted[0]-x, predicted[1]-y)
        domain = self.brief["observer_domains"][self.observer_id]
        maximum = 22. if domain == "air" else 6.
        payload = {"speed_mps": min(maximum, max(0., (distance-170.)/4)),
                   "heading_deg": math.degrees(math.atan2(predicted[0]-x, predicted[1]-y)) % 360}
        if domain == "air":
            payload["altitude_m"] = altitude
        return payload


class CooperativeTrackPolicy:
    """Heuristic coverage of public designations, never referee target IDs.

Air units retain distinct public-designation assignments. A surface unit moves
toward the centroid so it can acquire multiple tracks during an observation
handover. Shared snapshots are accepted as measurements only while fresh by
observed_tick; old samples remain explicitly historical search cues.
"""
    def __init__(self, brief, observer_id):
        if observer_id not in brief["mobile_observers"]:
            raise ValueError("a declared mobile observer is required")
        self.brief, self.observer_id = deepcopy(brief), observer_id
        self.domain = brief["observer_domains"][observer_id]
        self.assignment = brief["mobile_observers"].index(observer_id)
        self.tracks = []
        for region in brief["initial_designation_regions"]:
            points = region["coordinates_m"]
            self.tracks.append({"position": [sum(p[i] for p in points)/len(points) for i in (0,1)],
                                "velocity": [0.,0.], "observed_tick": None})
        if not self.tracks:
            raise ValueError("public designation regions required")

    def _predict(self, track, tick):
        dt = 0 if track["observed_tick"] is None else min(20, max(0,tick-track["observed_tick"]))
        return [track["position"][i]+dt*track["velocity"][i] for i in (0,1)]

    def command(self, observation):
        own = observation["own_entities"]
        if not own: return None
        if len(own) != 1 or own[0]["entity_id"] != self.observer_id:
            raise ValueError("cooperative policy received an unowned entity")
        tick = observation["tick"]
        measurements = []
        for origin, field in enumerate(("organic_contacts", "shared_contacts")):
            for row in observation.get(field, ()):
                observed = row["observed_tick"]
                if type(observed) is not int or not 0 <= tick-observed <= 8 or row["confidence"] <= 0:
                    continue
                point = row["estimated_position_m"][:2]
                measurements.append((observed, origin, list(point)))
        # Spatial deduplication does not parse hidden identities from contact IDs.
        unique = []
        for item in sorted(measurements, key=lambda m: (-m[0],m[1],m[2])):
            if not any(abs(item[0]-other[0]) <= 1 and math.dist(item[2],other[2]) < 25. for other in unique):
                unique.append(item)
        pairs = sorted((math.dist(self._predict(track,tick),m[2]),i,j)
                       for i,track in enumerate(self.tracks) for j,m in enumerate(unique))
        used_tracks, used_measurements = set(), set()
        for distance, i, j in pairs:
            if distance > 400. or i in used_tracks or j in used_measurements: continue
            measured, _, point = unique[j]; track = self.tracks[i]
            if track["observed_tick"] is not None and measured <= track["observed_tick"]:
                used_tracks.add(i); used_measurements.add(j)
                continue
            if track["observed_tick"] is not None:
                elapsed = measured-track["observed_tick"]
                velocity = [(point[a]-track["position"][a])/elapsed for a in (0,1)]
                magnitude = math.hypot(*velocity)
                track["velocity"] = velocity if magnitude <= 30. else [v*30./magnitude for v in velocity]
            track["position"], track["observed_tick"] = point, measured
            used_tracks.add(i); used_measurements.add(j)
        predicted = [self._predict(t,tick) for t in self.tracks]
        if self.domain == "surface":
            aim = [sum(p[i] for p in predicted)/len(predicted) for i in (0,1)]
            stand_off, maximum = 60., 6.
        else:
            aim = predicted[self.assignment % len(predicted)]
            stand_off, maximum = 100., 22.
        x,y,altitude = own[0]["position_m"]
        distance = math.hypot(aim[0]-x,aim[1]-y)
        payload = {"speed_mps": min(maximum,max(0.,(distance-stand_off)/4.)),
                   "heading_deg": math.degrees(math.atan2(aim[0]-x,aim[1]-y)) % 360.}
        if self.domain == "air": payload["altitude_m"] = altitude
        return payload
