from copy import deepcopy
import hashlib
import json

import pytest

from tools.competition_four_categories.build import ROOT, PACKAGES
from tools.competition_four_categories.runtime import compile_package, compile_candidate
from tools.competition_four_categories.tracking_budget_profile import load_profile, apply_def_p3
from tools.competition_four_categories.tracking import tracking
import yaml


def test_current_profile_is_exact_canonical_input():
    package, brief, plan, provenance = load_profile()
    actual, _ = compile_package(package)
    canonical, _ = compile_candidate(PACKAGES/"md_trk_008_standard")
    assert actual.resolved_hash == canonical.resolved_hash
    assert brief["difficulty"] == "standard" and provenance["calibration_only"]
    assert plan == json.loads((PACKAGES/"md_trk_008_standard/scripted_blue_policy.json").read_text(encoding="utf-8"))


def test_def_p3_changes_only_declared_assets_and_observer_scopes():
    base, original_brief, original_plan, _ = load_profile(profile="legacy-four-observers")
    profile, brief, plan, provenance = load_profile(profile="DEF-P3")
    assert plan == original_plan
    assert provenance["deployment_status"].startswith("UNVALIDATED")
    assert {d: list(brief["observer_domains"].values()).count(d) for d in ("air", "surface", "shore")} == {"air": 2, "surface": 3, "shore": 2}
    assert len(brief["track_reporting"]["reporter_ids"]) == 5
    assert set(brief["track_reporting"]["reporter_ids"]).isdisjoint(i for i,d in brief["observer_domains"].items() if d == "shore")
    added = {"unit.r05", "unit.r06", "unit.r07"}
    recovered = deepcopy(profile)
    recovered["scenario"]["entities"] = [e for e in recovered["scenario"]["entities"] if e["id"] not in added]
    recovered["scenario"]["controller_slots"] = [c for c in recovered["scenario"]["controller_slots"] if c["controller_endpoint_ref"] not in added]
    for changed, old in zip(recovered["scenario"]["scoring"]["metrics"], base["scenario"]["scoring"]["metrics"]):
        changed["selector"] = old["selector"]
        for key in ("observer_ids", "observer_groups", "reporter_ids"):
            if key in old["plugin_parameters"]: changed["plugin_parameters"][key] = old["plugin_parameters"][key]
    assert recovered == base
    assert brief["track_reporting"]["scoring"] == original_brief["track_reporting"]["scoring"]
    assert brief["initial_designation_regions"] == original_brief["initial_designation_regions"]
    assert "unit.x" not in json.dumps(brief)


def test_def_p3_compiles_with_existing_catalog_and_role_partition():
    package, brief, _, provenance = load_profile(profile="DEF-P3")
    resolved, _ = compile_package(package)
    original, _ = compile_candidate(PACKAGES/"md_trk_008_standard")
    assert resolved.catalog_hash == original.catalog_hash
    assert resolved.model_registry_hash == original.model_registry_hash
    assert resolved.resolved_hash == original.resolved_hash
    legacy, _ = compile_package(load_profile(profile="legacy-four-observers")[0])
    assert resolved.resolved_hash != legacy.resolved_hash
    groups = package["scenario"]["scoring"]["metrics"][0]["plugin_parameters"]["observer_groups"]
    for group in groups: assert all(brief["observer_domains"][i] == group["group_id"] for i in group["observer_ids"])
    for name, digest in provenance["canonical_file_hashes"].items():
        assert hashlib.sha256((PACKAGES/"md_trk_008_standard"/name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("number,profile", [(7, "DEF-P3"), (8, "unknown")])
def test_budget_extension_is_explicitly_scoped(number, profile):
    with pytest.raises(ValueError): load_profile(number, profile)


def test_reference_transform_is_idempotent_and_rejects_partial_or_changed_assets():
    package, brief, _, _ = tracking(8)
    before = deepcopy((package, brief))
    apply_def_p3(package, brief)
    assert (package, brief) == before
    partial = deepcopy(package)
    partial["scenario"]["entities"] = [e for e in partial["scenario"]["entities"] if e["id"] != "unit.r05"]
    with pytest.raises(ValueError, match="partial"): apply_def_p3(partial, deepcopy(brief))
    changed = deepcopy(package)
    next(e for e in changed["scenario"]["entities"] if e["id"] == "unit.r05")["initial_state"]["health"] = .5
    with pytest.raises(ValueError, match="differs"): apply_def_p3(changed, deepcopy(brief))


def test_promoted_generator_preserves_frozen_inputs_except_terminal_event_migration():
    plan = json.loads((ROOT/"artifacts/competition_four_categories/coverage-range-hold-heldout-plan.json").read_text(encoding="utf-8"))
    result = json.loads((ROOT/plan["reference"]).read_text(encoding="utf-8"))
    stage = ROOT/result["staged_input_path"]
    assert hashlib.sha256((ROOT/plan["reference"]).read_bytes()).hexdigest() == plan["reference_sha256"]
    for name, expected_hash in plan["staged_reference_hashes"].items():
        assert hashlib.sha256((stage/name).read_bytes()).hexdigest() == expected_hash
    expected = yaml.safe_load((stage/"scenario.yaml").read_text(encoding="utf-8"))
    # Explicit, bounded migration: only two outcome references and their new
    # marker declarations change. Frozen files and original results stay intact.
    scenario = expected["scenario"]
    for rule in scenario["mission_rules"]:
        assert rule["outcome"]["emit_event"] == "event.deadline"
        name = {"rule.success": "success", "rule.timeout": "timeout"}[rule["id"]]
        rule["outcome"]["emit_event"] = f"event.{name}"
        scenario["events"].append({"schema_version": "2.0", "id": f"event.{name}",
            "event_type": "mission_marker",
            "trigger": {"tick": scenario["world"]["duration_ticks"]},
            "payload": {"marker_id": f"marker.{name}"}})
    expected_brief = json.loads((stage/"public_brief.json").read_text(encoding="utf-8"))
    expected_brief["difficulty"] = "standard"
    expected_brief["asset_profile"]["status"] = "candidate_reference_budget"
    package, brief, gaps, opponent = tracking(8)
    assert package == expected and brief == expected_brief
    assert opponent == json.loads((stage/"scripted_blue_policy.json").read_text(encoding="utf-8"))
    resolved, _ = compile_package(package)
    assert result["staged_input_hashes"] == plan["staged_reference_hashes"]
    expected_resolved, _ = compile_package(expected)
    assert resolved.resolved_hash == expected_resolved.resolved_hash
    # Changed input identity requires fresh runtime evidence, not relabeling the
    # frozen run as validation of this revision.
    assert resolved.resolved_hash != result["resolved_hash"]
    assert gaps["competition_accepted"] is False


def test_canonical_coverage_evidence_requires_its_actual_sources():
    from tools.competition_four_categories.audit import tracking_policy_extension_matches
    from tools.competition_four_categories.validate_coverage_tracking import source_fingerprints
    fields = source_fingerprints()
    record = {"policy": "coverage-honest", **fields}
    assert tracking_policy_extension_matches(record)
    for key in fields:
        missing = dict(record); missing.pop(key)
        assert not tracking_policy_extension_matches(missing)
    assert not tracking_policy_extension_matches({"policy": "coverage-unknown", **fields})
