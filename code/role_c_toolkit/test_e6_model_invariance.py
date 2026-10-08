"""Offline contract tests for the E6 model-invariance tooling.

No network, no GPU, no real episode: the grid runner is replaced by a stub that
writes the two artifacts the real runner writes.
"""
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


e6 = load_module('e6_model_invariance', 'e6_model_invariance.py')
analyze = load_module('e6_analyze', 'e6_analyze.py')
summary_module = load_module('e6_summary', 'e6_summary.py')
summary = summary_module

CONSTANT = 'a' * 64


def base_plan(**overrides):
    plan = {
        'schema': e6.SCHEMA_PLAN,
        'seeds': list(range(2026100301, 2026100311)),
        'reference_seeds': [2026100301, 2026100302, 2026100303],
        'conditions': ['strong', 'hold'],
        'difficulty': 'medium', 'task_mode': 'continuous', 'stack': 'llm-rl',
        'plan_interval': 10, 'max_tokens': 1024, 'temperature': .1,
        'enable_thinking': False, 'llm_retries': 0,
        'llm_timeout_seconds': 120, 'case_wall_budget_seconds': 60,
        'models': {
            '27b': {'served_name': 'Qwen3.8-27B', 'directory': 'models/Qwen3.8-27B-BF16',
                    'manifest_sha256': CONSTANT, 'max_model_len': 131072, 'ports': [8001],
                    'endpoints': ['http://127.0.0.1:8001/v1']},
            '8b': {'served_name': 'Qwen3-8B', 'directory': 'models/Qwen3-8B-BF16',
                   'manifest_sha256': CONSTANT, 'max_model_len': 40960, 'ports': [8003],
                   'endpoints': ['http://127.0.0.1:8003/v1']},
        },
        'runner_sha256': CONSTANT, 'frozen_files': {},
    }
    plan.update(overrides)
    return plan


class PlanContractTests(unittest.TestCase):
    def verify(self, plan):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'plan.json'
            path.write_text(json.dumps(plan), encoding='utf-8')
            original_sha, original_plan_sha = e6.sha, None
            e6.sha = lambda _path: CONSTANT
            try:
                e6.verify_plan(plan, path)
            finally:
                e6.sha = original_sha

    def test_accepts_the_preregistered_shape(self):
        self.verify(base_plan())

    def test_rejects_wrong_seed_count(self):
        with self.assertRaises(ValueError):
            self.verify(base_plan(seeds=[1, 2, 3]))

    def test_accepts_an_extended_seed_set_with_the_extension_declared(self):
        plan = base_plan(seeds=list(range(2026100301, 2026100314)))
        plan['seed_set_extended_after_first_batch'] = True
        plan['extended_from'] = 'plan-10-seeds.json'
        self.verify(plan)

    def test_rejects_an_extension_flag_without_extra_seeds(self):
        plan = base_plan()
        plan['seed_set_extended_after_first_batch'] = True
        with self.assertRaises(ValueError):
            self.verify(plan)

    def test_rejects_unknown_condition(self):
        with self.assertRaises(ValueError):
            self.verify(base_plan(conditions=['strong']))

    def test_rejects_served_name_swap(self):
        plan = base_plan()
        plan['models']['8b']['served_name'] = 'Qwen3.8-27B'
        with self.assertRaises(ValueError):
            self.verify(plan)

    def test_rejects_shared_endpoint_between_models(self):
        plan = base_plan()
        plan['models']['8b']['endpoints'] = ['http://127.0.0.1:8001/v1']
        plan['models']['8b']['ports'] = [8001]
        with self.assertRaises(ValueError):
            self.verify(plan)

    def test_rejects_a_second_reference_replica(self):
        # Replica b's GPU pair belongs to the second model, so the 27B reference must
        # stay on exactly one preregistered endpoint.
        plan = base_plan()
        plan['models']['27b']['endpoints'] = ['http://127.0.0.1:8001/v1',
                                              'http://127.0.0.1:8002/v1']
        plan['models']['27b']['ports'] = [8001, 8002]
        with self.assertRaises(ValueError):
            self.verify(plan)

    def test_rejects_port_url_disagreement(self):
        plan = base_plan()
        plan['models']['8b']['ports'] = [8004]
        with self.assertRaises(ValueError):
            self.verify(plan)


class CaseRunnerTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = Path(self.folder.name)
        snapshot = root / 'snapshots' / 'SNAP'
        (snapshot / 'role_c_toolkit').mkdir(parents=True)
        self.snapshot = snapshot
        self.plan = base_plan(snapshot=str(snapshot), checkpoint=str(root / 'theta.npz'))
        (root / 'theta.npz').write_bytes(b'weights')
        self.plan_path = root / 'plan.json'
        self.plan_path.write_text(json.dumps(self.plan), encoding='utf-8')
        self.original = (e6.sha, e6.verify_plan, e6.load_runner)
        e6.sha = lambda _path: CONSTANT
        e6.verify_plan = lambda plan, path: CONSTANT

        class FakeGrid:
            @staticmethod
            def run_one(args):
                args.output.mkdir(parents=True, exist_ok=True)
                report = {'complete': True, 'V': 0.75, 'steps': 80, 'elapsed_seconds': 12.0,
                          'agent_stats': {'fallback_count': 0, 'goai_rejected': 0,
                                          'plan_calls': 8, 'parse_failures': 0},
                          'd1': {'input_role_truth_leaks': [], 'prompt_role_truth_leaks': []}}
                (args.output / 'episode.json').write_text(json.dumps(report), encoding='utf-8')
                if args.arm == 'llm-rl':
                    rows = [{'kind': 'request', 'model': args.model, 'base_url': args.base_url,
                             'max_tokens': 1024, 'temperature': .1, 'enable_thinking': False,
                             'system': 's', 'user': 'u'},
                            {'kind': 'response', 'text': 'ok', 'elapsed_seconds': 1.5, 'empty': False}]
                    (args.output / 'requests.jsonl').write_text(
                        chr(10).join(json.dumps(row) for row in rows), encoding='utf-8')
                if args.arm == 'llm-rl':
                    # The real runner reaches the LLM path through HybridAgent; the stub
                    # only has to make the request-lock checks pass, which it does above.
                    pass
                return 0

        e6.load_runner = lambda snapshot: FakeGrid

        # The real grid package is a sibling of the snapshot, not importable here;
        # the stub only needs the two symbols run_case patches on the LLM path.
        class FakeHybrid:
            PLANNER_SYSTEM_PROMPT = 'prompt'

            @staticmethod
            def _call_planner_llm(self, prompt):
                return ''

        class FakeMappo:
            @staticmethod
            def make_goai_controller(*args, **kwargs):
                def controller(env, unit_id, goal_state):
                    return {}
                return controller

        hybrid = type(sys)('grid_env.agents.hybrid_agent')
        hybrid.HybridAgent = FakeHybrid
        hybrid.PLANNER_SYSTEM_PROMPT = FakeHybrid.PLANNER_SYSTEM_PROMPT
        mappo = type(sys)('grid_env.agents.mappo_agent')
        mappo.make_goai_controller = FakeMappo.make_goai_controller
        package = type(sys)('grid_env')
        agents = type(sys)('grid_env.agents')
        agents.hybrid_agent, agents.mappo_agent = hybrid, mappo
        self.stubs = {'grid_env': package, 'grid_env.agents': agents,
                      'grid_env.agents.hybrid_agent': hybrid,
                      'grid_env.agents.mappo_agent': mappo}

    def tearDown(self):
        e6.sha, e6.verify_plan, e6.load_runner = self.original
        self.folder.cleanup()

    def test_pure_rl_reference_needs_no_llm_fields(self):
        output = Path(self.folder.name) / 'episodes' / 'rl-case'
        with patch.dict(sys.modules, self.stubs):
            code = e6.run_case(self.plan_path, output, '8b', 'strong', 2026100301, 0, arm='rl')
        self.assertEqual(code, 0)
        result = json.loads((output / 'E6-case.json').read_text(encoding='utf-8'))
        self.assertTrue(result['analysis_valid'])
        self.assertIsNone(result['endpoint'])
        self.assertEqual(result['V'], 0.75)

    def test_llm_case_without_a_recorded_call_is_invalid(self):
        output = Path(self.folder.name) / 'episodes' / 'llm-case'
        with patch.dict(sys.modules, self.stubs):
            code = e6.run_case(self.plan_path, output, '8b', 'strong', 2026100302, 0)
        self.assertEqual(code, 2)
        result = json.loads((output / 'E6-case.json').read_text(encoding='utf-8'))
        self.assertFalse(result['analysis_valid'])
        self.assertIn('LLM_RL_path_not_exercised', result['invalid_reasons'])

    def test_unpreregistered_case_is_refused(self):
        with self.assertRaises(ValueError):
            e6.run_case(self.plan_path, Path(self.folder.name) / 'x', '8b', 'strong', 424242, 0)


