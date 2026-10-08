"""Offline contract tests for the E6b third-party ablation (MiniMax adapter + runner).

No network and no GPU: the provider transport is replaced by a fake ``urlopen`` and the
grid runner by a stub that exercises the patched planner call path.
"""
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONSTANT = 'a' * 64
KEY_ENV = 'E6B_TEST_KEY'
# Assembled at runtime so the repository never carries a credential-shaped literal; it
# only has to be a value the scanner and the logger must refuse to persist.
KEY_VALUE = '-'.join(['sk', 'test', 'not', 'a', 'real', 'credential', '0123456789abcdef'])


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


adapter = load_module('minimax_client_under_test', 'minimax_client.py')
runner = load_module('e6b_under_test', 'e6b_remote_ablation.py')


class FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode('utf-8')

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def anthropic_payload(blocks, stop_reason='end_turn', output_tokens=40):
    return {'id': 'msg_1', 'type': 'message', 'role': 'assistant', 'model': 'MiniMax-M3',
            'content': blocks, 'stop_reason': stop_reason,
            'usage': {'input_tokens': 100, 'output_tokens': output_tokens}}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        os.environ[KEY_ENV] = KEY_VALUE

    def tearDown(self):
        os.environ.pop(KEY_ENV, None)
        self.folder.cleanup()

    def client(self, **kwargs):
        log = Path(self.folder.name) / 'requests.jsonl'
        return adapter.AnthropicMessagesClient(
            base_url='https://example.invalid', model='MiniMax-M3', key_env=KEY_ENV,
            request_log=str(log), **kwargs), log

    def with_payload(self, client, payload):
        """Patch the provider transport, so the retry and header logic stays real."""
        return patch.object(client, '_post', lambda _body: payload)

    def test_text_only_block_is_returned_and_logged(self):
        payload = anthropic_payload([{'type': 'text', 'text': '{"goal_commands": []}'}])
        client, log = self.client()
        with self.with_payload(client, payload):
            answer = client.chat('system', 'user', max_tokens=1024, temperature=0.1)
        self.assertEqual(answer, '{"goal_commands": []}')
        self.assertEqual(client.last_blocks, ['text'])
        self.assertEqual(client.thinking_blocks_seen, 0)
        self.assertEqual(client.last_stop_reason, 'end_turn')
        rows = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()]
        self.assertEqual([row['kind'] for row in rows], ['request', 'response'])
        self.assertEqual(rows[0]['thinking_policy'], 'disabled')
        self.assertEqual(rows[0]['max_tokens'], 1024)
        self.assertEqual(rows[0]['temperature'], 0.1)
        self.assertNotIn(KEY_VALUE, log.read_text(encoding='utf-8'))

    def test_thinking_block_is_counted_but_never_returned(self):
        payload = anthropic_payload([
            {'type': 'thinking', 'thinking': 'the user says ...', 'signature': 'x'},
            {'type': 'text', 'text': '{"goal_commands": [{"unit_id": "blue_0"}]}'}])
        client, _log = self.client()
        with self.with_payload(client, payload):
            answer = client.chat('system', 'user')
        self.assertEqual(answer, '{"goal_commands": [{"unit_id": "blue_0"}]}')
        self.assertEqual(client.last_blocks, ['thinking', 'text'])
        self.assertEqual(client.thinking_blocks_seen, 1)
        self.assertIn('thinking_block_returned', client.protocol_errors)

    def test_truncated_and_empty_responses_are_flagged(self):
        client, _log = self.client()
        truncated = anthropic_payload([{'type': 'text', 'text': '{"goal_comm'}],
                                      stop_reason='max_tokens')
        with self.with_payload(client, truncated):
            client.chat('system', 'user')
        self.assertEqual(client.truncated_responses, 1)
        self.assertIn('response_truncated_by_max_tokens', client.protocol_errors)

        empty = anthropic_payload([{'type': 'text', 'text': '   '}])
        with self.with_payload(client, empty):
            answer = client.chat('system', 'user')
        self.assertEqual(answer.strip(), '')
        self.assertIn('empty_text_block', client.protocol_errors)

    def test_the_adapter_pins_the_thinking_flag_and_reads_the_named_variable(self):
        captured = {}

        def fake_post(body):
            captured.update(body)
            captured['x-api-key'] = client._headers()['x-api-key']
            return anthropic_payload([{'type': 'text', 'text': '{}'}])

        client, _log = self.client()
        with patch.object(client, '_post', fake_post):
            client.chat('system', 'user')
        self.assertEqual(captured['thinking'], {'type': 'disabled'})
        self.assertEqual(captured['x-api-key'], KEY_VALUE)
        self.assertEqual(captured['model'], 'MiniMax-M3')

    def test_rate_limit_is_retried_then_reported(self):
        calls = {'n': 0}

        def flaky(_body):
            calls['n'] += 1
            raise urllib.error.HTTPError('https://example.invalid', 429, 'slow down', {},
                                         io.BytesIO(b'{}'))

        client, _log = self.client(max_retries=2)
        with patch.object(client, '_post', flaky), \
                patch.object(adapter.time, 'sleep', lambda _s: None):
            answer = client.chat('system', 'user')
        self.assertEqual(answer, '')
        self.assertEqual(calls['n'], 3)
        self.assertEqual(client.errors, 1)
        self.assertTrue(any('429' in item for item in client.protocol_errors))

    def test_missing_credential_fails_loudly_without_calling_out(self):
        os.environ.pop(KEY_ENV, None)
        client, _log = self.client()
        with self.assertRaises(adapter.ProviderError):
            client.chat('system', 'user')

    def test_record_writer_refuses_to_persist_the_key(self):
        with self.assertRaises(adapter.ProviderError):
            adapter.sanitize_record({'note': KEY_VALUE}, KEY_ENV)
        self.assertEqual(adapter.sanitize_record({'note': 'ok'}, KEY_ENV), {'note': 'ok'})


