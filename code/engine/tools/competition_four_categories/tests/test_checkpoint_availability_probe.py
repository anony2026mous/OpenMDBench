"""Diagnostic assertions; passing these does NOT pass checkpoint acceptance."""
import pytest

from tools.competition_four_categories.checkpoint_availability_probe import MODES, build_fixture, run_probe
from tools.competition_four_categories.calibration_matrix import frozen_inputs


@pytest.mark.parametrize("mode", MODES)
def test_fixture_is_stationary_and_does_not_rewrite_any_canonical_input(mode):
    before = frozen_inputs()["input_hashes"]
    package, resolved, _, _ = build_fixture(mode)
    assert len(package["scenario"]["entities"]) == 1
    assert package["scenario"]["entities"][0]["id"] == "unit.r04"
    assert package["scenario"]["events"] == []
    assert package["scenario"]["mission_rules"] == []
    assert resolved.world.duration_ticks == 4
    assert frozen_inputs()["input_hashes"] == before


def test_genuinely_measured_zero_exports_without_claiming_restore_equivalence():
    result = run_probe("measured_zero")
    assert all(r["checkpoint"]["status"] == "available_not_full_restore_equivalence" for r in result["rows"])
    assert result["checkpoint_acceptance_passed"] is False
    assert all(row["produced"] == {"metric.probe": 0.} for row in result["diagnostic_plugin_outputs"])


def test_missing_output_conflict_remains_explicit_after_a_later_numeric_sample():
    result = run_probe("missing_then_zero")
    assert result["rows"][0]["checkpoint"]["status"] == "available_not_full_restore_equivalence"
    first, second = result["rows"][1:3]
    assert result["diagnostic_plugin_outputs"][0] == {"tick": 1, "produced": {"metric.probe": None}}
    assert result["diagnostic_plugin_outputs"][1] == {"tick": 2, "produced": {"metric.probe": 0.}}
    assert first["score_receipts"][0]["metrics"][0]["value"] == 0.
    assert first["score_receipts"][0]["metric_receipts"][0]["data_status"] == "missing"
    assert second["score_receipts"][0]["metric_receipts"][0]["data_status"] == "available"
    for row in result["rows"][1:]:
        assert row["checkpoint"]["status"] == "FAILED_CHECKPOINT_GATE"
        assert any("plugin score input lacks authoritative output evidence" in x["error"]
                   for x in row["checkpoint"]["causes"])
    assert result["checkpoint_acceptance_passed"] is False


@pytest.mark.parametrize("mode,reason", [("omitted_output", "score output must be a mapping"),
                                         ("structured_unavailable", "invalid score evidence")])
def test_unsupported_candidate_encodings_are_native_rejections_not_workarounds(mode, reason):
    result = run_probe(mode)
    assert result["rows"][0]["checkpoint"]["status"] == "available_not_full_restore_equivalence"
    assert any(reason in item["error"] for item in result["rows"][1]["step_error"])
    assert result["checkpoint_acceptance_passed"] is False
