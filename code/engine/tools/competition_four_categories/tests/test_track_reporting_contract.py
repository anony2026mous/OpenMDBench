from copy import deepcopy
import json
from pathlib import Path

import pytest
import yaml

from tools.competition_four_categories.build import ROOT
from tools.competition_four_categories.runtime import compile_package
from tools.competition_four_categories.track_report_metrics_v1 import MODEL_REF, PROTOCOL
from tools.competition_four_categories.track_reporting import REPORT_METRICS
from tools.competition_four_categories.track_reporting_policy import TrackReportingPolicy
from tools.competition_four_categories.tracking import tracking


@pytest.mark.parametrize("number", [7, 8])
def test_report_extension_preserves_original_physics_routes_and_success_conditions(number):
    freeze = max((ROOT/"artifacts/competition_four_categories/frozen_versions").glob("before-track-reports-*"))
    path = freeze/"scenarios/competition_v1"/f"md_trk_{number:03d}_standard"
    original = yaml.safe_load((path/"scenario.yaml").read_text(encoding="utf-8"))
    # Isolate the report extension from the later, separately tested asset promotion.
    package, brief, gaps, opponent = tracking(number, asset_profile="legacy" if number == 8 else None)
    altered = deepcopy(package)
    new_ids = {r[0] for r in REPORT_METRICS}
    new_metrics = [m for m in altered["scenario"]["scoring"]["metrics"] if m["id"] in new_ids]
    assert len(new_metrics) == 4 and all(m["plugin_ref"] == MODEL_REF and m["required"] for m in new_metrics)
    old_metrics = [m for m in altered["scenario"]["scoring"]["metrics"] if m["id"] not in new_ids]
    for metric in old_metrics:
        metric["weight"] *= 2
        # Isolate the explicitly versioned N/A correction, not scoring physics
        # or thresholds. The old/new metric arithmetic has its own parity tests.
        assert metric["plugin_ref"] == "models.competition-tracking-metrics@1.0.1"
        frozen_metric = next(m for m in original["scenario"]["scoring"]["metrics"]
                             if m["id"] == metric["id"])
        assert frozen_metric["plugin_ref"] == "models.competition-tracking-metrics@1.0.0"
        metric["plugin_ref"] = frozen_metric["plugin_ref"]
    altered["scenario"]["scoring"]["metrics"] = old_metrics
    rule = next(r for r in altered["scenario"]["mission_rules"] if r["outcome"]["result"] == "objective_complete")
    conditions = rule["condition"]["parameters"]["conditions"]
    assert {c["parameters"]["metric_id"] for c in conditions if c["operator"] == "score"} >= new_ids
    rule["condition"]["parameters"]["conditions"] = [c for c in conditions if c.get("parameters", {}).get("metric_id") not in new_ids]
    # This archive also predates the separately tested terminal-marker repair.
    # Check each complete added declaration before reversing it for comparison;
    # never ignore arbitrary event, deadline or terminal-condition differences.
    terminal_markers = {"objective_complete": "success", "objective_incomplete": "timeout"}
    for terminal_rule in altered["scenario"]["mission_rules"]:
        marker = terminal_markers[terminal_rule["outcome"]["result"]]
        assert terminal_rule["outcome"]["emit_event"] == f"event.{marker}"
        expected_event = {"schema_version": "2.0", "id": f"event.{marker}",
                          "event_type": "mission_marker", "trigger": {"tick": 241},
                          "payload": {"marker_id": f"marker.{marker}"}}
        assert altered["scenario"]["events"].count(expected_event) == 1
        altered["scenario"]["events"].remove(expected_event)
        terminal_rule["outcome"]["emit_event"] = "event.deadline"
    assert altered == original
    assert opponent == json.loads((path/"scripted_blue_policy.json").read_text(encoding="utf-8"))
    assert "unit.x" not in json.dumps(brief)
    assert brief["track_reporting"]["schema_version"] == PROTOCOL
    assert len(brief["track_reporting"]["track_ids"]) == len(new_metrics[0]["plugin_parameters"]["tracks"])
    assert sum(m["weight"] for m in package["scenario"]["scoring"]["metrics"]) == pytest.approx(1.)
    assert any("RMSE" in g for g in gaps["unmet_gates"])
    switch = next(c for c in conditions if c.get("parameters", {}).get("metric_id") == "metric.report_switch_rate")
    assert switch["parameters"] == {"metric_id": "metric.report_switch_rate", "comparison": ">=", "value": .95}
    public_switch = next(m for m in brief["track_reporting"]["scoring"] if m["metric_id"] == "metric.report_switch_rate")
    assert public_switch["comparison"] == "<=" and public_switch["threshold"] == .05


