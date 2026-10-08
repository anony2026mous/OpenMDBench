"""Coverage-aware public-information baseline; no private target plan or scoring state.

Limits below match the current declared candidate sensor/dynamics resources.
They are baseline controls, not changes to native physics or task thresholds.
"""
import math

from .allocated_tracking_policy import _point
from .shore_beacon_policy import BeaconIdentityTrackPolicy, BeaconIdentityReportingPolicy

AIR_SPEED_LIMIT = 80.
SURFACE_SPEED_LIMIT = 12.9
SENSOR_RANGE_M = 450.
WORKING_RANGE_FRACTION = .85
PEER_FRESHNESS_TICKS = 12
OWN_REFRESH_TICKS = 4
ALLOCATION_LOOKAHEAD_TICKS = 60
POLICY_VERSION = "coverage-v2-surface-range-hold"
SURFACE_LOOKAHEAD_TICKS = 20


class CoverageTrackPolicy(BeaconIdentityTrackPolicy):
    def __init__(self, brief, observer_id):
        super().__init__(brief, observer_id)
        self.samples_by_owner = {i: {} for i in range(len(self.tracks))}
        self.native_rows, self.peer_rows = [], []
        self.primary_designations, self.backup_designations = [], []
        self.coverage_aim = None

    def _samples(self, observation):
        self.native_rows = super()._samples(observation)
        return self.native_rows

    def _peer_samples(self, observation):
        self.peer_rows = super()._peer_samples(observation)
        return self.peer_rows

    def _update(self, observation):
        self.native_rows, self.peer_rows = [], []
        super()._update(observation)
        for row in self.native_rows+self.peer_rows:
            index = self.bindings.get(row["key"])
            if index is not None:
                owner = row["key"][0]
                self.samples_by_owner[index][owner] = max(self.samples_by_owner[index].get(owner, -1), row["observed_tick"])

    def _future_point(self, index):
        track = self.tracks[index]
        return [track["position"][a]+ALLOCATION_LOOKAHEAD_TICKS*track["velocity"][a] for a in (0, 1)]

    def _groups(self):
        groups = {i: [] for i in self.brief["mobile_observers"]}
        indices = list(range(len(self.tracks)))
        if len(indices) <= len(self.air):
            for n, owner in enumerate(self.air): groups[owner] = [indices[n % len(indices)]]
            for owner in self.surface: groups[owner] = indices
            return groups
        ground = [i for i in indices if self.tracks[i]["position"][2] is not None and self.tracks[i]["position"][2] <= 40.]
        airborne = [i for i in indices if i not in ground]
        reserved = min(len(self.surface), math.ceil(len(ground)/2))
        for n, index in enumerate(ground):
            if reserved: groups[self.surface[n % reserved]].append(index)
        if not reserved: airborne = indices
        spare = self.surface[reserved:]
        excess = max(0, len(airborne)-len(self.air))
        reachable = sorted((i for i in airborne if self.tracks[i]["position"][2] is not None
                            and self.tracks[i]["position"][2] < SENSOR_RANGE_M*WORKING_RANGE_FRACTION),
                           key=lambda i: (self.tracks[i]["position"][2], i))
        transferred = reachable[:min(len(spare), excess)]
        for owner, index in zip(spare, transferred): groups[owner] = [index]
        airborne = [i for i in airborne if i not in transferred]
        if self.air and airborne:
            if len(airborne) <= len(self.air):
                for n, owner in enumerate(self.air): groups[owner] = [airborne[n % len(airborne)]]
            else:
                points = {i: self._future_point(i) for i in airborne}
                axis = max((0, 1), key=lambda a: max(p[a] for p in points.values())-min(p[a] for p in points.values()))
                ordered = sorted(airborne, key=lambda i: (points[i][axis], i))
                for n, index in enumerate(ordered):
                    groups[self.air[min(len(self.air)-1, n*len(self.air)//len(ordered))]].append(index)
        elif airborne and self.surface:
            for n, index in enumerate(airborne): groups[self.surface[n % len(self.surface)]].append(index)
        return groups

    def _altitude(self, indices, own_altitude):
        known = [self.tracks[i]["position"][2] for i in indices if self.tracks[i]["position"][2] is not None]
        if self.domain != "air": return own_altitude
        desired = sum(known)/len(known)+35.+25.*self.air.index(self.observer_id) if known else own_altitude
        return min(500., max(60., desired))

    def _joint_cover(self, indices, own_altitude, tick):
        points = [self._predict(self.tracks[i], tick) for i in indices]
        centre = [sum(p[a] for p in points)/len(points) for a in (0, 1)]
        altitude = self._altitude(indices, own_altitude)
        feasible = all(p[2] is not None and math.dist([*centre, altitude], p) <= SENSOR_RANGE_M*WORKING_RANGE_FRACTION for p in points)
        return feasible, centre, altitude

    def _surface_observation_goal(self, indices, position, tick):
        if any(self.tracks[i]["position"][2] is None for i in indices):
            return None
        horizon = min(SURFACE_LOOKAHEAD_TICKS, max(0, self.brief.get("scoring_deadline_tick", tick+SURFACE_LOOKAHEAD_TICKS)-tick))
        points = []
        for index in indices:
            current = self._predict(self.tracks[index], tick)
            points.append([current[a]+horizon*self.tracks[index]["velocity"][a] for a in range(3)])
        # Project the current location onto the intersection of predicted
        # sensor footprints. Do not force a ship toward a target's trailing
        # waypoint when its present location already provides coverage.
        for fraction in (WORKING_RANGE_FRACTION, .98):
            radii = [math.sqrt(max(0., (SENSOR_RANGE_M*fraction)**2-(p[2]-position[2])**2)) for p in points]
            if any(radius <= 0. for radius in radii): continue
            goal = list(position[:2])
            for _ in range(32):
                for point, radius in zip(points, radii):
                    dx,dy=goal[0]-point[0],goal[1]-point[1];distance=math.hypot(dx,dy)
                    if distance>radius:
                        goal=[point[0]+dx*radius/distance,point[1]+dy*radius/distance]
            if all(math.dist(goal,p[:2])<=radius+1e-6 for p,radius in zip(points,radii)):
                return goal
        return None

    def command(self, observation):
        own = observation["own_entities"]
        if not own: return None
        if len(own) != 1 or own[0]["entity_id"] != self.observer_id:
            raise ValueError("coverage policy received an unowned endpoint")
        tick = observation["tick"]
        if type(tick) is not int or tick < 0: raise ValueError("native integer tick required")
        position = _point(own[0]["position_m"])
        self._update(observation)
        unknown = [i for i, track in enumerate(self.tracks) if track["observed_tick"] is None]
        if unknown and self.domain == "air":
            indices = [unknown[self.air.index(self.observer_id) % len(unknown)]]
        else:
            indices = list(self._groups()[self.observer_id])
            if not indices:
                indices = [min(range(len(self.tracks)), key=lambda i: math.dist(self._predict(self.tracks[i], tick)[:2], position[:2]))]
        self.primary_designations = list(indices)
        self.backup_designations = []
        for index, track in enumerate(self.tracks):
            if index in indices or track["observed_tick"] is None: continue
            other_fresh = any(owner != self.observer_id and owner in self.brief["track_reporting"]["reporter_ids"]
                              and tick-sample <= PEER_FRESHNESS_TICKS for owner, sample in self.samples_by_owner[index].items())
            if not other_fresh and self._joint_cover(indices+[index], position[2], tick)[0]:
                indices.append(index);self.backup_designations.append(index)
        feasible, centre, altitude = self._joint_cover(indices, position[2], tick)
        self.assigned_designations = list(indices)
        if self.domain == "surface":
            if tick == 0 and all(self.tracks[i]["observed_tick"] is None for i in indices):
                self.coverage_aim = list(position[:2])
                return {"speed_mps": 0., "heading_deg": own[0].get("heading_deg", 90.)}
            goal = self._surface_observation_goal(indices, position, tick)
            if goal is not None:
                self.coverage_aim = goal
                dx,dy=goal[0]-position[0],goal[1]-position[1];distance=math.hypot(dx,dy)
                if distance <= .5:
                    return {"speed_mps": 0., "heading_deg": own[0].get("heading_deg", 90.)}
                heading=math.atan2(dx,dy)
                velocity=[sum(self.tracks[i]["velocity"][a] for i in indices)/len(indices) for a in (0,1)]
                radial=velocity[0]*math.sin(heading)+velocity[1]*math.cos(heading)
                return {"speed_mps": min(SURFACE_SPEED_LIMIT,max(0.,radial+distance/4.)),
                        "heading_deg": math.degrees(heading)%360.}
        if feasible and len(indices) > 1:
            aim = centre
            used = indices
        else:
            chosen = min(indices, key=lambda i: (self.samples_by_owner[i].get(self.observer_id, -1), i))
            used = [chosen]
            point = self._predict(self.tracks[chosen], tick)
            altitude = self._altitude(used, position[2])
            if len(indices) > 1 and point[2] is not None:
                horizontal = math.sqrt(max(0., SENSOR_RANGE_M**2-(point[2]-altitude)**2))*WORKING_RANGE_FRACTION
                dx, dy = centre[0]-point[0], centre[1]-point[1]
                norm = math.hypot(dx, dy)
                fraction = min(1., horizontal/norm) if norm else 0.
                aim = [point[0]+fraction*dx, point[1]+fraction*dy]
            else:
                velocity = self.tracks[chosen]["velocity"][:2]
                norm = math.hypot(*velocity);trail = 100. if self.domain == "surface" else 50.
                aim = [point[a]-trail*velocity[a]/norm for a in (0, 1)] if norm > .1 else point[:2]
        self.coverage_aim = list(aim)
        self.acquisition_mode = any(tick-self.samples_by_owner[i].get(self.observer_id, -1000) > OWN_REFRESH_TICKS for i in used)
        dx, dy = aim[0]-position[0], aim[1]-position[1]
        heading = math.atan2(dx, dy)
        velocity = [sum(self.tracks[i]["velocity"][a] for i in used)/len(used) for a in (0, 1)]
        radial = velocity[0]*math.sin(heading)+velocity[1]*math.cos(heading)
        maximum = AIR_SPEED_LIMIT if self.domain == "air" else SURFACE_SPEED_LIMIT
        payload = {"heading_deg": math.degrees(heading) % 360., "speed_mps": min(maximum, max(0., radial+math.hypot(dx, dy)/3.))}
        if self.domain == "air": payload["altitude_m"] = altitude
        return payload


class CoverageReportingPolicy(BeaconIdentityReportingPolicy):
    def __init__(self, brief, observer_id, mode="honest"):
        super().__init__(brief, observer_id, mode)
        self.tracker = CoverageTrackPolicy(brief, observer_id)
