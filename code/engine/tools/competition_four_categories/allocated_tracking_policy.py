"""Development tracking baseline using only each controller's public DTO.

This is a positional association heuristic, not proof of identity preservation.
Designation ordering comes from the public brief. Contact tokens are never parsed,
and no target-domain labels, future routes or referee state are consumed.
"""
from copy import deepcopy
import math


def _point(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 3
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in value)):
        raise ValueError("finite three-dimensional public position required")
    return list(value)


class AllocatedTrackPolicy:
    """Allocate observed low tracks to surface assets and remaining tracks to UAVs.

For fewer tracks than UAVs, preserve overlapping coverage for sensor handover.
For a larger task, distribute public designation indices instead of leaving the
third contact unassigned. Altitude commands use measured altitude, not truth.
The conservative flight band and standoff are baseline tactics, not new physics.
"""

    def __init__(self, brief, observer_id):
        self.brief, self.observer_id = deepcopy(brief), observer_id
        mobile = brief["mobile_observers"]
        domains = brief["observer_domains"]
        if len(set(mobile)) != len(mobile) or observer_id not in mobile:
            raise ValueError("a unique declared mobile observer is required")
        if any(domains.get(i) not in {"air", "surface"} for i in mobile):
            raise ValueError("unsupported public observer domain")
        self.domain = domains[observer_id]
        self.air = [i for i in mobile if domains[i] == "air"]
        self.surface = [i for i in mobile if domains[i] == "surface"]
        self.tracks = []
        for region in brief["initial_designation_regions"]:
            points = region["coordinates_m"]
            if not points or any(len(p) != 2 or any(not math.isfinite(v) for v in p) for p in points):
                raise ValueError("finite public designation polygon required")
            self.tracks.append({
                "position": [sum(p[a] for p in points)/len(points) for a in (0, 1)] + [None],
                "velocity": [0., 0., 0.], "observed_tick": None})
        if not self.tracks:
            raise ValueError("public designation regions required")
        self.assigned_designations = []

    def _predict(self, track, tick):
        dt = 0 if track["observed_tick"] is None else min(20, max(0, tick-track["observed_tick"]))
        return [None if p is None else p+dt*v for p, v in zip(track["position"], track["velocity"])]

    def _update(self, observation):
        tick = observation["tick"]
        measurements = []
        for origin, field in enumerate(("organic_contacts", "shared_contacts")):
            for row in observation.get(field, ()):
                measured = row["observed_tick"]
                if type(measured) is not int or not 0 <= tick-measured <= 8 or row["confidence"] <= 0:
                    continue
                measurements.append((measured, origin, _point(row["estimated_position_m"])))
        unique = []
        for item in sorted(measurements, key=lambda x: (-x[0], x[1], x[2])):
            if not any(abs(item[0]-other[0]) <= 1 and math.dist(item[2], other[2]) < 10. for other in unique):
                unique.append(item)
        used_tracks = set()
        # A newly received packet can contain an older sample of an already
        # updated track. Do not give its leftover sample to a different cue.
        for measured in sorted({row[0] for row in unique}, reverse=True):
            samples = []
            for timestamp, _, point in unique:
                if timestamp != measured:
                    continue
                explained = False
                for track in self.tracks:
                    if track["observed_tick"] is None:
                        continue
                    age = measured-track["observed_tick"]
                    historical = [p+age*v for p, v in zip(track["position"], track["velocity"])]
                    if -8 <= age <= 0 and math.dist(historical, point) <= 25.:
                        explained = True
                        break
                if not explained:
                    samples.append(point)
            pairs = []
            for i, track in enumerate(self.tracks):
                if i in used_tracks:
                    continue
                for j, point in enumerate(samples):
                    if track["observed_tick"] is not None:
                        elapsed = measured-track["observed_tick"]
                        if elapsed <= 0 or math.dist(track["position"], point) > 30.*elapsed+20.:
                            continue
                    predicted = self._predict(track, measured)
                    dimensions = 2 if predicted[2] is None else 3
                    pairs.append((math.dist(predicted[:dimensions], point[:dimensions]), i, j))
            used_measurements = set()
            for distance, i, j in sorted(pairs):
                if distance > 400. or i in used_tracks or j in used_measurements:
                    continue
                point, track = samples[j], self.tracks[i]
                used_tracks.add(i)
                used_measurements.add(j)
                if track["observed_tick"] is not None:
                    elapsed = measured-track["observed_tick"]
                    velocity = [(point[a]-track["position"][a])/elapsed for a in range(3)]
                    magnitude = math.sqrt(sum(v*v for v in velocity))
                    track["velocity"] = velocity if magnitude <= 30. else [v*30./magnitude for v in velocity]
                track["position"], track["observed_tick"] = point, measured

    def _assign(self):
        count = len(self.tracks)
        if count <= len(self.air):
            return (list(range(count)) if self.domain == "surface"
                    else [self.air.index(self.observer_id) % count])
        groups = {i: [] for i in self.brief["mobile_observers"]}
        capacity = math.ceil(count/len(groups))
        low = [i for i, t in enumerate(self.tracks) if t["position"][2] is not None and t["position"][2] <= 40.]
        unknown = [i for i, t in enumerate(self.tracks) if t["position"][2] is None]
        selected = (low+unknown)[:capacity*len(self.surface)] if self.air else list(range(count))
        for index, track in enumerate(selected):
            groups[self.surface[index % len(self.surface)]].append(track)
        remainder = [i for i in range(count) if i not in selected]
        for index, track in enumerate(remainder):
            groups[self.air[index % len(self.air)]].append(track)
        return groups[self.observer_id] or list(range(count))

    def command(self, observation):
        own = observation["own_entities"]
        if not own:
            return None
        if len(own) != 1 or own[0]["entity_id"] != self.observer_id:
            raise ValueError("allocated policy received an unowned entity")
        if type(observation["tick"]) is not int or observation["tick"] < 0:
            raise ValueError("nonnegative integer observation tick required")
        position = _point(own[0]["position_m"])
        self._update(observation)
        indices = self._assign()
        self.assigned_designations = list(indices)
        predictions = [self._predict(self.tracks[i], observation["tick"]) for i in indices]
        aim = [sum(p[a] for p in predictions)/len(predictions) for a in (0, 1)]
        dx, dy = aim[0]-position[0], aim[1]-position[1]
        distance = math.hypot(dx, dy)
        heading = math.atan2(dx, dy)
        velocity = [sum(self.tracks[i]["velocity"][a] for i in indices)/len(indices) for a in (0, 1)]
        radial = velocity[0]*math.sin(heading)+velocity[1]*math.cos(heading)
        standoff, maximum = (45., 6.) if self.domain == "surface" else (35., 22.)
        payload = {"speed_mps": min(maximum, max(0., radial+(distance-standoff)/3.)),
                   "heading_deg": math.degrees(heading) % 360.}
        if self.domain == "air":
            altitudes = [p[2] for p in predictions if p[2] is not None]
            desired = (sum(altitudes)/len(altitudes)+35.+25.*self.air.index(self.observer_id)
                       if altitudes else position[2])
            payload["altitude_m"] = max(60., min(500., desired))
        return payload
