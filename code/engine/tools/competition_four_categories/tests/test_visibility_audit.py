from copy import deepcopy
from types import SimpleNamespace as NS

import pytest

from openmdbench.world.checkpoint_v2 import CheckpointContactEvidenceV2
from tools.competition_four_categories.visibility_audit import VisibilityAudit, audit_observations, CONTRACT


class View:
    def __init__(self):
        self.tick = 0
        self.entities = {}
        for identifier, faction, x in (("own", "red", 0.), ("source", "red", 100.), ("unit.x01", "blue", 900.), ("unseen", "blue", 2000.)):
            self.entities[identifier] = NS(id=identifier, definition=NS(faction_id=faction),
                state=NS(lifecycle="active", position_m=(x, 0., 0.), velocity_mps=(0., 0., 0.), heading_deg=90., health=1., energy=1.))
        self.contacts = []
        self.event = NS(shared_contact_queue=[], shared_contacts_by_controller={}, message_queue=[], controller_inboxes={})
    def get_optional(self, identifier): return self.entities.get(identifier)
    def entities_stable(self): return tuple(self.entities.values())
    def presentation_snapshot(self): return NS(tick=self.tick, combat_contact_evidence=self.contacts, event_state=self.event)


def setup():
    view = View()
    slot = NS(id="slot.own", faction_id="red", selector=NS(entity_ids=("own",)), values={"controller_endpoint_ref": "own"})
    session = NS(session_id="session", world_view=view, resolved=NS(resolved_hash="resolved", catalog_hash="catalog", controller_slots=(slot,)))
    return view, VisibilityAudit(session, {"own": "slot.own"}, faction_id="red")


def observation(view):
    s = view.entities["own"].state
    return {"schema_version": "2.0", "session_id": "session", "tick": view.tick, "observer_faction_id": "red",
        "controller_slot_id": "slot.own", "controlled_entity_ids": ["own"],
        "own_entities": [{"entity_id": "own", "lifecycle_state": s.lifecycle, "position_m": list(s.position_m),
            "velocity_mps": list(s.velocity_mps), "heading_deg": s.heading_deg, "health": s.health, "energy": s.energy}],
        "organic_contacts": [], "shared_contacts": [], "received_messages": [], "contacts_by_faction": {},
        "metadata": {"resolved_hash": "resolved", "catalog_hash": "catalog", "controller_scope_contract": "controller-scope@2.0",
            "controller_endpoint_ref": "own", "communication_schema_version": "communication@2.0", "scope_is_not_authentication": True}}


def sensed(owner="own"):
    return CheckpointContactEvidenceV2(evidence_id=f"sensor.contact.{owner}.unit.x01", owner_entity_id=owner,
        target_entity_id="unit.x01", observed_tick=0, age_ticks=0, max_age_ticks=2, confidence=.8, minimum_confidence=.5,
        quality=.9, measurement_position_m=(950., 20., 0.), confirmed=True, source_sensor_ref="sensor.test@1.0.0")


def contact(record):
    return {"contact_id": record.evidence_id, "observer_entity_id": record.owner_entity_id,
        "estimated_position_m": list(record.measurement_position_m), "observed_tick": record.observed_tick,
        "age_ticks": record.age_ticks, "confidence": record.confidence, "quality": record.quality}


def test_detected_native_entity_identifier_is_not_by_itself_a_privacy_failure():
    view, audit = setup(); record = sensed(); view.contacts = [record]
    obs = observation(view); obs["organic_contacts"] = [contact(record)]; before = deepcopy(obs)
    assert audit.check({"own": obs}) is None
    assert "unit.x01" in obs["organic_contacts"][0]["contact_id"]
    assert obs == before and view.tick == 0
    assert audit.summary()["contract"] == CONTRACT


def test_valid_looking_dto_without_authority_cannot_silently_pass():
    view, _ = setup()
    assert audit_observations({"own": observation(view)})["violation"] == "missing_authority_evidence"


@pytest.mark.parametrize("field", ["future_events", "hidden_role", "rng_state", "mission_states", "terminal_result"])
def test_referee_field_injection_fails_even_without_a_suspicious_identifier(field):
    view, audit = setup(); obs = observation(view); obs[field] = {"secret": 1}
    assert audit.check({"own": obs})["violation"] == "observation_schema"


def test_undetected_enemy_truth_cannot_be_exposed_as_own_or_faction_data():
    for kind in ("own", "faction"):
        view, audit = setup(); obs = observation(view)
        if kind == "own": obs["own_entities"][0]["entity_id"] = "unseen"
        else: obs["contacts_by_faction"] = {"blue": [{"entity_id": "unseen", "position_m": [2000., 0., 0.]}]}
        assert audit.check({"own": obs}) is not None


def test_guessing_a_contact_token_does_not_create_sensor_evidence():
    view, audit = setup(); obs = observation(view); obs["organic_contacts"] = [contact(sensed())]
    assert audit.check({"own": obs})["violation"] == "organic_contact_evidence"


def test_true_position_cannot_replace_a_noisy_native_measurement():
    view, audit = setup(); r = sensed(); view.contacts = [r]; obs = observation(view)
    obs["organic_contacts"] = [contact(r)]; obs["organic_contacts"][0]["estimated_position_m"] = [900., 0., 0.]
    assert audit.check({"own": obs})["violation"] == "organic_contact_evidence"


