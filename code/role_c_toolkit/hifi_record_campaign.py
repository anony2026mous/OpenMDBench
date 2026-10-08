"""Recorded high-fidelity campaigns with replay gate and counterfactual attribution.

Successor of ``remote_seed_campaign.py`` (which stays frozen for its paused campaign).
Engine, scenarios, policies and scoring are untouched: every hook below only reads
state or wraps a harness call and returns its original result unchanged.

Per episode it writes
  manifest.json      frozen inputs, hashes, runtime, outcome
  trajectory.jsonl   every tick: all entity states (as before)
  decisions.jsonl    every tick: defender goal submissions (full GoalCommand + accepted/
                     rejected), goal status changes, executor fires, intruder fire count;
                     at plan ticks also the defender-visible contacts given to the planner
  requests.jsonl     every LLM request/response with the tick it was issued at
  events.jsonl       evaluator event log; report.json final report

Replay modes (no model calls):
  self            responses by call index; every prompt must equal the recording and
                  trajectory/decisions/score must match exactly (replay gate)
  frozen-planner  responses by tick, prompts not compared: forces the recorded upper
                  decisions at the same ticks under a different executor

Scheduler: N endpoints x K in-flight episodes each, separate CPU-only slots for
non-LLM jobs, seed-major order, optional pre-registered stop rule, and automatic
attribution jobs for episodes meeting the pre-registered failure rule.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, is_dataclass
import importlib.metadata
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import traceback
import urllib.request

from remote_seed_campaign import (REMOTE_BASE, ROOT, TrajectoryRecorder, alive, eligible, load,
                                  now, process_identity, save, sha, verify_files)

SCHEMA = 'hifi-record-campaign@1'
LLM_PLANNERS = {'llm', 'llm-rl', 'pure-llm'}
ARTIFACTS = ('report.json', 'events.jsonl', 'trajectory.jsonl', 'decisions.jsonl', 'requests.jsonl')


# ---------------------------------------------------------------- plan and inputs

def verify_plan(plan):
    if plan.get('schema') != SCHEMA:
        raise ValueError('Unknown campaign plan')
    ids = [case['id'] for case in plan['cases']]
    if len(ids) != len(set(ids)) or any('/' in x or chr(92) in x for x in ids):
        raise ValueError('Case identities must be unique plain names')
    verify_files(ROOT, plan['engine_pin']['expected_files_sha256'])
    verify_files(ROOT, plan['weights_sha256'])
    if sha(__file__) != plan['recorder_sha256']:
        raise RuntimeError('Recorder differs from frozen plan')
    if sys.platform == 'linux':
        for name, expected in plan['runtime_packages'].items():
            if importlib.metadata.version(name) != expected:
                raise RuntimeError('Runtime package changed: ' + name)


def service_health(plan, endpoint):
    """Check the owned replica serving ``endpoint`` against the frozen launch settings."""
    item = next(x for x in plan['endpoints'] if x['url'] == endpoint)
    state = load(REMOTE_BASE / 'services/qwen' / ('replica-' + item['name'] + '.json'))
    if process_identity(state['pid']) is None:
        raise RuntimeError('Owned Qwen replica is not alive: ' + item['name'])
    command = state['command']

    def flag(key):
        return command[command.index(key) + 1] if key in command else None
    for key, value in plan['service_requirements'].items():
        if str(flag(key)) != value:
            raise RuntimeError('Qwen launch setting differs: ' + item['name'] + ' ' + key)
    if flag('--quantization') not in (None, 'None', 'none'):
        raise RuntimeError('Weight quantization is not authorized')
    if state['model_manifest_sha256'] != plan['model_manifest_sha256']:
        raise RuntimeError('Replica model manifest differs: ' + item['name'])
    with urllib.request.urlopen(endpoint.removesuffix('/v1') + '/health', timeout=10) as response:
        if response.status != 200:
            raise RuntimeError('Qwen health failure: ' + item['name'])
    with urllib.request.urlopen(endpoint + '/models', timeout=10) as response:
        models = json.load(response)['data']
    if not any(x.get('id') == plan['model'] and x.get('max_model_len') == 131072 for x in models):
        raise RuntimeError('Served model/context differs: ' + item['name'])
    return {'replica': item['name'], 'pid': state['pid'], 'endpoint': endpoint,
            'gpu_devices': state.get('gpu_devices')}


def episode_arguments(plan, case, folder, endpoint, planner=None, ticks=None):
    planner = planner or case['planner']
    p = plan['parameters']
    argv = ['--scenario', case['scenario'], '--seed', str(case['seed']), '--planner', planner,
            '--max-ticks', str(ticks or p['max_ticks']), '--pure-llm-envelope', 'executor',
            '--frontend', 'graph', '--llm-briefing', p['briefing'], '--llm-backend', 'vllm',
            '--llm-base-url', endpoint or plan['endpoints'][0]['url'], '--llm-model', plan['model'],
            '--llm-max-tokens', str(p['llm_max_tokens']), '--plan-interval', str(p['plan_interval']),
            '--decision-interval', str(p['decision_interval']), '--rl-speed-source', 'legacy_tags',
            '--step-timeout', str(p.get('step_timeout_seconds', 60.0)),
            '--checkpoint-dir', str(folder / 'checkpoints'),
            '--log', str(folder / 'events.jsonl'), '--output', str(folder / 'report.json')]
    if planner in plan['weight_paths']:
        argv += ['--rl-theta', str(ROOT / plan['weight_paths'][planner])]
    # One interface definition for the whole counterfactual family (validity check i).
    if case['planner'] == 'llm-rl':
        argv += ['--goal-granularity', p['goal_granularity']]
    return argv


# ---------------------------------------------------------------- passive recording

def plain(value, depth=0):
    if depth > 12:
        return repr(value)
    if is_dataclass(value) and not isinstance(value, type):
        return plain(asdict(value), depth + 1)
    if hasattr(value, 'model_dump'):
        return value.model_dump(mode='json')
    if isinstance(value, dict) or hasattr(value, 'items'):
        try:
            return {str(k): plain(v, depth + 1) for k, v in value.items()}
        except Exception:  # noqa: BLE001 - recording must never change control flow
            return repr(value)
    if isinstance(value, (list, tuple, set, frozenset)):
        return [plain(v, depth + 1) for v in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else repr(value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return repr(value)


class DecisionRecorder:
    """Collects harness-level decisions; one line per tick, written after session.step."""

    def __init__(self, path, defender_faction_hint=None):
        self.stream = Path(path).open('x', encoding='utf-8', buffering=1)
        self.pending_submissions, self.pending_observations = [], []
        self.goal_status, self.count = {}, 0

    def submission(self, step, commands, result):
        self.pending_submissions.append({'step': step, 'commands': plain(commands),
                                         'result': plain(result)})

    def observation(self, tick, observation):
        try:
            faction = observation.observer_faction_id
            contacts = observation.contacts_by_faction.get(faction, ())
            self.pending_observations.append({'tick': tick, 'observer': faction,
                                              'contacts': plain(contacts),
                                              'own_entity_count': len(observation.own_entities)})
        except Exception as error:  # noqa: BLE001
            self.pending_observations.append({'tick': tick, 'error': repr(error)})

    def capture(self, frame_locals):
        tick = frame_locals.get('tick')
        result = frame_locals.get('result') or {}
        attack_result = frame_locals.get('attack_result') or {}
        defender = frame_locals.get('defender')
        changes = {}
        broker = getattr(defender, 'broker', None)
        if broker is not None:
            for task_id, state in broker.active.items():
                status = str(getattr(state, 'status', None))
                if self.goal_status.get(task_id) != status:
                    changes[task_id] = status
                    self.goal_status[task_id] = status
        executor = result.get('executor') or {}
        row = {'schema': 'rolec-tick-decisions@1', 'tick': tick,
               'submissions': self.pending_submissions,
               'planner_observations': self.pending_observations,
               'goal_status_changes': changes,
               'defender_fires': plain(executor.get('fires', ())),
               'executor_submitted': executor.get('submitted'),
               'safe_mode': plain(executor.get('safe_mode')),
               'intruder_fire_actions': len(attack_result.get('fire_actions', ()) or ())}
        self.stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + chr(10))
        self.pending_submissions, self.pending_observations = [], []
        self.count += 1

    def close(self):
        self.stream.flush(); os.fsync(self.stream.fileno()); self.stream.close()


class Recorder(TrajectoryRecorder):
    def __init__(self, folder, identity):
        super().__init__(folder / 'trajectory.jsonl', folder / 'progress.json', identity)
        self.decisions = DecisionRecorder(folder / 'decisions.jsonl')

    def run(self, function, *args):
        from remote_seed_campaign import capture_lines
        if sys.gettrace() is not None:
            raise RuntimeError('Refusing to replace an existing debugger/trace hook')
        points = capture_lines(function); target_code = function.__code__
        loop_line, after_step_line = sorted(points)

        def local_trace(frame, event, argument):
            if event == 'line' and frame.f_lineno in points:
                try:
                    if frame.f_lineno == after_step_line and 'receipt' in frame.f_locals:
                        self.decisions.capture(frame.f_locals)
                    self.capture(frame.f_locals['session'])
                except Exception as error:
                    self.error = type(error).__name__ + ': ' + str(error); raise
            return local_trace

        def dispatch(frame, event, argument):
            return local_trace if event == 'call' and frame.f_code is target_code else None
        sys.settrace(dispatch)
        try:
            return function(*args)
        finally:
            sys.settrace(None)

    def close(self):
        super().close(); self.decisions.close()


def current_plan_tick():
    frame = sys._getframe(2)
    for _ in range(8):
        if frame is None:
            return None
        if frame.f_code.co_name in ('plan', '__call__', 'act') and 'tick' in frame.f_locals:
            try:
                return int(frame.f_locals['tick'])
            except (TypeError, ValueError):
                return None
        frame = frame.f_back
    return None


class ReplayDivergence(RuntimeError):
    pass


def load_recorded_calls(folder):
    requests, responses = {}, {}
    for line in (Path(folder) / 'requests.jsonl').open(encoding='utf-8'):
        row = json.loads(line)
        if row['kind'] == 'request':
            requests[row['call_index']] = row
        elif row['kind'] == 'response':
            responses[row['call_index']] = row['response']
        elif row['kind'] == 'error':
            raise ReplayDivergence('Recording contains a failed LLM call; not replayable')
    if set(requests) != set(responses):
        raise ReplayDivergence('Recording has unanswered requests')
    calls = [{**requests[i], 'response': responses[i]} for i in sorted(requests)]
    if [c['call_index'] for c in calls] != list(range(len(calls))):
        raise ReplayDivergence('Recorded call indices are not contiguous')
    for index, call in enumerate(calls):
        if call.get('tick') is None:
            # Legacy recordings (remote-seed-episode@1) lack ticks; for the fixed-cadence
            # planner one call is made at every plan tick starting at 0.
            call['tick'] = index * int(call.get('_plan_interval', 10))
            call['tick_derived'] = True
    return calls


# ---------------------------------------------------------------- one episode

def run_episode_case(plan, case, folder, endpoint, *, planner=None, replay_from=None,
                     replay_mode=None, smoke_ticks=None):
    verify_plan(plan); folder.mkdir(parents=True, exist_ok=False)
    engine = ROOT / 'openmd/source-code/source_codes'; evaluation = ROOT / 'openmd/code/eval'
    os.environ['OPENMDBENCH_ROOT'] = str(engine); os.environ['MPLBACKEND'] = 'Agg'
    sys.path.insert(0, str(engine)); sys.path.insert(0, str(evaluation))
    from run_episode import run_episode, build_parser, _RunLog
    from llm_client_hifi import LLMClient
    from goai_protocol import GOAIBroker
    from llm_planner import LLMPlannerV2
    from rule_planner import RulePlannerV2
    import openmdbench
    assert Path(openmdbench.__file__).resolve().is_relative_to(engine)
    from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
    resolved, _ = compile_formal_scenario_v2(case['scenario'])
    expected = next(x for x in plan['engine_pin']['compiled_scenarios'] if x['scenario_id'] == case['scenario'])
    for key in ('resolved_hash', 'catalog_hash', 'model_registry_hash'):
        if getattr(resolved, key) != expected[key]:
            raise RuntimeError('Compiled scenario differs: ' + key)
    planner = planner or case['planner']
    argv = episode_arguments(plan, case, folder, endpoint, planner, smoke_ticks)
    args = build_parser().parse_args(argv)
    recorded = None; horizon = [None, 0]
    if replay_from is not None:
        recorded = load_recorded_calls(replay_from)
        by_tick = {}
        for call in recorded:
            if call['tick'] in by_tick:
                raise ReplayDivergence('Two recorded calls at one tick; frozen replay ambiguous')
            by_tick[call['tick']] = call
        horizon[0] = max(by_tick) if by_tick else None
    manifest = {'schema': 'hifi-record-episode@1', 'case': case, 'planner': planner, 'status': 'running',
                'started_utc': now(), 'snapshot': str(ROOT), 'endpoint': endpoint,
                'source_pin_commit': plan['engine_pin']['reference_commit'],
                'recorder_sha256': sha(__file__), 'cli_argv': argv, 'smoke_only': smoke_ticks is not None,
                'replay': None if replay_from is None else {
                    'from': str(replay_from), 'mode': replay_mode,
                    'requests_sha256': sha(Path(replay_from) / 'requests.jsonl'),
                    'recorded_calls': len(recorded),
                    'ticks_derived': any(c.get('tick_derived') for c in recorded)},
                'compiled_hashes': {k: getattr(resolved, k) for k in ('resolved_hash', 'catalog_hash', 'model_registry_hash')},
                'weights_sha256': plan['weights_sha256'], 'engine_module_origin': openmdbench.__file__,
                'runtime_packages': {n: importlib.metadata.version(n) for n in plan['runtime_packages']}}
    save(folder / 'manifest.json', manifest)
    recorder = Recorder(folder, case['id'])
    event_log = _RunLog(folder / 'events.jsonl')
    request_log = (folder / 'requests.jsonl').open('x', encoding='utf-8', buffering=1)
    lock = threading.Lock(); calls = [0]; divergence = []
    originals = {'chat': LLMClient.chat, 'submit': GOAIBroker.submit_goals,
                 'llm_plan': LLMPlannerV2.plan, 'rule_plan': RulePlannerV2.plan}
    p = plan['parameters']

    def write(row):
        with lock:
            request_log.write(json.dumps(row, ensure_ascii=False) + chr(10))

    def chat(client, system_prompt, user_message, max_tokens=None, temperature=0.1):
        effective = max_tokens or client.max_tokens
        if (client.model != plan['model'] or client.backend != 'vllm' or effective != p['llm_max_tokens']
                or temperature != p['temperature'] or client.enable_thinking is not False):
            raise RuntimeError('Actual LLM request differs from frozen ablation condition')
        tick = current_plan_tick()
        with lock:
            index = calls[0]; calls[0] += 1
        write({'kind': 'request', 'call_index': index, 'tick': tick, 'utc': now(),
               'base_url': client.base_url, 'model': client.model, 'backend': client.backend,
               'effective_max_tokens': effective, 'temperature': temperature,
               'enable_thinking': client.enable_thinking, 'replayed': recorded is not None,
               'system_prompt': system_prompt, 'user_message': user_message})
        started = time.monotonic()
        if recorded is not None:
            if replay_mode == 'self':
                if index >= len(recorded):
                    divergence.append({'call_index': index, 'reason': 'more calls than recording'})
                    raise ReplayDivergence('More LLM calls than the recording')
                call = recorded[index]
                if call['tick'] != tick and not call.get('tick_derived'):
                    divergence.append({'call_index': index, 'reason': 'tick', 'recorded': call['tick'], 'actual': tick})
                    raise ReplayDivergence('Recorded call tick differs')
                if call['system_prompt'] != system_prompt or call['user_message'] != user_message:
                    divergence.append({'call_index': index, 'tick': tick, 'reason': 'prompt differs'})
                    raise ReplayDivergence(f'Prompt differs at call {index}, tick {tick}')
            else:
                call = by_tick.get(tick)
                if call is None and horizon[0] is not None and tick is not None and tick > horizon[0]:
                    # Beyond the original episode the recorded planner issued nothing new. An empty
                    # reply is the planner's native no-new-plan path: it keeps executing its last
                    # validated recorded plan (stale_plan_reuse). Counted in the manifest.
                    horizon[1] += 1
                    call = {'response': ''}
                if call is None:
                    divergence.append({'call_index': index, 'tick': tick, 'reason': 'no recorded decision at tick'})
                    raise ReplayDivergence(f'No recorded decision at tick {tick}')
            response = call['response']
        else:
            try:
                response = originals['chat'](client, system_prompt, user_message,
                                             max_tokens=max_tokens, temperature=temperature)
            except Exception as error:
                write({'kind': 'error', 'call_index': index, 'tick': tick, 'utc': now(), 'error': str(error)})
                raise
        write({'kind': 'response', 'call_index': index, 'tick': tick, 'utc': now(),
               'elapsed_seconds': time.monotonic() - started, 'response': response})
        return response

    def submit_goals(broker, commands, step, *rest, **kwargs):
        result = originals['submit'](broker, commands, step, *rest, **kwargs)
        recorder.decisions.submission(step, commands, result)
        return result

    def wrap_plan(original):
        def planned(planner_self, observation, tick, *rest, **kwargs):
            recorder.decisions.observation(tick, observation)
            return original(planner_self, observation, tick, *rest, **kwargs)
        return planned

    LLMClient.chat = chat; GOAIBroker.submit_goals = submit_goals
    LLMPlannerV2.plan = wrap_plan(originals['llm_plan']); RulePlannerV2.plan = wrap_plan(originals['rule_plan'])
    report = None
    try:
        report = recorder.run(run_episode, args, event_log)
        save(folder / 'report.json', report)
    except Exception as error:
        manifest.update(status='exception', error=type(error).__name__ + ': ' + str(error),
                        traceback=traceback.format_exc())
    finally:
        LLMClient.chat = originals['chat']; GOAIBroker.submit_goals = originals['submit']
        LLMPlannerV2.plan = originals['llm_plan']; RulePlannerV2.plan = originals['rule_plan']
        recorder.close()
        request_log.flush(); os.fsync(request_log.fileno()); request_log.close()
        if not event_log._stream.closed:
            event_log.close()
    verify_plan(plan)
    if report is not None and report.get('error') and 'ReplayDivergence' in str(report.get('error')):
        divergence.append({'reason': 'evaluator reported divergence', 'error': report.get('error')})
    complete_trace = bool(report and recorder.error is None and recorder.count == report['ticks_run'] + 1
                          and recorder.last_tick == report['ticks_run']
                          and recorder.decisions.count == report['ticks_run'] - report.get('start_tick', 0))
    normal = bool(report and eligible(report) and complete_trace and not divergence)
    smoke_ok = bool(smoke_ticks and report and not report.get('error') and not report.get('aborted')
                    and report['ticks_run'] == smoke_ticks and complete_trace and not divergence)
    if report is not None:
        manifest['status'] = 'smoke_passed' if smoke_ok else 'complete' if normal and not smoke_ticks else 'ineligible'
    if recorded is not None and replay_mode == 'frozen-planner':
        manifest['frozen_plan_horizon'] = {'last_recorded_decision_tick': horizon[0],
                                           'held_last_plan_calls_after_horizon': horizon[1]}
    manifest.update(finished_utc=now(), llm_calls=calls[0], replay_divergence=divergence,
                    trajectory_frames=recorder.count, decision_frames=recorder.decisions.count,
                    trajectory_last_tick=recorder.last_tick, trajectory_complete=complete_trace,
                    trajectory_error=recorder.error, ticks_run=report.get('ticks_run') if report else None,
                    eligible_for_main_score=normal and not smoke_ticks,
                    natural_terminal=bool(report and report.get('terminal_result') and not report.get('aborted')),
                    terminal_result=report.get('terminal_result') if report else None,
                    defender_score=(report.get('strategy_scorecard') or {}).get('defender_score') if report else None,
                    artifacts_sha256={n: sha(folder / n) for n in ARTIFACTS if (folder / n).exists()})
    save(folder / 'manifest.json', manifest)
    save(folder / 'progress.json', {'case_id': case['id'], 'tick': recorder.last_tick,
                                    'status': manifest['status'], 'updated_utc': now()})
    print(json.dumps({k: manifest.get(k) for k in ['case', 'planner', 'status', 'ticks_run', 'llm_calls',
                                                    'defender_score', 'replay_divergence']},
                     ensure_ascii=False), flush=True)
    return 0 if normal or smoke_ok else 2


def episode_folder(plan, campaign, case_id):
    """Certified episode from a declared prior campaign (same frozen conditions), else this one."""
    for prior in plan.get('prior_campaigns', ()):
        folder = Path(prior) / 'episodes' / case_id
        if certified(folder):
            return folder
    return campaign / 'episodes' / case_id


def reusable_run(plan, case_id, name):
    """A completed counterfactual run of the same case under the same frozen conditions."""
    for prior in plan.get('prior_campaigns', ()):
        folder = Path(prior) / 'attribution' / case_id / name
        if (folder / 'manifest.json').exists():
            m = load(folder / 'manifest.json')
            if m.get('status') == 'complete' and not m.get('replay_divergence'):
                return folder
    return None


def prior_attribution_complete(plan, case_id):
    for prior in plan.get('prior_campaigns', ()):
        path = Path(prior) / 'attribution' / case_id / 'attribution.json'
        if path.exists() and load(path).get('status') == 'complete':
            return True
    return False


def certified(folder):
    path = folder / 'manifest.json'
    if not path.exists():
        return False
    m = load(path)
    if m.get('status') != 'complete' or not m.get('eligible_for_main_score') or not m.get('trajectory_complete'):
        return False
    if set(m.get('artifacts_sha256', {})) != set(ARTIFACTS):
        return False
    return all((folder / n).is_file() and sha(folder / n) == d for n, d in m['artifacts_sha256'].items())


# ---------------------------------------------------------------- replay gate and attribution

def _stripped_lines(path, drop):
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            for key in drop:
                row.pop(key, None)
            yield row


def compare_runs(original, replay):
    """Exact comparison of everything the simulation produced; wall-clock fields excluded."""
    result = {}
    for name, drop in (('trajectory.jsonl', ('recorded_at_utc',)), ('decisions.jsonl', ())):
        if name == 'decisions.jsonl' and not (original / name).exists():
            result['decisions_not_in_legacy_original'] = True
            continue
        first = None; count = 0
        a, b = _stripped_lines(original / name, drop), _stripped_lines(replay / name, drop)
        for left, right in zip(a, b):
            if left != right:
                first = left.get('tick'); break
            count += 1
        rest = next(a, None) is not None or next(b, None) is not None
        result[name] = {'identical': first is None and not rest, 'first_divergent_tick': first,
                        'matched_lines': count}
    left, right = load(original / 'report.json'), load(replay / 'report.json')
    keys = ('ticks_run', 'terminal_result', 'strategy_scorecard', 'total_fires', 'damage_by_kind')
    result['report'] = {k: left.get(k) == right.get(k) for k in keys}
    result['exact_match'] = all(v['identical'] for k, v in result.items()
                                if k.endswith('.jsonl') and isinstance(v, dict)) \
        and all(result['report'].values())
    return result


def label_attribution(rule, delta_p, delta_e, delta_i):
    """Pre-registered rule: label the layer whose reference substitution helps most."""
    shares = {'planning': delta_p, 'execution': delta_e, 'interface': abs(delta_i)}
    best = max(shares, key=lambda k: (shares[k], k == 'planning', k == 'execution'))
    if shares[best] < rule['min_effect']:
        return 'undetermined'
    ordered = sorted(shares.values(), reverse=True)
    if ordered[0] - ordered[1] < rule['tie_margin']:
        return 'balanced'
    return best


def attribute_case(plan, campaign, case):
    """Self-replay gate + three reference substitutions for one recorded failure."""
    source = episode_folder(plan, campaign, case['id'])
    target = campaign / 'attribution' / case['id']
    target.mkdir(parents=True, exist_ok=False)
    spec = plan['attribution']
    runs = [('self_replay', case['planner'], 'self'),
            ('reference_executor', spec['reference_executor_planner'], 'frozen-planner'),
            ('reference_planner', spec['reference_planner_planner'], None),
            ('reference_full', spec['reference_full_planner'], None)]
    out = {'schema': 'hifi-attribution@1', 'case': case, 'started_utc': now(), 'runs': {},
           'rule': spec['label_rule'], 'recorder_sha256': sha(__file__),
           'reference_components_certified_oracles': False}
    save(target / 'attribution.json', out)
    for name, planner, mode in runs:
        folder = target / name
        reused = reusable_run(plan, case['id'], name)
        if reused is not None:
            folder = reused
            manifest = load(folder / 'manifest.json')
            out['runs'][name] = {'planner': planner, 'replay_mode': mode, 'returncode': 0, 'reused_from': str(folder),
                                 'frozen_plan_horizon': manifest.get('frozen_plan_horizon'),
                                 'status': manifest.get('status'), 'score': manifest.get('defender_score'),
                                 'outcome': (manifest.get('terminal_result') or {}).get('outcome'),
                                 'divergence': manifest.get('replay_divergence')}
            if name == 'self_replay':
                out['replay_gate'] = compare_runs(source, folder)
                if not out['replay_gate']['exact_match']:
                    out.update(status='replay_gate_failed', finished_utc=now())
                    save(target / 'attribution.json', out); return 2
            save(target / 'attribution.json', out)
            continue
        command = [sys.executable, '-u', '-B', str(Path(__file__).resolve()), 'episode',
                   '--plan', str(campaign / 'plan.json'), '--campaign-dir', str(campaign),
                   '--case-id', case['id'], '--planner', planner, '--output-dir', str(folder)]
        if mode:
            command += ['--replay-from', str(source), '--replay-mode', mode]
        with (target / (name + '.log')).open('ab', buffering=0) as log:
            code = subprocess.run(command, cwd=str(ROOT / 'openmd/code/eval'), env=child_env(),
                                  stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT).returncode
        manifest = load(folder / 'manifest.json') if (folder / 'manifest.json').exists() else {}
        out['runs'][name] = {'planner': planner, 'replay_mode': mode, 'returncode': code,
                             'frozen_plan_horizon': manifest.get('frozen_plan_horizon'),
                             'status': manifest.get('status'), 'score': manifest.get('defender_score'),
                             'outcome': (manifest.get('terminal_result') or {}).get('outcome'),
                             'divergence': manifest.get('replay_divergence')}
        if name == 'self_replay':
            gate = compare_runs(source, folder) if code == 0 else {'exact_match': False}
            out['replay_gate'] = gate
            if not gate['exact_match']:
                out.update(status='replay_gate_failed', finished_utc=now())
                save(target / 'attribution.json', out); return 2
        save(target / 'attribution.json', out)
    scores = {k: v['score'] for k, v in out['runs'].items()}
    if any(scores[k] is None or out['runs'][k]['returncode'] != 0 for k in scores):
        out.update(status='counterfactual_incomplete', finished_utc=now())
        save(target / 'attribution.json', out); return 2
    v0 = load(source / 'manifest.json')['defender_score']
    dp = scores['reference_planner'] - v0
    de = scores['reference_executor'] - v0
    di = scores['reference_full'] - scores['reference_planner'] - scores['reference_executor'] + v0
    out.update(status='complete', finished_utc=now(), original_score=v0,
               delta_planning=dp, delta_execution=de, delta_interface=di,
               machine_label=label_attribution(spec['label_rule'], dp, de, di))
    save(target / 'attribution.json', out)
    return 0


# ---------------------------------------------------------------- scheduler

def child_env():
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               NUMEXPR_NUM_THREADS='1', MPLBACKEND='Agg', PYTHONDONTWRITEBYTECODE='1')
    return env


def is_failure(plan, case, manifest):
    rule = plan.get('failure_rule')
    if not rule or case['planner'] not in rule['planners']:
        return False
    score = manifest.get('defender_score')
    return score is not None and float(score) < rule['score_below']


def pick_endpoint(plan, inflight):
    best = min(plan['endpoints'], key=lambda e: (inflight.get(e['url'], 0), e['name']))
    return best['url'] if inflight.get(best['url'], 0) < plan['max_inflight_per_endpoint'] else None


def next_cases(plan, done, active, stop_seeds):
    """Seed-major order. With a stop rule, no seed beyond ``stop_seeds`` starts."""
    pending = [c for c in plan['cases'] if c['id'] not in done and c['id'] not in active]
    if stop_seeds is not None:
        pending = [c for c in pending if c['seed'] in stop_seeds]
    return pending


def scheduler(plan, campaign):
    import fcntl
    with (campaign / '.run.lock').open('a') as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        verify_plan(plan)
        done = {c['id'] for c in plan['cases'] if certified(episode_folder(plan, campaign, c['id']))}
        state = {'schema': 'hifi-record-status@1', 'status': 'running', 'started_utc': now(),
                 'controller': process_identity(os.getpid()), 'snapshot': str(ROOT),
                 'total_cases': len(plan['cases']), 'failures': [], 'active': {},
                 'rule_failures': [], 'attribution': {}, 'stop_seeds': None,
                 'policy': {'endpoints': [e['url'] for e in plan['endpoints']],
                            'max_inflight_per_endpoint': plan['max_inflight_per_endpoint'],
                            'max_cpu_jobs': plan['max_cpu_jobs']}}
        by_id = {c['id']: c for c in plan['cases']}
        running = {}  # key -> (process, kind, case, endpoint, stream, started)
        attribution_queue = []
        for cid in sorted(done):
            m = load(episode_folder(plan, campaign, cid) / 'manifest.json')
            if is_failure(plan, by_id[cid], m):
                state['rule_failures'].append(cid)
                if (plan.get('attribution', {}).get('enabled') and not (campaign / 'attribution' / cid).exists()
                        and not prior_attribution_complete(plan, cid)):
                    attribution_queue.append(cid)

        def persist():
            state['updated_utc'] = now(); state['completed'] = sorted(done)
            state['completed_by_seed'] = dict(Counter(str(by_id[c]['seed']) for c in done))
            save(campaign / 'status.json', state)

        def update_stop_rule():
            rule = plan.get('stop_rule')
            if rule and state['stop_seeds'] is None and len(state['rule_failures']) >= rule['failures_needed']:
                # Finish every seed already started so no seed group is truncated by outcome.
                started = {k.split(':', 1)[1] for k in running if k.startswith('episode:')}
                state['stop_seeds'] = sorted({by_id[c]['seed'] for c in done | started})
        update_stop_rule(); persist()
        try:
            while True:
                for key, (process, kind, case, endpoint, stream, started) in list(running.items()):
                    if process.poll() is None and time.monotonic() - started > plan['episode_wall_watchdog_seconds']:
                        os.killpg(process.pid, signal.SIGTERM)
                        try: process.wait(timeout=20)
                        except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); process.wait()
                        state['failures'].append({'job': key, 'reason': 'wall watchdog; partial traces retained'})
                    if process.poll() is None:
                        continue
                    stream.close(); del running[key]; state['active'].pop(key, None)
                    if kind == 'episode':
                        folder = campaign / 'episodes' / case['id']
                        if process.returncode == 0 and certified(folder):
                            done.add(case['id'])
                            m = load(folder / 'manifest.json')
                            if is_failure(plan, case, m):
                                state['rule_failures'].append(case['id'])
                                if plan.get('attribution', {}).get('enabled'):
                                    attribution_queue.append(case['id'])
                            update_stop_rule()
                        else:
                            state['failures'].append({'job': key, 'returncode': process.returncode,
                                                      'manifest': str(folder / 'manifest.json')})
                    else:
                        path = campaign / 'attribution' / case['id'] / 'attribution.json'
                        state['attribution'][case['id']] = load(path).get('status') if path.exists() else 'missing'
                    print(json.dumps({'event': 'job_finished', 'job': key, 'returncode': process.returncode,
                                      'completed': len(done), 'utc': now()}), flush=True)
                    persist()
                stop_file = (campaign / 'STOP_AFTER_CURRENT_EPISODES').exists()
                too_many = len(state['failures']) >= plan['max_job_failures']
                pending = next_cases(plan, done, {k.split(':', 1)[1] for k in running if k.startswith('episode:')},
                                     state['stop_seeds'])
                pending = [c for c in pending if not any(f['job'] == 'episode:' + c['id'] for f in state['failures'])]
                if (stop_file or ((too_many or not pending) and not attribution_queue)) and not running:
                    break
                if too_many:
                    pending = []  # new episodes blocked; queued attribution (CPU only) still drains
                if not stop_file:
                    inflight = Counter(e for _, kind, _, e, _, _ in running.values() if e)
                    cpu = sum(1 for _, kind, case, e, _, _ in running.values() if not e)
                    launches = []
                    for case in pending:
                        if case['planner'] in LLM_PLANNERS:
                            endpoint = pick_endpoint(plan, inflight)
                            if endpoint is None:
                                continue
                            inflight[endpoint] += 1
                        else:
                            if cpu >= plan['max_cpu_jobs']:
                                continue
                            endpoint = None; cpu += 1
                        launches.append(('episode', case, endpoint))
                    while attribution_queue and cpu < plan['max_cpu_jobs']:
                        launches.append(('attribution', by_id[attribution_queue.pop(0)], None)); cpu += 1
                    for kind, case, endpoint in launches:
                        key = kind + ':' + case['id']
                        if kind == 'episode':
                            folder = campaign / 'episodes' / case['id']
                            if folder.exists():
                                raise RuntimeError('Uncertified prior attempt preserved; review required: ' + case['id'])
                            if endpoint:
                                service_health(plan, endpoint)
                            command = ['episode', '--case-id', case['id']] + (['--endpoint', endpoint] if endpoint else [])
                        else:
                            command = ['attribute', '--case-id', case['id']]
                        command = [sys.executable, '-u', '-B', str(Path(__file__).resolve())] + command + [
                            '--plan', str(campaign / 'plan.json'), '--campaign-dir', str(campaign)]
                        stream = (campaign / 'logs' / (key.replace(':', '__') + '.log')).open('ab', buffering=0)
                        process = subprocess.Popen(command, cwd=str(ROOT / 'openmd/code/eval'), env=child_env(),
                                                   stdin=subprocess.DEVNULL, stdout=stream,
                                                   stderr=subprocess.STDOUT, start_new_session=True)
                        running[key] = (process, kind, case, endpoint, stream, time.monotonic())
                        state['active'][key] = {'case': case, 'endpoint': endpoint, 'started_utc': now(),
                                                'process': process_identity(process.pid)}
                        print(json.dumps({'event': 'job_started', 'job': key, 'endpoint': endpoint,
                                          'utc': now()}), flush=True)
                        persist()
                time.sleep(2); persist()
            state['status'] = ('stopped_by_control_file' if (campaign / 'STOP_AFTER_CURRENT_EPISODES').exists()
                               else 'blocked_too_many_failures' if len(state['failures']) >= plan['max_job_failures']
                               else 'complete')
        except Exception as error:
            state['status'] = 'controller_error'
            state['controller_error'] = type(error).__name__ + ': ' + str(error)
            state['traceback'] = traceback.format_exc()
        finally:
            state['finished_utc'] = now(); persist()
    return 0 if state['status'] == 'complete' else 2


def launch(plan_path, campaign):
    if os.name != 'posix':
        raise RuntimeError('Launch is server-only')
    import fcntl
    campaign = campaign.resolve(); allowed = (REMOTE_BASE / 'experiments').resolve()
    if campaign == allowed or not campaign.is_relative_to(allowed):
        raise ValueError('Campaign must be below the owned experiments directory')
    plan = load(plan_path); verify_plan(plan)
    health = [service_health(plan, e['url']) for e in plan['endpoints']]
    campaign.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (campaign / '.launch.lock').open('a') as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (campaign / 'launch.json').exists():
            old = load(campaign / 'launch.json')
            if alive(old['controller']):
                return {'status': 'already_running', **old}
            raise RuntimeError('Stopped campaign requires reviewed recovery; no automatic restart')
        save(campaign / 'plan.json', plan); save(campaign / 'service-preflight.json', health)
        for name in ('episodes', 'logs', 'attribution'):
            (campaign / name).mkdir(exist_ok=True)
        command = [sys.executable, '-u', '-B', str(Path(__file__).resolve()), 'run',
                   '--plan', str(campaign / 'plan.json'), '--campaign-dir', str(campaign)]
        with (campaign / 'controller.log').open('ab', buffering=0) as log:
            process = subprocess.Popen(command, cwd=str(ROOT / 'openmd/code/eval'), stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        record = {'created_utc': now(), 'controller': process_identity(process.pid),
                  'campaign_dir': str(campaign), 'snapshot': str(ROOT),
                  'plan_sha256': sha(campaign / 'plan.json'), 'command': command}
        save(campaign / 'launch.json', record)
        return {'status': 'started', **record}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'run', 'episode', 'smoke', 'attribute', 'status'])
    parser.add_argument('--plan', type=Path); parser.add_argument('--campaign-dir', type=Path, required=True)
    parser.add_argument('--case-id'); parser.add_argument('--endpoint')
    parser.add_argument('--planner'); parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--replay-from', type=Path)
    parser.add_argument('--replay-mode', choices=['self', 'frozen-planner'])
    parser.add_argument('--ticks', type=int, default=20)
    args = parser.parse_args()
    if args.action == 'status':
        print(json.dumps(load(args.campaign_dir / 'status.json'), ensure_ascii=False), flush=True); return 0
    if args.plan is None:
        parser.error('--plan is required')
    plan = load(args.plan)
    if args.action == 'start':
        print(json.dumps(launch(args.plan, args.campaign_dir), ensure_ascii=False), flush=True); return 0
    if args.action == 'run':
        return scheduler(plan, args.campaign_dir)
    case = next(c for c in plan['cases'] if c['id'] == args.case_id)
    if args.action == 'attribute':
        return attribute_case(plan, args.campaign_dir, case)
    if bool(args.replay_from) != bool(args.replay_mode):
        parser.error('--replay-from and --replay-mode go together')
    if args.action == 'smoke':
        if not 1 <= args.ticks <= 60:
            parser.error('Smoke ticks must be 1..60')
        folder = args.output_dir or (args.campaign_dir / 'smoke' / case['id'])
        return run_episode_case(plan, case, folder, args.endpoint, planner=args.planner,
                                replay_from=args.replay_from, replay_mode=args.replay_mode, smoke_ticks=args.ticks)
    folder = args.output_dir or (args.campaign_dir / 'episodes' / case['id'])
    return run_episode_case(plan, case, folder, args.endpoint, planner=args.planner,
                            replay_from=args.replay_from, replay_mode=args.replay_mode)


if __name__ == '__main__':
    raise SystemExit(main())
