"""Fixed-snapshot inference campaign. No engine, policy or score patches.

Only the pinned evaluator frame is traced at its loop boundary and immediately
after native session.step returns. The recorder reads state; it never changes it.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import inspect
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

ROOT = Path(__file__).resolve().parents[1]
REMOTE_BASE = Path('/mnt/<lab>/<user>-codex')

def now():
    return datetime.now(timezone.utc).isoformat()

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def save(path, value):
    path = Path(path); temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10)); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)

def verify_files(root, expected):
    root = Path(root).resolve()
    for rel, digest in expected.items():
        path = (root / rel).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha(path) != digest:
            raise RuntimeError('Frozen input differs: ' + rel)

def verify_plan(plan):
    if plan['schema'] != 'remote-seed-campaign@1':
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

def process_identity(pid):
    try:
        text = Path('/proc', str(pid), 'stat').read_text()
        fields = text[text.rfind(')') + 2:].split()
        return {'pid': int(pid), 'start_ticks': fields[19], 'session_id': int(fields[3]), 'state': fields[0]}
    except (OSError, IndexError, ValueError):
        return None

def alive(identity):
    actual = process_identity(identity.get('pid', -1)) if identity else None
    return bool(actual and actual['start_ticks'] == identity.get('start_ticks') and actual['state'] != 'Z')

def service_health(plan):
    rows = []
    for name, endpoint in zip(('a', 'b'), plan['endpoints']):
        state = load(REMOTE_BASE / 'services/qwen' / ('replica-' + name + '.json'))
        if process_identity(state['pid']) is None:
            raise RuntimeError('Owned Qwen replica is not alive: ' + name)
        command = state['command']
        def flag(key):
            return command[command.index(key) + 1] if key in command else None
        required = {'--dtype': 'bfloat16', '--tensor-parallel-size': '2', '--max-model-len': '131072',
                    '--kv-cache-dtype': 'fp8', '--num-gpu-blocks-override': '296'}
        if any(str(flag(k)) != value for k, value in required.items()):
            raise RuntimeError('Qwen launch settings differ: ' + name)
        if flag('--quantization') not in (None, 'None', 'none'):
            raise RuntimeError('Weight quantization is not authorized')
        with urllib.request.urlopen(endpoint.removesuffix('/v1') + '/health', timeout=10) as response:
            if response.status != 200: raise RuntimeError('Qwen health failure')
        with urllib.request.urlopen(endpoint + '/models', timeout=10) as response:
            models = json.load(response)['data']
        if not any(x.get('id') == plan['model'] and x.get('max_model_len') == 131072 for x in models):
            raise RuntimeError('Served model/context differs: ' + name)
        rows.append({'replica': name, 'pid': state['pid'], 'endpoint': endpoint,
            'gpu_devices': state['gpu_devices'], 'known_launch_settings': required,
            'model_manifest_sha256': state['model_manifest_sha256'],
            'reference_host_hashes_compared': state.get('reference_host_hashes_compared', False)})
    if rows[0]['model_manifest_sha256'] != rows[1]['model_manifest_sha256']:
        raise RuntimeError('Replica model manifests differ')
    return rows

def capture_lines(function):
    tree = ast.parse(Path(inspect.getsourcefile(function)).read_text(encoding='utf-8-sig'))
    target = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function.__name__)
    points = []
    for loop in ast.walk(target):
        if not isinstance(loop, ast.For): continue
        for index, node in enumerate(loop.body[:-1]):
            value = getattr(node, 'value', None)
            if (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
                    and isinstance(value.func.value, ast.Name) and value.func.value.id == 'session'
                    and value.func.attr == 'step'):
                points.append((loop.lineno, loop.body[index + 1].lineno))
    if len(points) != 1:
        raise RuntimeError('Expected one pinned evaluator step boundary')
    return set(points[0])

class TrajectoryRecorder:
    def __init__(self, path, progress_path, identity):
        self.path, self.progress_path, self.identity = Path(path), Path(progress_path), identity
        self.stream = self.path.open('x', encoding='utf-8', buffering=1)
        self.last_tick, self.count, self.error = -1, 0, None
        self.last_progress = 0.0

    def capture(self, session):
        view = session.world_view; tick = int(view.tick)
        if tick == self.last_tick: return
        if tick != self.last_tick + 1:
            raise RuntimeError(f'Trajectory skipped ticks: {self.last_tick} -> {tick}')
        entities = []
        for entity in view.entities_stable():
            state = entity.state
            entities.append({'entity_id': entity.id, 'faction_id': entity.definition.faction_id,
                'lifecycle': str(state.lifecycle), 'position_m': [float(x) for x in state.position_m],
                'velocity_mps': [float(x) for x in state.velocity_mps], 'heading_deg': float(state.heading_deg),
                'health': float(state.health), 'energy': state.energy,
                'ammunition': {str(k): int(v) for k, v in state.ammunition.items()}})
        self.stream.write(json.dumps({'schema': 'rolec-native-trajectory@1',
            'case_id': self.identity, 'tick': tick, 'recorded_at_utc': now(), 'entities': entities},
            ensure_ascii=False, allow_nan=False) + chr(10))
        self.stream.flush(); self.last_tick = tick; self.count += 1
        if tick % 32 == 0: os.fsync(self.stream.fileno())
        if time.monotonic() - self.last_progress >= 5 or tick == 0:
            save(self.progress_path, {'case_id': self.identity, 'tick': tick, 'frames': self.count,
                                      'updated_utc': now(), 'status': 'running'})
            self.last_progress = time.monotonic()

    def run(self, function, *args):
        if sys.gettrace() is not None:
            raise RuntimeError('Refusing to replace an existing debugger/trace hook')
        points = capture_lines(function); target_code = function.__code__
        def local_trace(frame, event, argument):
            if event == 'line' and frame.f_lineno in points:
                try: self.capture(frame.f_locals['session'])
                except Exception as error:
                    self.error = type(error).__name__ + ': ' + str(error); raise
            return local_trace
        def dispatch(frame, event, argument):
            return local_trace if event == 'call' and frame.f_code is target_code else None
        sys.settrace(dispatch)
        try: return function(*args)
        finally: sys.settrace(None)

    def close(self):
        self.stream.flush(); os.fsync(self.stream.fileno()); self.stream.close()

def episode_arguments(plan, case, folder, ticks=None):
    planner = case['planner']
    argv = ['--scenario', case['scenario'], '--seed', str(case['seed']), '--planner', planner,
        '--max-ticks', str(ticks or plan['parameters']['max_ticks']), '--pure-llm-envelope', 'executor',
        '--frontend', 'graph', '--llm-briefing', 'withheld', '--llm-backend', 'vllm',
        '--llm-base-url', plan['endpoints'][case['slot']], '--llm-model', plan['model'],
        '--llm-max-tokens', '1024', '--plan-interval', '10', '--decision-interval', '5',
        '--rl-speed-source', 'legacy_tags', '--checkpoint-dir', str(folder / 'checkpoints'),
        '--log', str(folder / 'events.jsonl'), '--output', str(folder / 'report.json')]
    if planner in plan['weight_paths']:
        argv += ['--rl-theta', str(ROOT / plan['weight_paths'][planner])]
    if planner == 'llm-rl': argv += ['--goal-granularity', 'strong']
    return argv

def eligible(report):
    score = report.get('strategy_scorecard') or {}; terminal = report.get('terminal_result') or {}
    return bool(not report.get('aborted') and not report.get('error') and terminal.get('outcome')
        and report.get('ticks_run', 0) > 0 and score.get('scored_weight') is not None
        and float(score['scored_weight']) > 0 and score.get('defender_score') is not None
        and math.isfinite(float(score['defender_score'])))

def run_episode_case(plan, case, folder, smoke_ticks=None):
    verify_plan(plan); folder.mkdir(parents=True, exist_ok=False)
    engine = ROOT / 'openmd/source-code/source_codes'; evaluation = ROOT / 'openmd/code/eval'
    os.environ['OPENMDBENCH_ROOT'] = str(engine); os.environ['MPLBACKEND'] = 'Agg'
    sys.path.insert(0, str(engine)); sys.path.insert(0, str(evaluation))
    from run_episode import run_episode, build_parser, _RunLog
    from llm_client_hifi import LLMClient
    import openmdbench
    assert Path(openmdbench.__file__).resolve().is_relative_to(engine)
    from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
    resolved, _ = compile_formal_scenario_v2(case['scenario'])
    expected = next(x for x in plan['engine_pin']['compiled_scenarios'] if x['scenario_id'] == case['scenario'])
    for key in ('resolved_hash', 'catalog_hash', 'model_registry_hash'):
        if getattr(resolved, key) != expected[key]: raise RuntimeError('Compiled scenario differs: ' + key)
    argv = episode_arguments(plan, case, folder, smoke_ticks); args = build_parser().parse_args(argv)
    manifest = {'schema': 'remote-seed-episode@1', 'case': case, 'status': 'running',
        'started_utc': now(), 'snapshot': str(ROOT), 'source_pin_commit': plan['engine_pin']['reference_commit'],
        'source_pin_manifest_sha256': plan['engine_pin']['scope_manifest_sha256'],
        'recorder_sha256': sha(__file__), 'cli_argv': argv, 'smoke_only': smoke_ticks is not None,
        'compiled_hashes': {k: getattr(resolved, k) for k in ('resolved_hash', 'catalog_hash', 'model_registry_hash')},
        'weights_sha256': plan['weights_sha256'], 'engine_module_origin': openmdbench.__file__,
        'runtime_packages': {name: importlib.metadata.version(name) for name in plan['runtime_packages']},
        'historical_runtime_equivalence_claimed': False}
    save(folder / 'manifest.json', manifest)
    trajectory = TrajectoryRecorder(folder / 'trajectory.jsonl', folder / 'progress.json', case['id'])
    event_log = _RunLog(folder / 'events.jsonl')
    request_log = (folder / 'requests.jsonl').open('x', encoding='utf-8', buffering=1)
    original_chat = LLMClient.chat; lock = threading.Lock(); calls = [0]
    def chat(client, system_prompt, user_message, max_tokens=None, temperature=0.1):
        effective = max_tokens or client.max_tokens
        if (client.base_url.rstrip('/') != plan['endpoints'][case['slot']] or client.model != plan['model']
                or client.backend != 'vllm' or effective != 1024 or temperature != 0.1
                or client.enable_thinking is not False):
            raise RuntimeError('Actual LLM request differs from frozen ablation condition')
        with lock:
            index = calls[0]; calls[0] += 1
            request_log.write(json.dumps({'kind': 'request', 'call_index': index, 'utc': now(),
                'base_url': client.base_url, 'model': client.model, 'backend': client.backend,
                'effective_max_tokens': effective, 'temperature': temperature, 'enable_thinking': client.enable_thinking,
                'system_prompt': system_prompt, 'user_message': user_message}, ensure_ascii=False) + chr(10))
        started = time.monotonic()
        try: response = original_chat(client, system_prompt, user_message, max_tokens=max_tokens, temperature=temperature)
        except Exception as error:
            with lock: request_log.write(json.dumps({'kind': 'error', 'call_index': index, 'utc': now(), 'error': str(error)}) + chr(10))
            raise
        with lock:
            request_log.write(json.dumps({'kind': 'response', 'call_index': index, 'utc': now(),
                'elapsed_seconds': time.monotonic()-started, 'response': response}, ensure_ascii=False) + chr(10))
        return response
    LLMClient.chat = chat; report = None
    try:
        report = trajectory.run(run_episode, args, event_log)
        save(folder / 'report.json', report)
    except Exception as error:
        manifest.update(status='exception', error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
    finally:
        LLMClient.chat = original_chat; trajectory.close()
        request_log.flush(); os.fsync(request_log.fileno()); request_log.close()
        if not event_log._stream.closed: event_log.close()
    verify_plan(plan)
    complete_trace = bool(report and trajectory.error is None and trajectory.count == report['ticks_run']+1
                          and trajectory.last_tick == report['ticks_run'])
    normal = bool(report and eligible(report) and complete_trace)
    smoke_ok = bool(smoke_ticks and report and not report.get('error') and not report.get('aborted')
                    and report['ticks_run'] == smoke_ticks and complete_trace)
    if report is not None:
        manifest['status'] = 'smoke_passed' if smoke_ok else 'complete' if normal and not smoke_ticks else 'ineligible'
    manifest.update(finished_utc=now(), llm_calls=calls[0], trajectory_frames=trajectory.count,
        trajectory_last_tick=trajectory.last_tick, trajectory_complete=complete_trace, trajectory_error=trajectory.error,
        ticks_run=report.get('ticks_run') if report else None, eligible_for_main_score=normal and not bool(smoke_ticks),
        natural_terminal=bool(report and report.get('terminal_result') and not report.get('aborted')),
        terminal_result=report.get('terminal_result') if report else None,
        defender_score=(report.get('strategy_scorecard') or {}).get('defender_score') if report else None,
        artifacts_sha256={name: sha(folder/name) for name in ['report.json','events.jsonl','trajectory.jsonl','requests.jsonl'] if (folder/name).exists()})
    save(folder / 'manifest.json', manifest)
    save(folder / 'progress.json', {'case_id': case['id'], 'tick': trajectory.last_tick, 'status': manifest['status'], 'updated_utc': now()})
    print(json.dumps({k: manifest.get(k) for k in ['case','status','ticks_run','trajectory_frames','llm_calls','defender_score']}, ensure_ascii=False), flush=True)
    return 0 if normal or smoke_ok else 2

def certified(folder):
    path = folder / 'manifest.json'
    if not path.exists(): return False
    m = load(path)
    if m.get('status') != 'complete' or not m.get('eligible_for_main_score') or not m.get('trajectory_complete'):
        return False
    if m.get('trajectory_frames') != m.get('ticks_run', -2)+1: return False
    required = {'report.json','events.jsonl','trajectory.jsonl','requests.jsonl'}
    if set(m.get('artifacts_sha256', {})) != required: return False
    return all((folder/name).is_file() and sha(folder/name) == digest for name,digest in m['artifacts_sha256'].items())

def seed_batch(cases, completed):
    pending = [c for c in cases if c['id'] not in completed]
    if not pending: return []
    first = pending[0]
    return [c for c in pending if (c['phase'],c['seed']) == (first['phase'],first['seed'])]

def scheduler(plan, campaign):
    import fcntl
    with (campaign / '.run.lock').open('a') as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        verify_plan(plan)
        completed = {c['id'] for c in plan['cases'] if certified(campaign/'episodes'/c['id'])}
        state = {'schema':'remote-seed-status@1','status':'running','started_utc':now(),
            'controller':process_identity(os.getpid()),'snapshot':str(ROOT),'total_cases':len(plan['cases']),
            'completed':sorted(completed),'active':{},'failures':[],'queue_policy':'strict seed barrier; maximum two episodes'}
        running = {}
        def persist():
            state['updated_utc'] = now(); state['completed'] = sorted(completed)
            state['completed_by_seed'] = dict(Counter(str(c['seed']) for c in plan['cases'] if c['id'] in completed))
            save(campaign/'status.json',state)
        persist()
        try:
            while len(completed) < len(plan['cases']):
                for slot, job in list(running.items()):
                    process, case, stream, started = job
                    if process.poll() is None and time.monotonic()-started > plan['episode_wall_watchdog_seconds']:
                        os.killpg(process.pid,signal.SIGTERM)
                        state['failures'].append({'case_id':case['id'],'reason':'external wall watchdog; partial traces retained'})
                        try:process.wait(timeout=20)
                        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
                    if process.poll() is not None:
                        stream.close();folder=campaign/'episodes'/case['id']
                        if process.returncode==0 and certified(folder):completed.add(case['id'])
                        else:state['failures'].append({'case_id':case['id'],'returncode':process.returncode,
                            'manifest':str(folder/'manifest.json'),'console':str(campaign/'logs'/(case['id']+'.log'))})
                        del running[slot];state['active'].pop(case['id'],None)
                        print(json.dumps({'event':'case_finished','case_id':case['id'],
                            'certified':case['id'] in completed,'completed':len(completed),'utc':now()}),flush=True)
                        persist()
                stop=(campaign/'STOP_AFTER_CURRENT_EPISODES').exists() or bool(state['failures'])
                if stop and not running:break
                if not stop:
                    batch=seed_batch(plan['cases'],completed)
                    for slot in range(2):
                        if slot in running:continue
                        case=next((c for c in batch if c['slot']==slot and c['id'] not in state['active']),None)
                        if case is None:continue
                        folder=campaign/'episodes'/case['id']
                        if folder.exists():raise RuntimeError('Uncertified prior attempt preserved; review required: '+case['id'])
                        if case['planner']!='rl':service_health(plan)
                        stream=(campaign/'logs'/(case['id']+'.log')).open('ab',buffering=0)
                        command=[sys.executable,'-u','-B',str(Path(__file__).resolve()),'episode','--plan',str(campaign/'plan.json'),
                            '--campaign-dir',str(campaign),'--case-id',case['id']]
                        env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
                            NUMEXPR_NUM_THREADS='1',MPLBACKEND='Agg',PYTHONDONTWRITEBYTECODE='1')
                        process=subprocess.Popen(command,cwd=str(ROOT/'openmd/code/eval'),env=env,stdin=subprocess.DEVNULL,
                            stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                        identity=process_identity(process.pid)
                        state['active'][case['id']]={'case':case,'process':identity,'started_utc':now(),
                            'folder':str(folder),'console':str(campaign/'logs'/(case['id']+'.log'))}
                        running[slot]=(process,case,stream,time.monotonic())
                        print(json.dumps({'event':'case_started','case':case,'process':identity,'utc':now()}),flush=True)
                        persist()
                time.sleep(2);persist()
            state['status']='complete' if len(completed)==len(plan['cases']) else 'blocked_failed_case' if state['failures'] else 'stopped_by_control_file'
        except Exception as error:
            state['status']='controller_error';state['controller_error']=type(error).__name__+': '+str(error)
            state['traceback']=traceback.format_exc()
        finally:
            state['finished_utc']=now();persist()
    return 0 if state['status']=='complete' else 2

def launch(plan_path, campaign):
    if os.name != 'posix':raise RuntimeError('Launch is server-only; use the configured Huairou eval profile')
    import fcntl
    campaign=campaign.resolve();allowed=(REMOTE_BASE/'experiments').resolve()
    if campaign==allowed or not campaign.is_relative_to(allowed):
        raise ValueError('Campaign must be below the owned experiments directory')
    plan=load(plan_path);verify_plan(plan);health=service_health(plan)
    campaign.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (campaign/'.launch.lock').open('a') as lockfile:
        fcntl.flock(lockfile,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (campaign/'launch.json').exists():
            old=load(campaign/'launch.json')
            if alive(old['controller']):return {'status':'already_running',**old}
            state=load(campaign/'status.json') if (campaign/'status.json').exists() else {}
            if any(alive(x.get('process')) for x in state.get('active',{}).values()):
                raise RuntimeError('Owned episode children remain alive; do not duplicate the controller')
            if state.get('status')=='complete':return {'status':'already_complete',**old}
            raise RuntimeError('Stopped campaign requires reviewed recovery; no automatic replay')
        save(campaign/'plan.json',plan);save(campaign/'service-preflight.json',health)
        (campaign/'episodes').mkdir(exist_ok=True);(campaign/'logs').mkdir(exist_ok=True)
        command=[sys.executable,'-u','-B',str(Path(__file__).resolve()),'run','--plan',str(campaign/'plan.json'),'--campaign-dir',str(campaign)]
        with (campaign/'controller.log').open('ab',buffering=0) as log:
            process=subprocess.Popen(command,cwd=str(ROOT/'openmd/code/eval'),stdin=subprocess.DEVNULL,
                stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        record={'created_utc':now(),'controller':process_identity(process.pid),'campaign_dir':str(campaign),
            'snapshot':str(ROOT),'plan_sha256':sha(campaign/'plan.json'),'controller_log':str(campaign/'controller.log'),
            'command':command,'source_reference_commit':plan['engine_pin']['reference_commit']}
        save(campaign/'launch.json',record);return {'status':'started',**record}

def status(campaign):
    launch=load(campaign/'launch.json');state=load(campaign/'status.json') if (campaign/'status.json').exists() else {}
    active=[]
    for key,item in state.get('active',{}).items():
        progress=Path(item['folder'])/'progress.json'
        active.append({'case_id':key,'alive':alive(item.get('process')),
            'progress':load(progress) if progress.exists() else None,'folder':item['folder']})
    return {'campaign_dir':str(campaign),'status':state.get('status','starting'),'controller_alive':alive(launch['controller']),
        'controller':launch['controller'],'completed':len(state.get('completed',[])),'total':state.get('total_cases'),
        'completed_by_seed':state.get('completed_by_seed',{}),'active':active,'failures':state.get('failures',[]),
        'controller_error':state.get('controller_error'),'snapshot':launch['snapshot']}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start','run','episode','smoke','status'])
    parser.add_argument('--plan',type=Path);parser.add_argument('--campaign-dir',type=Path,required=True)
    parser.add_argument('--case-id');parser.add_argument('--ticks',type=int,default=6);args=parser.parse_args()
    if args.action=='status':print(json.dumps(status(args.campaign_dir),ensure_ascii=False),flush=True);return 0
    if args.plan is None:parser.error('--plan is required')
    plan=load(args.plan)
    if args.action=='start':print(json.dumps(launch(args.plan,args.campaign_dir),ensure_ascii=False),flush=True);return 0
    if args.action=='run':return scheduler(plan,args.campaign_dir)
    case=next(c for c in plan['cases'] if c['id']==args.case_id)
    if args.action=='smoke':
        if not 1<=args.ticks<=20:parser.error('Smoke ticks must be 1..20 and separate from formal episodes')
        return run_episode_case(plan,case,args.campaign_dir,args.ticks)
    return run_episode_case(plan,case,args.campaign_dir/'episodes'/case['id'])

if __name__=='__main__':raise SystemExit(main())