def test_another_observers_detection_is_not_an_organic_contact_for_this_endpoint():
    view, audit = setup(); r = sensed("source"); view.contacts = [r]; obs = observation(view); obs["organic_contacts"] = [contact(r)]
    assert audit.check({"own": obs})["violation"] == "organic_contact_evidence"


def test_hidden_attributes_cannot_be_added_to_a_legitimate_contact():
    view, audit = setup(); r = sensed(); view.contacts = [r]; obs = observation(view); obs["organic_contacts"] = [contact(r)]
    obs["organic_contacts"][0]["target_entity_id"] = "unit.x01"
    assert audit.check({"own": obs})["violation"] == "organic_contacts[0]"


def prepare_shared():
    view, audit = setup(); r = sensed("source"); view.contacts = [r]
    snapshot = {"shared_contact_id": "shared-contact:measured:slot.own", "source_contact_id": r.evidence_id,
        "observer_entity_id": "source", "estimated_position_m": list(r.measurement_position_m), "observed_tick": 0,
        "age_ticks": 0, "confidence": .8, "quality": .9, "source_sensor_ref": r.source_sensor_ref}
    q = {"shared_contact_id": snapshot["shared_contact_id"], "source_contact_id": r.evidence_id,
        "sender_entity_id": "source", "recipient_entity_id": "own", "recipient_controller_slot": "slot.own",
        "generated_tick": 0, "delivered_tick": 1, "expiry_tick": 8, "transport_status": "delivered", "contact_snapshot": snapshot}
    assert audit.check({"own": observation(view)}) is None
    view.tick = 1; view.contacts = []; view.event.shared_contact_queue = [q]
    delivered = {**deepcopy(snapshot), "recipient_controller_slot": "slot.own", "delivered_tick": 1, "expiry_tick": 8}
    view.event.shared_contacts_by_controller = {"slot.own": {delivered["shared_contact_id"]: deepcopy(delivered)}}
    obs = observation(view); obs["shared_contacts"] = [delivered]
    return view, audit, obs


def test_shared_delivery_retains_historical_measurement_after_source_contact_disappears():
    view, audit, obs = prepare_shared()
    assert audit.check({"own": obs}) is None
    assert audit.summary()["sensor_samples_retained"] == 1


@pytest.mark.parametrize("change", ["queued", "blocked", "wrong_receiver", "premature"])
def test_even_matching_cached_shared_data_needs_actual_recipient_delivery(change):
    view, audit, obs = prepare_shared(); q = view.event.shared_contact_queue[0]
    if change in {"queued", "blocked"}: q["transport_status"] = change
    elif change == "wrong_receiver": q["recipient_entity_id"] = "source"
    else: q["delivered_tick"] = 2
    failure = audit.check({"own": obs})
    assert failure["violation"] in {"shared_transport_scope", "shared_transport_delivery"}


def test_shared_inbox_and_packet_cannot_jointly_fabricate_a_source_measurement():
    view, audit, obs = prepare_shared(); sid = obs["shared_contacts"][0]["shared_contact_id"]
    for r in (obs["shared_contacts"][0], view.event.shared_contacts_by_controller["slot.own"][sid], view.event.shared_contact_queue[0]["contact_snapshot"]):
        r["estimated_position_m"] = [2000., 0., 0.]
    assert audit.check({"own": obs})["violation"] == "shared_source_measurement"


def prepare_message():
    view, audit = setup(); assert audit.check({"own": observation(view)}) is None; view.tick = 1
    q = {"message_id": "msg/own", "origin_message_id": "msg", "sender_entity_id": "source",
        "recipient_entity_id": "own", "recipient_controller_slots": ["slot.own"], "generated_tick": 0,
        "delivered_tick": 1, "expiry_tick": 8, "transport_status": "delivered",
        "payload": 'A source may report its observed unit.x01 token; this is not an extra oracle field.'}
    row = {"message_id": q["message_id"], "origin_message_id": q["origin_message_id"], "sender_entity_id": q["sender_entity_id"],
        "recipient_controller_slots": q["recipient_controller_slots"], "sent_tick": 0, "delivered_tick": 1,
        "expiry_tick": 8, "payload_type": "text/plain", "payload": q["payload"]}
    view.event.message_queue = [q]; view.event.controller_inboxes = {"slot.own": {row["message_id"]: deepcopy(row)}}
    obs = observation(view); obs["received_messages"] = [row]
    return view, audit, obs


def test_real_message_content_is_checked_against_transport_not_keyword_censored():
    view, audit, obs = prepare_message()
    assert audit.check({"own": obs}) is None


@pytest.mark.parametrize("change", ["blocked", "wrong_receiver", "payload", "future"])
def test_message_cache_alone_does_not_prove_delivery(change):
    view, audit, obs = prepare_message(); q = view.event.message_queue[0]
    if change == "blocked": q["transport_status"] = "blocked"
    elif change == "wrong_receiver": q["recipient_entity_id"] = "source"
    elif change == "future": q["delivered_tick"] = 3
    else: q["payload"] = "different actual source content"
    assert audit.check({"own": obs}) is not None


def test_audit_cannot_skip_unseen_intermediate_frames_or_start_mid_episode():
    view, audit = setup(); view.tick = 3
    with pytest.raises(ValueError, match="every native tick"):
        audit.check({"own": observation(view)})
    view.tick = 0; assert audit.check({"own": observation(view)}) is None
    view.tick = 2
    with pytest.raises(ValueError, match="every native tick"):
        audit.check({"own": observation(view)})
