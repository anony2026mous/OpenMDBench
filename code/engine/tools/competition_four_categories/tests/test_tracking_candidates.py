from copy import deepcopy
import json

import pytest

from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2
from tools.competition_four_categories.runtime import load_candidate_catalog, compile_package
from tools.competition_four_categories.tracking import tracking
from tools.competition_four_categories.tracking_policy import ScheduledNavigationPolicy, ContactFollowPolicy


@pytest.mark.parametrize("number", range(1, 9))
def test_tracking_compiles_and_success_requires_the_entire_horizon(number):
    package, brief, gaps, plan = tracking(number)
    resolved, catalog = compile_package(package)
    assert resolved.world.duration_ticks == brief["adjudication_tick"]
    rule = package["scenario"]["mission_rules"][0]
    conditions = rule["condition"]["parameters"]["conditions"]
    assert {"operator": "time", "parameters": {"comparison": ">=", "tick": 241}} in conditions
    assert all(m["plugin_parameters"]["end_tick"] <= 241 for m in package["scenario"]["scoring"]["metrics"])
    assert next(m for m in package["scenario"]["scoring"]["metrics"] if m["id"] == "metric.continuity")["plugin_parameters"]["end_tick"] == 241
    assert gaps["competition_accepted"] is False
    assert brief["difficulty"] == "standard"
    assert "segments" not in brief and "events" not in brief
    assert "unit.x" not in json.dumps(brief)
    scheduled = ScheduledNavigationPolicy(plan)
    blue_ids = {e["id"] for e in package["scenario"]["entities"] if e["faction_id"] == "blue"}
    assert set(scheduled.entity_ids) == blue_ids
    assert all(max(s["end_tick"] for s in plan["segments"] if s["entity_id"] == i) == 240 for i in blue_ids)


def test_eight_mechanisms_differ_beyond_labels_and_positions():
    signatures = set()
    for n in range(1, 9):
        package, brief, _, plan = tracking(n)
        s = package["scenario"]
        signature = {"target_count": len({i["entity_id"] for i in plan["segments"]}),
            "target_platforms": [e["platform_ref"] for e in s["entities"] if e["faction_id"] == "blue"],
            "event_types": [e["event_type"] for e in s["events"]],
            "metrics": [m["plugin_parameters"]["kind"] for m in s["scoring"]["metrics"]],
            "navigation_segments": [{k: v for k, v in item.items() if k != "entity_id"} for item in plan["segments"]]}
        signatures.add(json.dumps(signature, sort_keys=True))
    assert len(signatures) == 8


def test_cross_domain_groups_match_real_platforms():
    for number in (3, 6):
        package, brief, _, _ = tracking(number)
        groups = package["scenario"]["scoring"]["metrics"][0]["plugin_parameters"]["observer_groups"]
        for group in groups:
            assert {brief["observer_domains"][i] for i in group["observer_ids"]} == {group["group_id"]}


def test_turn_and_weather_windows_cannot_hide_behind_whole_episode_average():
    for number, expected in ((4, {"metric.after_turn1": (71, 141), "metric.after_turn2": (141, 241)}),
                             (5, {"metric.after_fog": (80, 241)})):
        s = tracking(number)[0]["scenario"]
        metrics = {m["id"]: m["plugin_parameters"] for m in s["scoring"]["metrics"]}
        for key, window in expected.items():
            assert (metrics[key]["start_tick"], metrics[key]["end_tick"]) == window
        required = {c["parameters"].get("metric_id") for c in s["mission_rules"][0]["condition"]["parameters"]["conditions"]}
        assert set(expected) <= required


def test_scheduled_turns_use_normal_commands_at_exact_own_side_times():
    _, _, _, plan = tracking(4)
    p = ScheduledNavigationPolicy(plan)
    observations = {i: {"own_entities": [{"entity_id": i}]} for i in p.entity_ids}
    initial = p.commands(0, observations)
    assert len(initial) == 2 and all(c["payload"]["heading_deg"] == 90 for c in initial.values())
    assert p.commands(69, observations) == {}
    assert {c["payload"]["heading_deg"] for c in p.commands(70, observations).values()} == {0., 180.}
    assert all(c["payload"]["heading_deg"] == 270 for c in p.commands(140, observations).values())
    assert p.commands(240, observations) == {}


def test_opponent_cannot_command_unowned_scope_and_rejects_overlapping_plan():
    _, _, _, plan = tracking(1)
    p = ScheduledNavigationPolicy(plan)
    with pytest.raises(ValueError, match="own declared fleet"):
        p.commands(0, {"unit.r01": {"own_entities": [{"entity_id": "unit.r01"}]}})
    wrong = {i: {"own_entities": [{"entity_id": "unit.r01"}]} for i in p.entity_ids}
    with pytest.raises(ValueError, match="unowned"):
        p.commands(0, wrong)
    duplicate = deepcopy(plan)
    duplicate["segments"].append(deepcopy(plan["segments"][0]))
    with pytest.raises(ValueError, match="nonoverlapping"):
        ScheduledNavigationPolicy(duplicate)


def test_follow_policy_uses_estimates_not_internal_target_identity():
    _, brief, _, _ = tracking(1)
    a, b = ContactFollowPolicy(brief, "unit.r01"), ContactFollowPolicy(brief, "unit.r01")
    observation = {"tick": 1, "own_entities": [{"entity_id": "unit.r01", "position_m": [0., 0., 100.]}],
        "organic_contacts": [{"contact_id": "opaque.23", "age_ticks": 0, "observed_tick": 1,
                              "estimated_position_m": [320., 40., 0.]}]}
    renamed = deepcopy(observation)
    renamed["organic_contacts"][0]["contact_id"] = "unrelated.opaque-token"
    assert a.command(observation) == b.command(renamed)
    with pytest.raises(ValueError, match="different controller scope"):
        observation["own_entities"][0]["entity_id"] = "unit.r02"
        a.command(observation)


def test_validation_uses_authoritative_missing_status_not_internal_zero_placeholder():
    from types import SimpleNamespace as N
    from tools.competition_four_categories.validate_tracking import score_evidence
    raw = N(world_receipt=N(score_receipts=[
        N(tick=2, metric_receipts=[N(metric_id="metric.a", raw_value=0., data_status="missing")]),
        N(tick=1, metric_receipts=[N(metric_id="metric.a", raw_value=0., data_status="available")])]))
    scores, status = score_evidence(raw)
    assert scores == {"metric.a": None} and status == {"metric.a": "missing"}
