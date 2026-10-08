from copy import deepcopy
import json

import pytest

from tools.competition_four_categories.build import zone
from tools.competition_four_categories.identity_tracking_policy import (
    IdentityTrackPolicy, IdentityReportingPolicy, PEER_PROTOCOL, inside_polygon)
from tools.competition_four_categories.track_report_metrics_v1 import PROTOCOL


def brief():
    return {"mobile_observers": ["own.a", "own.b", "own.s"],
        "observers": ["own.a", "own.b", "own.s", "sink"],
        "observer_domains": {"own.a": "air", "own.b": "air", "own.s": "surface", "sink": "shore"},
        "initial_designation_regions": [zone("cue.a", 100., -80., 25.), zone("cue.b", 100., 80., 25.)],
        "track_reporting": {"schema_version": PROTOCOL, "track_ids": ["cue.a", "cue.b"],
            "reporter_ids": ["own.a", "own.b", "own.s"], "recipient_controller_slot": "slot.sink",
            "maximum_age_ticks": 12}}


def contact(token, point, tick=1, owner="own.a"):
    return {"observer_entity_id": owner, "contact_id": token, "observed_tick": tick,
            "estimated_position_m": list(point), "confidence": .9}


def obs(tick=4, own="own.a", contacts=(), shared=(), messages=()):
    return {"tick": tick, "own_entities": [{"entity_id": own, "position_m": [0., 0., 150.]}],
            "organic_contacts": list(contacts), "shared_contacts": list(shared), "received_messages": list(messages)}


def peer(label="cue.a", token="peer-token", point=(400., -80., 150.), measured=30, sent=32, delivered=34, **changes):
    body = {"schema_version": PEER_PROTOCOL, "issued_tick": sent, "bindings": [{"track_id": label,
        "contact_id": token, "observed_tick": measured, "estimated_position_m": list(point)}]}
    return {"sender_entity_id": "own.b", "recipient_controller_slots": ["slot.own.a"],
            "sent_tick": sent, "delivered_tick": delivered, "expiry_tick": 100, "payload": json.dumps(body), **changes}


def test_unrelated_contact_outside_initial_cue_does_not_create_a_phantom_track():
    p = IdentityTrackPolicy(brief(), "own.a")
    p.command(obs(contacts=[contact("outside", [260., 30., 250.])]))
    assert p.bindings == {}
    assert all(t["observed_tick"] is None for t in p.tracks)


def test_persistent_tokens_keep_identity_when_positions_cross():
    p = IdentityTrackPolicy(brief(), "own.a")
    p.command(obs(contacts=[contact("A", [100., -80., 150.]), contact("B", [100., 80., 150.])]))
    p.command(obs(tick=20, contacts=[contact("A", [200., 80., 150.], 19), contact("B", [200., -80., 150.], 19),
                                  contact("distractor", [201., -80., 150.], 19)]))
    assert p.bindings[("own.a", "A")] == 0 and p.bindings[("own.a", "B")] == 1
    assert p.tracks[0]["position"] == [200., 80., 150.]
    assert p.tracks[1]["position"] == [200., -80., 150.]
    assert ("own.a", "distractor") not in p.bindings


def test_two_initial_contacts_in_one_cue_are_ambiguous_not_sorted_by_id():
    p = IdentityTrackPolicy(brief(), "own.a")
    p.command(obs(contacts=[contact("aaa", [100., -80., 150.]), contact("zzz", [102., -80., 160.])]))
    assert p.bindings == {}


def test_late_entry_into_initial_region_is_not_initial_identity_evidence():
    p = IdentityTrackPolicy(brief(), "own.a")
    p.command(obs(tick=50, contacts=[contact("late-stranger", [100., -80., 150.], 49)]))
    assert p.bindings == {}


def test_historical_shared_sample_can_seed_identity_without_becoming_fresh():
    p = IdentityTrackPolicy(brief(), "own.a")
    row = contact("shared", [100., -80., 150.], 1, owner="own.b")
    row["source_contact_id"] = row.pop("contact_id")
    p.command(obs(tick=30, shared=[row]))
    assert p.bindings[("own.b", "shared")] == 0
    assert p.tracks[0]["observed_tick"] == 1
    assert p.acquisition_mode


def test_delivered_peer_binding_allows_unique_late_own_contact_association():
    p = IdentityTrackPolicy(brief(), "own.a")
    p.command(obs(tick=36, messages=[peer()], contacts=[contact("new-own-token", [402., -80., 150.], 35)]))
    assert p.bindings[("own.a", "new-own-token")] == 0
    assert p.tracks[0]["observed_tick"] == 35


@pytest.mark.parametrize("changes", [{"sender_entity_id": "opponent"},
    {"recipient_controller_slots": ["slot.other"]}, {"delivered_tick": 40},
    {"expiry_tick": 33}, {"sent_tick": True}])
def test_untrusted_or_not_yet_delivered_peer_claims_have_no_effect(changes):
    p = IdentityTrackPolicy(brief(), "own.a")
    p.command(obs(tick=36, messages=[peer(**changes)]))
    assert p.bindings == {}


