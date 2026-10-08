from copy import deepcopy

import pytest

from tools.competition_four_categories.allocated_tracking_policy import AllocatedTrackPolicy
from tools.competition_four_categories.build import zone


def brief(centres=((300., -180.), (350., 180.), (300., 0.))):
    return {"mobile_observers": ["air.a", "air.b", "surface"],
            "observer_domains": {"air.a": "air", "air.b": "air", "surface": "surface"},
            "initial_designation_regions": [zone(f"cue.{i}", x, y, 60.) for i, (x, y) in enumerate(centres)]}


def contact(position, tick=4, token="opaque"):
    return {"contact_id": token, "observed_tick": tick, "age_ticks": 0,
            "estimated_position_m": list(position), "confidence": .9}


def observed(identifier, tick=4, contacts=(), shared=()):
    return {"tick": tick, "own_entities": [{"entity_id": identifier,
            "position_m": [0., 0., 100. if identifier.startswith("air") else 0.]}],
            "organic_contacts": list(contacts), "shared_contacts": list(shared)}


def three_contacts():
    return [contact([300., -180., 0.]), contact([350., 180., 0.]), contact([300., 0., 250.])]


def test_three_contacts_are_allocated_without_omitting_the_airborne_contact():
    assigned, commands = {}, {}
    for identifier in brief()["mobile_observers"]:
        policy = AllocatedTrackPolicy(brief(), identifier)
        commands[identifier] = policy.command(observed(identifier, contacts=three_contacts()))
        assigned[identifier] = policy.assigned_designations
    assert assigned == {"air.a": [1], "air.b": [2], "surface": [0]}
    assert commands["air.b"]["altitude_m"] == 310.
    assert commands["air.a"]["altitude_m"] == 60.
    assert "altitude_m" not in commands["surface"]


def test_small_track_set_retains_redundant_surface_handover_coverage():
    policy = AllocatedTrackPolicy(brief(((300., -80.), (350., 150.))), "surface")
    policy.command(observed("surface"))
    assert policy.assigned_designations == [0, 1]


def test_same_horizontal_position_at_different_altitudes_is_not_one_contact():
    policy = AllocatedTrackPolicy(brief(((300., 0.), (300., 0.))), "air.a")
    policy.command(observed("air.a", contacts=[contact([300., 0., 0.]), contact([300., 0., 250.])]))
    assert sorted(t["position"][2] for t in policy.tracks) == [0., 250.]


def test_duplicate_sensor_samples_do_not_create_two_tracks():
    policy = AllocatedTrackPolicy(brief(), "air.a")
    row = contact([300., -180., 0.])
    policy.command(observed("air.a", contacts=[row], shared=[row]))
    assert sum(t["observed_tick"] is not None for t in policy.tracks) == 1
    policy.command(observed("air.a", tick=8, shared=[row]))
    assert sum(t["observed_tick"] is not None for t in policy.tracks) == 1


@pytest.mark.parametrize("sample_tick", [0, 31, True])
def test_stale_future_or_boolean_sample_ticks_are_not_fresh(sample_tick):
    policy = AllocatedTrackPolicy(brief(), "surface")
    policy.command(observed("surface", tick=30, shared=[contact([300., -180., 0.], sample_tick)]))
    assert all(t["observed_tick"] is None for t in policy.tracks)


def test_tokens_hidden_keys_and_measurement_order_do_not_change_commands():
    first = observed("air.b", contacts=three_contacts())
    second = deepcopy(first)
    second["organic_contacts"].reverse()
    for row in second["organic_contacts"]: row["contact_id"] = "unit.x99.hidden-role"
    second["referee_future"] = {"route": [999, 999], "target_role": "secret"}
    a, b = AllocatedTrackPolicy(brief(), "air.b"), AllocatedTrackPolicy(brief(), "air.b")
    assert a.command(first) == b.command(second)
    assert a.tracks == b.tracks


def test_empty_owned_state_is_safe_but_other_ownership_is_rejected():
    policy = AllocatedTrackPolicy(brief(), "surface")
    assert policy.command({"own_entities": []}) is None
    with pytest.raises(ValueError, match="unowned"):
        policy.command(observed("air.a"))


@pytest.mark.parametrize("position", [[float("nan"), 0., 0.], [0., float("inf"), 0.], [0., 0.], [True, 0., 0.]])
def test_nonfinite_or_malformed_measurements_fail_closed(position):
    with pytest.raises(ValueError, match="finite"):
        AllocatedTrackPolicy(brief(), "surface").command(observed("surface", contacts=[contact(position)]))


def test_predictions_remain_bounded_and_commands_stay_inside_baseline_envelope():
    policy = AllocatedTrackPolicy(brief(), "air.b")
    policy.command(observed("air.b", contacts=three_contacts()))
    track = policy.tracks[2]
    track["velocity"] = [4., 0., 0.]
    assert policy._predict(track, 100) == [380., 0., 250.]
    command = policy.command(observed("air.b", tick=100))
    assert 0. <= command["speed_mps"] <= 22.
    assert 60. <= command["altitude_m"] <= 500.


@pytest.mark.parametrize("domain", ["air", "surface"])
def test_single_domain_mobile_groups_remain_well_defined(domain):
    data = brief()
    data["mobile_observers"] = ["only"]
    data["observer_domains"] = {"only": domain}
    policy = AllocatedTrackPolicy(data, "only")
    assert policy.command(observed("only", contacts=three_contacts())) is not None
    assert policy.assigned_designations == [0, 1, 2]


def test_allocated_evidence_requires_current_policy_and_adapter_fingerprints():
    from tools.competition_four_categories.audit import tracking_policy_extension_matches
    from tools.competition_four_categories.validate_allocated_tracking import source_fingerprints

    fingerprints = source_fingerprints()
    assert set(fingerprints) == {"validator_sha256", "evaluated_policy_source_sha256", "action_adapter_sha256"}
    record = {"policy": "allocated", **fingerprints}
    assert tracking_policy_extension_matches(record)
    for key in fingerprints:
        missing = dict(record); missing.pop(key)
        assert not tracking_policy_extension_matches(missing)
        assert not tracking_policy_extension_matches({**record, key: "0"*64})
    assert tracking_policy_extension_matches({"policy": "cooperative"})


def test_late_shared_measurement_cannot_reidentify_a_different_surface_track():
    policy = AllocatedTrackPolicy(brief(), "air.a")
    policy.command(observed("air.a", tick=8, contacts=[
        contact([334., -180., 0.], 8), contact([384., 180., 0.], 8),
        contact([348., 0., 250.], 8)]))
    policy.command(observed("air.a", tick=16, contacts=[
        contact([410., 180., 0.], 15), contact([390., 0., 250.], 15)]))
    policy.command(observed("air.a", tick=20, contacts=[
        contact([425., 180., 0.], 19), contact([414., 0., 250.], 19)],
        shared=[contact([372., 0., 250.], 12)]))
    assert policy.tracks[0]["observed_tick"] == 8
    assert policy.tracks[0]["position"] == [334., -180., 0.]
    assert policy.tracks[2]["observed_tick"] == 19
    assert policy.tracks[2]["position"] == [414., 0., 250.]
    assert policy.assigned_designations == [1]
