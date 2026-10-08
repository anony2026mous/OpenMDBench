"""Public-evidence identity tracking and cooperative binding messages.

Tokens are opaque equality keys, not strings encoding target truth. Initial
labels require an unambiguous public cue. Later aliases require fresh spatial
agreement or an actually received, scoped teammate claim. Teammate claims are
agent beliefs, not referee evidence; the native report scorer still judges them.
"""
from copy import deepcopy
import json
import math

from .allocated_tracking_policy import AllocatedTrackPolicy, _point
from .track_report_metrics_v1 import PROTOCOL as REPORT_PROTOCOL

PEER_PROTOCOL = "track-binding@1.0"
INITIAL_SAMPLE_LIMIT = 12
PEER_INTERVAL = 8
ASSOCIATION_RADIUS_M = 35.
ASSOCIATION_MARGIN_M = 20.
ACQUISITION_AIR_SPEED_MPS = 80.  # Existing interceptor-uav control limit, not new dynamics.


def inside_polygon(point, vertices):
    x, y = point[:2]
    inside = False
    for a, b in zip(vertices, vertices[1:]+vertices[:1]):
        ax, ay = a; bx, by = b
        cross = (x-ax)*(by-ay)-(y-ay)*(bx-ax)
        if abs(cross) <= 1e-8 and min(ax, bx)-1e-8 <= x <= max(ax, bx)+1e-8 and min(ay, by)-1e-8 <= y <= max(ay, by)+1e-8:
            return True
        if (ay > y) != (by > y) and x < ax+(y-ay)*(bx-ax)/(by-ay):
            inside = not inside
    return inside


