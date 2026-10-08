"""Offline tests for the E5 kappa report.

The report must: read the annotator's CSV as the ground truth, refuse to run while any
packet is unlabelled, and state a sub-threshold kappa honestly (never soften it).
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

spec = importlib.util.spec_from_file_location('e5_kappa_report_under_test',
                                              ROOT / 'e5_kappa_report.py')
report = importlib.util.module_from_spec(spec)
sys.modules['e5_kappa_report_under_test'] = report
spec.loader.exec_module(report)

KEY = {"E5-01-a16a": "case-a", "E5-02-b": "case-b"}
SUMMARY = {
    "n_paired": 2, "cohen_kappa": 0.25, "agreement": 0.5,
    "machine_label_counts": {"planning": 1, "execution": 0, "interface": 1},
    "confusion": {"planning": {"execution": 1}, "interface": {"balanced": 1}},
    "disagreements": [{"case_id": "case-a", "machine": "planning", "human": "execution"},
                      {"case_id": "case-b", "machine": "interface", "human": "balanced"}],
    "all_replay_gates_passed": True, "all_attributions_complete": True,
    "success_criterion": {"kappa_at_least": 0.6, "disagreements_at_most": 2, "met": False},
}


class KappaReportTests(unittest.TestCase):
    def write_inputs(self, folder, rows):
        human = Path(folder) / 'annotation_form.csv'
        human.write_text('packet_id,label,confidence,rationale\n' + ''.join(rows),
                         encoding='utf-8')
        kappa = Path(folder) / 'kappa.json'
        kappa.write_text(json.dumps(SUMMARY), encoding='utf-8')
        key = Path(folder) / 'key.json'
        key.write_text(json.dumps(KEY), encoding='utf-8')
        return kappa, human, key

    def test_renders_an_honest_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            kappa, human, key = self.write_inputs(folder, [
                'E5-01-a16a,execution,2,"tick 250 射击停止"\n',
                'E5-02-b,balanced,2,"两层都有问题"\n'])
            summary = report.load_cases(kappa)
            text = report.render(summary, report.load_rationales(human),
                                 json.loads(key.read_text(encoding='utf-8')))
            self.assertIn('0.250', text)
            self.assertIn('未达标', text)
            self.assertIn('归因歧义', text)
            self.assertIn('机器', text)
            self.assertIn('0 例', text)

    def test_refuses_to_run_while_a_packet_is_unlabelled(self):
        with tempfile.TemporaryDirectory() as folder:
            kappa, human, key = self.write_inputs(folder, ['E5-01-a16a,execution,2,"x"\n'])
            missing = [packet for packet in KEY
                       if packet not in report.load_rationales(human)]
            self.assertEqual(missing, ['E5-02-b'])

    def test_write_output_file(self):
        with tempfile.TemporaryDirectory() as folder:
            kappa, human, key = self.write_inputs(folder, [
                'E5-01-a16a,execution,2,"a"\n', 'E5-02-b,planning,1,"b"\n'])
            argv = ['e5_kappa_report.py', '--kappa', str(kappa), '--human', str(human),
                    '--key', str(key), '--output', str(Path(folder) / 'out.md')]
            original = sys.argv
            sys.argv = argv
            try:
                report.main()
            finally:
                sys.argv = original
            text = (Path(folder) / 'out.md').read_text(encoding='utf-8')
            self.assertIn("Cohen's κ", text)
            self.assertIn('混淆矩阵', text)


if __name__ == '__main__':
    unittest.main()
