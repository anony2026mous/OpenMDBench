from copy import deepcopy

import pytest

from tools.competition_four_categories.build import zone
from tools.competition_four_categories.tracking_policy import CooperativeTrackPolicy


def brief():
    return {"mobile_observers": ["air.a", "air.b", "surface"],
        "observer_domains": {"air.a": "air", "air.b": "air", "surface": "surface"},
        "initial_designation_regions": [zone("public.a", 300., -150.), zone("public.b", 300., 150.)]}


def observed(identifier="surface", tick=4, contacts=(), shared=()):
    return {"tick": tick, "own_entities": [{"entity_id": identifier, "position_m": [0., 0., 0. if identifier=='surface' else 100.]}],
            "organic_contacts": list(contacts), "shared_contacts": list(shared)}


def measurement(token="opaque", tick=1, position=(310., -140., 0.)):
    return {"contact_id": token, "source_contact_id": token, "observed_tick": tick,
            "age_ticks": 0, "estimated_position_m": list(position), "confidence": .9}


def test_surface_covers_public_centroid_and_air_assignments_remain_distinct():
    p = CooperativeTrackPolicy(brief(), "surface")
    command = p.command(observed())
    assert command["heading_deg"] == pytest.approx(90.)
    assert command["speed_mps"] == 6.
    a = CooperativeTrackPolicy(brief(), "air.a").command(observed("air.a"))
    b = CooperativeTrackPolicy(brief(), "air.b").command(observed("air.b"))
    assert a["heading_deg"] != b["heading_deg"]


def test_shared_snapshot_age_is_computed_from_observed_tick_not_frozen_age_field():
    p = CooperativeTrackPolicy(brief(), "surface")
    p.command(observed(tick=30, shared=[measurement(tick=0)]))
    assert all(t["observed_tick"] is None for t in p.tracks)


def test_fresh_shared_measurement_updates_only_one_designated_track():
    p = CooperativeTrackPolicy(brief(), "surface")
    p.command(observed(shared=[measurement()]))
    assert p.tracks[0]["observed_tick"] == 1
    assert p.tracks[1]["observed_tick"] is None
    p.command(observed(tick=8, shared=[measurement()]))
    assert p.tracks[1]["observed_tick"] is None


def test_duplicate_sensor_reports_are_not_two_targets():
    p = CooperativeTrackPolicy(brief(), "surface")
    p.command(observed(contacts=[measurement("own-token")], shared=[measurement("peer-token")]))
    assert sum(t["observed_tick"] is not None for t in p.tracks) == 1


def test_token_text_and_extra_referee_keys_do_not_drive_the_policy():
    a,b = CooperativeTrackPolicy(brief(), "surface"), CooperativeTrackPolicy(brief(), "surface")
    first = observed(contacts=[measurement("token.one")])
    second = observed(contacts=[measurement("unit.x99")]); second["referee_future"] = {"secret": 999}
    assert a.command(first) == b.command(second)


def test_empty_control_state_is_safe_but_another_owned_identity_is_rejected():
    p = CooperativeTrackPolicy(brief(), "surface")
    assert p.command({"own_entities": []}) is None
    with pytest.raises(ValueError, match="unowned"):
        p.command(observed("air.a"))
