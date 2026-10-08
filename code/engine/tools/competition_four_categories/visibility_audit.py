"""Referee-only structural and native-evidence visibility checks.

Detected contact identifiers are permitted by the native observation contract.
This module never rewrites a participant DTO and is not an authentication layer,
an anonymizer, a semantic message reviewer or a recovery-checkpoint substitute.
"""
from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

CONTRACT = "native-visibility-evidence@1.0"
TOP = {"schema_version", "session_id", "tick", "observer_faction_id", "controller_slot_id",
       "controlled_entity_ids", "own_entities", "organic_contacts", "shared_contacts",
       "received_messages", "contacts_by_faction", "metadata"}
OWN = {"entity_id", "lifecycle_state", "position_m", "velocity_mps", "heading_deg", "health", "energy"}
ORGANIC = {"contact_id", "observer_entity_id", "estimated_position_m", "observed_tick", "age_ticks", "confidence", "quality"}
SHARED = {"shared_contact_id", "source_contact_id", "observer_entity_id", "estimated_position_m",
          "observed_tick", "age_ticks", "confidence", "quality", "source_sensor_ref",
          "recipient_controller_slot", "delivered_tick", "expiry_tick"}
MESSAGE = {"message_id", "origin_message_id", "sender_entity_id", "recipient_controller_slots",
           "sent_tick", "delivered_tick", "expiry_tick", "payload_type", "payload"}


def plain(value):
    if isinstance(value, Mapping): return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [plain(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True, allow_nan=False).encode()).hexdigest()


def vector(value):
    return isinstance(value, (list, tuple)) and len(value) == 3 and all(type(v) in (int, float) and math.isfinite(v) for v in value)


def contact_key(record):
    return json.dumps([record["evidence_id"], record["owner_entity_id"], record["observed_tick"]])


def structural_failure(observations):
    """Fail on unsupported fields, not on a substring inside a valid token."""
    for observer, observation in observations.items():
        if not isinstance(observation, dict) or set(observation) != TOP:
            return observer, "observation_schema", "top-level observation fields differ from the native controller DTO"
        for field, allowed in (("own_entities", OWN), ("organic_contacts", ORGANIC),
                               ("shared_contacts", SHARED), ("received_messages", MESSAGE)):
            rows = observation[field]
            if not isinstance(rows, (list, tuple)):
                return observer, field, "expected a sequence of native records"
            for index, row in enumerate(rows):
                if not isinstance(row, dict) or set(row) != allowed:
                    return observer, f"{field}[{index}]", "record fields expose unsupported data or omit required evidence"
                identifiers = {"own_entities": ("entity_id", "lifecycle_state"),
                    "organic_contacts": ("contact_id", "observer_entity_id"),
                    "shared_contacts": ("shared_contact_id", "source_contact_id", "observer_entity_id", "recipient_controller_slot"),
                    "received_messages": ("message_id", "origin_message_id", "payload_type")}
                if any(not isinstance(row[k], str) or not row[k] for k in identifiers[field]):
                    return observer, f"{field}[{index}]", "identity fields must be nonempty strings"
                clocks = ("observed_tick", "age_ticks") if field in {"organic_contacts", "shared_contacts"} else ()
                if field == "shared_contacts": clocks += ("delivered_tick", "expiry_tick")
                if field == "received_messages": clocks = ("sent_tick", "delivered_tick", "expiry_tick")
                if any(type(row[k]) is not int or row[k] < 0 for k in clocks):
                    return observer, f"{field}[{index}]", "native times and ages must be nonnegative integers"
                vectors = ("position_m", "velocity_mps") if field == "own_entities" else ("estimated_position_m",) if field in {"organic_contacts", "shared_contacts"} else ()
                if any(not vector(row[k]) for k in vectors):
                    return observer, f"{field}[{index}]", "positions and velocities require three finite numbers"
                scalars = ("heading_deg", "health") if field == "own_entities" else ("confidence", "quality") if field in {"organic_contacts", "shared_contacts"} else ()
                if any(type(row[k]) not in (int, float) or not math.isfinite(row[k]) for k in scalars):
                    return observer, f"{field}[{index}]", "native scalar measurements must be finite numbers"
                if field == "own_entities" and row["energy"] is not None and (type(row["energy"]) not in (int, float) or not math.isfinite(row["energy"])):
                    return observer, f"{field}[{index}]", "invalid own energy measurement"
                if field == "received_messages" and (not isinstance(row["payload"], str) or not isinstance(row["recipient_controller_slots"], (list, tuple)) or any(not isinstance(s, str) or not s for s in row["recipient_controller_slots"])):
                    return observer, f"{field}[{index}]", "invalid message content or recipient scope"
    return None