def plan_fixture(snapshot: Path, **overrides):
    plan = {
        'schema': runner.SCHEMA_PLAN,
        'not_before_utc': '2020-01-01T00:00:00+00:00',
        'snapshot': str(snapshot),
        'checkpoint': str(snapshot / 'theta.npz'),
        'difficulty': 'medium', 'task_mode': 'continuous', 'stack': 'llm-rl',
        'plan_interval': 10, 'conditions': ['strong', 'hold'],
        'seeds': list(range(2026100401, 2026100411)),
        'reference_seeds': [2026100401, 2026100402, 2026100403],
        'smoke_seeds': [2026100491],
        'max_tokens': 8192, 'temperature': .1, 'enable_thinking': False, 'llm_retries': 0,
        'provider_retries': 2, 'llm_timeout_seconds': 300.0,
        'case_wall_budget_seconds': 60, 'jobs_per_model': 1,
        'models': {
            'm3': {'kind': 'remote-provider', 'filename': 'm3', 'served_name': 'MiniMax-M3',
                   'provider': 'minimax', 'base_url': 'https://api.example.invalid',
                   'api_path': '/anthropic/v1/messages', 'key_env': KEY_ENV,
                   'transcript': 'anthropic-text-block', 'thinking_policy': 'disabled',
                   'expect_no_thinking': True, 'min_interval_seconds': 0,
                   'endpoints': ['https://api.example.invalid']},
            'm27': {'kind': 'remote-provider', 'filename': 'm27',
                    'served_name': 'MiniMax-M2.7-highspeed', 'provider': 'minimax',
                    'base_url': 'https://api.example.invalid',
                    'api_path': '/anthropic/v1/messages', 'key_env': KEY_ENV,
                    'transcript': 'anthropic-text-block', 'thinking_policy': 'disabled',
                    'expect_no_thinking': False, 'min_interval_seconds': 0,
                    'endpoints': ['https://api.example.invalid']},
        },
        'runner_sha256': CONSTANT,
        'adapter_sha256': CONSTANT,
        'frozen_files': {},
    }
    plan.update(overrides)
    return plan


class PlanContractTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.snapshot = Path(self.folder.name) / 'snap'
        (self.snapshot / 'role_c_toolkit').mkdir(parents=True)
        (self.snapshot / 'role_c_toolkit/grid_rolec6.py').write_text('# stub', encoding='utf-8')
        (self.snapshot / 'theta.npz').write_bytes(b'w')
        self.plan_path = Path(self.folder.name) / 'plan.json'

    def tearDown(self):
        self.folder.cleanup()

    def verify(self, plan):
        self.plan_path.write_text(json.dumps(plan), encoding='utf-8')
        original = runner.sha
        runner.sha = lambda _path: CONSTANT
        try:
            runner.verify_plan(plan, self.plan_path)
        finally:
            runner.sha = original

    def test_accepts_the_declared_shape(self):
        self.verify(plan_fixture(self.snapshot))

    def test_rejects_remote_model_without_credential_variable(self):
        plan = plan_fixture(self.snapshot)
        plan['models']['m3'].pop('key_env')
        with self.assertRaises(ValueError):
            self.verify(plan)

    def test_rejects_remote_model_without_the_text_block_transcript(self):
        plan = plan_fixture(self.snapshot)
        plan['models']['m3']['transcript'] = 'openai-answer-text'
        with self.assertRaises(ValueError):
            self.verify(plan)

    def test_rejects_undeclared_thinking_expectation(self):
        plan = plan_fixture(self.snapshot)
        plan['models']['m27'].pop('expect_no_thinking')
        with self.assertRaises(ValueError):
            self.verify(plan)

    def test_rejects_non_https_provider(self):
        plan = plan_fixture(self.snapshot)
        plan['models']['m3']['base_url'] = 'http://api.example.invalid'
        plan['models']['m3']['endpoints'] = ['http://api.example.invalid']
        with self.assertRaises(ValueError):
            self.verify(plan)

    def test_rejects_out_of_range_provider_retries(self):
        plan = plan_fixture(self.snapshot)
        plan['provider_retries'] = 9
        with self.assertRaises(ValueError):
            self.verify(plan)

    def test_rejects_missing_start_timestamp(self):
        plan = plan_fixture(self.snapshot)
        plan['not_before_utc'] = 'soon'
        with self.assertRaises(ValueError):
            self.verify(plan)

    def test_rejects_smoke_seed_overlapping_the_analysis(self):
        plan = plan_fixture(self.snapshot)
        plan['smoke_seeds'] = [plan['seeds'][0]]
        with self.assertRaises(ValueError):
            self.verify(plan)


