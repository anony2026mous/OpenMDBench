"""Resume the four requested arms, completing all scenes per seed first."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from p1_6_campaign import id_for, now, sha256
from p1_6_run import verify_freeze
from toolkit_paths import ENGINE, EVAL

KIT = Path(__file__).resolve().parent
RUNNER = KIT / 'p1_6_run.py'
ARMS = ('llm-rl', 'llm', 'rl', 'pure-llm')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def queue_for(config):
    return [(scene, seed, arm) for seed in config['seeds']
            for scene in config['scenarios'] for arm in ARMS]


def certified(out, provenance, scene, seed, arm, runner_hash):
    ident = id_for(scene, arm, seed)
    path = out / (ident + '_manifest.json')
    if not path.exists():
        if any((out / (ident + suffix)).exists() for suffix in
               ('.json', '.jsonl', '_requests.jsonl', '_console.txt')):
            raise RuntimeError('Orphaned outputs require inspection: ' + ident)
        return False
    manifest = load(path)
    if (manifest.get('status') != 'complete' or not manifest.get('eligible_for_main_score')
            or not manifest.get('natural_terminal')
            or manifest.get('wrapper_sha256') != runner_hash
            or manifest.get('scenario_resolved_hash') != provenance['scenarios'][scene]['resolved_hash']):
        raise RuntimeError('Existing attempt is not certified; preserve and inspect: ' + ident)
    for suffix, field in (('.json', 'report_sha256'), ('.jsonl', 'events_sha256'),
                          ('_requests.jsonl', 'requests_sha256')):
        artifact = out / (ident + suffix)
        if not artifact.is_file() or sha256(artifact) != manifest.get(field):
            raise RuntimeError('Output hash mismatch: ' + str(artifact))
    return True


def progress(config, completed):
    return {str(seed): {
        'completed': sum(id_for(scene, arm, seed) in completed
                         for scene in config['scenarios'] for arm in ARMS),
        'required': len(config['scenarios']) * len(ARMS),
        'scenes': {scene: [arm for arm in ARMS if id_for(scene, arm, seed) in completed]
                   for scene in config['scenarios']}
    } for seed in config['seeds']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--schedule-name', default='seed_first_20260929')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if Path(args.schedule_name).name != args.schedule_name:
        parser.error('schedule-name must be a plain directory name')
    config = load(out / 'toolkit_config.json')
    provenance = load(out / 'provenance.json')
    frozen = load(out / 'night_budget_plan.json')
    runner_hash = sha256(RUNNER)
    if runner_hash != frozen['hashes'][RUNNER.name]:
        raise RuntimeError('Original runner changed')
    if sha256(out / 'toolkit_config.json') != frozen['toolkit_config_sha256']:
        raise RuntimeError('Original configuration changed')
    if not set(ARMS).issubset(config['arms']):
        raise RuntimeError('Requested arms are outside locked design')
    os.environ['OPENMDBENCH_ROOT'] = str(ENGINE)
    sys.path.insert(0, str(ENGINE))
    sys.path.insert(0, str(EVAL))
    for scene in config['scenarios']:
        verify_freeze(provenance, scene)
    queue = queue_for(config)
    completed = {id_for(s, a, n) for s, n, a in queue
                 if certified(out, provenance, s, n, a, runner_hash)}
    initial = progress(config, completed)
    print(json.dumps({'verified_existing': len(completed), 'remaining': len(queue)-len(completed),
                      'seed_progress': initial}, ensure_ascii=False), flush=True)
    if args.dry_run:
        return 0
    schedule = out / args.schedule_name
    schedule.mkdir(exist_ok=False)
    env = dict(os.environ, ROLEC_LLM_BASE_URL=config['base_url'],
               ROLEC_LLM_MODEL=config['model'], PYTHONIOENCODING='utf-8')
    hosts = '172.18.116.170,<server-ip>,localhost,127.0.0.1'
    env['NO_PROXY'] = env['no_proxy'] = hosts
    status = {'pid': os.getpid(), 'started_utc': now(), 'phase': 'running',
              'current': None, 'child_pid': None, 'stop_reason': None,
              'reused': sorted(completed), 'newly_completed': []}
    def update():
        status.update(updated_utc=now(), seed_progress=progress(config, completed))
        save(schedule / 'status.json', status)
    save(schedule / 'plan.json', {
        'created_utc': now(), 'arms': ARMS, 'seed_order': config['seeds'],
        'scenario_order': config['scenarios'], 'queue': queue,
        'order': 'seed -> scenario -> llm-rl, llm (LLM+rule), rl, pure-llm',
        'scope': 'Only existing pilot seeds; no historical gap filling or Git uploads.',
        'deadline': None, 'runner_sha256': runner_hash,
        'controller_sha256': sha256(Path(__file__)),
        'config_sha256': sha256(out / 'toolkit_config.json'), 'initial_progress': initial})
    update()
    try:
        for scene, seed, arm in queue:
            ident = id_for(scene, arm, seed)
            if ident in completed:
                continue
            status['current'] = ident
            update()
            command = [sys.executable, str(RUNNER), '--output-dir', str(out),
                       '--scenario', scene, '--arm', arm, '--seed', str(seed),
                       '--max-ticks', str(config['max_ticks']),
                       '--goal-granularity', config['goal_granularity']]
            with (out / (ident + '_console.txt')).open('x', encoding='utf-8') as log:
                child = subprocess.Popen(command, cwd=KIT, env=env, stdout=log,
                                         stderr=subprocess.STDOUT,
                                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                status['child_pid'] = child.pid
                update()
                while child.poll() is None:
                    time.sleep(5)
                    update()
            status['child_pid'] = None
            if child.returncode != 0:
                raise RuntimeError(f'{ident} exited {child.returncode}; no automatic overwrite/retry')
            if not certified(out, provenance, scene, seed, arm, runner_hash):
                raise RuntimeError('Missing completion manifest: ' + ident)
            completed.add(ident)
            status['newly_completed'].append(ident)
            status['current'] = None
            update()
            print('COMPLETE ' + ident, flush=True)
            with (schedule / (ident + '_analysis.log')).open('x', encoding='utf-8') as log:
                result = subprocess.run([sys.executable, str(KIT / 'p1_6_analyze.py'),
                                         '--output-dir', str(out)], cwd=KIT, env=env,
                                        stdout=log, stderr=subprocess.STDOUT,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode:
                raise RuntimeError('Analysis failed after ' + ident)
        status['phase'] = 'complete'
        update()
        return 0
    except Exception as exc:
        status.update(phase='stopped', stop_reason=str(exc))
        update()
        raise


if __name__ == '__main__':
    raise SystemExit(main())
