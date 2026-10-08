"""Public-DTO tracking reporter; honest/silent/swapped are explicit ablations."""
from copy import deepcopy
import json
import math

from .allocated_tracking_policy import AllocatedTrackPolicy
from .track_report_metrics_v1 import PROTOCOL


class TrackReportingPolicy:
    def __init__(self, brief, observer_id, mode="honest"):
        if mode not in {"honest", "silent", "swapped"}:
            raise ValueError("unknown reporting ablation")
        contract = brief.get("track_reporting", {})
        if contract.get("schema_version") != PROTOCOL or observer_id not in contract.get("reporter_ids", ()):
            raise ValueError("public report contract and authorized reporter required")
        self.brief, self.identifier, self.mode = deepcopy(brief), observer_id, mode
        self.contract = self.brief["track_reporting"]
        self.labels = self.contract["track_ids"]
        if self.labels != [r["id"] for r in brief["initial_designation_regions"]]:
            raise ValueError("report labels must match public designations")
        if mode == "swapped" and len(self.labels) < 2:
            raise ValueError("label-swap ablation needs at least two public tracks")
        self.tracker = AllocatedTrackPolicy(brief, observer_id)

    def decide(self, observation):
        navigation = self.tracker.command(observation)
        if navigation is None or self.mode == "silent":
            return {"navigation": navigation, "messages": []}
        tick = observation["tick"]
        rows = [r for r in observation.get("organic_contacts", ())
                if r.get("observer_entity_id") == self.identifier
                and type(r.get("observed_tick")) is int
                and 0 <= tick-r["observed_tick"] <= self.contract["maximum_age_ticks"]
                and r.get("confidence", 0) > 0]
        pairs = []
        for index in self.tracker.assigned_designations:
            track = self.tracker.tracks[index]
            if track["observed_tick"] is None:
                continue
            for j, row in enumerate(rows):
                prediction = self.tracker._predict(track, row["observed_tick"])
                pairs.append((math.dist(prediction, row["estimated_position_m"]), index, j))
        used_tracks, used_contacts, messages = set(), set(), []
        for distance, index, j in sorted(pairs):
            if distance > 75. or index in used_tracks or j in used_contacts:
                continue
            used_tracks.add(index); used_contacts.add(j)
            row = rows[j]
            label = self.labels[(index+1) % len(self.labels)] if self.mode == "swapped" else self.labels[index]
            body = {"schema_version": PROTOCOL, "track_id": label, "contact_id": row["contact_id"],
                    "observed_tick": row["observed_tick"], "reported_tick": tick}
            messages.append({"message_id": f"track-report-{self.identifier}-{tick}-{index}",
                "sender_id": self.identifier, "recipient_controller_slots": [self.contract["recipient_controller_slot"]],
                "message": json.dumps(body, sort_keys=True)})
        return {"navigation": navigation, "messages": messages}
