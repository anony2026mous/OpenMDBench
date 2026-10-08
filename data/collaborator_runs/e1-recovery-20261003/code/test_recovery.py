import json
from pathlib import Path
import tempfile
import unittest
from resume_e1 import classify_completion, digest


class RecoveryTests(unittest.TestCase):
    def make_case(self, root, exit_code, report):
        folder = Path(root) / 'COUNT-A' / 'pure-llm-strong-g0' / 'seed-4101'
        folder.mkdir(parents=True)
        (folder / 'report.json').write_text(json.dumps(report))
        c = {'config': {'scenario': 'COUNT-A', 'arm': 'pure-llm', 'dose': 'strong', 'greedy': False,
                       'seed': 4101, 'protocol_sha': 'frozen'}, 'exit_code': exit_code,
             'report_sha': digest(folder / 'report.json')}
        (folder / 'completion.json').write_text(json.dumps(c))
        return folder

    def test_valid_losing_result_not_retried(self):
        with tempfile.TemporaryDirectory() as root:
            f = self.make_case(root, 0, {'V': -1})
            kind, value = classify_completion(f, {'public_id': 'COUNT-A'}, 'frozen', lambda p, r: {'V': -1, 'SR': 0})
            self.assertEqual(kind, 'valid')
            self.assertEqual(value['SR'], 0)

    def test_timeout_is_engineering_only(self):
        with tempfile.TemporaryDirectory() as root:
            f = self.make_case(root, 1, {'aborted': {'reason': 'step_timeout'}})
            self.assertEqual(classify_completion(f, {'public_id': 'COUNT-A'}, 'frozen', lambda p, r: None)[0], 'step_timeout')

    def test_changed_report_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            f = self.make_case(root, 0, {'V': 0})
            (f / 'report.json').write_text('{}')
            with self.assertRaises(ValueError): classify_completion(f, {'public_id': 'COUNT-A'}, 'frozen', lambda p, r: None)

    def test_non_timeout_failure_not_rerun(self):
        with tempfile.TemporaryDirectory() as root:
            f = self.make_case(root, 1, {'aborted': {'reason': 'something_else'}})
            with self.assertRaises(ValueError): classify_completion(f, {'public_id': 'COUNT-A'}, 'frozen', lambda p, r: None)

    def test_native_timeout_string(self):
        with tempfile.TemporaryDirectory() as root:
            f = self.make_case(root, 1, {'aborted': 'step_timeout at tick 0: 78.7s > 60.0s'})
            self.assertEqual(classify_completion(f, {'public_id': 'COUNT-A'}, 'frozen', lambda p, r: None)[0], 'step_timeout')


if __name__ == '__main__': unittest.main()