class IdentityTrackPolicy(AllocatedTrackPolicy):
    def __init__(self, brief, observer_id):
        super().__init__(brief, observer_id)
        self.labels = [r["id"] for r in brief["initial_designation_regions"]]
        self.bindings = {}
        self.owner_labels = {}
        self.binding_events = []
        self.rejected_peer_claims = 0
        self.acquisition_mode = False
        self.current_tick = 0

    def _bind(self, key, index, reason, tick):
        if key in self.bindings:
            return self.bindings[key] == index
        pair = (key[0], index)
        if pair in self.owner_labels and self.owner_labels[pair] != key[1]:
            return False
        self.bindings[key] = index
        self.owner_labels[pair] = key[1]
        self.binding_events.append({"tick": tick, "owner": key[0], "contact_id": key[1],
                                    "track_id": self.labels[index], "reason": reason})
        return True

    def _peer_samples(self, observation, *, allowed_senders=None):
        tick = observation["tick"]
        reporters = self.brief["track_reporting"]["reporter_ids"] if allowed_senders is None else allowed_senders
        result = []
        for envelope in observation.get("received_messages", ()):
            try:
                body = json.loads(envelope.get("payload", ""))
            except (ValueError, TypeError):
                continue
            if not isinstance(body, dict) or body.get("schema_version") != PEER_PROTOCOL:
                continue
            sender = envelope.get("sender_entity_id")
            clocks = [envelope.get(k) for k in ("sent_tick", "delivered_tick", "expiry_tick")]
            if (sender not in reporters or sender == self.observer_id
                    or f"slot.{self.observer_id}" not in envelope.get("recipient_controller_slots", ())
                    or any(type(t) is not int for t in clocks)
                    or not 0 <= clocks[0] <= clocks[1] <= tick <= clocks[2]
                    or set(body) != {"schema_version", "issued_tick", "bindings"}
                    or type(body["issued_tick"]) is not int or body["issued_tick"] != clocks[0]
                    or not isinstance(body["bindings"], list) or len(body["bindings"]) > len(self.labels)):
                self.rejected_peer_claims += 1
                continue
            for item in body["bindings"]:
                try:
                    if (not isinstance(item, dict) or set(item) != {"track_id", "contact_id", "observed_tick", "estimated_position_m"}
                            or item["track_id"] not in self.labels or not isinstance(item["contact_id"], str)
                            or not 0 < len(item["contact_id"]) <= 256 or type(item["observed_tick"]) is not int
                            or not 0 <= item["observed_tick"] <= clocks[0]):
                        raise ValueError("invalid peer sample")
                    point = _point(item["estimated_position_m"])
                    known = [r for r in observation.get("shared_contacts", ())
                             if r.get("observer_entity_id") == sender and r.get("source_contact_id") == item["contact_id"]
                             and r.get("observed_tick") == item["observed_tick"]]
                    if any(math.dist(point, _point(r["estimated_position_m"])) > 1e-6 for r in known):
                        raise ValueError("peer claim contradicts a native shared sample")
                except (ValueError, TypeError, KeyError):
                    self.rejected_peer_claims += 1
                    continue
                key = (sender, item["contact_id"])
                if not self._bind(key, self.labels.index(item["track_id"]), "delivered_peer_claim", tick):
                    self.rejected_peer_claims += 1
                    continue
                result.append({"key": key, "observed_tick": item["observed_tick"], "point": point})
        return result

    def _samples(self, observation):
        tick = observation["tick"]
        rows = []
        for field in ("organic_contacts", "shared_contacts"):
            for item in observation.get(field, ()):
                owner = item.get("observer_entity_id")
                token = item.get("contact_id" if field == "organic_contacts" else "source_contact_id")
                measured = item.get("observed_tick")
                if (owner not in self.brief["observer_domains"] or (field == "organic_contacts" and owner != self.observer_id)
                        or not isinstance(token, str) or not token or type(measured) is not int
                        or not 0 <= measured <= tick or item.get("confidence", 0) <= 0):
                    continue
                rows.append({"key": (owner, token), "observed_tick": measured, "point": _point(item["estimated_position_m"])})
        unique = {}
        for row in rows:
            key = (*row["key"], row["observed_tick"])
            if key in unique and math.dist(unique[key]["point"], row["point"]) > 1e-6:
                raise ValueError("conflicting native observation sample")
            unique.setdefault(key, row)
        return sorted(unique.values(), key=lambda r: (r["observed_tick"], r["point"]))

    def _update_known(self, rows):
        for row in rows:
            index = self.bindings.get(row["key"])
            if index is None:
                continue
            track = self.tracks[index]
            measured = row["observed_tick"]
            if track["observed_tick"] is not None and measured <= track["observed_tick"]:
                continue
            if track["observed_tick"] is not None:
                delta = measured-track["observed_tick"]
                velocity = [(row["point"][a]-track["position"][a])/delta for a in range(3)]
                norm = math.sqrt(sum(v*v for v in velocity))
                track["velocity"] = velocity if norm <= 30. else [v*30./norm for v in velocity]
            track["position"], track["observed_tick"] = list(row["point"]), measured

    def _update(self, observation):
        tick = observation["tick"]; self.current_tick = tick
        rows = self._samples(observation)
        candidates = {}
        for row in rows:
            if row["key"] in self.bindings or row["observed_tick"] > INITIAL_SAMPLE_LIMIT:
                continue
            possible = [i for i, region in enumerate(self.brief["initial_designation_regions"])
                        if inside_polygon(row["point"], region["coordinates_m"])]
            if len(possible) == 1:
                candidates.setdefault((row["key"][0], possible[0]), set()).add(row["key"])
        for (_, index), keys in candidates.items():
            if len(keys) == 1:
                self._bind(next(iter(keys)), index, "unambiguous_initial_public_region", tick)
        # Direct/public native cue evidence takes priority over teammate belief.
        rows += self._peer_samples(observation)
        rows.sort(key=lambda r: (r["observed_tick"], r["point"]))
        self._update_known(rows)
        references = [r for r in rows if r["key"] in self.bindings and tick-r["observed_tick"] <= 12]
        for row in rows:
            if row["key"] in self.bindings or tick-row["observed_tick"] > 8:
                continue
            distances = {}
            for ref in references:
                index = self.bindings[ref["key"]]
                if (row["key"][0], index) in self.owner_labels or abs(row["observed_tick"]-ref["observed_tick"]) > 8:
                    continue
                delta = row["observed_tick"]-ref["observed_tick"]
                point = [ref["point"][a]+delta*self.tracks[index]["velocity"][a] for a in range(3)]
                distances[index] = min(distances.get(index, float("inf")), math.dist(point, row["point"]))
            ordered = sorted((distance, index) for index, distance in distances.items())
            if ordered and ordered[0][0] <= ASSOCIATION_RADIUS_M and (len(ordered) == 1 or ordered[1][0]-ordered[0][0] >= ASSOCIATION_MARGIN_M):
                self._bind(row["key"], ordered[0][1], "fresh_unique_cross_observer_measurement", tick)
        self._update_known(rows)

    def _assign(self):
        unknown = [i for i, t in enumerate(self.tracks)
                   if t["observed_tick"] is None or self.current_tick-t["observed_tick"] > 20]
        self.acquisition_mode = bool(unknown and self.domain == "air")
        if self.acquisition_mode:
            return [unknown[self.air.index(self.observer_id) % len(unknown)]]
        return super()._assign()

    def command(self, observation):
        payload = super().command(observation)
        if payload is None or not self.acquisition_mode:
            return payload
        index = self.assigned_designations[0]
        aim = self._predict(self.tracks[index], observation["tick"])
        own = observation["own_entities"][0]["position_m"]
        distance = math.hypot(aim[0]-own[0], aim[1]-own[1])
        payload["speed_mps"] = min(ACQUISITION_AIR_SPEED_MPS, max(0., (distance-35.)/2.))
        return payload


