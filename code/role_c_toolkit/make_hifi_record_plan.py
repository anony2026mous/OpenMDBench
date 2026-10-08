"""Build a frozen ``hifi-record-campaign@1`` plan from an already verified campaign plan.

Engine pin, runtime packages and policy weights are inherited unchanged from the
reference plan (server-side, verified earlier); only scope, seeds and scheduling
are new. Run on the server inside the snapshot that will execute the campaign.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from remote_seed_campaign import REMOTE_BASE, load, save, sha

HERE = Path(__file__).resolve().parent
SCENARIO_IDS = {
    'IE-01': 'IE-01-SINGLE-TARGET', 'IE-02': 'IE-02-DUAL-THREAT', 'IE-03': 'IE-03-SURFACE-RAID',
    'IE-04': 'IE-04-COMBINED-ARMS', 'IE-05': 'IE-05-MULTI-AXIS', 'IE-06': 'IE-06-DECOY-MIXED',
    'IE-07': 'IE-07-CROSS-DOMAIN', 'IE-08': 'IE-08-ISLAND-STRIKE', 'IE-09': 'IE-09-STAGGERED-WAVES',
    'IE-10': 'IE-10-DUAL-AXIS-PINCER', 'IE-11': 'IE-11-DECOY-SCREEN', 'IE-12': 'IE-12-FOG-ONSET',
    'IE-13': 'IE-13-DEEP-STRIKE', 'IE-14': 'IE-14-SATURATION-THREE-WAVE'}


def build(reference, scenarios, planners, seeds, *, inflight, cpu_jobs, purpose,
          failure_below=None, failures_needed=None, attribution=False,
          step_timeout=60.0, prior_campaigns=()):
    endpoints = [{'name': 'a', 'url': 'http://127.0.0.1:8001/v1'},
                 {'name': 'b', 'url': 'http://127.0.0.1:8002/v1'}]
    manifests = {load(REMOTE_BASE / 'services/qwen' / f'replica-{e["name"]}.json')['model_manifest_sha256']
                 for e in endpoints}
    if len(manifests) != 1:
        raise RuntimeError('Replica model manifests differ')
    p = reference['parameters']
    weights = dict(reference['weight_paths'])
    weights['rule-rl'] = weights['llm-rl']  # reference planner keeps the identical RL executor
    pinned = {path: digest for path, digest in reference['weights_sha256'].items()
              if path in weights.values()}
    cases = []
    for seed in seeds:  # seed-major
        for scenario in scenarios:
            for planner in planners:
                sid = SCENARIO_IDS[scenario]
                cases.append({'id': f'{sid.lower()}__{planner}__s{seed}', 'scenario': sid,
                              'seed': seed, 'planner': planner})
    plan = {
        'schema': 'hifi-record-campaign@1', 'purpose': purpose,
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'reference_plan_sha256': sha(reference['_path']),
        'model': reference['model'], 'model_manifest_sha256': manifests.pop(),
        'endpoints': endpoints, 'max_inflight_per_endpoint': inflight, 'max_cpu_jobs': cpu_jobs,
        'service_requirements': {'--dtype': 'bfloat16', '--tensor-parallel-size': '2',
                                 '--max-model-len': '131072', '--kv-cache-dtype': 'fp8',
                                 '--num-gpu-blocks-override': '296',
                                 '--gpu-memory-utilization': '0.92'},
        'engine_pin': reference['engine_pin'], 'runtime_packages': reference['runtime_packages'],
        'weight_paths': weights, 'weights_sha256': pinned,
        'recorder_sha256': sha(HERE / 'hifi_record_campaign.py'),
        'parameters': {'max_ticks': p['max_ticks'], 'llm_max_tokens': p['llm_max_tokens'],
                       'temperature': p['temperature'], 'briefing': p['llm_briefing'],
                       'plan_interval': p['plan_interval'], 'decision_interval': p['decision_interval'],
                       'goal_granularity': p['hybrid_goal_granularity'],
                       'step_timeout_seconds': step_timeout},
        'prior_campaigns': [str(x) for x in prior_campaigns],
        'episode_wall_watchdog_seconds': reference['episode_wall_watchdog_seconds'],
        'max_job_failures': 3, 'cases': cases,
    }
    if failure_below is not None:
        plan['failure_rule'] = {'planners': ['llm-rl'], 'metric': 'defender_score',
                                'score_below': failure_below}
    if failures_needed is not None:
        plan['stop_rule'] = {'failures_needed': failures_needed,
                             'note': 'After the target is met, seeds already started are completed; '
                                     'no new seed starts. Selection is the first N failures in seed order.'}
    if attribution:
        plan['attribution'] = {
            'enabled': True, 'reference_executor_planner': 'llm',
            'reference_planner_planner': 'rule-rl', 'reference_full_planner': 'rule',
            'label_rule': {'min_effect': 0.05, 'tie_margin': 0.05,
                           'definition': 'dP=V(rule-rl)-V0, dE=V(frozen LLM goals + GOAI rule executor)-V0, '
                                         'dI=V(rule)-V(rule-rl)-V(frozen+GOAI)+V0; label = largest of '
                                         'dP, dE, |dI|; balanced if top two within tie_margin; '
                                         'undetermined if largest < min_effect'},
            'limits': ['Reference components are archived baselines, not certified oracles']}
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scenarios', nargs='+', required=True, choices=sorted(SCENARIO_IDS))
    parser.add_argument('--planners', nargs='+', required=True,
                        choices=['rule', 'llm', 'pure-llm', 'rl', 'llm-rl', 'rule-rl'])
    parser.add_argument('--seeds', nargs='+', type=int, required=True)
    parser.add_argument('--inflight', type=int, default=6)
    parser.add_argument('--cpu-jobs', type=int, default=8)
    parser.add_argument('--purpose', required=True)
    parser.add_argument('--failure-below', type=float)
    parser.add_argument('--failures-needed', type=int)
    parser.add_argument('--attribution', action='store_true')
    parser.add_argument('--step-timeout', type=float, default=60.0,
                        help='Harness deadlock watchdog per tick (includes LLM latency); no effect on outcomes')
    parser.add_argument('--prior-campaign', type=Path, action='append', default=[])
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Plans are immutable; choose a new output path')
    reference = load(args.reference_plan); reference['_path'] = args.reference_plan
    plan = build(reference, args.scenarios, args.planners, args.seeds, inflight=args.inflight,
                 cpu_jobs=args.cpu_jobs, purpose=args.purpose, failure_below=args.failure_below,
                 failures_needed=args.failures_needed, attribution=args.attribution,
                 step_timeout=args.step_timeout, prior_campaigns=args.prior_campaign)
    save(args.output, plan)
    print(json.dumps({'output': str(args.output), 'cases': len(plan['cases']),
                      'recorder_sha256': plan['recorder_sha256']}))


if __name__ == '__main__':
    main()