class CaseRunnerTests(unittest.TestCase):
    """A stub grid exercises the patched planner path end to end."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        snapshot = self.root / 'snap'
        (snapshot / 'role_c_toolkit').mkdir(parents=True)
        (snapshot / 'role_c_toolkit/grid_rolec6.py').write_text('# stub', encoding='utf-8')
        (snapshot / 'theta.npz').write_bytes(b'w')
        self.plan = plan_fixture(snapshot)
        self.plan_path = self.root / 'plan.json'
        self.plan_path.write_text(json.dumps(self.plan), encoding='utf-8')
        self.original = (runner.sha, runner.verify_plan, runner.load_runner)
        runner.sha = lambda _path: CONSTANT
        runner.verify_plan = lambda plan, path: CONSTANT

        class FakeGrid:
            @staticmethod
            def run_one(args):
                args.output.mkdir(parents=True, exist_ok=True)
                # The real grid builds the agent and drives it.  The stub drives the same
                # two hooks run_case patches -- the planner call and the RL controller --
                # so the request lock and the fallback guards are genuinely exercised.
                if args.arm == 'llm-rl':
                    agent = FakeHybrid(role='blue', seed=args.seed, llm_client=None)
                    FakeHybrid._call_planner_llm(agent, 'situation report')
                report = {'complete': True, 'V': 0.4, 'steps': 30, 'elapsed_seconds': 5.0,
                          'agent_stats': {'fallback_count': 0, 'goai_rejected': 0},
                          'd1': {'input_role_truth_leaks': [], 'prompt_role_truth_leaks': []}}
                (args.output / 'episode.json').write_text(json.dumps(report), encoding='utf-8')
                return 0

        class FakeLLM:
            def __init__(self):
                self.total_tokens = 0
                self.total_calls = 0
                self.errors = 0
                self.last_blocks = []
                self.last_stop_reason = None
                self.thinking_blocks = 0
                self.protocol_errors = []

            def chat(self, system_prompt, prompt, max_tokens=512, temperature=0.1):
                self.total_calls += 1
                return '{"goal_commands": []}'

        class FakeAgent:
            def __init__(self, role=None, seed=None, llm_client=None):
                self.plan_calls = 0
                self.llm = FakeLLM()

        class FakeHybrid:
            PLANNER_SYSTEM_PROMPT = 'planner system prompt'

            def __init__(self, role=None, seed=None, llm_client=None, planner_interval=None,
                         executor_checkpoint=None):
                self.plan_calls = 0
                self.llm = FakeLLM()

            def _call_planner_llm(self, prompt):
                return self.llm.chat(FakeHybrid.PLANNER_SYSTEM_PROMPT, prompt)

        class FakeMappo:
            @staticmethod
            def make_goai_controller(*args, **kwargs):
                def controller(env, unit_id, goal_state):
                    return {}
                return controller

        class FakeLLMClient:
            """Base class of the grid's client family; the runner patches its chat()."""

            def __init__(self, base_url=None, api_key=None, model=None, timeout=120,
                         max_retries=2):
                self.base_url = base_url
                self.model = model

            def chat(self, system_prompt, user_message, max_tokens=512, temperature=0.1):
                return '{"goal_commands": []}'

        hybrid = type(sys)('grid_env.agents.hybrid_agent')
        hybrid.HybridAgent = FakeHybrid
        hybrid.PLANNER_SYSTEM_PROMPT = FakeHybrid.PLANNER_SYSTEM_PROMPT
        mappo = type(sys)('grid_env.agents.mappo_agent')
        mappo.make_goai_controller = FakeMappo.make_goai_controller
        llm = type(sys)('grid_env.agents.llm_client')
        llm.LLMClient = FakeLLMClient
        package, agents = type(sys)('grid_env'), type(sys)('grid_env.agents')
        agents.hybrid_agent, agents.mappo_agent, agents.llm_client = hybrid, mappo, llm
        self.stubs = {'grid_env': package, 'grid_env.agents': agents,
                      'grid_env.agents.hybrid_agent': hybrid,
                      'grid_env.agents.mappo_agent': mappo,
                      'grid_env.agents.llm_client': llm}
        runner.load_runner = lambda snapshot: FakeGrid
        os.environ[KEY_ENV] = KEY_VALUE
        self.payload = anthropic_payload(
            [{'type': 'text', 'text': '{"goal_commands": [{"unit_id": "blue_0"}]}'}])

    def tearDown(self):
        runner.sha, runner.verify_plan, runner.load_runner = self.original
        os.environ.pop(KEY_ENV, None)
        self.folder.cleanup()

    def run_one(self, model='m3', condition='strong', seed=2026100401, arm='llm-rl'):
        output = self.root / 'episodes' / f'{model}-{condition}-{seed}'
        # Patch the class the runner itself imported, not a second copy of the module,
        # so no test can reach the real provider.
        with patch.dict(sys.modules, self.stubs), \
                patch.object(runner.AnthropicMessagesClient, '_post',
                             lambda _self, _body: self.payload):
            code = runner.run_case(self.plan_path, output, model, condition, seed, arm)
        return code, json.loads((output / 'E6b-case.json').read_text(encoding='utf-8'))

    def test_thinking_off_case_is_valid_and_records_no_reasoning(self):
        code, result = self.run_one()
        self.assertEqual(code, 0)
        self.assertTrue(result['analysis_valid'], result['invalid_reasons'])
        self.assertEqual(result['thinking_blocks'], 0)
        self.assertEqual(result['provider'], 'minimax')
        self.assertEqual(result['key_env'], KEY_ENV)
        self.assertNotIn(KEY_VALUE, json.dumps(result, ensure_ascii=False))

    def test_thinking_block_breaks_the_guard_when_it_must_be_off(self):
        self.payload = anthropic_payload([
            {'type': 'thinking', 'thinking': 'reasoning...', 'signature': 'x'},
            {'type': 'text', 'text': '{"goal_commands": []}'}])
        code, result = self.run_one()
        self.assertEqual(code, 2)
        self.assertFalse(result['analysis_valid'])
        self.assertEqual(result['thinking_blocks'], 1)
        self.assertIn('thinking_block_returned', result['invalid_reasons'])

    def test_truncated_answer_is_not_accepted(self):
        self.payload = anthropic_payload([{'type': 'text', 'text': '{"goal_comm'}],
                                         stop_reason='max_tokens')
        code, result = self.run_one()
        self.assertEqual(code, 2)
        self.assertIn('response_truncated_by_max_tokens', result['invalid_reasons'])

    def test_pure_rl_reference_needs_no_provider_call(self):
        code, result = self.run_one(condition='strong', seed=2026100401, arm='rl')
        self.assertEqual(code, 0)
        self.assertTrue(result['analysis_valid'])
        self.assertEqual(result['arm'], 'rl')
        self.assertIsNone(result['served_name'])
        self.assertEqual(result['thinking_blocks'], 0)

    def test_unpreregistered_case_is_refused(self):
        with self.assertRaises(ValueError):
            self.run_one(seed=1)


