"""Per-controller reactive dispatch using only public duties and its own inbox."""
from copy import deepcopy
import json
import math

from .delivered_dispatch_v1 import valid_task_body


def center(region):
    vertices = region["coordinates_m"]
    return [sum(v[i] for v in vertices)/len(vertices) for i in (0, 1)]


def inside(point, region):
    return all(min(v[a] for v in region["coordinates_m"]) <= point[a] <= max(v[a] for v in region["coordinates_m"]) for a in (0, 1))


def crosses(a, b, region):
    first, last = 0., 1.
    for axis in (0, 1):
        low, high = min(v[axis] for v in region["coordinates_m"]), max(v[axis] for v in region["coordinates_m"])
        delta = b[axis]-a[axis]
        if abs(delta) < 1e-9:
            if not low <= a[axis] <= high: return False
        else:
            x, y = (low-a[axis])/delta, (high-a[axis])/delta
            first, last = max(first, min(x, y)), min(last, max(x, y))
            if first > last: return False
    return True


class ResponsePolicy:
    def __init__(self, brief, identifier, mode):
        if mode not in {"idle", "naive", "coordinated"} or identifier not in brief["responders"]:
            raise ValueError("invalid response controller configuration")
        self.brief, self.identifier, self.mode = deepcopy(brief), identifier, mode
        self.tasks = {r["request_id"]: deepcopy(r) for r in brief["initial_requests"] if identifier in r["observer_ids"]}
        self.versions = {key: (-1, -1, "") for key in self.tasks}
        self.completed, self.seen_messages = set(), set()
        self.dwell, self.route, self.route_key, self.last_tick = {}, [], None, -1

    def command(self, observation):
        tick, entities = observation["tick"], observation["own_entities"]
        if not entities: return None
        if len(entities) != 1 or entities[0]["entity_id"] != self.identifier:
            raise ValueError("response policy received another controller's observation")
        if tick <= self.last_tick:
            raise ValueError("response policy requires increasing observation ticks")
        self.last_tick = tick
        if self.mode == "idle" or tick >= self.brief["scoring_deadline_tick"]: return None
        for message in observation["received_messages"]:
            key = message.get("message_id")
            if key in self.seen_messages or message.get("sender_entity_id") not in self.brief["trusted_dispatch_sources"]:
                continue
            if f"slot.{self.identifier}" not in message.get("recipient_controller_slots", ()):
                continue
            sent, delivered, expiry = [message.get(k) for k in ("sent_tick", "delivered_tick", "expiry_tick")]
            if not isinstance(key, str) or any(type(t) is not int for t in (sent, delivered, expiry)) or not 0 <= sent <= delivered <= tick <= expiry:
                continue
            try: body = json.loads(message.get("payload", ""))
            except (ValueError, TypeError): continue
            if (not valid_task_body(body)
                or self.identifier not in body.get("observer_ids", ())):
                continue
            version = (sent, delivered, key)
            rid = body["request_id"]
            self.seen_messages.add(key)
            if version < self.versions.get(rid, (-1, -1, "")): continue
            old = self.tasks.get(rid)
            if old is None or old["status"] != body["status"]:
                self.dwell.pop(rid, None)
                self.route_key = None
            self.tasks[rid], self.versions[rid] = body, version
        position = entities[0]["position_m"]
        for rid, task in self.tasks.items():
            if task["status"] == "confirmed" and tick <= task["deadline_tick"] and inside(position, task["destination"]):
                self.dwell[rid] = self.dwell.get(rid, 0)+1
                if self.dwell[rid] >= task["dwell_ticks"]: self.completed.add(rid)
            else: self.dwell.pop(rid, None)
        allowed = {"confirmed", "unverified"} if self.mode == "naive" else {"confirmed"}
        tasks = sorted((r for rid, r in self.tasks.items() if rid not in self.completed and r["status"] in allowed and tick <= r["deadline_tick"]),
                       key=lambda r: (-r["priority"], r["request_id"]))
        if not tasks:
            return {"speed_mps": 0., "heading_deg": 0., "altitude_m": position[2]}
        rank = self.brief["responders"].index(self.identifier) if self.mode == "coordinated" else 0
        task = tasks[min(rank, len(tasks)-1)]
        if self.route_key != task["request_id"]:
            goal = center(task["destination"])
            fleet = task["observer_ids"]
            if len(fleet) > 1:
                width = max(v[1] for v in task["destination"]["coordinates_m"])-min(v[1] for v in task["destination"]["coordinates_m"])
                goal[1] += (fleet.index(self.identifier)-(len(fleet)-1)/2)*min(60., width/(len(fleet)+1))
            obstacles = [r for r in self.brief["risk_regions"] if crosses(position, goal, r)]
            self.route = []
            if self.mode == "coordinated" and obstacles:
                floor = min(v[1] for r in obstacles for v in r["coordinates_m"])-160.
                self.route.extend([(position[0], floor), (goal[0], floor)])
            self.route.append(goal); self.route_key = task["request_id"]
        tx, ty = self.route[0]
        if math.hypot(tx-position[0], ty-position[1]) < 45 and len(self.route) > 1:
            self.route.pop(0); tx, ty = self.route[0]
        distance = math.hypot(tx-position[0], ty-position[1])
        return {"speed_mps": 0. if distance < 35 else min(22., max(3., distance/3)),
                "heading_deg": math.degrees(math.atan2(tx-position[0], ty-position[1])) % 360., "altitude_m": 100.}
