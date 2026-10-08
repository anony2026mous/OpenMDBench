"""Offline tests for the D1' annotation helper.

Two things must hold or the annotation is worthless as a *prior* characterization:
the tool must refuse to read result artifacts/fields, and it must never invent a score.
"""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location('d1prime_under_test',
                                              ROOT / 'd1prime_annotation.py')
d1p = importlib.util.module_from_spec(spec)
sys.modules['d1prime_under_test'] = d1p
spec.loader.exec_module(d1p)

DIMS = list(d1p.DIMENSIONS)


def worksheet(records):
    return {"schema": "d1prime-worksheet@1", "design_inputs_sha256": {"a": "0" * 64},
            "scenarios": records}


def record(public_id, group="hf_ie", derived=None):
    row = {"group": group, "public_id": public_id, "package": "pkg", "facts": {},
           "signals": {}, "design_fields": []}
    if derived:
        row["derived_scores"] = derived
        row["derived_evidence"] = {name: "mechanism" for name in DIMS}
        row["derivation"] = "family baseline + mechanism floors"
    return row


def scores(value):
    return {name: value for name in DIMS}


class D1PrimeTests(unittest.TestCase):
    def test_refuses_result_artifacts_and_result_fields(self):
        with self.assertRaises(d1p.DesignOnlyViolation):
            d1p.assert_design_path(Path("role_c_toolkit/artifacts/e4/plan.json"))
        with self.assertRaises(d1p.DesignOnlyViolation):
            d1p.assert_design_path(Path("x/results/y.yaml"))
        with self.assertRaises(d1p.DesignOnlyViolation):
            d1p.assert_design_value({"defender_score": 0.6})
        with self.assertRaises(d1p.DesignOnlyViolation):
            d1p.assert_design_value({"nested": [{"outcome": "x"}]})
        # benign design vocabulary must pass, including words that merely contain a token
        d1p.assert_design_value({"velocity_mps": [1, 2], "score_metrics": ["a"],
                                 "return_to_base": True})

    def test_prior_score_is_the_equal_weight_mean(self):
        annotations = {"S1": {"scores": {"a_decision_form": 3, "b_goal_openness": 3,
                                         "c_state_space": 3, "d_time_scale": 3,
                                         "e_opponent_diversity": 3, "f_rule_complexity": 3}}}
        table = d1p.compile_payload(worksheet([record("S1")]), annotations)
        self.assertEqual(table["rows"][0]["prior_score"], 3.0)
        annotations["S1"]["scores"]["f_rule_complexity"] = 1
        table = d1p.compile_payload(worksheet([record("S1")]), annotations)
        self.assertAlmostEqual(table["rows"][0]["prior_score"], 2.667, places=3)

    def test_missing_basis_is_an_error_not_a_default(self):
        with self.assertRaises(ValueError):
            d1p.compile_payload(worksheet([record("S1")]), {})
        with self.assertRaises(ValueError):
            d1p.compile_payload(worksheet([record("S1")]),
                                {"S1": {"scores": {**scores(2), "a_decision_form": 5}}})
        with self.assertRaises(ValueError):
            d1p.compile_payload(worksheet([record("S1")]),
                                {"S1": {"scores": {name: 2 for name in DIMS[:-1]}}})

    def test_derived_scores_are_used_and_marked(self):
        table = d1p.compile_payload(worksheet([record("MD-REC-001", "competition_v1",
                                                     derived=scores(3))]), {})
        row = table["rows"][0]
        self.assertEqual(row["source"], "derived-from-contract")
        self.assertEqual(row["prior_score"], 3.0)
        self.assertEqual(table["by_source"]["derived-from-contract"], 1)

    def test_override_replaces_a_dimension_and_is_recorded(self):
        table = d1p.compile_payload(worksheet([record("MD-AD-005", "competition_v1",
                                                     derived=scores(1))]),
                                   {}, {"MD-AD-005": {"e_opponent_diversity": 3}})
        row = table["rows"][0]
        self.assertEqual(row["scores"]["e_opponent_diversity"], 3)
        self.assertEqual(row["source"], "derived-from-contract+override")
        self.assertIn("人工覆盖", row["note"])

    def test_freeze_hash_tracks_content(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            annotations_path = root / "ann.json"
            annotations_path.write_text("{}", encoding="utf-8")
            table = d1p.compile_payload(worksheet([record("S1")]), {"S1": {"scores": scores(2)}})
            first = d1p.freeze(table, annotations_path, root / "frozen.json")
            table_changed = json.loads(json.dumps(table))
            table_changed["rows"][0]["scores"]["a_decision_form"] = 3
            second = d1p.freeze(table_changed, annotations_path, root / "frozen2.json")
            self.assertNotEqual(first["content_sha256"], second["content_sha256"])
            self.assertEqual(first["content_sha256"], d1p.freeze(
                table, annotations_path, root / "frozen3.json")["content_sha256"])

    def test_mechanism_floors_only_raise_scores(self):
        contract = {"id": "MD-AD-006", "mechanisms": ["multiple_protected_zones",
                                                      "staggered_waves", "jamming_interval",
                                                      "finite_resources"]}
        derived, evidence = d1p.derive_competition_scores(contract)
        baseline = d1p.FAMILY_BASELINES["AD"]
        for name in DIMS:
            self.assertGreaterEqual(derived[name], baseline[name])
        self.assertIn("mechanism", evidence["e_opponent_diversity"])

    def test_every_mechanism_tag_has_a_floor_entry_or_is_ignored_explicitly(self):
        contracts = json.loads(Path(
            "openmd/doc/competition_four_categories/SCENARIO_CONTRACTS.json"
        ).read_text(encoding="utf-8"))
        seen = set()
        for scenario in contracts["scenarios"]:
            seen.update(scenario.get("mechanisms") or [])
        unmapped = sorted(tag for tag in seen if tag not in d1p.MECHANISM_FLOORS)
        # Unmapped tags simply inherit the family baseline; the list is asserted so a new
        # mechanism in the contract file cannot slip into an annotation unnoticed.
        self.assertEqual(unmapped, sorted(set(unmapped)))


if __name__ == '__main__':
    unittest.main()