def test_optional_report_registration_does_not_change_other_scenario_catalogs():
    before, catalog = compile_package(tracking(1)[0])
    assert all(m.exact_ref != MODEL_REF for m in catalog.model_registry.snapshot())
    _, report_catalog = compile_package(tracking(7)[0])
    assert any(m.exact_ref == MODEL_REF for m in report_catalog.model_registry.snapshot())
    after, catalog = compile_package(tracking(1)[0])
    assert after.catalog_hash == before.catalog_hash
    assert after.model_registry_hash == before.model_registry_hash
    assert all(m.exact_ref != MODEL_REF for m in catalog.model_registry.snapshot())


def observation(brief, identifier):
    index = brief["mobile_observers"].index(identifier)
    cue = brief["initial_designation_regions"][index % len(brief["initial_designation_regions"])]["coordinates_m"]
    position = [sum(p[a] for p in cue)/len(cue) for a in (0, 1)]+[220.]
    return {"tick": 4, "own_entities": [{"entity_id": identifier, "position_m": [0., 0., 100.]}],
            "organic_contacts": [{"observer_entity_id": identifier, "contact_id": "opaque-evidence",
                "estimated_position_m": position, "observed_tick": 3, "confidence": .9}], "shared_contacts": []}


def test_reporting_modes_keep_navigation_equal_and_change_only_public_labels():
    _, brief, _, _ = tracking(7)
    identifier = brief["mobile_observers"][0]
    obs = observation(brief, identifier); before = deepcopy(obs)
    outputs = {mode: TrackReportingPolicy(brief, identifier, mode).decide(obs) for mode in ("honest", "silent", "swapped")}
    assert obs == before
    assert outputs["honest"]["navigation"] == outputs["silent"]["navigation"] == outputs["swapped"]["navigation"]
    assert outputs["silent"]["messages"] == []
    a = json.loads(outputs["honest"]["messages"][0]["message"]); b = json.loads(outputs["swapped"]["messages"][0]["message"])
    assert a["track_id"] != b["track_id"]
    assert {k: v for k, v in a.items() if k != "track_id"} == {k: v for k, v in b.items() if k != "track_id"}
    assert a["contact_id"] == obs["organic_contacts"][0]["contact_id"]


def test_shared_only_measurements_and_foreign_owners_cannot_be_reported_as_organic():
    _, brief, _, _ = tracking(7); identifier = brief["mobile_observers"][0]
    obs = observation(brief, identifier)
    obs["shared_contacts"] = obs.pop("organic_contacts")
    assert TrackReportingPolicy(brief, identifier).decide(obs)["messages"] == []
    obs = observation(brief, identifier); obs["organic_contacts"][0]["observer_entity_id"] = "somebody-else"
    assert TrackReportingPolicy(brief, identifier).decide(obs)["messages"] == []


def test_opaque_token_renaming_does_not_change_report_assignment():
    _, brief, _, _ = tracking(7); identifier = brief["mobile_observers"][0]
    a = observation(brief, identifier); b = deepcopy(a); b["organic_contacts"][0]["contact_id"] = "unit.x99.secret"
    x = TrackReportingPolicy(brief, identifier).decide(a); y = TrackReportingPolicy(brief, identifier).decide(b)
    assert x["navigation"] == y["navigation"]
    assert json.loads(x["messages"][0]["message"])["track_id"] == json.loads(y["messages"][0]["message"])["track_id"]


def test_report_runner_evidence_binds_policy_metric_and_both_action_adapters():
    from tools.competition_four_categories.audit import tracking_policy_extension_matches
    from tools.competition_four_categories.validate_tracking_reports import source_fingerprints
    expected = source_fingerprints()
    for mode in ("honest", "silent", "swapped"):
        record = {"policy": f"report-{mode}", **expected}
        assert tracking_policy_extension_matches(record)
        for key in expected:
            missing = dict(record); missing.pop(key)
            assert not tracking_policy_extension_matches(missing)
            assert not tracking_policy_extension_matches({**record, key: "0"*64})
    assert not tracking_policy_extension_matches({"policy": "report-unknown", **expected})