class WaitTests(unittest.TestCase):
    def test_past_timestamp_returns_immediately(self):
        runner.wait_until('2020-01-01T00:00:00+00:00', 'test')

    def test_naive_timestamp_is_read_as_utc(self):
        started = runner.datetime.now(runner.timezone.utc)
        runner.wait_until('2020-01-01T00:00:00', 'naive')
        self.assertLess((runner.datetime.now(runner.timezone.utc) - started).total_seconds(), 5)


class ControllerObserverTests(unittest.TestCase):
    """The RL fallback counter is the only signal for a controller-side failure."""

    def test_counter_tracks_calls_and_fallbacks(self):
        counters = {'calls': 0, 'none_on_active_unit': 0, 'none_on_inactive_unit': 0}

        def factory(*_args, **_kwargs):
            def controller(env, unit_id, goal_state):
                return None if unit_id == 'blue_0' else {'go': 1}
            return controller

        wrapped = runner.observe_controller(factory, counters)
        controller = wrapped()
        self.assertEqual(controller(None, 'blue_1', None), {'go': 1})

        class Entity:
            alive = True

        class Env:
            entities = {'blue_0': Entity()}

        self.assertIsNone(controller(Env(), 'blue_0', None))
        self.assertEqual(counters['calls'], 2)
        self.assertEqual(counters['none_on_active_unit'], 1)
        self.assertEqual(counters['none_on_inactive_unit'], 0)


if __name__ == '__main__':
    unittest.main()
