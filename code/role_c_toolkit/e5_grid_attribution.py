"""E5 grid arm: natural LLM+rule failures with replay-gated reference attribution.

Each seed runs the frozen ``grid_rolec6_counterfactual.py`` (LLM planner + heuristic
GOAI executor; original, own-goal self-replay gate, reference executor with frozen
goals, reference planner, full reference) in its own process. Selection rule fixed
before any run: V(original) < threshold; the first ``--failures`` qualifying seeds in
seed order enter E5. Labels use the same pre-registered rule as the hifi arm.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from hifi_record_campaign import label_attribution  # noqa: E402
from remote_seed_campaign import load, save, sha  # noqa: E402


def run_seed(args, seed, endpoint):
    out = args.output / f'seed-{seed}'
    if (out / 'summary.json').exists() or (out / 'failed.json').exists():
        return seed
    command = [sys.executable, '-B', str(HERE / 'grid_rolec6_counterfactual.py'), '--source', str(args.source),
               '--output', str(out), '--seed', str(seed), '--difficulty', 'medium', '--task-mode', 'continuous',
               '--planner', 'llm', '--executor', 'heuristic', '--base-url', endpoint, '--model', args.model,
               '--interval', '10']
    env = os.environ.copy(); env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                                        MPLBACKEND='Agg')
    with (args.output / f'seed-{seed}.log').open('ab') as log:
        subprocess.run(command, cwd=str(HERE), env=env, stdin=subprocess.DEVNULL, stdout=log,
                       stderr=subprocess.STDOUT)
    return seed


def collect(args):
    rows = []
    for seed in args.seeds:
        out = args.output / f'seed-{seed}'
        if (out / 'summary.json').exists():
            s = load(out / 'summary.json')
            v0 = s['reports']['original']['V']
            row = {'seed': seed, 'V0': v0, 'replay_gate': s['self_replay_gate'],
                   'reference_scores': {k: v['V'] for k, v in s['reports'].items()},
                   'dP': s['reference_improvement_planning'], 'dE': s['reference_improvement_execution'],
                   'dI': s['reference_nonadditivity'], 'summary_sha256': sha(out / 'summary.json')}
            row['failure'] = v0 < args.threshold
            row['machine_label'] = label_attribution(args.rule, row['dP'], row['dE'], row['dI']) \
                if row['failure'] else None
        elif (out / 'failed.json').exists():
            row = {'seed': seed, 'status': 'failed', 'reason': load(out / 'failed.json').get('reason'),
                   'failure': None}
        else:
            row = {'seed': seed, 'status': 'not_run', 'failure': None}
        rows.append(row)
    failures = [r for r in rows if r.get('failure')]
    return {'schema': 'e5-grid-natural-failures@1', 'updated_utc': datetime.now(timezone.utc).isoformat(),
            'config': {'difficulty': 'medium', 'task_mode': 'continuous', 'planner': 'llm',
                       'executor': 'heuristic (GOAI rule)', 'interval': 10, 'model': args.model,
                       'threshold_V_below': args.threshold, 'failures_wanted': args.failures,
                       'label_rule': args.rule, 'seeds': args.seeds},
            'seeds': rows, 'selected_failures': failures[:args.failures],
            'enough_failures': len(failures) >= args.failures,
            'limits': ['grid reference components are archived oracle planner/executor, not certified oracles']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', type=int, nargs='+', required=True)
    parser.add_argument('--endpoint', action='append', required=True)
    parser.add_argument('--model', default='Qwen3.8-27B')
    parser.add_argument('--parallel', type=int, default=4)
    parser.add_argument('--threshold', type=float, default=0.6)
    parser.add_argument('--failures', type=int, default=3)
    args = parser.parse_args()
    args.rule = {'min_effect': 0.05, 'tie_margin': 0.05}
    args.output.mkdir(parents=True, exist_ok=True)
    plan = args.output / 'plan.json'
    frozen = {'seeds': args.seeds, 'threshold': args.threshold, 'failures': args.failures, 'rule': args.rule,
              'runner_sha256': sha(HERE / 'grid_rolec6_counterfactual.py'), 'driver_sha256': sha(Path(__file__))}
    if plan.exists() and load(plan) != frozen:
        raise RuntimeError('Plan differs from the frozen one; use a new output directory')
    save(plan, frozen)
    with ThreadPoolExecutor(args.parallel) as pool:
        futures = [pool.submit(run_seed, args, seed, args.endpoint[i % len(args.endpoint)])
                   for i, seed in enumerate(args.seeds)]
        for future in futures:
            future.result()
            save(args.output / 'e5_grid_summary.json', collect(args))
    result = collect(args); save(args.output / 'e5_grid_summary.json', result)
    print(json.dumps({'failures': len([r for r in result['seeds'] if r.get('failure')]),
                      'enough': result['enough_failures']}))


if __name__ == '__main__':
    main()