class AnalyzerTests(unittest.TestCase):
    """A synthetic two-model run: the analyzer must not need the real grid."""

    def write_case(self, run_dir, model, condition, seed, value, arm='llm-rl'):
        identifier = e6.case_id(model, condition, seed) if arm == 'llm-rl' else f'{model}-rl-s{seed}'
        folder = Path(run_dir) / 'episodes' / identifier
        folder.mkdir(parents=True, exist_ok=True)
        native = folder / 'episode.json'
        native.write_text(json.dumps({'complete': True, 'V': value}), encoding='utf-8')
        result = {'schema': e6.SCHEMA_CASE, 'model': model, 'condition': condition, 'seed': seed,
                  'arm': arm, 'replica': 0 if arm == 'llm-rl' else None,
                  'served_name': e6.SERVED[model] if arm == 'llm-rl' else None,
                  'endpoint': 'http://127.0.0.1:8001/v1' if arm == 'llm-rl' else None,
                  'native_report': str(native), 'native_report_sha256': 'x',
                  'V': value, 'complete': True, 'steps': 60, 'analysis_valid': True,
                  'invalid_reasons': [], 'plan_sha256': 'y',
                  'costs': {'llm_calls': 5, 'actual_API_total_tokens': 100,
                            'request_seconds': 4.0, 'episode_wall_seconds': 30.0},
                  'agent_stats': {'fallback_count': 0}, 'RL_controller_observation': {}}
        path = folder / 'E6-case.json'
        path.write_text(json.dumps(result), encoding='utf-8')
        return {'case_id': identifier, 'exit_code': 0, 'result': str(path),
                'analysis_valid': True, 'model': model, 'condition': condition, 'seed': seed,
                'sha256': CONSTANT}

    def build_run(self, root, plan, model, values):
        run_dir = Path(root) / f'run-{model}'
        run_dir.mkdir(parents=True, exist_ok=True)
        state = {'schema': e6.SCHEMA_STATUS, 'status': 'complete', 'pid': 1,
                 'plan_sha256': 'z', 'completed': [], 'active': {}, 'failures': []}
        for condition, seed, value in values:
            state['completed'].append(self.write_case(run_dir, model, condition, seed, value))
        for seed, value in plan['values_rl'][model]:
            state['completed'].append(self.write_case(run_dir, model, 'strong', seed, value, 'rl'))
        (run_dir / 'status.json').write_text(json.dumps(state), encoding='utf-8')
        return run_dir

    def test_two_run_directories_merge_into_one_verdict(self):
        with tempfile.TemporaryDirectory() as folder:
            plan = base_plan()
            plan_path = Path(folder) / 'plan.json'
            plan_path.write_text(json.dumps(plan), encoding='utf-8')
            # 27B: strong below hold and below its pure-RL reference -> both criteria fail
            # the way a real "not reproduced" batch would.  8B: identical arms -> the
            # paired difference is exactly zero, so it must not be called significant.
            values_27b, values_8b = [], []
            for index, seed in enumerate(plan['seeds']):
                strong = 0.1 + 0.01 * index
                values_27b.append(('strong', seed, strong))
                values_27b.append(('hold', seed, 0.6 + 0.01 * index if index else 0.61))
                values_8b.append(('strong', seed, 0.4))
                values_8b.append(('hold', seed, 0.4))
            plan['values_rl'] = {'27b': [(seed, 0.9) for seed in plan['reference_seeds']],
                                 '8b': [(seed, 0.9) for seed in plan['reference_seeds']]}
            run_27b = self.build_run(folder, plan, '27b', values_27b)
            run_8b = self.build_run(folder, plan, '8b', values_8b)
            reference_paths = sorted((run_27b / 'episodes').glob('27b-rl-s*'))
            self.assertEqual(len(reference_paths), len(plan['reference_seeds']))
            for path in reference_paths:
                row = json.loads((path / 'E6-case.json').read_text(encoding='utf-8'))
                self.assertEqual(row['arm'], 'rl')
                self.assertEqual(row['V'], 0.9)
            original_sha = analyze.sha
            analyze.sha = lambda _path: CONSTANT
            try:
                summary = analyze.analyze([run_27b, run_8b], plan_path, Path(folder) / 'analysis')
            finally:
                analyze.sha = original_sha
            # 27B: strong below hold, and strong below its pure-RL reference -> the interface
            # criterion fails and the "behind baseline" criterion holds, which is exactly the
            # combination the law predicts.  8B: identical arms -> the paired difference is
            # exactly zero, so it must not be reported as significant.
            self.assertEqual(summary['verdicts']['27b']['interface_causal_necessity'], 'failed')
            self.assertEqual(summary['verdicts']['27b']['deployment_behind_baseline'], 'passed')
            self.assertEqual(summary['verdicts']['27b']['overall'], 'not_reproduced')
            self.assertEqual(summary['verdicts']['27b']['overall'], 'not_reproduced')
            self.assertEqual(summary['verdicts']['8b']['interface_causal_necessity'], 'failed')

    def test_positive_but_unstable_effect_is_not_called_significant(self):
        """A positive mean whose interval still crosses zero must not be a pass."""
        with tempfile.TemporaryDirectory() as folder:
            plan = base_plan()
            plan_path = Path(folder) / 'plan.json'
            plan_path.write_text(json.dumps(plan), encoding='utf-8')
            values = []
            for index, seed in enumerate(plan['seeds']):
                # Mean is +0.1, but seed noise reaches -0.4 and +0.6.
                values.append(('strong', seed, 0.5 + (0.6 if index % 2 else -0.4)))
                values.append(('hold', seed, 0.5))
            plan['values_rl'] = {'27b': [], '8b': []}
            run = self.build_run(folder, plan, '27b', values)
            original_sha = analyze.sha
            analyze.sha = lambda _path: CONSTANT
            try:
                summary = analyze.analyze([run], plan_path, Path(folder) / 'analysis')
            finally:
                analyze.sha = original_sha
            block = summary['group_summary']['27b']['strong_minus_hold']
            self.assertAlmostEqual(block['mean'], 0.1, places=6)
            self.assertLess(block['ci95'][0], 0)
            self.assertEqual(summary['verdicts']['27b']['interface_causal_necessity'],
                             'not_significant_ci_includes_zero')
            # This run deliberately omits the other model, so it must say so.
            self.assertEqual(summary['verdicts']['_run'], 'incomplete_preregistered_case_set')


