"""Offline tests for the E4 scenario-family inventory and gate ledger.

The ledger is the audit trail for admission gates, so the tests pin the three ways it
could lie: presenting an unrun gate as passed, losing the D1 "not applicable" reasoning,
and silently matching a D2 result to the wrong scenario.
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

spec = importlib.util.spec_from_file_location('e4_scenario_family_under_test',
                                              ROOT / 'e4_scenario_family.py')
e4 = importlib.util.module_from_spec(spec)
sys.modules['e4_scenario_family_under_test'] = e4
spec.loader.exec_module(e4)

REGISTRY = """schema_version: formal-scenario-registry@2.0
scenarios:
  - public_id: MD-INT-002-AIR-SURFACE
    package: md_int_002_air_surface
    catalog_bundle: md_ad_002
  - public_id: IE-08-ISLAND-STRIKE
    package: ie_08_island_strike
    catalog_bundle: md_ad_002
"""

D1_SUMMARY = {
    "IE-06-DECOY-MIXED": {
        "numeric_restricted": {"n": 400, "balanced_accuracy": 0.8425,
                               "balanced_accuracy_ci95": [0.7225, 0.96], "n_errors": 0},
        "LLM": {"n": 400, "balanced_accuracy": 0.5125,
                "balanced_accuracy_ci95": [0.4849375, 0.545], "n_errors": 0},
        "n_seed_clusters": 10, "Cinfo_difference": -0.33, "Cinfo_ci95": [-0.44, -0.2125],
        "D1_point_pass": False, "scope": "controlled classification only",
    }
}


def make_tree(root: Path) -> Path:
    source = root / 'source_codes'
    formal = source / 'scenarios' / 'formal'
    formal.mkdir(parents=True)
    (formal / 'registry.yaml').write_text(REGISTRY, encoding='utf-8')
    for package in ('md_int_002_air_surface', 'ie_08_island_strike'):
        target = formal / package
        target.mkdir()
        (target / 'scenario.yaml').write_text('schema_version: package@2.0\n', encoding='utf-8')
    competition = source / 'scenarios' / 'competition_v1'
    for package in ('md_rec_001_medium', 'md_trk_007_standard', 'md_ad_005_standard',
                    'md_er_006_standard'):
        target = competition / package
        target.mkdir(parents=True)
        (target / 'scenario.yaml').write_text('schema_version: package@2.0\n', encoding='utf-8')
    return source


class ScenarioFamilyTests(unittest.TestCase):
    def test_category_comes_from_a_segment_not_a_prefix(self):
        self.assertEqual(e4.category_of('MD-AD-002-EASY'), '区域拒止 Area Denial')
        self.assertEqual(e4.category_of('MD-INT-003-EASY'), '拦截交战 Interception-Engagement')
        self.assertEqual(e4.category_of('IE-08-ISLAND-STRIKE'), '拦截交战 Interception-Engagement')
        self.assertEqual(e4.category_of('md_rec_001_medium'), '侦察搜索 Reconnaissance')
        self.assertEqual(e4.category_of('md_er_006_standard'), '应急响应 Emergency Response')
        self.assertEqual(e4.category_of('something-else'), 'unknown')

    def test_contract_id_collapses_difficulty_variants(self):
        self.assertEqual(e4.contract_id('MD-REC-001-EASY', 'md_rec_001_easy'), 'MD-REC-001')
        self.assertEqual(e4.contract_id('MD-REC-001-MEDIUM', 'md_rec_001_medium'), 'MD-REC-001')
        self.assertEqual(e4.contract_id('MD-TRK-007-STANDARD', 'md_trk_007_standard'), 'MD-TRK-007')
        # IE ids stay whole: that is the key the E10/D2 sources use for them.
        self.assertEqual(e4.contract_id('IE-08-ISLAND-STRIKE', 'ie_08_island_strike'),
                         'IE-08-ISLAND-STRIKE')

    def test_inventory_hashes_every_package_and_splits_admitted_from_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            source = make_tree(Path(folder))
            payload = e4.inventory(source)
            self.assertEqual(payload['counts'], {'total': 6, 'admitted': 2, 'candidate': 4})
            for row in payload['scenarios']:
                self.assertTrue(row['package_sha256'])
                self.assertGreater(row['file_count'], 0)
            categories = payload['by_category']
            self.assertEqual(categories['侦察搜索 Reconnaissance'],
                             {'admitted': 0, 'candidate': 1})
            self.assertEqual(categories['拦截交战 Interception-Engagement'],
                             {'admitted': 2, 'candidate': 0})

    def test_ledger_never_claims_an_unrun_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = e4.inventory(make_tree(Path(folder)))
            ledger = e4.ledger_template(payload, 'report.md')
            self.assertEqual(ledger['schema'], 'e4-admission-ledger@2')
            for row in ledger['scenarios']:
                self.assertEqual(row['gates']['D1_prime_decision_form']['verdict'], 'pending')
                self.assertEqual(row['gates']['D2_headroom']['verdict'], 'pending')
                self.assertIsNone(row['gates']['D2_headroom']['evidence'])
                # D3 has no implementation in this engine version: blocked, with a reason.
                self.assertEqual(row['gates']['D3_interface_budget']['verdict'], 'blocked')
                self.assertTrue(row['gates']['D3_interface_budget']['note'])

    def test_d1_is_reported_when_measured_blocked_when_mechanism_exists_and_na_otherwise(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = e4.inventory(make_tree(Path(folder)))
            report = e4.load_d1_report_from_payload(D1_SUMMARY, 'e10/summary.json')
            ledger = e4.ledger_template(payload, '', report)
            by_id = {row['public_id']: row for row in ledger['scenarios']}
            # MD-TRK-007 and MD-AD-005 declare a feint/decoy mechanism -> blocked, not N/A.
            self.assertEqual(by_id['MD-TRK-007-STANDARD']['gates'][
                'D1_information_asymmetry']['verdict'], 'blocked')
            self.assertEqual(by_id['MD-AD-005-STANDARD']['gates'][
                'D1_information_asymmetry']['verdict'], 'blocked')
            # A reconnaissance package has no such mechanism.
            rec = by_id['MD-REC-001-MEDIUM']['gates']['D1_information_asymmetry']
            self.assertEqual(rec['verdict'], 'not_applicable')
            self.assertIn('未声明', rec['note'])

    def test_d1_report_loader_keeps_numbers_and_the_failed_point_gate(self):
        report = e4.load_d1_report_from_payload(D1_SUMMARY, 'e10/summary.json')
        entry = report['IE-06-DECOY-MIXED']
        self.assertEqual(entry['numeric_balanced_accuracy'], 0.8425)
        self.assertEqual(entry['llm_balanced_accuracy'], 0.5125)
        self.assertFalse(entry['point_gate_passed'])
        self.assertEqual(entry['reference_thresholds'], {'numeric_max': 0.6, 'llm_min': 0.85})

    def test_d2_merge_fills_only_matching_contracts(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = e4.inventory(make_tree(Path(folder)))
            ledger = e4.ledger_template(payload, '')
            headroom = {"scenarios": {
                "MD-REC-001": {"best_baseline_policy": "sweep", "best_baseline_success_rate": 0.6,
                               "best_baseline_ci95": [0.4, 0.8], "d2_headroom_verdict": "pass",
                               "policies": {"sweep": {"seeds": 5}}},
                "MD-TRK-007": {"best_baseline_policy": "identity-honest",
                               "best_baseline_success_rate": 1.0,
                               "best_baseline_ci95": [1.0, 1.0], "d2_headroom_verdict": "fail",
                               "policies": {"identity-honest": {"seeds": 5}}},
            }}
            merged = e4.apply_d2(ledger, e4.d2_results(headroom, 'd2.json'))
            by_id = {row['public_id']: row for row in merged['scenarios']}
            self.assertEqual(by_id['MD-REC-001-MEDIUM']['gates']['D2_headroom']['verdict'], 'pass')
            self.assertEqual(by_id['MD-REC-001-MEDIUM']['gates']['D2_headroom']['success_rate'], 0.6)
            self.assertEqual(by_id['MD-TRK-007-STANDARD']['gates']['D2_headroom']['verdict'], 'fail')
            self.assertEqual(by_id['MD-ER-006-STANDARD']['gates']['D2_headroom']['verdict'],
                             'pending')
            # one MD-REC-001 package + one MD-TRK-007 package carry a D2 result
            self.assertEqual(merged['d2_applied']['matched'], 2)

    def test_appendix_counts_only_decided_gates(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = e4.inventory(make_tree(Path(folder)))
            ledger = e4.ledger_template(payload, '')
            headroom = {"scenarios": {
                "MD-ER-006": {"best_baseline_policy": "coordinated",
                              "best_baseline_success_rate": 0.6,
                              "best_baseline_ci95": [0.4, 0.8],
                              "d2_headroom_verdict": "pass",
                              "policies": {"coordinated": {"seeds": 5}}}}}
            merged = e4.apply_d2(ledger, e4.d2_results(headroom, 'd2.json'))
            text = e4.appendix_table(merged)
            self.assertIn('not_applicable', text)
            self.assertIn('blocked', text)
            self.assertIn('判定值含义', text)
            self.assertIn('（尚无）', text)  # no category has three decided scenarios yet

    def test_graded_merge_skips_rows_outside_the_calibrated_tree(self):
        """Rows outside the calibrated tree must not receive a graded value, and the mix must
        still match the rows that are inside it.

        MD-AD-006-ISLAND-STRIKE (the IE-08 alias, ``formal``) and MD-AD-006-STANDARD
        (``competition_v1``) share one contract id but are different scenarios.
        """
        with tempfile.TemporaryDirectory() as folder:
            payload = e4.inventory(make_tree(Path(folder)))
            ledger = e4.ledger_template(payload, '')
            gates = {name: {"verdict": "pending", "evidence": None, "note": None}
                     for name in e4.GATES}
            ledger["scenarios"] = [
                {"public_id": "MD-AD-006-ISLAND-STRIKE", "package": "ie_08_island_strike",
                 "contract_id": "MD-AD-006", "tree": "formal",
                 "category": "拦截交战 Interception-Engagement", "package_sha256": "b" * 64,
                 "gates": json.loads(json.dumps(gates))},
                {"public_id": "MD-AD-006-STANDARD", "package": "md_ad_006_standard",
                 "contract_id": "MD-AD-006", "tree": "competition_v1",
                 "category": "区域拒止 Area Denial", "package_sha256": "b" * 64,
                 "gates": json.loads(json.dumps(gates))},
            ]
            graded = {"scenarios": {"MD-AD-006": {
                "best_baseline_policy": "guard", "best_composite_mean": 0.788,
                "best_composite_ci95": [0.788, 0.788], "best_task_relevant_policy": "guard",
                "best_task_relevant_composite": 0.788, "headroom_band": "window",
                "d2_graded_verdict": "pass", "best_is_floor_control": False}}}
            merged = e4.apply_d2_graded(ledger, e4.d2_graded_results(graded, 'graded.json'))
            by_id = {row['public_id']: row for row in merged['scenarios']}
            self.assertEqual(by_id['MD-AD-006-STANDARD']['gates']['D2_headroom'][
                'graded']['composite'], 0.788)
            self.assertNotIn('graded', by_id['MD-AD-006-ISLAND-STRIKE']['gates']['D2_headroom'])
            self.assertEqual(merged['d2_graded_applied']['matched'], 1)
            self.assertEqual(merged['d2_graded_applied']['without_graded'], [])

    def test_appendix_shows_both_measurements(self):
        ledger = {"schema": "e4-admission-ledger@2", "scenarios": [{
            "public_id": "MD-REC-006-STANDARD", "package": "md_rec_006_standard",
            "contract_id": "MD-REC-006", "tree": "competition_v1",
            "category": "侦察搜索 Reconnaissance", "package_sha256": "c" * 64,
            "d1prime_prior": {"prior_score": 2.17},
            "gates": {
                "D1_prime_decision_form": {"verdict": "pending"},
                "D2_headroom": {"verdict": "pass", "verdict_binary": "fail", "success_rate": 1.0,
                                "graded": {"verdict": "pass", "composite": 0.635}},
                "D3_interface_budget": {"verdict": "blocked"},
                "D1_information_asymmetry": {"verdict": "not_applicable"},
            }}]}
        text = e4.appendix_table(ledger)
        self.assertIn("pass (0.64)", text)
        self.assertIn("二值 fail (1.00)", text)

    def test_appendix_tolerates_an_at1_ledger(self):
        at1 = {"schema": "e4-admission-ledger@1", "scenarios": [{
            "public_id": "IE-08-ISLAND-STRIKE", "package": "ie_08_island_strike",
            "contract_id": "IE-08", "tree": "formal",
            "category": "拦截交战 Interception-Engagement", "package_sha256": "a" * 64,
            "gates": {name: {"verdict": "pending", "evidence": None, "note": None}
                      for name in e4.GATES}}]}
        text = e4.appendix_table(at1)
        self.assertIn('IE-08-ISLAND-STRIKE', text)


if __name__ == '__main__':
    unittest.main()