def audit_observations(observations, *, auditor=None):
    if auditor is not None:
        return auditor.check(observations)
    issue = structural_failure(observations)
    observer, violation, detail = issue or (next(iter(observations), "unknown"), "missing_authority_evidence",
        "a valid-looking DTO is insufficient without native sensing and delivery evidence")
    obs = observations.get(observer, {})
    return {"status": "FAILED_PRIVACY_GATE", "audit_contract": CONTRACT, "observer_id": observer,
            "audit_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "violation": violation, "detail": detail,
            "observed_contact_records": {k: deepcopy(obs.get(k, [])) for k in ("organic_contacts", "shared_contacts")}}


class VisibilityAudit:
    """Audits explicit single-entity candidate controllers using immutable reads.

The authority view, all-side sensor history and transport proof stay here on the
referee side; the policy receives the original unmodified controller DTO only.
"""
    def __init__(self, session, slots, *, faction_id):
        self.view = session.world_view
        self.session_id, self.faction_id = session.session_id, faction_id
        self.resolved_hash, self.catalog_hash = session.resolved.resolved_hash, session.resolved.catalog_hash
        self.slots, self.endpoints = dict(slots), {}
        declared = {str(slot.id): slot for slot in session.resolved.controller_slots}
        if not slots or len(set(slots.values())) != len(slots):
            raise ValueError("visibility audit requires distinct explicit controller slots")
        for entity, slot_id in self.slots.items():
            slot = declared.get(slot_id)
            if (slot is None or slot.faction_id != faction_id or tuple(slot.selector.entity_ids) != (entity,)
                or slot.values.get("controller_endpoint_ref") != entity):
                raise ValueError("audit scope differs from the compiled controller declaration")
            self.endpoints[entity] = entity
        self.last_tick = -1
        self.history = {}
        self.checked_frames = self.checked_observations = 0
        self.evidence_chain = "0" * 64

    def capture(self):
        frame = self.view.presentation_snapshot()
        tick = frame.tick
        if (self.last_tick == -1 and tick != 0) or (self.last_tick >= 0 and tick not in (self.last_tick, self.last_tick+1)):
            raise ValueError("visibility auditing must start at zero and observe every native tick")
        contacts = [r.model_dump(mode="json") for r in frame.combat_contact_evidence]
        history = dict(self.history)
        for r in contacts:
            if r["confirmed"] and r["measurement_position_m"] is not None:
                # age_ticks changes on later reads; the original measured sample does not.
                key = contact_key(r)
                sample = {k: r[k] for k in ("evidence_id", "owner_entity_id", "target_entity_id", "observed_tick",
                    "confidence", "quality", "measurement_position_m", "source_sensor_ref")}
                if key in history and history[key] != sample:
                    raise ValueError("a historical native sensor measurement changed")
                history[key] = sample
        own = {}
        for identifier in self.slots:
            entity = self.view.get_optional(identifier)
            if entity is None or entity.state.lifecycle not in {"active", "degraded"}:
                own[identifier] = []
                continue
            if entity.definition.faction_id != self.faction_id:
                raise ValueError("controlled entity changed to an unauthorized faction")
            s = entity.state
            own[identifier] = [{"entity_id": identifier, "lifecycle_state": s.lifecycle, "position_m": list(s.position_m),
                "velocity_mps": list(s.velocity_mps), "heading_deg": s.heading_deg, "health": s.health, "energy": s.energy}]
        event = frame.event_state
        authority = {"tick": tick, "own": own, "contacts": contacts,
            "present_entity_ids": {e.id for e in self.view.entities_stable()},
            "shared_queue": plain(event.shared_contact_queue), "shared_inboxes": plain(event.shared_contacts_by_controller),
            "message_queue": plain(event.message_queue), "message_inboxes": plain(event.controller_inboxes)}
        return authority, history

    def failure(self, observations, observer, violation, detail):
        obs = observations.get(observer, {})
        return {"status": "FAILED_PRIVACY_GATE", "audit_contract": CONTRACT, "observer_id": observer,
            "audit_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "violation": violation, "detail": detail, "tick": self.view.tick,
            "contact_ids": [r.get("contact_id", r.get("shared_contact_id")) for k in ("organic_contacts", "shared_contacts") for r in obs.get(k, ()) if isinstance(r, dict)],
            "observed_contact_records": {k: deepcopy(obs.get(k, [])) for k in ("organic_contacts", "shared_contacts")}}

    def check(self, observations):
        issue = structural_failure(observations)
        if issue: return self.failure(observations, *issue)
        if set(observations) != set(self.slots):
            return self.failure(observations, next(iter(observations), "unknown"), "controller_set", "participant observation scopes differ from declared slots")
        authority, history = self.capture()
        tick = authority["tick"]
        for identifier, observation in observations.items():
            def fail(key, reason): return self.failure(observations, identifier, key, reason)
            slot, endpoint = self.slots[identifier], self.endpoints[identifier]
            if (observation["schema_version"] != "2.0" or observation["session_id"] != self.session_id
                or type(observation["tick"]) is not int or observation["tick"] != tick
                or observation["observer_faction_id"] != self.faction_id or observation["controller_slot_id"] != slot):
                return fail("scope_or_clock", "observation identity, faction, slot or tick differs from authority")
            expected_ids = [r["entity_id"] for r in authority["own"][identifier]]
            if plain(observation["controlled_entity_ids"]) != expected_ids or plain(observation["own_entities"]) != authority["own"][identifier]:
                return fail("own_state_scope", "unowned, invented or incorrectly projected own-state data")
            metadata = {"resolved_hash": self.resolved_hash, "catalog_hash": self.catalog_hash,
                "controller_scope_contract": "controller-scope@2.0", "controller_endpoint_ref": endpoint,
                "communication_schema_version": "communication@2.0", "scope_is_not_authentication": True}
            if observation["contacts_by_faction"] != {} or observation["metadata"] != metadata:
                return fail("metadata_or_faction_truth", "unsupported metadata or faction-wide truth appeared in a controller DTO")
            organic = {}
            for r in authority["contacts"]:
                if r["owner_entity_id"] != endpoint or not r["confirmed"] or r["target_entity_id"] not in authority["present_entity_ids"]: continue
                if not vector(r["measurement_position_m"]):
                    return fail("contact_position_evidence", "contact location has no frozen native measurement proof")
                organic[r["evidence_id"]] = {"contact_id": r["evidence_id"], "observer_entity_id": r["owner_entity_id"],
                    "estimated_position_m": r["measurement_position_m"], "observed_tick": r["observed_tick"],
                    "age_ticks": r["age_ticks"], "confidence": r["confidence"], "quality": r["quality"]}
            rows = observation["organic_contacts"]
            if len({r["contact_id"] for r in rows}) != len(rows) or {r["contact_id"]: plain(r) for r in rows} != organic:
                return fail("organic_contact_evidence", "contact or position does not match this endpoint's confirmed native sensor evidence")
            shared = {key: value for key, value in authority["shared_inboxes"].get(slot, {}).items() if value["expiry_tick"] >= tick}
            rows = observation["shared_contacts"]
            if len({r["shared_contact_id"] for r in rows}) != len(rows) or {r["shared_contact_id"]: plain(r) for r in rows} != shared:
                return fail("shared_inbox_evidence", "shared contacts differ from the actual receiver inbox")
            for row in rows:
                matches = [q for q in authority["shared_queue"] if q.get("shared_contact_id") == row["shared_contact_id"]
                    and q.get("recipient_controller_slot") == slot and q.get("recipient_entity_id") == identifier]
                if len(matches) != 1: return fail("shared_transport_scope", "shared contact lacks unique recipient transport proof")
                q = matches[0]
                if (q.get("transport_status") != "delivered" or type(q.get("delivered_tick")) is not int
                    or not 0 <= q["generated_tick"] <= q["delivered_tick"] <= tick <= q["expiry_tick"]
                    or q["sender_entity_id"] != row["observer_entity_id"]):
                    return fail("shared_transport_delivery", "a queued, blocked, expired or wrongly scoped contact was exposed")
                expected = {**q["contact_snapshot"], "recipient_controller_slot": slot, "delivered_tick": q["delivered_tick"], "expiry_tick": q["expiry_tick"]}
                if plain(row) != expected: return fail("shared_payload", "shared measurement was altered in transit")
                key = json.dumps([row["source_contact_id"], row["observer_entity_id"], row["observed_tick"]])
                source = history.get(key)
                if (source is None or source["observed_tick"] > q["generated_tick"]
                    or row["estimated_position_m"] != source["measurement_position_m"]
                    or row["confidence"] != source["confidence"] or row["quality"] != source["quality"]
                    or row["source_sensor_ref"] != source["source_sensor_ref"]):
                    return fail("shared_source_measurement", "shared contact has no matching historical native sensor sample")
            inbox = {key: value for key, value in authority["message_inboxes"].get(slot, {}).items() if value["expiry_tick"] >= tick}
            rows = observation["received_messages"]
            if len({r["message_id"] for r in rows}) != len(rows) or {r["message_id"]: plain(r) for r in rows} != inbox:
                return fail("message_inbox_evidence", "messages differ from the native controller inbox")
            for row in rows:
                records = [q for q in authority["message_queue"] if q.get("message_id") == row["message_id"]
                           and q.get("recipient_entity_id") == identifier and slot in q.get("recipient_controller_slots", ())]
                if len(records) != 1: return fail("message_transport_scope", "message lacks unique receiver transport evidence")
                q = records[0]
                if (q.get("transport_status") != "delivered" or type(q.get("delivered_tick")) is not int
                    or not 0 <= q["generated_tick"] <= q["delivered_tick"] <= tick <= q["expiry_tick"]):
                    return fail("message_transport_delivery", "undelivered or expired message exposed")
                expected = {"message_id": q["message_id"], "origin_message_id": q.get("origin_message_id", q["message_id"]),
                    "sender_entity_id": q["sender_entity_id"], "recipient_controller_slots": q["recipient_controller_slots"],
                    "sent_tick": q["generated_tick"], "delivered_tick": q["delivered_tick"], "expiry_tick": q["expiry_tick"],
                    "payload_type": "text/plain", "payload": q["payload"]}
                if plain(row) != expected: return fail("message_payload", "delivered application message differs from its native source record")
        self.history = history
        self.checked_observations += len(observations)
        if tick != self.last_tick: self.checked_frames += 1
        self.last_tick = tick
        authority_receipt = {**authority, "present_entity_ids": sorted(authority["present_entity_ids"])}
        self.evidence_chain = digest([self.evidence_chain, tick, digest(authority_receipt), digest(observations)])
        return None

    def summary(self):
        return {"contract": CONTRACT, "checked_frames": self.checked_frames, "checked_observations": self.checked_observations,
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "last_tick": self.last_tick, "sensor_samples_retained": len(self.history), "evidence_chain_sha256": self.evidence_chain,
            "scope": "controller DTO fields, native sensing and receiver delivery; not authentication, semantic payload review or identity-shortcut calibration"}