class SchedulerTests(unittest.TestCase):
    """The scheduler must finish every preregistered case on bounded slots."""

    def test_every_preregistered_case_completes_without_deadlock(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan = base_plan(seeds=[1, 2, 3, 4], reference_seeds=[1], snapshot=str(root / 'snap'))
            (root / 'snap' / 'role_c_toolkit').mkdir(parents=True)
            plan['models']['27b']['endpoints'] = ['http://127.0.0.1:8001/v1',
                                                  'http://127.0.0.1:8002/v1']
            plan['models']['27b']['ports'] = [8001, 8002]
            (root / 'plan.json').write_text(json.dumps(plan), encoding='utf-8')
            (root / 'endpoints.json').write_text(json.dumps(
                {'plan_sha256': CONSTANT, 'records': [
                    {'model': name, 'base_url': entry['endpoints'][0], 'reply_non_empty': True}
                    for name, entry in plan['models'].items()]}), encoding='utf-8')
            launched = []

            class FakeProcess:
                def __init__(self, command, **kwargs):
                    self.pid = 4321
                    self.command = command
                    launched.append(command)

                def wait(self, timeout=None):
                    output = Path(self.command[self.command.index('--output') + 1])
                    output.mkdir(parents=True, exist_ok=True)
                    # The real child runs the case and writes its own verdict; model
                    # the one case that must be reported as invalid.
                    valid = output.name != '8b-hold-s2'
                    (output / 'E6-case.json').write_text(json.dumps(
                        {'analysis_valid': valid, 'V': 0.5}), encoding='utf-8')
                    return 0 if valid else 2

                def terminate(self):
                    return None

            original = (e6.sha, e6.verify_plan)
            e6.sha = lambda _path: CONSTANT
            e6.verify_plan = lambda plan, path: CONSTANT
            with patch.object(e6.subprocess, 'Popen', FakeProcess):
                try:
                    code = e6.schedule(root / 'plan.json', root / 'run', ['27b', '8b'], 2)
                finally:
                    e6.sha, e6.verify_plan = original
            state = json.loads((root / 'run' / 'status.json').read_text(encoding='utf-8'))
            # A failed case is reported, not hidden, and never blocks the others.
            self.assertEqual(code, 1)
            self.assertEqual(state['status'], 'complete_with_failures')
            self.assertEqual(len(state['completed']), 2 * (4 * 2 + 1))
            self.assertEqual([row['case_id'] for row in state['failures']], ['8b-hold-s2'])
            self.assertEqual(state['active'], {})
            self.assertEqual(len(launched), 2 * (4 * 2 + 1))

    def test_extension_only_runs_the_newly_added_cases(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'snap' / 'role_c_toolkit').mkdir(parents=True)
            plan = base_plan(seeds=[1, 2, 3, 4], reference_seeds=[1], snapshot=str(root / 'snap'),
                             case_wall_budget_seconds=60)
            (root / 'plan.json').write_text(json.dumps(plan), encoding='utf-8')
            (root / 'endpoints.json').write_text(json.dumps(
                {'plan_sha256': CONSTANT, 'records': [
                    {'model': name, 'base_url': entry['endpoints'][0], 'reply_non_empty': True}
                    for name, entry in plan['models'].items()]}), encoding='utf-8')
            launched = []

            class FakeProcess:
                def __init__(self, command, **kwargs):
                    self.pid = 99
                    self.command = command
                    launched.append(command)

                def wait(self, timeout=None):
                    output = Path(self.command[self.command.index('--output') + 1])
                    output.mkdir(parents=True, exist_ok=True)
                    (output / 'E6-case.json').write_text(json.dumps(
                        {'analysis_valid': True, 'V': 0.5}), encoding='utf-8')
                    return 0

                def terminate(self):
                    return None

            original = (e6.sha, e6.verify_plan)
            e6.sha = lambda _path: CONSTANT
            e6.verify_plan = lambda plan, path: CONSTANT
            try:
                with patch.object(e6.subprocess, 'Popen', FakeProcess):
                    e6.schedule(root / 'plan.json', root / 'run', ['27b'], 2)
                    first_round = len(launched)
                    # Same seeds again: nothing to do, and the run must refuse silently.
                    e6.schedule(root / 'plan.json', root / 'run', ['27b'], 2, extend=True)
                    self.assertEqual(len(launched), first_round)
                    # Extend the plan with one new seed and one new reference seed.
                    extended = dict(plan, seeds=[1, 2, 3, 4, 5], reference_seeds=[1, 2],
                                    seed_set_extended_after_first_batch=True)
                    (root / 'plan-ext.json').write_text(json.dumps(extended), encoding='utf-8')
                    launched.clear()
                    e6.schedule(root / 'plan-ext.json', root / 'run', ['27b'], 2, extend=True)
            finally:
                e6.sha, e6.verify_plan = original
            # Only the two new strong/hold pairs plus one new reference episode.
            self.assertEqual(len(launched), 3)
            state = json.loads((root / 'run' / 'status.json').read_text(encoding='utf-8'))
            self.assertEqual(len(state['completed']), 2 * 5 + 2)
            self.assertEqual(state['extensions'][0]['plan_sha256'], CONSTANT)
            self.assertEqual(state['failures'], [])


class ProviderPlanAnalyzerTests(unittest.TestCase):
    """The analyzer must also accept a plan whose models are remote providers."""

    def test_remote_provider_plan_without_local_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan = base_plan()
            plan['models'] = {
                'm3': {'served_name': 'MiniMax-M3', 'kind': 'remote-provider', 'provider': 'minimax',
                       'base_url': 'https://api.example.invalid', 'expected_manifest': None,
                       'thinking_policy': 'disabled', 'expect_no_thinking': True},
            }
            plan.pop('models')
            plan['models'] = {'m3': {'served_name': 'MiniMax-M3', 'kind': 'remote-provider',
                                     'provider': 'minimax',
                                     'base_url': 'https://api.example.invalid',
                                     'thinking_policy': 'disabled', 'expect_no_thinking': True}}
            plan_path = root / 'plan.json'
            plan_path.write_text(json.dumps(plan), encoding='utf-8')
            run_dir = root / 'run-m3'
            (run_dir / 'episodes').mkdir(parents=True)
            state = {'schema': e6.SCHEMA_STATUS, 'status': 'complete', 'pid': 1,
                     'plan_sha256': 'z', 'completed': [], 'active': {}, 'failures': []}
            for index, seed in enumerate(plan['seeds']):
                for condition, value in (('strong', 0.6 + 0.02 * index), ('hold', 0.2)):
                    identifier = e6.case_id('m3', condition, seed)
                    case = run_dir / 'episodes' / identifier
                    case.mkdir(parents=True, exist_ok=True)
                    native = case / 'episode.json'
                    native.write_text(json.dumps({'complete': True}), encoding='utf-8')
                    (case / 'E6-case.json').write_text(json.dumps({
                        'schema': e6.SCHEMA_CASE, 'model': 'm3', 'condition': condition,
                        'seed': seed, 'arm': 'llm-rl', 'served_name': 'MiniMax-M3',
                        'provider': 'minimax', 'native_report': str(native), 'V': value,
                        'complete': True, 'analysis_valid': True, 'invalid_reasons': [],
                        'thinking_blocks': 0, 'expect_no_thinking': True,
                        'costs': {'llm_calls': 3, 'actual_API_total_tokens': 100},
                        'agent_stats': {}}), encoding='utf-8')
                    state['completed'].append({'case_id': identifier, 'exit_code': 0,
                                               'result': str(case / 'E6-case.json'),
                                               'analysis_valid': True, 'model': 'm3',
                                               'condition': condition, 'seed': seed,
                                               'sha256': CONSTANT})
            for seed in plan['reference_seeds']:
                identifier = f'm3-rl-s{seed}'
                case = run_dir / 'episodes' / identifier
                case.mkdir(parents=True, exist_ok=True)
                native = case / 'episode.json'
                native.write_text(json.dumps({'complete': True}), encoding='utf-8')
                (case / 'E6-case.json').write_text(json.dumps({
                    'schema': e6.SCHEMA_CASE, 'model': 'm3', 'condition': 'strong', 'seed': seed,
                    'arm': 'rl', 'analysis_valid': True, 'invalid_reasons': [], 'V': 0.9,
                    'costs': {}, 'agent_stats': {}}), encoding='utf-8')
                state['completed'].append({'case_id': identifier, 'exit_code': 0,
                                           'result': str(case / 'E6-case.json'),
                                           'analysis_valid': True, 'model': 'm3',
                                           'condition': 'strong', 'seed': seed,
                                           'sha256': CONSTANT})
            (run_dir / 'status.json').write_text(json.dumps(state), encoding='utf-8')
            original_sha = analyze.sha
            analyze.sha = lambda _path: CONSTANT
            try:
                summary = analyze.analyze([run_dir], plan_path, root / 'analysis')
            finally:
                analyze.sha = original_sha
            self.assertEqual(summary['models']['m3']['kind'], 'remote-provider')
            self.assertIsNone(summary['models']['m3'].get('directory'))
            self.assertEqual(summary['thinking_summary']['m3']['thinking_blocks'], 0)
            self.assertTrue(summary['all_preregistered_cases_present'])
            text = summary_module.render(summary)
            self.assertIn('MiniMax-M3', text)
            self.assertIn('要求关闭思考', text)


class StatisticsTests(unittest.TestCase):
    def test_bootstrap_interval_brackets_the_mean(self):
        block = analyze.bootstrap([0.9, 0.85, 0.95, 0.8, 0.92])
        self.assertAlmostEqual(block['mean'], statistics.fmean([0.9, 0.85, 0.95, 0.8, 0.92]))
        self.assertLessEqual(block['ci95'][0], block['mean'])
        self.assertGreaterEqual(block['ci95'][1], block['mean'])
        self.assertEqual(block['n'], 5)

    def test_bootstrap_is_deterministic(self):
        values = [0.2, 0.4, 0.6, 0.8]
        self.assertEqual(analyze.bootstrap(values)['ci95'], analyze.bootstrap(values)['ci95'])

    def test_too_few_seeds_reports_not_evaluable(self):
        block = analyze.bootstrap([0.5, 0.6])
        self.assertIsNone(block['ci95'])
        self.assertIn('too few', block['interpretation'])


class SummaryRenderingTests(unittest.TestCase):
    def test_unknown_verdict_does_not_crash(self):
        self.assertEqual(summary.LABELS.get('something_new', '—'), '—')

    def test_render_covers_every_model_and_limit(self):
        plan_models = {'27b': {'served_name': 'Qwen3.8-27B', 'directory': 'd1',
                               'manifest_sha256': CONSTANT},
                       '8b': {'served_name': 'Qwen3-8B', 'directory': 'd2',
                              'manifest_sha256': CONSTANT}}
        block = {'mean': 0.4, 'ci95': [0.1, 0.7], 'seeds_used': [1, 2, 3], 'per_seed': {'1': 0.5},
                 'draws': 10000, 'seed': 1}
        fake = {'run_status': {'run-27b': 'complete', 'run-8b': 'complete'},
                'all_preregistered_cases_valid': True,
                'all_preregistered_cases_present': True,
                'models': plan_models, 'seeds': [1, 2, 3], 'reference_seeds': [1],
                'utility_definition': 'V', 'records': [], 'no_cross_batch_data_merged': True,
                'data_problems': [],
                'masked_condition_available': False, 'condition_note': 'no masked mode',
                'conditions': ['strong', 'hold'], 'endpoint_continuity': [],
                'verdicts': {'27b': {'interface_causal_necessity': 'passed',
                                     'deployment_behind_baseline': 'failed',
                                     'overall': 'not_reproduced'},
                             '8b': {'interface_causal_necessity': 'failed',
                                    'deployment_behind_baseline': 'passed',
                                    'overall': 'not_reproduced'}},
                'group_summary': {name: {'strong': block, 'hold': block,
                                         'strong_minus_hold': block,
                                         'strong_minus_pure_rl': block}
                                  for name in plan_models}}
        text = summary.render(fake)
        for fragment in ('Qwen3.8-27B', 'Qwen3-8B', 'strong/hold', '未通过', '局限'):
            self.assertIn(fragment, text)


if __name__ == '__main__':
    unittest.main()