def test_peer_claim_cannot_relabel_an_existing_token_or_contradict_native_shared_data():
    p = IdentityTrackPolicy(brief(), "own.a")
    row = contact("peer-token", [100., -80., 150.], 1, owner="own.b");row["source_contact_id"] = row.pop("contact_id")
    p.command(obs(tick=4, shared=[row]))
    p.command(obs(tick=36, messages=[peer(label="cue.b")]))
    assert p.bindings[("own.b", "peer-token")] == 0 and p.rejected_peer_claims > 0
    q = IdentityTrackPolicy(brief(), "own.a")
    bad = peer(point=(999., 999., 999.), measured=1, sent=2, delivered=3)
    q.command(obs(tick=4, shared=[row], messages=[bad]))
    assert q.tracks[0]["position"] == [100., -80., 150.]


def test_stale_sample_does_not_move_known_track_backwards():
    p = IdentityTrackPolicy(brief(), "own.a")
    p.command(obs(contacts=[contact("A", [100., -80., 150.])]))
    p.command(obs(tick=12, contacts=[contact("A", [180., -80., 150.], 11)]))
    p.command(obs(tick=16, contacts=[contact("A", [110., -80., 150.], 3)]))
    assert p.tracks[0]["observed_tick"] == 11 and p.tracks[0]["position"] == [180., -80., 150.]


def test_reports_use_bound_organic_identity_not_nearest_crossing_target():
    p = IdentityReportingPolicy(brief(), "own.a")
    p.decide(obs(contacts=[contact("A", [100., -80., 150.]), contact("B", [100., 80., 150.])]))
    result = p.decide(obs(tick=20, contacts=[contact("A", [200., 80., 150.], 19), contact("B", [200., -80., 150.], 19)]))
    bodies = [json.loads(x["message"]) for x in result["messages"] if json.loads(x["message"])["schema_version"] == PROTOCOL]
    assert {(b["track_id"], b["contact_id"]) for b in bodies} == {("cue.a", "A"), ("cue.b", "B")}


def test_ablation_changes_only_sink_reports_not_navigation_or_peer_information():
    sample = obs(tick=8, contacts=[contact("A", [100., -80., 150.], 7), contact("B", [100., 80., 150.], 7)])
    results = {mode: IdentityReportingPolicy(brief(), "own.a", mode).decide(sample) for mode in ("honest", "silent", "swapped")}
    assert results["honest"]["navigation"] == results["silent"]["navigation"] == results["swapped"]["navigation"]
    peers = {mode: [x for x in r["messages"] if json.loads(x["message"])["schema_version"] == PEER_PROTOCOL] for mode, r in results.items()}
    assert peers["honest"] == peers["silent"] == peers["swapped"]
    assert all("slot.sink" not in x["recipient_controller_slots"] for x in peers["honest"])
    assert all(json.loads(x["message"])["schema_version"] != PROTOCOL for x in results["silent"]["messages"])


def test_bijective_token_renaming_and_hidden_extra_fields_do_not_change_navigation():
    first = obs(contacts=[contact("A", [100., -80., 150.]), contact("B", [100., 80., 150.])])
    second = deepcopy(first);second["referee_future"] = {"secret": 999}
    second["organic_contacts"][0]["contact_id"] = "unit.x999.decoy"
    second["organic_contacts"][1]["contact_id"] = "random-token"
    a, b = IdentityReportingPolicy(brief(), "own.a"), IdentityReportingPolicy(brief(), "own.a")
    assert a.decide(first)["navigation"] == b.decide(second)["navigation"]
    assert a.tracker.tracks == b.tracker.tracks


def test_acquisition_commands_stay_within_existing_native_control_limit():
    data = brief();data["initial_designation_regions"] = [zone("cue.a", 800., 0., 25.), zone("cue.b", 900., 100., 25.)]
    p = IdentityTrackPolicy(data, "own.a");command = p.command(obs())
    assert p.acquisition_mode and command["speed_mps"] == 80.
    assert IdentityReportingPolicy(brief(), "own.a").decide({"own_entities": []}) == {"navigation": None, "messages": []}


def test_polygon_boundary_and_concavity_are_respected():
    polygon = [[0., 0.], [2., 0.], [2., 1.], [1., 1.], [1., 2.], [0., 2.]]
    assert inside_polygon([0., 1.], polygon)
    assert inside_polygon([.5, 1.5], polygon)
    assert not inside_polygon([1.5, 1.5], polygon)


def test_injected_agents_cannot_claim_undeclared_controller_endpoints():
    from tools.competition_four_categories.validate_tracking_reports import execute
    from types import SimpleNamespace
    with pytest.raises(ValueError, match="controller endpoints"):
        execute(None, brief(), None, "honest", agents={"outsider": SimpleNamespace(identifier="outsider")})


def test_identity_result_requires_actual_policy_and_executor_fingerprints():
    from tools.competition_four_categories.audit import tracking_policy_extension_matches
    from tools.competition_four_categories.validate_identity_tracking import source_fingerprints
    fields = source_fingerprints()
    record = {"policy": "identity-honest", **fields}
    assert tracking_policy_extension_matches(record)
    for key in fields:
        missing = dict(record); missing.pop(key)
        assert not tracking_policy_extension_matches(missing)
    assert not tracking_policy_extension_matches({"policy": "identity-unknown", **fields})
