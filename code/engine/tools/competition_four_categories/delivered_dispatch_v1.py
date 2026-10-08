"""Candidate dispatch metrics gated by native recipient-specific delivery.

Public initial duties and actual delivered notices are distinct evidence sources.
No native events are synthesized and no world or communication state is modified.
"""
from copy import deepcopy
import hashlib
import json
import math
import re

from .recon_metrics_v1 import plain

MODEL_ID = "models.competition-delivered-dispatch"
MODEL_VERSION = "1.0.1"
MODEL_REF = f"{MODEL_ID}@{MODEL_VERSION}"
PROTOCOL = "dispatch-task@1.0"


def contract_hash(body):
    return hashlib.sha256(json.dumps({k: v for k, v in body.items() if k != "status"},
                                    sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _ids(values):
    return isinstance(values, list) and bool(values) and all(isinstance(v, str) and v for v in values) and len(set(values)) == len(values)


def valid_task_body(body):
    fields = {"schema_version", "request_id", "status", "destination", "caution_regions",
              "observer_ids", "deadline_tick", "dwell_ticks", "priority"}
    if (not isinstance(body, dict) or set(body) != fields or body["schema_version"] != PROTOCOL
        or not isinstance(body["request_id"], str) or not body["request_id"]
        or not isinstance(body["status"], str) or body["status"] not in {"confirmed", "unverified", "cancelled"}
        or not _ids(body["observer_ids"]) or not isinstance(body["caution_regions"], list) or len(body["caution_regions"]) > 16
        or any(type(body[k]) is not int or body[k] < 0 for k in ("deadline_tick", "priority"))
        or type(body["dwell_ticks"]) is not int or body["dwell_ticks"] < 1):
        return False
    for region in [body["destination"], *body["caution_regions"]]:
        if (not isinstance(region, dict) or set(region) != {"schema_version", "id", "geometry_type", "coordinates_m"}
            or region["schema_version"] != "2.0" or not isinstance(region["id"], str) or not region["id"]
            or region["geometry_type"] != "polygon" or not isinstance(region["coordinates_m"], list)
            or not 3 <= len(region["coordinates_m"]) <= 64):
            return False
        if any(not isinstance(point, list) or len(point) != 2
               or any(type(v) not in (int, float) or not math.isfinite(v) for v in point) for point in region["coordinates_m"]):
            return False
    return True


class DeliveredDispatchMetricV1:
    def bind_session(self, *, session_id, seed, parameters):
        del session_id, seed
        p = plain(parameters)
        required = {"metric_id", "kind", "requests", "hazards", "source_ids", "observer_slots", "start_tick", "end_tick", "unit"}
        if set(p) != required or p["unit"] != "1":
            raise ValueError("delivered dispatch parameters must match v1")
        if p["kind"] not in {"arrival_fraction", "timeliness", "route_safety", "triage_discipline"} or not isinstance(p["metric_id"], str) or not p["metric_id"]:
            raise ValueError("named supported dispatch metric required")
        if type(p["start_tick"]) is not int or type(p["end_tick"]) is not int or not 0 <= p["start_tick"] < p["end_tick"]:
            raise ValueError("invalid dispatch scoring window")
        if not _ids(p["source_ids"]) or not isinstance(p["observer_slots"], dict) or not p["observer_slots"]:
            raise ValueError("explicit source and receiver scopes required")
        if not _ids(list(p["observer_slots"])) or not _ids(list(p["observer_slots"].values())):
            raise ValueError("observer slots must be unique nonempty identities")
        if not isinstance(p["requests"], list) or not p["requests"]:
            raise ValueError("dispatch requests must not be empty")
        fields = {"request_id", "zone_id", "deadline_tick", "weight", "dwell_ticks", "observer_ids",
                  "initially_known", "required", "contract_sha256", "caution_zone_ids"}
        for r in p["requests"]:
            if set(r) != fields or not isinstance(r["request_id"], str) or not r["request_id"] or not isinstance(r["zone_id"], str) or not r["zone_id"]:
                raise ValueError("request schema mismatch")
            if not _ids(r["observer_ids"]) or not set(r["observer_ids"]) <= set(p["observer_slots"]):
                raise ValueError("request observer scope invalid")
            if type(r["initially_known"]) is not bool or type(r["required"]) is not bool:
                raise ValueError("request flags must be booleans")
            if type(r["deadline_tick"]) is not int or not p["start_tick"] <= r["deadline_tick"] < p["end_tick"] or type(r["dwell_ticks"]) is not int or r["dwell_ticks"] < 1:
                raise ValueError("request timing invalid")
            if type(r["weight"]) not in (int, float) or not math.isfinite(r["weight"]) or r["weight"] <= 0:
                raise ValueError("request weight must be finite and positive")
            if not isinstance(r["contract_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", r["contract_sha256"]):
                raise ValueError("public task content fingerprint required")
            if not isinstance(r["caution_zone_ids"], list) or (r["caution_zone_ids"] and not _ids(r["caution_zone_ids"])):
                raise ValueError("invalid caution zones")
        if not _ids([r["request_id"] for r in p["requests"]]) or not any(r["required"] for r in p["requests"]):
            raise ValueError("unique requests and at least one required duty needed")
        if not isinstance(p["hazards"], list):
            raise ValueError("hazards must be a list")
        for h in p["hazards"]:
            if set(h) != {"zone_id", "activation_event_id"} or not isinstance(h["zone_id"], str) or not h["zone_id"] or (h["activation_event_id"] is not None and (not isinstance(h["activation_event_id"], str) or not h["activation_event_id"])):
                raise ValueError("invalid native hazard declaration")
        self.parameters = deepcopy(p)
        # No sampled ticks means unavailable, even when the metric is declared.
        # Preserve that evidence rather than masking a native checkpoint failure.
        self.last_tick, self.last_input_hash, self.last_value = -1, None, None
        self.notices = {r["request_id"]: {} for r in p["requests"]}
        self.arrivals, self.seen_messages = {}, {}
        self.dwell = {r["request_id"]: {} for r in p["requests"]}
        self.previous_zones = {o: [] for o in p["observer_slots"]}
        self.samples = self.hazard_entity_ticks = self.unverified_entries = 0

    def _deliveries(self, snapshot):
        p = self.parameters
        requests = {r["request_id"]: r for r in p["requests"]}
        records, fingerprints = [], dict(self.seen_messages)
        for raw in snapshot.communications:
            if raw.get("transport_status") != "delivered" or raw.get("sender_entity_id") not in p["source_ids"]:
                continue
            receiver = raw.get("recipient_entity_id")
            if receiver not in p["observer_slots"] or p["observer_slots"][receiver] not in raw.get("recipient_controller_slots", ()):
                continue
            generated, delivered, expiry = [raw.get(k) for k in ("generated_tick", "delivered_tick", "expiry_tick")]
            if any(type(t) is not int for t in (generated, delivered, expiry)) or not 0 <= generated <= delivered <= min(expiry, snapshot.tick):
                continue
            try:
                body = json.loads(raw.get("payload", ""))
            except (ValueError, TypeError):
                continue
            if not valid_task_body(body):
                continue
            r = requests.get(body.get("request_id"))
            if r is None or receiver not in r["observer_ids"] or contract_hash(body) != r["contract_sha256"]:
                continue
            identifier = raw.get("message_id")
            if not isinstance(identifier, str) or not identifier:
                raise ValueError("delivered task lacks a native message identity")
            row = {"request_id": r["request_id"], "observer_id": receiver, "status": body["status"],
                "generated_tick": generated, "delivered_tick": delivered, "message_id": identifier}
            key = json.dumps([identifier, receiver])
            digest = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
            if key in fingerprints and fingerprints[key] != digest:
                raise ValueError("conflicting delivered message identity")
            fingerprints[key] = digest
            records.append((key, digest, row))
        return sorted(records, key=lambda x: (x[2]["generated_tick"], x[2]["delivered_tick"], x[0]))

    def _score(self):
        if not self.samples:
            return None
        p = self.parameters
        if p["kind"] == "route_safety":
            return float(self.hazard_entity_ticks == 0)
        if p["kind"] == "triage_discipline":
            return float(self.unverified_entries == 0)
        required = [r for r in p["requests"] if r["required"]]
        total, value = sum(r["weight"] for r in required), 0.
        for r in required:
            a = self.arrivals.get(r["request_id"])
            if a is None:
                continue
            fraction = 1. if p["kind"] == "arrival_fraction" else 1-a["latency_ticks"]/max(1, r["deadline_tick"]-a["eligible_tick"]+1)
            value += r["weight"]*fraction
        return value/total

    def evaluate(self, snapshot):
        p, tick = self.parameters, snapshot.tick
        active = sorted(o for o in p["observer_slots"] if snapshot.entity_states.get(o, {}).get("lifecycle") in {"active", "degraded"})
        required_zones = {r["zone_id"] for r in p["requests"]} | {z for r in p["requests"] for z in r["caution_zone_ids"]} | {h["zone_id"] for h in p["hazards"]}
        if not required_zones <= set(snapshot.zone_activation):
            raise ValueError("required dispatch zone activation facts missing")
        zones = {o: sorted(z for z in snapshot.zone_membership.get(o, ()) if z in required_zones and snapshot.zone_activation[z]) for o in active}
        deliveries = self._deliveries(snapshot)
        hazard_zones = sorted(h["zone_id"] for h in p["hazards"] if h["activation_event_id"] is None or h["activation_event_id"] in snapshot.event_ids)
        anchor = hashlib.sha256(json.dumps([tick, zones, deliveries, hazard_zones], sort_keys=True).encode()).hexdigest()
        if tick < self.last_tick:
            raise ValueError("dispatch clock cannot go backward")
        if tick == self.last_tick:
            if anchor != self.last_input_hash:
                raise ValueError("conflicting dispatch input for the same tick")
            return {p["metric_id"]: self.last_value}
        if (self.last_tick >= 0 and tick != self.last_tick+1) or (self.last_tick < 0 and tick > p["start_tick"]):
            raise ValueError("dispatch requires every authoritative tick")
        if p["start_tick"] <= tick < p["end_tick"]:
            self.samples += 1
            for r in p["requests"]:
                if r["initially_known"]:
                    for o in r["observer_ids"]:
                        self.notices[r["request_id"]].setdefault(o, {"status": "confirmed", "generated_tick": 0,
                            "delivered_tick": None, "delivery_anchor_tick": None, "eligible_tick": p["start_tick"], "message_id": None, "origin": "public_brief"})
            for key, digest, row in deliveries:
                if key in self.seen_messages:
                    continue
                self.seen_messages[key] = digest
                rid, observer = row["request_id"], row["observer_id"]
                old = self.notices[rid].get(observer)
                if old and (old["generated_tick"], old["delivered_tick"] or -1, old["message_id"] or "") > (row["generated_tick"], row["delivered_tick"], row["message_id"]):
                    continue
                eligible = old["eligible_tick"] if old and old["status"] == row["status"] == "confirmed" else max(p["start_tick"], row["delivered_tick"])
                delivery_anchor = old["delivery_anchor_tick"] if old and old["status"] == row["status"] == "confirmed" else row["delivered_tick"]
                self.notices[rid][observer] = {k: row[k] for k in ("status", "generated_tick", "delivered_tick", "message_id")} | {"eligible_tick": eligible, "delivery_anchor_tick": delivery_anchor, "origin": "native_delivery"}
                if rid not in self.arrivals and (not old or old["status"] != row["status"]):
                    self.dwell[rid].pop(observer, None)
            self.hazard_entity_ticks += sum(bool(set(zones[o]) & set(hazard_zones)) for o in active)
            for r in p["requests"]:
                rid = r["request_id"]
                for o in active:
                    notice = self.notices[rid].get(o)
                    # A command already committed before inbox publication must
                    # not be retroactively charged as an unverified dispatch.
                    if (notice and notice["status"] != "confirmed" and notice["delivered_tick"] is not None
                        and tick > notice["delivered_tick"]+1
                        and set(r["caution_zone_ids"]) & (set(zones[o])-set(self.previous_zones[o]))):
                        self.unverified_entries += 1
                if rid in self.arrivals:
                    continue
                for o in r["observer_ids"]:
                    notice = self.notices[rid].get(o)
                    eligible = notice is not None and notice["status"] == "confirmed" and notice["eligible_tick"] <= tick <= r["deadline_tick"]
                    if o not in active or not eligible or r["zone_id"] not in zones.get(o, ()):
                        self.dwell[rid].pop(o, None)
                        continue
                    self.dwell[rid][o] = self.dwell[rid].get(o, 0)+1
                    if self.dwell[rid][o] >= r["dwell_ticks"]:
                        self.arrivals[rid] = {"tick": tick, "observer_id": o, "eligible_tick": notice["eligible_tick"],
                            "delivered_tick": notice["delivery_anchor_tick"], "latency_ticks": tick-notice["eligible_tick"]}
                        break
            self.previous_zones = {o: zones.get(o, []) for o in p["observer_slots"]}
        self.last_tick, self.last_input_hash, self.last_value = tick, anchor, self._score()
        return {p["metric_id"]: self.last_value}

    def snapshot(self):
        names = ("parameters", "last_tick", "last_input_hash", "last_value", "notices", "arrivals", "seen_messages",
                 "dwell", "previous_zones", "samples", "hazard_entity_ticks", "unverified_entries")
        return deepcopy({k: getattr(self, k) for k in names})

    def restore(self, state):
        state = plain(state)
        if set(state) != set(self.snapshot()) or state["parameters"] != self.parameters:
            raise ValueError("delivered dispatch checkpoint schema/parameters mismatch")
        p, last = self.parameters, state["last_tick"]
        if type(last) is not int or last < -1:
            raise ValueError("invalid dispatch checkpoint clock")
        samples = max(0, min(last, p["end_tick"]-1)-p["start_tick"]+1)
        if type(state["samples"]) is not int or state["samples"] != samples:
            raise ValueError("dispatch checkpoint sample count mismatch")
        for key, maximum in (("hazard_entity_ticks", samples*len(p["observer_slots"])),
                             ("unverified_entries", samples*len(p["observer_slots"])*len(p["requests"]))):
            if type(state[key]) is not int or not 0 <= state[key] <= maximum:
                raise ValueError("invalid dispatch exposure count")
        fingerprint = state["last_input_hash"]
        if (last == -1 and fingerprint is not None) or (last >= 0 and (not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint))):
            raise ValueError("invalid dispatch input fingerprint")
        request_ids = {r["request_id"] for r in p["requests"]}
        if set(state["notices"]) != request_ids or set(state["dwell"]) != request_ids or not set(state["arrivals"]) <= request_ids or set(state["previous_zones"]) != set(p["observer_slots"]):
            raise ValueError("dispatch checkpoint identities mismatch")
        for key, digest in state["seen_messages"].items():
            identity = json.loads(key)
            if not isinstance(identity, list) or len(identity) != 2 or not isinstance(identity[0], str) or identity[1] not in p["observer_slots"] or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("invalid delivered message fingerprint")
        for r in p["requests"]:
            rid = r["request_id"]
            if not set(state["notices"][rid]) <= set(r["observer_ids"]) or not set(state["dwell"][rid]) <= set(r["observer_ids"]):
                raise ValueError("dispatch receiver scope differs")
            for o, n in state["notices"][rid].items():
                if set(n) != {"status", "generated_tick", "delivered_tick", "delivery_anchor_tick", "eligible_tick", "message_id", "origin"} or n["status"] not in {"confirmed", "unverified", "cancelled"}:
                    raise ValueError("invalid notice history")
                if type(n["generated_tick"]) is not int or n["generated_tick"] < 0 or type(n["eligible_tick"]) is not int or not p["start_tick"] <= n["eligible_tick"] <= min(last, p["end_tick"]-1):
                    raise ValueError("invalid notice timing")
                if n["delivery_anchor_tick"] is not None and (type(n["delivery_anchor_tick"]) is not int or not 0 <= n["delivery_anchor_tick"] <= n["eligible_tick"]):
                    raise ValueError("invalid first-confirmation delivery anchor")
                if n["origin"] == "public_brief":
                    if not r["initially_known"] or n["generated_tick"] != 0 or n["delivered_tick"] is not None or n["delivery_anchor_tick"] is not None or n["eligible_tick"] != p["start_tick"] or n["message_id"] is not None or n["status"] != "confirmed":
                        raise ValueError("fake public-brief notice")
                elif n["origin"] == "native_delivery":
                    if type(n["delivered_tick"]) is not int or not 0 <= n["generated_tick"] <= n["delivered_tick"] <= last or json.dumps([n["message_id"], o]) not in state["seen_messages"]:
                        raise ValueError("notice lacks delivered-message provenance")
                    if n["delivery_anchor_tick"] is None and not r["initially_known"]:
                        raise ValueError("native request lost its first delivery anchor")
                else:
                    raise ValueError("unknown notice origin")
            if any(type(count) is not int or not 1 <= count <= samples for count in state["dwell"][rid].values()):
                raise ValueError("invalid delivered dispatch dwell")
            for o in state["dwell"][rid]:
                notice = state["notices"][rid].get(o)
                if notice is None or (rid not in state["arrivals"] and notice["status"] != "confirmed"):
                    raise ValueError("dwell lacks a valid receiver notification")
            if rid in state["arrivals"]:
                a = state["arrivals"][rid]
                if (set(a) != {"tick", "observer_id", "eligible_tick", "delivered_tick", "latency_ticks"}
                    or a["observer_id"] not in r["observer_ids"] or a["observer_id"] not in state["notices"][rid] or any(type(a[k]) is not int for k in ("tick", "eligible_tick", "latency_ticks"))
                    or not p["start_tick"] <= a["eligible_tick"] <= a["tick"] <= min(last, r["deadline_tick"])
                    or a["latency_ticks"] != a["tick"]-a["eligible_tick"] or a["latency_ticks"]+1 < r["dwell_ticks"]
                    or state["dwell"][rid].get(a["observer_id"], 0) < r["dwell_ticks"]):
                    raise ValueError("arrival contradicts native delivered dwell history")
                if a["delivered_tick"] is None:
                    if not r["initially_known"]:
                        raise ValueError("unannounced arrival cannot claim public-brief release")
                elif type(a["delivered_tick"]) is not int or not 0 <= a["delivered_tick"] <= a["eligible_tick"]:
                    raise ValueError("arrival lacks a valid delivery timestamp")
        if state["last_value"] is not None and (type(state["last_value"]) not in (int, float) or not 0 <= state["last_value"] <= 1):
            raise ValueError("invalid delivered dispatch score")
        old = self.snapshot()
        for key, value in state.items():
            setattr(self, key, deepcopy(value))
        if self.last_value != self._score():
            for key, value in old.items():
                setattr(self, key, value)
            raise ValueError("dispatch score disagrees with restored evidence")

    def close(self):
        pass
