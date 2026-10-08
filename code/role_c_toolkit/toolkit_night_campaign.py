"""Run an audited, sequential subset until a fixed wall-clock deadline."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from toolkit_paths import EVAL, PROJECT

KIT = Path(__file__).resolve().parent
LLM_ARMS = ('llm', 'llm-rl', 'pure-llm')
CHEAP_ARMS = ('rule', 'rule-rl', 'rl')

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def save(path, value):
    path = Path(path)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    os.replace(temp, path)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def make_queue(config):
    scenes, seeds = config['scenarios'], config['seeds']
    primary, first = scenes[0], seeds[0]
    queue = [(primary, first, arm) for arm in CHEAP_ARMS + LLM_ARMS]
    queue += [(scene, seed, arm) for seed in seeds for scene in scenes
              for arm in CHEAP_ARMS if not (scene == primary and seed == first)]
    queue += [(scene, seed, arm) for seed in seeds for scene in scenes
              for arm in LLM_ARMS if not (scene == primary and seed == first)]
    return queue

def estimated_seconds(scene, arm, history):
    values = history.get((scene, arm), [])
    if values:
        return max(90, max(values) * 1.15 + 30)
    return 420 if arm in CHEAP_ARMS else 65 * 60

class Campaign:
    def __init__(self, out, deadline):
        self.out, self.deadline = out.resolve(), deadline
        self.config = load(self.out / 'toolkit_config.json')
        self.status = {'pid': os.getpid(), 'started_utc': now(), 'deadline': deadline.isoformat(),
                       'phase': 'preflight', 'current': None, 'completed': [],
                       'deferred': [], 'failed': [], 'stop_reason': None}
        self.history = {}
        for p in (EVAL / '_w1_runs').glob('*_n3*.json'):
            try:
                r = load(p)
                if r.get('aborted') is None and r.get('terminal_result') is not None:
                    key = (r.get('scenario'), r.get('planner'))
                    self.history.setdefault(key, []).append(float(r['elapsed_seconds']))
            except (ValueError, KeyError, TypeError):
                continue
        self.write_status()

    def remaining(self):
        return (self.deadline - datetime.now(timezone.utc)).total_seconds()

    def write_status(self):
        self.status.update(updated_utc=now(), remaining_seconds=round(self.remaining(), 1))
        save(self.out / 'night_status.json', self.status)

    def command(self, name, argv, timeout=None):
        log_path = self.out / (name + '_controller.log')
        if log_path.exists():
            raise FileExistsError(f'Refusing to replace attempt log: {log_path}')
        self.status['current'] = name
        self.write_status()
        env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1',
                   PYTHONDONTWRITEBYTECODE='1', ROLEC_LLM_BASE_URL=self.config['base_url'],
                   ROLEC_LLM_MODEL=self.config['model'])
        started = time.monotonic()
        with log_path.open('x', encoding='utf-8') as stream:
            child = subprocess.Popen([sys.executable, '-u', *map(str, argv)], cwd=PROJECT,
                                     env=env, stdout=stream, stderr=subprocess.STDOUT,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.status['child_pid'] = child.pid
            while child.poll() is None:
                if self.remaining() <= 30 or (timeout and time.monotonic() - started > timeout):
                    child.terminate()
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()
                    self.status['failed'].append({'name': name, 'reason': 'deadline_or_safety_timeout',
                                                  'eligible_for_main_score': False})
                    save(self.out / (name + '_budget_stop.json'), self.status['failed'][-1])
                    self.write_status()
                    return False
                self.write_status()
                time.sleep(2)
        self.status.pop('child_pid', None)
        if child.returncode:
            self.status['failed'].append({'name': name, 'exit_code': child.returncode, 'log': str(log_path)})
            self.write_status()
            return False
        return True

    def gates(self):
        from p0_6_audit import inventory
        inventory(self.out)
        if not self.command('scorecard_tests', [EVAL / '_w1_test_strategy_metrics.py'], 120):
            return False
        tests = (self.out / 'scorecard_tests_controller.log').read_text(encoding='utf-8')
        (self.out / 'strategy_metrics_tests.txt').write_text(tests, encoding='utf-8')
        for scene, ticks, arms in [('IE-10-DUAL-AXIS-PINCER', 1, CHEAP_ARMS + LLM_ARMS),
                                    ('IE-11-DECOY-SCREEN', 11, LLM_ARMS)]:
            for arm in arms:
                ident = f"{scene.lower().replace('-', '_')}_{arm}_s9901_t{ticks}"
                manifest = self.out / (ident + '_manifest.json')
                if manifest.exists():
                    if not load(manifest).get('interface_ok'):
                        return False
                    continue
                if not self.command(ident + '_smoke', [KIT / 'p0_6_smoke.py', '--output-dir', self.out,
                       '--scenario', scene, '--arm', arm, '--seed', 9901, '--ticks', ticks], 420):
                    return False
        if not self.command('contact_audit', [KIT / 'p0_6_contacts.py', '--output',
                   self.out / 'ie11_contact_trace.json', '--ticks', 170], 600):
            return False
        for label in ('A', 'B'):
            if not self.command('replay' + label, [KIT / 'p0_6_smoke.py', '--output-dir', self.out,
                     '--scenario', 'IE-10-DUAL-AXIS-PINCER', '--arm', 'rule', '--seed', 9901,
                     '--ticks', 20, '--tag', 'replay' + label], 180):
                return False
        if not self.command('p0_summary', [KIT / 'p0_6_summarize.py', '--output-dir', self.out], 180):
            return False
        gates = load(self.out / 'p0_summary.json')
        required = ('endpoint_model_gate', 'scorecard_unit_test_gate', 'ie10_six_arms_interface_ok',
                    'ie11_three_llm_arms_interface_ok', 'ie11_future_timeline_withheld')
        good = all(gates.get(k) for k in required) and gates['file_integrity']['all_match']
        good = good and gates['baseline_replay']['status'] == 'match'
        self.status['gate_summary'] = {k: gates.get(k) for k in required}
        self.status['d1_no_hidden_role_truth_gate'] = gates['p0_d1_no_hidden_role_truth_gate']
        self.status['d1_scope'] = ('unlabeled interpretation still needs statistics'
            if gates['p0_d1_no_hidden_role_truth_gate'] else 'public-information use only; no autonomous unlabeled deception claim')
        self.write_status()
        return good

    def analyze(self, label):
        return self.command('analysis_' + label, [KIT / 'p1_6_analyze.py', '--output-dir', self.out], 180)

    def run(self):
        plan_path = self.out / 'night_budget_plan.json'
        if plan_path.exists():
            raise FileExistsError('This night controller is single-launch; do not overwrite an earlier run.')
        queue = make_queue(self.config)
        save(plan_path, {'deadline': self.deadline.isoformat(), 'budget_origin': '2026-09-28T22:05:23+08:00',
            'priority': 'Complete IE10 seed601 six-arm pair first; then cheap cells, then more LLM pairs.',
            'queue': [{'scenario': s, 'seed': n, 'arm': a} for s, n, a in queue],
            'hashes': {p.name: sha(p) for p in KIT.glob('*.py')},
            'toolkit_config_sha256': sha(self.out / 'toolkit_config.json'),
            'main_score_rule': 'Only natural terminal with complete score and hash-verified records.',
            'deadline_rule': 'Do not admit a job above remaining estimated budget; terminate unfinished child near deadline and never score it.',
            'concurrency': 'one queued episode; one already started rule episode may overlap preflight only',
            'dependencies': 'Hi-fi inference uses existing NumPy stack; missing Torch/SciPy means grid/training not enabled.'})
        if not self.gates():
            self.status.update(phase='stopped', stop_reason='P0_gate_failed')
            self.write_status()
            return 2
        self.status['phase'] = 'episodes'
        for scene, seed, arm in queue:
            ident = f"{scene.lower().replace('-', '_')}_{arm}_s{seed}_a1"
            path = self.out / (ident + '_manifest.json')
            if path.exists():
                while load(path).get('status') == 'running' and self.remaining() > 120:
                    self.status['current'] = ident + ' (existing process)'
                    self.write_status()
                    time.sleep(5)
                manifest = load(path)
                if not manifest.get('eligible_for_main_score'):
                    self.status['failed'].append({'name': ident, 'reason': 'existing_attempt_not_eligible'})
                    continue
            else:
                estimate = estimated_seconds(scene, arm, self.history)
                if self.remaining() < estimate + 180:
                    self.status['deferred'].append({'run_id': ident, 'estimated_seconds': round(estimate)})
                    self.write_status()
                    continue
                if not self.command(ident, [KIT / 'p1_6_run.py', '--output-dir', self.out,
                    '--scenario', scene, '--arm', arm, '--seed', seed, '--max-ticks', self.config['max_ticks'],
                    '--goal-granularity', self.config['goal_granularity']]):
                    self.status.update(phase='stopped', stop_reason='episode_failed_or_deadline')
                    break
                manifest = load(path)
                if not manifest.get('eligible_for_main_score'):
                    self.status['failed'].append({'name': ident, 'reason': 'not_naturally_terminal'})
                    continue
            report = load(self.out / (ident + '.json'))
            self.history.setdefault((scene, arm), []).append(float(report['elapsed_seconds']))
            self.status['completed'].append({'run_id': ident, 'score': manifest['defender_score'],
                                             'seconds': report['elapsed_seconds'], 'ticks': report['ticks_run']})
            self.write_status()
            if self.remaining() > 120:
                self.analyze(str(len(self.status['completed'])))
        if self.remaining() > 60:
            self.analyze('final')
        if self.status['phase'] != 'stopped':
            self.status.update(phase='finished', stop_reason='budget_admission_limit' if self.status['deferred'] else 'queue_complete')
        self.status['current'] = None
        self.write_status()
        return 0

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--deadline', required=True, help='Timezone-aware ISO date/time')
    args = parser.parse_args()
    deadline = datetime.fromisoformat(args.deadline)
    if deadline.tzinfo is None or deadline <= datetime.now(timezone.utc):
        parser.error('Deadline must be a future timezone-aware time')
    if (args.output_dir / 'night_budget_plan.json').exists():
        parser.error('Existing controller plan: inspect it instead of starting duplicate jobs')
    c = Campaign(args.output_dir, deadline)
    try:
        return c.run()
    except Exception as exc:
        c.status.update(phase='stopped', stop_reason=f'{type(exc).__name__}: {exc}')
        c.write_status()
        raise

if __name__ == '__main__':
    raise SystemExit(main())
