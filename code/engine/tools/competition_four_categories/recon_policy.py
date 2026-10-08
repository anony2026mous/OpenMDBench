"""Public-brief search and native contact-report baselines."""
from copy import deepcopy
import json
import math


class SearchPolicy:
    def __init__(self, brief, entity_id, mode):
        if mode not in {"idle", "sweep", "coordinated"}:
            raise ValueError("invalid search baseline")
        self.brief, self.entity_id, self.mode = deepcopy(brief), entity_id, mode
        assets = [a for a in brief["own_assets"] if a["entity_id"] == entity_id]
        if len(assets) != 1:
            raise ValueError("search policy needs one declared own asset")
        self.asset, self.index = assets[0], 0
        assigned = brief["suggested_sector_assignments"].get(entity_id, [])
        self.waypoints = []
        for sector in brief["search_sectors"]:
            if mode == "coordinated" and sector["sector_id"] not in assigned:
                continue
            for cell in sector["cells"]:
                points = cell["coordinates_m"]
                self.waypoints.append([sum(p[i] for p in points)/len(points) for i in range(2)])

    def _own(self, observation):
        rows = observation["own_entities"]
        if not rows:
            return None
        if len(rows) != 1 or rows[0]["entity_id"] != self.entity_id:
            raise ValueError("search policy received another controller's observation")
        return rows[0]

    def navigation(self, observation):
        own = self._own(observation)
        tick = observation["tick"]
        if own is None or self.mode == "idle" or self.asset["domain"] == "shore" or not self.waypoints or tick >= self.brief["scoring_deadline_tick"]:
            return None
        position = own["position_m"]
        goal = self.waypoints[self.index]
        if math.dist(position[:2], goal) <= 80.:
            self.index = (self.index+1) % len(self.waypoints)
            goal = self.waypoints[self.index]
        dx, dy = goal[0]-position[0], goal[1]-position[1]
        speed = 12. if self.asset["domain"] == "air" else 6.
        payload = {"speed_mps": speed if math.hypot(dx, dy) > 40. else 0.,
                   "heading_deg": math.degrees(math.atan2(dx, dy)) % 360.}
        if self.asset["domain"] == "air":
            payload["altitude_m"] = max(60., position[2])
        return {"payload": payload, "valid_until_tick": min(tick+4, self.brief["scoring_deadline_tick"])}

    def report(self, observation):
        if self._own(observation) is None:
            return None
        protocol, tick = self.brief["report_protocol"], observation["tick"]
        if (self.mode != "coordinated" or self.entity_id == protocol["recipient_entity_id"]
            or tick >= self.brief["scoring_deadline_tick"] or tick % protocol["report_interval_ticks"]):
            return None
        contacts = [{"contact_id": c["contact_id"], "observed_tick": c["observed_tick"]}
                    for c in observation["organic_contacts"] if c["age_ticks"] <= 1 and c["confidence"] > 0]
        contacts.sort(key=lambda c: (c["contact_id"], c["observed_tick"]))
        if not contacts:
            return None
        return {"recipient_controller_slots": [protocol["recipient_controller_slot"]],
            "message": json.dumps({"schema_version": protocol["schema_version"], "contacts": contacts[:16]}, sort_keys=True)}
