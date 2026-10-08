"""E6b: third-party model ablation on the frozen grid pipeline (MiniMax M3 / M2.7).

Same design as ``e6_model_invariance.py`` -- grid medium/continuous, ``llm-rl`` stack,
strong vs hold goal mode, one seed set, seed-bootstrap intervals -- but the planner is a
remote provider reached over its Anthropic-compatible Messages API instead of a local
vLLM replica.  Engine, scenarios, scorer and the RL checkpoint stay frozen.

Sub-commands:
    plan      freeze the protocol (refuses to overwrite)
    probe     verify provider identity and that thinking really is off
    case      run exactly one preregistered case
    schedule  run every preregistered case, one worker per model
    status    print a compact progress line

The provider key is read from the environment named in the plan and is never written.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from types import SimpleNamespace
from unittest.mock import patch

from minimax_client import (AnthropicMessagesClient, DEFAULT_ANTHROPIC_VERSION,
                            DEFAULT_API_PATH, ProviderError, sanitize_record)

SCHEMA_PLAN = 'E6b-thirdparty-ablation-plan@1'
SCHEMA_CASE = 'E6b-thirdparty-ablation-case@1'
SCHEMA_STATUS = 'E6b-thirdparty-ablation-status@1'
SCHEMA_PROBE = 'E6b-thirdparty-ablation-probe@1'
CONDITIONS = ('strong', 'hold')
ARMS = ('llm-rl', 'rl')
KINDS = ('local', 'remote-provider')


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path: Path, value) -> None:
    path = Path(path)
    temporary = Path(str(path) + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + chr(10),
                         encoding='utf-8')
    os.replace(temporary, path)


def case_id(model: str, condition: str, seed: int, arm: str = 'llm-rl') -> str:
    return f'{model}-{condition}-s{seed}' if arm == 'llm-rl' else f'{model}-rl-s{seed}'


def load_runner(snapshot: Path):
    snapshot = Path(snapshot)
    sys.path.insert(0, str(snapshot / 'role_c_toolkit'))
    sys.path.insert(0, str(snapshot / 'openmd/code'))
    spec = importlib.util.spec_from_file_location(
        'frozen_E6b_grid_runner', snapshot / 'role_c_toolkit/grid_rolec6.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- plan handling

def verify_plan(plan: dict, plan_path: Path) -> str:
    if plan.get('schema') != SCHEMA_PLAN:
        raise ValueError('Unexpected plan schema')
    seeds = list(plan.get('seeds') or [])
    if len(seeds) != 10 or len(set(seeds)) != 10:
        raise ValueError('E6b requires exactly 10 distinct strong/hold seeds')
    if list(plan.get('conditions') or []) != list(CONDITIONS):
        raise ValueError('E6b conditions must be exactly strong and hold')
    if plan.get('difficulty') != 'medium' or plan.get('task_mode') != 'continuous':
        raise ValueError('E6b runs grid medium/continuous only')
    if plan.get('plan_interval') != 10 or plan.get('stack') != 'llm-rl':
        raise ValueError('E6b uses the frozen llm-rl stack at plan_interval 10')
    if plan.get('max_tokens') != 8192 or plan.get('temperature') != .1:
        raise ValueError('Frozen sampling settings differ')
    if plan.get('enable_thinking') is not False or plan.get('llm_retries') != 0:
        raise ValueError('Thinking must be off and retries pinned to zero')
    smoke = list(plan.get('smoke_seeds') or [])
    if len(set(smoke)) != len(smoke) or (set(smoke) & set(seeds)) or \
            (set(smoke) & set(plan.get('reference_seeds') or [])):
        raise ValueError('Smoke seeds must be distinct from every analysed seed')
    models = plan.get('models') or {}
    if len(models) < 2:
        raise ValueError('E6b needs at least two provider models')
    reported: set[str] = set()
    for name, entry in models.items():
        if entry.get('kind') not in KINDS:
            raise ValueError('Unknown model kind: ' + name)
        if not entry.get('filename'):
            raise ValueError('Model slug is missing: ' + name)
        if entry.get('served_name') is None:
            raise ValueError('Served model name is missing: ' + name)
        if entry.get('expect_no_thinking') is None:
            raise ValueError('Thinking policy is not declared: ' + name)
        if entry['kind'] == 'local':
            if not re.fullmatch('[0-9a-f]{64}', str(entry.get('manifest_sha256'))):
                raise ValueError('Local model manifest hash is missing: ' + name)
            if not entry.get('directory'):
                raise ValueError('Local model directory is missing: ' + name)
            endpoints = entry.get('endpoints') or []
        else:
            if not entry.get('key_env'):
                raise ValueError('Remote model must name its credential variable: ' + name)
            if entry.get('transcript') != 'anthropic-text-block':
                raise ValueError('Remote model needs the anthropic-text-block transcript')
            if entry.get('api_path', DEFAULT_API_PATH) != DEFAULT_API_PATH:
                raise ValueError('Unexpected remote API path: ' + name)
            if not str(entry.get('base_url', '')).startswith('https://'):
                raise ValueError('Remote model must use an https base URL: ' + name)
            endpoints = [str(entry.get('base_url')).rstrip('/')]
        if not endpoints:
            raise ValueError('Model has no endpoint: ' + name)
        identity = f"{endpoints[0]}|{entry['served_name']}"
        if identity in reported:
            raise ValueError('Two models resolve to the same served model: ' + name)
        reported.add(identity)
    retries = plan.get('provider_retries')
    if not isinstance(retries, int) or not 0 <= retries <= 5:
        raise ValueError('provider_retries must be an integer in [0, 5]')
    if plan.get('llm_retries') != 0:
        raise ValueError('The grid planner retry count stays at zero')
    for name, entry in models.items():
        interval = entry.get('min_interval_seconds', 0)
        if not isinstance(interval, (int, float)) or interval < 0 or interval > 120:
            raise ValueError('min_interval_seconds out of range: ' + name)
    not_before = plan.get('not_before_utc')
    if not isinstance(not_before, str) or 'T' not in not_before:
        raise ValueError('Plan must carry an ISO not_before_utc timestamp')
    if sha(Path(__file__)) != plan.get('runner_sha256'):
        raise ValueError('Runner changed after the plan was frozen')
    for path, digest in (plan.get('frozen_files') or {}).items():
        if not Path(path).is_file():
            raise ValueError('Frozen file is missing: ' + path)
        if sha(Path(path)) != digest:
            raise ValueError('Frozen source or weight changed: ' + path)
    return sha(plan_path)


# ------------------------------------------------------------------- endpoints

def get_json(url: str, headers: dict | None = None, timeout: float = 30.0):
    request = urllib.request.Request(url, headers=dict(headers or {}, Accept='application/json'))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8', 'replace'))


def provider_models(entry: dict) -> list[str]:
    key = os.environ.get(entry['key_env'], '')
    if not key:
        raise ProviderError(f"{entry['key_env']} is not set in the environment")
    # Prefer the Anthropic-compatible listing; the OpenAI-shaped one rejects x-api-key.
    # Both headers are sent, which the provider documents as supported.
    headers = {'x-api-key': key, 'anthropic-version': DEFAULT_ANTHROPIC_VERSION,
               'Authorization': 'Bearer ' + key}
    base = str(entry['base_url']).rstrip('/')
    last_error: Exception | None = None
    for path in ('/anthropic/v1/models', '/v1/models'):
        try:
            listing = get_json(base + path, headers)
        except Exception as exc:  # noqa: BLE001 - try the other shape
            last_error = exc
            continue
        rows = listing.get('data') or []
        if rows:
            return [str(row.get('id')) for row in rows]
    raise ProviderError(f'Could not list provider models: {last_error}')


def probe(plan: dict, model: str) -> dict:
    entry = plan['models'][model]
    record = {'model': model, 'kind': entry['kind'], 'served_name': entry['served_name'],
              'key_env': entry.get('key_env'), 'expect_no_thinking': entry['expect_no_thinking'],
              'base_url': entry.get('base_url'),
              'thinking_policy': entry.get('thinking_policy')}
    if entry['kind'] == 'remote-provider':
        available = provider_models(entry)
        record['available_models'] = available
        record['served_model_present'] = entry['served_name'] in available
        if not record['served_model_present']:
            raise ValueError(f"{entry['served_name']} is not offered by the provider")
        client = AnthropicMessagesClient(
            base_url=entry['base_url'], model=entry['served_name'],
            key_env=entry['key_env'], timeout=plan['llm_timeout_seconds'],
            max_retries=plan.get('provider_retries', 2),
            thinking_policy=entry['thinking_policy'])
        answer = client.chat('Reply with one JSON object and nothing else.',
                             'Reply {"ready": true}', max_tokens=64, temperature=0.0)
        record.update(blocks=client.last_blocks, thinking_blocks=client.thinking_blocks_seen,
                      stop_reason=client.last_stop_reason, output_tokens=client.last_output_tokens,
                      answer_head=answer.strip()[:120], answer_non_empty=bool(answer.strip()),
                      protocol_errors=client.protocol_errors,
                      total_tokens=client.total_tokens)
    else:
        base = entry['endpoints'][0]
        listing = get_json(base + '/models')
        rows = [row for row in (listing.get('data') or []) if row.get('id') == entry['served_name']]
        if not rows:
            raise ValueError('Local endpoint does not serve ' + entry['served_name'])
        record.update(root=rows[0].get('root'), max_model_len=rows[0].get('max_model_len'))
    return record


# ------------------------------------------------------------------ case runner

def observe_controller(factory, counters):
    def wrapped_factory(*args, **kwargs):
        original = factory(*args, **kwargs)

        def controller(env, unit_id, goal_state):
            result = original(env, unit_id, goal_state)
            counters['calls'] += 1
            if result is None:
                entity = env.entities.get(unit_id)
                active = entity is not None and entity.alive
                counters['none_on_active_unit' if active else 'none_on_inactive_unit'] += 1
            return result
        return controller
    return wrapped_factory


def run_case(plan_path: Path, output: Path, model: str, condition: str, seed: int,
             arm: str = 'llm-rl') -> int:
    plan_path, output = Path(plan_path), Path(output)
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    digest = verify_plan(plan, plan_path)
    if seed not in plan['seeds'] + plan['reference_seeds'] + plan.get('smoke_seeds', []) \
            or condition not in CONDITIONS or arm not in ARMS:
        raise ValueError('Case is not preregistered')
    if arm == 'rl' and condition != 'strong':
        raise ValueError('The pure-RL reference has no goal-mode condition')
    if output.exists():
        raise FileExistsError('Never overwrite an episode')
    entry = plan['models'][model]
    base = load_runner(Path(plan['snapshot']))
    args = SimpleNamespace(source=Path(plan['snapshot']) / 'openmd', output=output, seed=seed,
                           arm=arm, difficulty=plan['difficulty'], task_mode=plan['task_mode'],
                           checkpoint=Path(plan['checkpoint']),
                           # The frozen runner requires an explicit endpoint for every
                           # LLM arm.  Both fields describe the provider as served; the
                           # remote case routes the transport itself below.
                           base_url=(entry['endpoints'][0] if arm == 'llm-rl' else None),
                           model=entry['served_name'] if arm == 'llm-rl' else None,
                           plan_interval=plan['plan_interval'], pure_call_interval=1,
                           goal_mode=condition, max_steps=None,
                           llm_timeout=plan['llm_timeout_seconds'], llm_retries=plan['llm_retries'])
    counters = {'calls': 0, 'none_on_active_unit': 0, 'none_on_inactive_unit': 0}
    agents, client = [], None
    with ExitStack() as stack:
        if arm == 'llm-rl':
            from grid_env.agents import hybrid_agent, mappo_agent

            if entry['kind'] == 'remote-provider':
                client = AnthropicMessagesClient(
                    base_url=entry['base_url'], model=entry['served_name'],
                    key_env=entry['key_env'], timeout=plan['llm_timeout_seconds'],
                    max_retries=plan.get('provider_retries', 2),
                    thinking_policy=entry['thinking_policy'],
                    request_log=str(output / 'requests.jsonl'),
                    min_interval_seconds=entry.get('min_interval_seconds', 0))

            def locked_call(agent, prompt, _client=client):
                if not agents:
                    agents.append(agent)
                agent.plan_calls += 1
                if _client is not None:
                    # Remote providers: the adapter replaces the transport entirely.
                    # The grid's own HTTP client is left untouched; the provider-facing
                    # request and response land in requests.jsonl via the adapter.
                    answer = _client.chat(hybrid_agent.PLANNER_SYSTEM_PROMPT, prompt,
                                          max_tokens=plan['max_tokens'],
                                          temperature=plan['temperature'])
                    agent.llm.total_calls += 1
                    agent.llm.total_tokens += int(_client.last_output_tokens or 0)
                    agent.llm.last_blocks = list(_client.last_blocks)
                    agent.llm.last_stop_reason = _client.last_stop_reason
                    agent.llm.thinking_blocks = _client.thinking_blocks_seen
                    agent.llm.protocol_errors = list(_client.protocol_errors)
                    return answer
                return agent.llm.chat(hybrid_agent.PLANNER_SYSTEM_PROMPT, prompt,
                                      max_tokens=plan['max_tokens'],
                                      temperature=plan['temperature'])

            stack.enter_context(patch.object(hybrid_agent.HybridAgent, '_call_planner_llm',
                                             locked_call))
            if client is not None:
                # The grid family inherits from the module-level LLMClient, so patching
                # that one method redirects every variant (including RecordingClient)
                # without touching the frozen source.
                llm_module = sys.modules.get('grid_env.agents.llm_client') or \
                    importlib.import_module('grid_env.agents.llm_client')
                stack.enter_context(patch.object(
                    llm_module.LLMClient, 'chat',
                    lambda self, system_prompt, user_message, max_tokens=512, temperature=0.1:
                    locked_call(self, user_message)))
            stack.enter_context(patch.object(
                mappo_agent, 'make_goai_controller',
                observe_controller(mappo_agent.make_goai_controller, counters)))
        code = base.run_one(args)
    native_path = output / 'episode.json'
    native = json.loads(native_path.read_text(encoding='utf-8'))
    requests_path = output / 'requests.jsonl'
    rows = ([json.loads(line) for line in requests_path.read_text(encoding='utf-8').splitlines()
             if line.strip()] if requests_path.exists() else [])
    requests = [row for row in rows if row.get('kind') == 'request']
    responses = [row for row in rows if row.get('kind') == 'response']
    leaks = (native.get('d1') or {}).get('input_role_truth_leaks') or []
    prompt_leaks = (native.get('d1') or {}).get('prompt_role_truth_leaks') or []
    reasons = []
    if not native.get('complete') or code:
        reasons.append('native_episode_failed')
    if leaks:
        reasons.append('input_role_truth_leak')
    if prompt_leaks:
        reasons.append('prompt_role_truth_leak')
    thinking_blocks = 0
    output_tokens = 0
    stop_reasons: set[str] = set()
    if arm == 'llm-rl':
        # Either verified instrumentation signal is enough: the planner hook having run
        # (agents) or the RL controller having been observed (counters).
        exercised = bool(agents) or int(counters['calls']) > 0
        if not exercised or not requests:
            reasons.append('LLM_RL_path_not_exercised')
        if any(row.get('max_tokens') != plan['max_tokens']
               or row.get('temperature') != plan['temperature']
               or row.get('enable_thinking') is not False for row in requests):
            reasons.append('request_lock_mismatch')
        if (native.get('agent_stats') or {}).get('fallback_count', 0):
            reasons.append('planner_rule_fallback')
        # Only meaningful when the RL controller actually ran; an episode that never
        # reaches the controller is caught by the LLM_RL_path check above.
        if counters['calls'] and counters['none_on_active_unit']:
            reasons.append('RL_controller_fallback')
        if len(requests) != len(responses) or any(row.get('empty') for row in responses):
            reasons.append('missing_or_empty_response')
        if entry['kind'] == 'remote-provider' and client is not None:
            thinking_blocks = client.thinking_blocks_seen
            output_tokens = int(client.total_output_tokens)
            stop_reasons = {str(row.get('stop_reason')) for row in responses}
            if entry['expect_no_thinking'] and thinking_blocks:
                reasons.append('thinking_block_returned')
            if client.truncated_responses:
                reasons.append('response_truncated_by_max_tokens')
            if client.errors:
                reasons.append('provider_request_error')
        elif agents:
            output_tokens = int(agents[0].llm.total_tokens)
    verify_plan(plan, plan_path)
    if sha(plan_path) != digest:
        raise ValueError('Frozen plan changed during the episode')
    result = {'schema': SCHEMA_CASE, 'model': model, 'condition': condition, 'seed': seed,
              'arm': arm, 'served_name': entry['served_name'] if arm == 'llm-rl' else None,
              'provider': entry.get('provider') if entry['kind'] == 'remote-provider' else 'local',
              'kind': entry['kind'], 'transcript': entry.get('transcript'),
              'native_report': str(native_path), 'native_report_sha256': sha(native_path),
              'V': native.get('V'), 'complete': native.get('complete'), 'steps': native.get('steps'),
              'analysis_valid': not reasons, 'invalid_reasons': sorted(set(reasons)),
              'plan_sha256': digest,
              'costs': {'llm_calls': len(requests), 'actual_API_total_tokens': output_tokens,
                        'request_seconds': sum(row.get('elapsed_seconds') or 0 for row in responses),
                        'episode_wall_seconds': native.get('elapsed_seconds')},
              'thinking_blocks': thinking_blocks,
              'stop_reasons': sorted(reason for reason in stop_reasons if reason),
              'thinking_policy': entry.get('thinking_policy'),
              'expect_no_thinking': entry['expect_no_thinking'],
              'key_env': entry.get('key_env'),
              'RL_controller_observation': counters, 'agent_stats': native.get('agent_stats') or {},
              'engine_files_unchanged': True, 'new_training': False}
    save(output / 'E6b-case.json', result)
    return 0 if result['analysis_valid'] else 2


# -------------------------------------------------------------------- schedule

def wait_until(iso_timestamp: str, label: str) -> None:
    """Hold the batch until a pre-agreed wall-clock time.

    A quota or rate-limit window may need to pass before a paid batch starts; refusing
    to start early is cheaper and more honest than discovering 429s mid-run.
    """
    target = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    while True:
        remaining = (target - datetime.now(timezone.utc)).total_seconds()
        if remaining <= 0:
            return
        print(f'waiting {remaining/60:.1f} min until {iso_timestamp} ({label})', flush=True)
        time.sleep(min(remaining, 600))


def schedule(plan_path: Path, run_dir: Path, models, jobs_per_model: int) -> int:
    plan_path, run_dir = Path(plan_path).resolve(), Path(run_dir).resolve()
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    verify_plan(plan, plan_path)
    wait_until(plan['not_before_utc'], 'pre-agreed start')
    if (run_dir / 'status.json').exists():
        raise RuntimeError('Existing campaign state; do not duplicate')
    probe_path = plan_path.parent / 'endpoints.json'
    if not probe_path.exists():
        raise RuntimeError('Run `probe` first so the providers are verified before any episode')
    probes = json.loads(probe_path.read_text(encoding='utf-8'))
    if probes.get('plan_sha256') != sha(plan_path):
        raise RuntimeError('Probe belongs to a different plan; re-run `probe`')
    for row in probes['records']:
        if not row.get('answer_non_empty'):
            raise RuntimeError('Provider failed its pre-flight reply: ' + str(row.get('model')))
        if row.get('expect_no_thinking') and row.get('thinking_blocks'):
            raise RuntimeError('Provider returned thinking blocks although thinking must be off: '
                               + str(row.get('model')))
    (run_dir / 'episodes').mkdir(parents=True, exist_ok=True)
    (run_dir / 'logs').mkdir(exist_ok=True)
    state = {'schema': SCHEMA_STATUS, 'status': 'running', 'pid': os.getpid(),
             'started_utc': datetime.now(timezone.utc).isoformat(),
             'plan_sha256': sha(plan_path), 'completed': [], 'active': {}, 'failures': []}
    lock = threading.Lock()

    def persist():
        save(run_dir / 'status.json', state)

    persist()

    def launch(model, condition, seed, arm):
        identifier = case_id(model, condition, seed, arm)
        output = run_dir / 'episodes' / identifier
        command = [sys.executable, '-B', str(Path(__file__).resolve()), 'case',
                   '--plan', str(plan_path), '--output', str(output), '--model', model,
                   '--condition', condition, '--seed', str(seed)]
        if arm == 'rl':
            command += ['--arm', 'rl']
        env = os.environ.copy()
        env.update(MPLBACKEND='Agg', CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='2',
                   OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2')
        log_path = run_dir / 'logs' / (identifier + '.log')
        with log_path.open('x', encoding='utf-8') as log:
            child = subprocess.Popen(command, cwd=plan['snapshot'], env=env,
                                     stdin=subprocess.DEVNULL, stdout=log,
                                     stderr=subprocess.STDOUT)
            with lock:
                state['active'][identifier] = {'pid': child.pid, 'model': model,
                                               'condition': condition}
                persist()
            try:
                code = child.wait(timeout=plan['case_wall_budget_seconds'])
            except BaseException:
                child.terminate()
                child.wait(timeout=30)
                raise
        result_path = output / 'E6b-case.json'
        result = (json.loads(result_path.read_text(encoding='utf-8'))
                  if result_path.exists() else None)
        valid = code == 0 and result is not None and result['analysis_valid']
        with lock:
            state['active'].pop(identifier, None)
            row = {'case_id': identifier, 'exit_code': code, 'result': str(result_path),
                   'analysis_valid': valid, 'model': model, 'condition': condition, 'seed': seed}
            if result_path.exists():
                row['sha256'] = sha(result_path)
            state['completed'].append(row)
            if not valid:
                state['failures'].append(row)
            persist()
        return valid

    try:
        workers = []
        for model in models:
            pending = queue.Queue()
            for condition in CONDITIONS:
                for seed in plan['seeds']:
                    pending.put((condition, seed, 'llm-rl'))
            for seed in plan['reference_seeds']:
                pending.put(('strong', seed, 'rl'))
            for index in range(max(1, jobs_per_model)):
                workers.append(threading.Thread(target=_slot_worker,
                                                args=(model, index, pending, launch),
                                                daemon=False, name=f'{model}-{index}'))
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        state['status'] = 'complete' if not state['failures'] else 'complete_with_failures'
    except BaseException as exc:  # noqa: BLE001
        state['status'] = 'aborted'
        state['abort_reason'] = f'{type(exc).__name__}: {exc}'
        persist()
        raise
    state['finished_utc'] = datetime.now(timezone.utc).isoformat()
    persist()
    return 0 if not state['failures'] else 1


def _slot_worker(model: str, index: int, pending: queue.Queue, launch) -> None:
    while True:
        try:
            condition, seed, arm = pending.get_nowait()
        except queue.Empty:
            return
        try:
            launch(model, condition, seed, arm)
        except BaseException as exc:  # noqa: BLE001
            print(f'slot {model}#{index} failed on {condition} s{seed}: '
                  f'{type(exc).__name__}: {exc}', flush=True)


def probe_command(plan_path: Path, output: Path, only):
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    verify_plan(plan, Path(plan_path))
    records = []
    for model, entry in plan['models'].items():
        if only and model not in only:
            continue
        record = sanitize_record(probe(plan, model), entry.get('key_env') or 'MINIMAX_API_KEY')
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    save(Path(output), {'schema': SCHEMA_PROBE, 'plan_sha256': sha(Path(plan_path)),
                        'probed_utc': datetime.now(timezone.utc).isoformat(),
                        'records': records})
    ok = all(row.get('answer_non_empty') for row in records)
    ok = ok and not any(row.get('expect_no_thinking') and row.get('thinking_blocks')
                        for row in records)
    return 0 if ok else 3


def status_command(run_dir: Path) -> int:
    state = json.loads((Path(run_dir) / 'status.json').read_text(encoding='utf-8'))
    done = state['completed']
    valid = sum(1 for row in done if row.get('analysis_valid'))
    print(f"E6b {state.get('status')} valid={valid}/{len(done)} "
          f"active={len(state['active'])} failures={len(state['failures'])}")
    for row in state['failures']:
        print('  FAIL', row['case_id'], row.get('exit_code'))
    return 0


def plan_command(args) -> int:
    if args.output.exists():
        raise FileExistsError('Plan already exists: ' + str(args.output))
    models = {}
    for spec in args.model:
        fields = spec.split('|')
        if len(fields) != 9:
            raise ValueError('--model needs 9 pipe-separated fields, got: ' + spec)
        (name, kind, served, provider, base_url, key_env, policy, expect,
         interval) = fields
        entry = {'kind': kind, 'served_name': served, 'filename': name,
                 'provider': provider or None,
                 'thinking_policy': policy, 'expect_no_thinking': expect.lower() == 'true',
                 'min_interval_seconds': float(interval or 0), 'endpoints': []}
        if kind == 'remote-provider':
            entry.update(base_url=base_url.rstrip('/'), api_path=DEFAULT_API_PATH,
                         key_env=key_env, transcript='anthropic-text-block',
                         anthropic_version=DEFAULT_ANTHROPIC_VERSION,
                         endpoints=[base_url.rstrip('/')])
        models[name] = entry
    snapshot = Path(args.snapshot).resolve()
    plan = {
        'schema': SCHEMA_PLAN,
        'scope': 'E6b third-party model ablation: grid medium/continuous llm-rl, strong vs hold',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'not_before_utc': normalize_stamp(args.not_before),
        'snapshot': str(snapshot),
        'checkpoint': str(Path(args.checkpoint).resolve()),
        'difficulty': 'medium', 'task_mode': 'continuous', 'stack': 'llm-rl',
        'plan_interval': 10, 'conditions': list(CONDITIONS),
        'seeds': list(args.seeds), 'reference_seeds': list(args.reference_seeds),
        'smoke_seeds': list(args.smoke_seeds),
        'max_tokens': args.max_tokens, 'temperature': args.temperature,
        'enable_thinking': False, 'llm_retries': 0,
        'provider_retries': args.provider_retries,
        'llm_timeout_seconds': args.llm_timeout_seconds,
        'case_wall_budget_seconds': args.case_wall_budget_seconds,
        'jobs_per_model': args.jobs_per_model,
        'max_tokens_measurement': ('M3: ~130-175 output tokens with thinking disabled; '
                                  'M2.x: ~1500-1800 output tokens including reasoning, '
                                  'truncated at 1024 and complete from 4096 up'),
        'models': models,
        'runner_sha256': sha(Path(__file__)),
        'adapter_sha256': sha(Path(__file__).with_name('minimax_client.py')),
        'frozen_files': {str((snapshot / 'role_c_toolkit/grid_rolec6.py').resolve()):
                         sha(snapshot / 'role_c_toolkit/grid_rolec6.py'),
                         str(Path(args.checkpoint).resolve()): sha(Path(args.checkpoint))},
        'success_criteria': {
            'interface_causal_necessity': 'per model: mean(V_strong - V_hold) > 0 with the '
                                          'seed-bootstrap 95% CI lower bound > 0',
            'deployment_behind_baseline': 'per model: mean(V_strong - V_pure_rl_same_seed) < 0',
            'validity_gate': 'every case analysis_valid, zero planner fallbacks, zero thinking '
                             'blocks where expect_no_thinking is true, no truncated responses',
            'honest_failure': 'a model failing any criterion is reported as a law boundary',
        },
        'no_cross_batch_merge': True,
        'credential_policy': 'the provider key is read from the named environment variable and '
                             'is never written to the plan, the request log or any artefact',
    }
    save(Path(args.output), plan)
    verify_plan(json.loads(Path(args.output).read_text(encoding='utf-8')),
                Path(args.output).resolve())
    print(json.dumps({'plan': str(args.output), 'sha256': sha(Path(args.output))}, indent=2))
    return 0


def normalize_stamp(value: str) -> str:
    stamp = value.strip()
    if not stamp:
        return datetime.now(timezone.utc).isoformat()
    parsed = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)

    make = sub.add_parser('plan', help='write the frozen plan')
    make.add_argument('--output', type=Path, required=True)
    make.add_argument('--snapshot', type=Path, required=True)
    make.add_argument('--checkpoint', type=Path, required=True)
    make.add_argument('--model', action='append', required=True,
                      help='slug|kind|served_name|provider|base_url|key_env|thinking_policy|'
                           'expect_no_thinking|min_interval_seconds')
    make.add_argument('--not-before', default='',
                      help='ISO timestamp; the batch refuses to start before it')
    make.add_argument('--seeds', type=int, nargs='+', required=True)
    make.add_argument('--reference-seeds', type=int, nargs='+', required=True)
    make.add_argument('--smoke-seeds', type=int, nargs='+', default=[2026100491])
    make.add_argument('--max-tokens', type=int, default=8192,
                      help='shared output ceiling; M2.x cannot disable thinking, so its '
                           'reasoning consumes part of the budget (measured: 4096 suffices)')
    make.add_argument('--temperature', type=float, default=.1)
    make.add_argument('--provider-retries', type=int, default=2,
                      help='transport retries for 429/5xx; the grid planner retry stays 0')
    make.add_argument('--llm-timeout-seconds', type=float, default=300.0)
    make.add_argument('--case-wall-budget-seconds', type=int, default=5400)
    make.add_argument('--jobs-per-model', type=int, default=1)

    check = sub.add_parser('probe', help='verify provider identity and thinking policy')
    check.add_argument('--plan', type=Path, required=True)
    check.add_argument('--output', type=Path, required=True)
    check.add_argument('--model', action='append')

    one = sub.add_parser('case', help='run exactly one preregistered case')
    one.add_argument('--plan', type=Path, required=True)
    one.add_argument('--output', type=Path, required=True)
    one.add_argument('--model', required=True)
    one.add_argument('--condition', choices=CONDITIONS, required=True)
    one.add_argument('--seed', type=int, required=True)
    one.add_argument('--arm', choices=ARMS, default='llm-rl')

    run = sub.add_parser('schedule', help='run every preregistered case')
    run.add_argument('--plan', type=Path, required=True)
    run.add_argument('--run-dir', type=Path, required=True)
    run.add_argument('--model', action='append')
    run.add_argument('--jobs-per-model', type=int, default=1)

    show = sub.add_parser('status', help='print progress')
    show.add_argument('--run-dir', type=Path, required=True)

    args = parser.parse_args()
    if args.command == 'plan':
        return plan_command(args)
    if args.command == 'probe':
        return probe_command(args.plan, args.output, args.model)
    if args.command == 'case':
        return run_case(args.plan, args.output, args.model, args.condition, args.seed, args.arm)
    if args.command == 'status':
        return status_command(args.run_dir)
    plan = json.loads(args.plan.read_text(encoding='utf-8'))
    chosen = args.model or list(plan['models'])
    return schedule(args.plan, args.run_dir, chosen, args.jobs_per_model)


if __name__ == '__main__':
    raise SystemExit(main())
