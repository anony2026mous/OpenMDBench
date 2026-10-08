from copy import deepcopy
import json

import pytest

from tools.competition_four_categories.build import PACKAGES
from tools.competition_four_categories.runtime import compile_candidate
from tools.competition_four_categories.reconnaissance import reconnaissance
from tools.competition_four_categories.recon_policy import SearchPolicy
from tools.competition_four_categories.denial_policy import WaveNavigationPolicy


@pytest.mark.parametrize("number", range(2, 9))
def test_recon_candidates_compile_with_full_deadline_and_private_plans(number):
    package, brief, gaps, plan = reconnaissance(number)
    resolved, _ = compile_candidate(PACKAGES / f"md_rec_{number:03d}_standard")
    assert resolved.resolved_hash.startswith("sha256:")
    assert package["scenario"]["world"]["duration_ticks"] == brief["adjudication_tick"] == 241
    success = package["scenario"]["mission_rules"][0]["condition"]["parameters"]["conditions"]
    assert success[0]["operator"] == "time" and success[0]["parameters"]["tick"] == 241
    assert "unit.x" not in json.dumps(brief)
    assert "spawn" not in json.dumps(brief)
    assert not gaps["competition_accepted"] and gaps["unmet_gates"]
    assert set(WaveNavigationPolicy(plan).active_ids(0)) < set(plan["controller_slots"]) if number in (7, 8) else WaveNavigationPolicy(plan).active_ids(0)


def test_seven_recon_mechanism_signatures_are_distinct_not_only_ids():
    signatures = []
    for n in range(2, 9):
        p, brief, _, _ = reconnaissance(n); s = p["scenario"]
        signatures.append((len(brief["search_sectors"]), len(s["entities"]),
            tuple(e["event_type"] for e in s["events"]),
            tuple(m["plugin_parameters"]["kind"] for m in s["scoring"]["metrics"]),
            tuple(len(m["plugin_parameters"]["groups"]) for m in s["scoring"]["metrics"])))
    assert len(set(signatures)) == 7


def test_cross_domain_and_delivery_goals_use_separate_owners_not_global_union():
    for n in (3, 5):
        p, _, _, _ = reconnaissance(n)
        g = p["scenario"]["scoring"]["metrics"][0]["plugin_parameters"]
        assert {r["group_id"] for r in g["groups"]} == {"domain.air", "domain.surface"}
        assert set(g["groups"][0]["observer_ids"]).isdisjoint(g["groups"][1]["observer_ids"])
        assert (g["delivery"] is not None) == (n == 5)


def test_weather_and_late_waves_have_post_event_windows():
    for n in (6, 7, 8):
        p, _, _, _ = reconnaissance(n)
        groups = p["scenario"]["scoring"]["metrics"][0]["plugin_parameters"]["groups"]
        assert max(g["start_tick"] for g in groups) > 140
        assert max(g["end_tick"] for g in groups) == 241


def observation(identifier="unit.r01", tick=3):
    return {"tick": tick, "own_entities": [{"entity_id": identifier, "position_m": [0., 350., 120.]}],
        "organic_contacts": [{"contact_id": "opaque.test-token", "observed_tick": tick-1,
            "age_ticks": 1, "confidence": .9, "estimated_position_m": [500., 0., 100.]}]}


def test_report_policy_uses_only_published_opaque_token_and_observed_time():
    brief = reconnaissance(5)[1]
    p = SearchPolicy(brief, "unit.r01", "coordinated")
    payload = p.report(observation())
    body = json.loads(payload["message"])
    assert body["contacts"] == [{"contact_id": "opaque.test-token", "observed_tick": 2}]
    assert payload["recipient_controller_slots"] == ["slot.unit.r03"]
    assert "estimated_position_m" not in payload["message"] and "target_id" not in payload["message"]
    assert p.report(observation(tick=4)) is None
    assert SearchPolicy(brief, "unit.r01", "sweep").report(observation()) is None


def test_policy_cannot_consume_another_asset_or_future_plan():
    brief = reconnaissance(2)[1]
    p = SearchPolicy(brief, "unit.r01", "coordinated")
    with pytest.raises(ValueError, match="another controller"):
        p.navigation(observation("unit.r02"))
    a, b = SearchPolicy(brief, "unit.r01", "coordinated"), SearchPolicy(brief, "unit.r04", "coordinated")
    assert a.waypoints != b.waypoints
    contaminated = deepcopy(observation()); contaminated["future_plan"] = {"secret": 123}
    assert a.navigation(observation()) == SearchPolicy(brief, "unit.r01", "coordinated").navigation(contaminated)
