from copy import deepcopy
import json

import pytest
import yaml

from tools.competition_four_categories import surface_profile as profile
from tools.competition_four_categories.candidate_geometry import SITE_PLATFORM_REF
from tools.competition_four_categories.build import ROOT, PACKAGES, candidate_catalog, entity


def test_profile_has_independent_speed_evidence_and_keeps_transient_limitations():
    p = profile.read_profile()
    assert p["holdout_all_passed"] is True
    assert p["fidelity"] == "UNVALIDATED_REAL_WORLD"
    assert p["turn_full_steady_tolerances_passed"] is False
    assert p["maximum_nps"] == pytest.approx(p["maximum_speed_mps"]*p["nps_per_mps"])


def test_new_candidate_resource_does_not_replace_the_original_definition():
    resources = candidate_catalog()["resources"]
    old = next(r for r in resources if r["id"] == "dynamics.picket-usv" and r["version"] == "2.0.0")
    new = next(r for r in resources if r["id"]+"@"+r["version"] == profile.DYNAMICS_REF)
    assert old["content"]["max_nps"] == 5.
    assert new["content"]["max_nps"] > old["content"]["max_nps"]
    assert old["model_id"] == new["model_id"] == "models.native-sim2sea-mmg@2.0.0"
    own = entity("test", "any_side", "surface", [0., 0., 0.], None)
    assert own["platform_ref"] == profile.PLATFORM_REF and own["dynamics_ref"] == profile.DYNAMICS_REF


def test_task_scoring_routes_and_public_information_are_unchanged_by_mapping():
    snapshot = max((ROOT/"artifacts/competition_four_categories/frozen_versions").glob("before-surface-calibration-*"), key=lambda p:p.stat().st_mtime)
    def translate(value):
        if isinstance(value, list): return [translate(v) for v in value]
        if isinstance(value, dict):
            return {k: (profile.PLATFORM_REF if k == "platform_ref" and v == "platform.picket-usv@2.0.0" else
                        SITE_PLATFORM_REF if k == "platform_ref" and v == "platform.shore-defence-site@2.0.0" else
                        profile.DYNAMICS_REF if k == "dynamics_ref" and v == "dynamics.picket-usv@2.0.0" else translate(v)) for k,v in value.items()}
        return value
    count = 0
    for path in PACKAGES.glob("*/scenario.yaml"):
        before = snapshot/path.relative_to(ROOT)
        expected = translate(yaml.safe_load(before.read_text(encoding="utf-8")))
        expected_brief = json.loads((before.parent/"public_brief.json").read_text(encoding="utf-8"))
        # The later report extension is tested separately against its own
        # frozen baseline; keep the full mapping/route comparison here too.
        if path.parent.name in {"md_trk_007_standard", "md_trk_008_standard"}:
            from tools.competition_four_categories.track_reporting import attach_reporting_contract
            targets = expected["scenario"]["scoring"]["metrics"][0]["plugin_parameters"]["target_ids"]
            attach_reporting_contract(expected, expected_brief, {"unmet_gates": []}, targets)
            if path.parent.name == "md_trk_008_standard":
                from tools.competition_four_categories.tracking_budget_profile import apply_def_p3
                apply_def_p3(expected, expected_brief)
        assert yaml.safe_load(path.read_text(encoding="utf-8")) == expected
        for name in ("public_brief.json", "scripted_blue_policy.json", "scripted_message_policy.json"):
            if name == "public_brief.json":
                assert json.loads((path.parent/name).read_text(encoding="utf-8")) == expected_brief
            elif (path.parent/name).exists():
                assert (path.parent/name).read_bytes() == (before.parent/name).read_bytes()
        count += 1
    assert count == 30


@pytest.mark.parametrize("change", ["status", "bounds", "units", "evidence", "consistent_unmeasured", "turn_claim"])
def test_profile_rejects_unverified_or_inconsistent_overrides(tmp_path, monkeypatch, change):
    p = deepcopy(profile.read_profile())
    if change == "status": p["holdout_all_passed"] = False
    elif change == "bounds": p["maximum_nps"] = 241.
    elif change == "units": p["nps_per_mps"] /= 2
    elif change == "consistent_unmeasured":
        p["nps_per_mps"] *= 1.1; p["maximum_nps"] *= 1.1
    elif change == "turn_claim": p["turn_full_steady_tolerances_passed"] = True
    else: p["evidence"]["holdout"]["sha256"] = "0"*64
    path = tmp_path/"profile.json"; path.write_text(json.dumps(p), encoding="utf-8")
    monkeypatch.setattr(profile, "PROFILE_PATH", path)
    with pytest.raises(ValueError): profile.read_profile()
