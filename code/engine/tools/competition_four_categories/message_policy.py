"""Data-only source-agent messages through existing native Action API.

The dispatcher owns this private script; responders only get actual inbox DTOs.
This does not modify the world, transport queues, observations or event engine.
"""
from copy import deepcopy
import hashlib
import json
import random


class ScheduledMessagePolicy:
    def __init__(self, plan):
        if not isinstance(plan, dict) or set(plan) != {"schema_version", "faction_id", "controller_slots", "messages"}:
            raise ValueError("scheduled message plan schema mismatch")
        if plan["schema_version"] != "scheduled-messages@1.0" or not isinstance(plan["faction_id"], str) or not plan["faction_id"]:
            raise ValueError("versioned source faction required")
        slots = plan["controller_slots"]
        if not isinstance(slots, dict) or not slots or any(not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in slots.items()) or len(set(slots.values())) != len(slots):
            raise ValueError("each source actor needs its own controller slot")
        messages = plan["messages"]
        if not isinstance(messages, list) or not messages:
            raise ValueError("message schedule must be nonempty")
        identities = set()
        previous_tick = -1
        for row in messages:
            if not isinstance(row, dict) or set(row) != {"message_id", "sender_id", "send_tick", "recipient_controller_slots", "message"}:
                raise ValueError("scheduled message entry schema mismatch")
            if row["sender_id"] not in slots or not isinstance(row["message_id"], str) or not row["message_id"] or row["message_id"] in identities:
                raise ValueError("unique message identity and controlled source required")
            if type(row["send_tick"]) is not int or row["send_tick"] < previous_tick:
                raise ValueError("message ticks must be nonnegative and ordered")
            if row["send_tick"] < 0:
                raise ValueError("negative message tick")
            recipients = row["recipient_controller_slots"]
            if not isinstance(recipients, list) or not recipients or any(not isinstance(i, str) or not i for i in recipients) or len(recipients) != len(set(recipients)):
                raise ValueError("unique explicit recipient controller slots required")
            if not isinstance(row["message"], str) or not 0 < len(row["message"]) <= 4096:
                raise ValueError("native message body must fit the existing schema")
            body = json.loads(row["message"])
            if not isinstance(body, dict):
                raise ValueError("scheduled application messages must be JSON objects")
            identities.add(row["message_id"]); previous_tick = row["send_tick"]
        self.plan = deepcopy(plan)

    def actions(self, tick, observations):
        if type(tick) is not int or tick < 0:
            raise ValueError("invalid source-agent clock")
        if set(observations) != set(self.plan["controller_slots"]):
            raise ValueError("source observations do not match the controlled source fleet")
        available = set()
        for identifier, observation in observations.items():
            if observation["tick"] != tick:
                raise ValueError("source observation tick differs from action clock")
            rows = observation["own_entities"]
            if rows and (len(rows) != 1 or rows[0]["entity_id"] != identifier):
                raise ValueError("source policy received another controller's own state")
            if rows:
                available.add(identifier)
        return [deepcopy(row) for row in self.plan["messages"]
                if row["send_tick"] == tick and row["sender_id"] in available]


def sample_schedule(plan, *, seed, maximum_shift_ticks):
    """Sample source-agent behavior, not the World or native event engine.

Each message has its own deterministic substream; per-request issue order is
preserved, so a delayed confirmation cannot be moved ahead of its first alert.
The realized plan must be recorded privately with its content hash.
"""
    ScheduledMessagePolicy(plan)
    if type(seed) is not int or seed < 0 or type(maximum_shift_ticks) is not int or maximum_shift_ticks < 0:
        raise ValueError("nonnegative integer seed and timing bound required")
    sampled, previous = deepcopy(plan), {}
    for row in sampled["messages"]:
        body = json.loads(row["message"])
        key = json.dumps([row["sender_id"], body.get("request_id", row["message_id"])])
        identity = json.dumps([seed, row["sender_id"], row["message_id"], row["message"]])
        rng = random.Random(int(hashlib.sha256(identity.encode()).hexdigest(), 16))
        candidate = max(0, row["send_tick"]+rng.randint(-maximum_shift_ticks, maximum_shift_ticks))
        row["send_tick"] = max(previous.get(key, 0), candidate)
        previous[key] = row["send_tick"]
    sampled["messages"].sort(key=lambda row: (row["send_tick"], row["message_id"]))
    ScheduledMessagePolicy(sampled)
    return sampled
