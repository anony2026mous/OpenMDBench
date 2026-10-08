from copy import deepcopy
import json

import pytest

from tools.competition_four_categories import calibrate_surface as c
from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2


def test_calibration_and_holdout_commands_are_predeclared_and_disjoint():
    assert c.FIT_SPEEDS == [2., 4., 6., 8., 10., 12.]
    assert c.HOLDOUT_SPEEDS == [3., 5., 7., 9., 11., 12.9]
    assert set(c.FIT_SPEEDS).isdisjoint(c.HOLDOUT_SPEEDS)
    assert c.TOLERANCES["relative_speed_error"] == .05


def test_reference_ratio_is_read_from_existing_native_resource():
    assert c.reference_ratio() == pytest.approx(133.33333333333334/10.)


def test_temporary_resources_preserve_original_picket_definition():
    catalog, pref, dref, dynamic, platform = c.calibration_catalog(12., "unit-test")
    original = next(r for r in catalog.snapshot() if r.id == "dynamics.picket-usv" and r.version == "2.0.0")
    assert original.content["max_nps"] == 5.
    assert dynamic["content"]["max_nps"] == pytest.approx(12.*12.9)
    assert platform["content"]["allowed_dynamics"] == [dref]
    package = c.trial_package([2., 4.], pref, dref)
    assert "scoring" not in package["scenario"]
    resolved = ScenarioCompilerV2(catalog=catalog).compile(ScenarioPackageV2.from_mapping(package))
    assert resolved.world.duration_ticks == 181
    assert len(resolved.entities) == 2


@pytest.mark.parametrize("ratio", [0., -1., float('nan'), 30.])
def test_native_actuator_bound_is_not_bypassed(ratio):
    with pytest.raises(ValueError, match="trusted envelope"):
        c.calibration_catalog(ratio, "invalid")


def test_fit_uses_measured_gain_not_scenario_scores(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "ROOT", tmp_path)
    evidence = {"source_sha256": c.sha(c.__file__), "label": "reference", "ratio_nps_per_mps": 13.2,
        "summaries": [{"requested_speed_mps": speed, "settled_speed_mps": speed*1.1} for speed in c.FIT_SPEEDS],
        "protected_inputs_after": {"baseline_sha256": "frozen"}}
    path = tmp_path/"reference.json"; path.write_text(json.dumps(evidence), encoding="utf-8")
    result = c.fit_mapping(path)
    assert result["reference_gain"] == pytest.approx(1.1)
    assert result["nps_per_mps"] == pytest.approx(12.)
    assert result["status"] == "fitted_pending_holdout"
    assert result["reference_evidence_sha256"] == c.sha(path)


def test_fit_rejects_stale_code_and_changed_speed_set(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "ROOT", tmp_path)
    base = {"source_sha256": c.sha(c.__file__), "label": "reference", "ratio_nps_per_mps": 12.,
        "summaries": [{"requested_speed_mps": speed, "settled_speed_mps": speed} for speed in c.FIT_SPEEDS],
        "protected_inputs_after": {"baseline_sha256": "frozen"}}
    for change in ("source", "speeds"):
        value = deepcopy(base)
        if change == "source": value["source_sha256"] = "wrong"
        else: value["summaries"].pop()
        path = tmp_path/f"{change}.json"; path.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises(ValueError): c.fit_mapping(path)