class IdentityReportingPolicy:
    def __init__(self, brief, observer_id, mode="honest"):
        if mode not in {"honest", "silent", "swapped"}:
            raise ValueError("unknown identity report mode")
        self.brief, self.identifier, self.mode = deepcopy(brief), observer_id, mode
        self.contract = self.brief["track_reporting"]
        if observer_id not in self.contract["reporter_ids"] or self.contract["schema_version"] != REPORT_PROTOCOL:
            raise ValueError("declared native reporter required")
        self.tracker = IdentityTrackPolicy(brief, observer_id)

    def decide(self, observation):
        navigation = self.tracker.command(observation)
        if navigation is None:
            return {"navigation": None, "messages": []}
        tick = observation["tick"]; messages = []; peer_bindings = []
        by_track = {}
        for row in observation.get("organic_contacts", ()):
            if row.get("observer_entity_id") != self.identifier:
                continue
            index = self.tracker.bindings.get((self.identifier, row["contact_id"]))
            if index is None or not 0 <= tick-row["observed_tick"] <= self.contract["maximum_age_ticks"]:
                continue
            if index not in by_track or row["observed_tick"] > by_track[index]["observed_tick"]:
                by_track[index] = row
        for index, row in sorted(by_track.items()):
            label = self.tracker.labels[index]
            peer_bindings.append({"track_id": label, "contact_id": row["contact_id"],
                "observed_tick": row["observed_tick"], "estimated_position_m": list(row["estimated_position_m"])})
            if self.mode != "silent":
                sent_label = self.tracker.labels[(index+1) % len(self.tracker.labels)] if self.mode == "swapped" else label
                body = {"schema_version": REPORT_PROTOCOL, "track_id": sent_label, "contact_id": row["contact_id"],
                        "observed_tick": row["observed_tick"], "reported_tick": tick}
                messages.append({"message_id": f"identity-report-{self.identifier}-{tick}-{index}", "sender_id": self.identifier,
                    "recipient_controller_slots": [self.contract["recipient_controller_slot"]], "message": json.dumps(body, sort_keys=True)})
        peers = [f"slot.{i}" for i in self.contract["reporter_ids"] if i != self.identifier]
        if peers and peer_bindings and tick % PEER_INTERVAL == 0:
            body = {"schema_version": PEER_PROTOCOL, "issued_tick": tick, "bindings": peer_bindings}
            messages.append({"message_id": f"identity-peer-{self.identifier}-{tick}", "sender_id": self.identifier,
                "recipient_controller_slots": peers, "message": json.dumps(body, sort_keys=True)})
        return {"navigation": navigation, "messages": messages}
