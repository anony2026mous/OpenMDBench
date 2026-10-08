import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import e1_split as split


def row(count=17, arm='rule', v=.7, sr=.8):
    return {'count': count, 'family': 'IE-05-MULTI-AXIS', 'public_id': f'COUNT-IE-05-MULTI-AXIS-N{count:03d}',
            'arm': arm, 'eligible': True, 'V': {'mean': v, 'n_seeds': 10, 'ci95': [v, v]},
            'SR': {'mean': sr, 'n_seeds': 10, 'ci95': [sr, sr]}}


class Tests(unittest.TestCase):
    def test_fixed_comparator_uses_score_not_success_rate(self):
        rs = [row(arm='rule', v=.8, sr=.8), row(arm='rl', v=.7, sr=1), row(arm='pure-llm', v=.6, sr=1)]
        self.assertEqual(split.selected(rs, [17])[0]['calibration_selected_pure'], 'rule')

    def test_incomplete_calibration_never_selects(self):
        rs = [row(arm=a) for a in split.PURE]
        rs[0]['V']['n_seeds'] = 9
        with self.assertRaises(ValueError):
            split.selected(rs, [17])

    def test_gate_counts_and_no_llm(self):
        jobs = split.gate_jobs([row(n) for n in [17, 18, 19, 27]], list(range(4151, 4161)))
        self.assertEqual(len(jobs), 200)
        self.assertEqual({j['arm'] for j in jobs}, {'rule', 'rule-rl'})
        self.assertEqual(len({tuple(sorted(j.items())) for j in jobs}), 200)

    def test_owner_blocks_all_ten_seeds_and_no_duplicate_cases(self):
        all_keys = set()
        for owner, counts in split.ASSIGNMENTS.items():
            rs = [{**row(n), 'calibration_selected_pure': 'rule'} for n in counts]
            jobs = split.confirmation_jobs(rs, list(range(4201, 4211)))
            self.assertEqual(len(jobs), 60)
            keys = {tuple(sorted(j.items())) for j in jobs}
            self.assertFalse(all_keys & keys)
            all_keys |= keys
            for n in counts:
                self.assertEqual(len([j for j in jobs if j['scenario'].endswith(f'N{n:03d}')]), 30)
        self.assertEqual(len(all_keys), 120)

    def test_modified_and_losing_completion_handling(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            split.write(p / 'report.json', {'V': .2})
            expected = split.completion_config(split.job_spec(row(), 4201, 'rule'), 'p', 's')
            split.write(p / 'completion.json', {'config': expected, 'exit_code': 0, 'elapsed_seconds': 1,
                                               'report_sha': split.sha(p / 'report.json')})
            campaign = SimpleNamespace(outcome=lambda p, r: {'V': .2, 'SR': 0, 'eligible': True})
            self.assertEqual(split.checked_case(p, row(), expected, campaign)['outcome']['SR'], 0)
            split.write(p / 'report.json', {'V': .8})
            with self.assertRaises(ValueError):
                split.checked_case(p, row(), expected, campaign)

    def test_wave_incomplete_loss_is_retained_not_retried(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            split.write(p / 'report.json', {'V': .1})
            expected = split.completion_config(split.job_spec(row(), 4151, 'rule', 'hold'), 'p', 's')
            split.write(p / 'completion.json', {'config': expected, 'exit_code': 0, 'elapsed_seconds': 1,
                                               'report_sha': split.sha(p / 'report.json')})
            campaign = SimpleNamespace(outcome=lambda p, r: {'V': .1, 'SR': 0, 'eligible': False})
            self.assertFalse(split.checked_case(p, row(), expected, campaign)['outcome']['eligible'])

    @unittest.skipUnless(os.name == 'posix', 'Remote Linux flock only')
    def test_screen_exports_then_pauses_even_when_gates_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, batch, code, repo = [root / k for k in ['source', 'batch', 'code', 'repo']]
            for p in [source, batch, code, repo]:
                p.mkdir()
            split.write(source / 'protocol.json', {})
            split.write(source / 'variants.json', {'engine': str(source / 'engine')})
            split.write(source / 'recovery/r02/status.json', {'state': 'finished'})
            split.write(source / 'status.json', {'state': 'count-menu-infeasible'})
            split.write(batch / 'protocol/split_execution.json', {
                'toolkit_sha256': split.sha(Path(split.__file__)), 'original_code_hashes': {},
                'original_protocol_sha256': split.sha(source / 'protocol.json'),
                'engine_hashes': {}, 'eval_python_hashes': {}, 'weights': {},
                'gate_seeds': list(range(4151, 4161))})
            stats = [row(n, a, .8 if a == 'rule' else .6) for n in [17, 18, 19, 27] for a in split.PURE]
            gates = [{'count': n, 'D1_prime': {'pass': False}, 'D2_calibration': {'pass': True},
                      'D3': [{'pass': False}, {'pass': False}]} for n in [17, 18, 19, 27]]
            fake = SimpleNamespace(prepare=lambda r, s: None)
            args = SimpleNamespace(batch=batch, code=code, source=source, repo=repo, watch_pid=999999)
            with patch.object(split, 'process_running', return_value=False), patch.object(split, 'check_inventory'), \
                 patch.object(split, 'load_campaign', return_value=fake), \
                 patch.object(split, 'calibration', return_value=(stats, [])), \
                 patch.object(split, 'menu_feasibility', return_value={'families': {}, 'IE09_rule_N18_minus_N6': {'mean': -.1, 'ci95': [-.2, 0]}}), \
                 patch.object(split, 'run_jobs', return_value=[]) as jobs, \
                 patch.object(split, 'summarize_gates', return_value=gates), \
                 patch.object(split, 'export_handoff', return_value=batch / 'package.zip') as export:
                split.screen(args)
                self.assertEqual(len(jobs.call_args.args[0]), 200)
                export.assert_called_once()
            state = split.read(batch / 'status.json')
            self.assertEqual(state['state'], 'paused-after-calibration-and-gates')
            self.assertEqual(state['completed_confirmation'], 0)
            self.assertFalse(state['confirmation_auto_start'])

    def test_actual_model_shard_identity_is_hashed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / 'model-00001-of-00001.safetensors').write_bytes(b'fake-unit-test-checkpoint')
            split.write(p / 'config.json', {'model': 'unit-test'})
            before = split.model_record(p)
            (p / 'model-00001-of-00001.safetensors').write_bytes(b'different-unit-test-data')
            self.assertNotEqual(before, split.model_record(p))


if __name__ == '__main__':
    unittest.main()
