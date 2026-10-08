"""Offline tests for the four-model side-by-side overview.

The overview must state the batch separation and must never look like a pooled
statistic; these tests pin that contract on synthetic analysis files.
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

spec = importlib.util.spec_from_file_location('e6_family_summary_under_test',
                                              ROOT / 'e6_family_summary.py')
family = importlib.util.module_from_spec(spec)
sys.modules['e6_family_summary_under_test'] = family
spec.loader.exec_module(family)


def block(mean, low, high, n=13, seeds=(1, 2, 3)):
    return {'mean': mean, 'ci95': [low, high], 'n': n, 'unit': 'seed', 'draws': 10000,
            'seeds_used': list(seeds), 'per_seed': {'2026100301': 0.5, '2026100302': -0.1}}


def analysis(models, verdicts, thinking=None):
    return {
        'schema': 'E6-model-invariance-analysis@1',
        'models': models,
        'verdicts': verdicts,
        'group_summary': {name: {'strong': block(0.6, 0.4, 0.8), 'hold': block(0.2, 0.19, 0.21),
                                 'strong_minus_hold': block(0.4, 0.2, 0.6),
                                 'strong_minus_pure_rl': block(-0.3, -0.7, 0.066)}
                          for name in models},
        'thinking_summary': thinking or {},
        'endpoint_continuity': [], 'provider_identity': [], 'data_problems': [],
        'seeds': list(range(1, 14)), 'reference_seeds': [1, 2, 3],
        'utility_definition': 'V', 'all_preregistered_cases_present': True,
        'all_preregistered_cases_valid': True, 'no_cross_batch_data_merged': True,
        'run_status': {'run': 'complete'},
    }


class FamilySummaryTests(unittest.TestCase):
    def write(self, folder, name, plan_extra, summary):
        root = Path(folder) / name
        (root / 'analysis').mkdir(parents=True)
        plan = {'max_tokens': plan_extra.pop('max_tokens'), 'seeds': [1] * 13,
                'reference_seeds': [1, 2, 3], 'conditions': ['strong', 'hold']}
        plan.update(plan_extra)
        (root / 'plan.json').write_text(json.dumps(plan), encoding='utf-8')
        (root / 'analysis' / 'e6_analysis.json').write_text(json.dumps(summary), encoding='utf-8')
        return root / 'analysis' / 'e6_analysis.json'

    def test_renders_four_models_from_two_batches_without_pooling(self):
        with tempfile.TemporaryDirectory() as folder:
            local = analysis(
                {'27b': {'served_name': 'Qwen3.8-27B', 'directory': 'models/Qwen3.8-27B-BF16'},
                 '8b': {'served_name': 'Qwen3-8B', 'directory': 'models/Qwen3-8B-BF16'}},
                {'27b': {'interface_causal_necessity': 'passed',
                         'deployment_behind_baseline': 'passed', 'overall': 'reproduced'},
                 '8b': {'interface_causal_necessity': 'passed',
                        'deployment_behind_baseline': 'passed', 'overall': 'reproduced'}},
                {'27b': {'expect_no_thinking': None, 'thinking_blocks': 0,
                         'cases_with_thinking': 0},
                 '8b': {'expect_no_thinking': None, 'thinking_blocks': 0,
                        'cases_with_thinking': 0}})
            remote = analysis(
                {'m3': {'served_name': 'MiniMax-M3', 'kind': 'remote-provider',
                        'base_url': 'https://api.example.invalid', 'expect_no_thinking': True},
                 'm27h': {'served_name': 'MiniMax-M2.7-highspeed', 'kind': 'remote-provider',
                          'base_url': 'https://api.example.invalid', 'expect_no_thinking': False}},
                {'m3': {'interface_causal_necessity': 'passed',
                        'deployment_behind_baseline': 'passed', 'overall': 'reproduced'},
                 'm27h': {'interface_causal_necessity': 'passed',
                          'deployment_behind_baseline': 'failed', 'overall': 'not_reproduced'}},
                {'m3': {'expect_no_thinking': True, 'thinking_blocks': 0, 'cases_with_thinking': 0},
                 'm27h': {'expect_no_thinking': False, 'thinking_blocks': 184,
                          'cases_with_thinking': 20}})
            a = self.write(folder, 'batch-local', {'max_tokens': 1024}, local)
            b = self.write(folder, 'batch-remote', {'max_tokens': 8192}, remote)
            rows = family.collect(a, a.parent.parent / 'plan.json') + \
                family.collect(b, b.parent.parent / 'plan.json')
            text = family.render(rows)
            for fragment in ('Qwen3.8-27B', 'Qwen3-8B', 'MiniMax-M3', 'MiniMax-M2.7-highspeed',
                             '未通过', '不适用（无此开关）', '184',
                             '不合并统计', '不可合并'):
                self.assertIn(fragment, text)
            self.assertIn('1024', text)
            self.assertIn('8192', text)
            self.assertEqual(len(rows), 4)

    def test_borderline_section_names_the_failing_model(self):
        with tempfile.TemporaryDirectory() as folder:
            remote = analysis(
                {'m27h': {'served_name': 'MiniMax-M2.7-highspeed', 'kind': 'remote-provider',
                          'expect_no_thinking': False}},
                {'m27h': {'interface_causal_necessity': 'passed',
                          'deployment_behind_baseline': 'failed', 'overall': 'not_reproduced'}},
                {'m27h': {'expect_no_thinking': False, 'thinking_blocks': 5,
                          'cases_with_thinking': 3}})
            path = self.write(folder, 'batch', {'max_tokens': 8192}, remote)
            rows = family.collect(path, path.parent.parent / 'plan.json')
            rows[0]['rl_delta'] = 0.022
            rows[0]['rl_ci'] = '[0.000, 0.067]'
            text = family.render(rows)
            self.assertIn('MiniMax-M2.7-highspeed 未通过', text)


if __name__ == '__main__':
    unittest.main()
