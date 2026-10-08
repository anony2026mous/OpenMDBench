"""Frozen calibration -> independent confirmation; never selects hybrid outcomes."""
import argparse
import concurrent.futures as futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from common import read, write, digest, estimate
from e1_variants import prepare


def outcomes(report):
    if report.get('aborted'):
        raise ValueError('Aborted episode is not an outcome')
    card = report['strategy_scorecard']
    state = card['terminal']['state']
    if state not in ('defender_success', 'attacker_success', 'intruder_success', 'draw'):
        raise ValueError(f'Unclassified terminal: {state}')
    return int(state == 'defender_success'), float(card['defender_score'])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--workers', type=int, default=32)
    a = p.parse_args()
    a.repo, a.output = a.repo.resolve(), a.output.resolve()
    a.output.mkdir(parents=True, exist_ok=True)
    # flock closes on interruption; no stale-file lock deletion necessary.
    import fcntl
    lock = (a.output / 'campaign.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    m = prepare(a.repo, a.output)
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               MKL_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg',
               MPLCONFIGDIR=str(a.output / 'mpl'))
    script = Path(__file__).with_name('e1_trial.py')
    frozen = {'variant_manifest_sha256': digest(a.output / 'variant_manifest.json'),
              'script_hashes': {q.name: digest(q) for q in [script, Path(__file__), Path(__file__).with_name('common.py')]},
              'weights': {name: digest(a.repo / 'openmd/code/eval/_w1_runs/rl' / name)
                          for name in ['theta_rl_legacy2.npz', 'theta_arm5_v12.npz']},
              'workers': a.workers, 'endpoints': ['http://127.0.0.1:8101/v1', 'http://127.0.0.1:8102/v1'],
              'calibration_seeds': m['calibration_seeds'], 'confirmation_seeds': m['confirmation_seeds'],
              'selection': 'one fixed pure arm per family, maximize mean calibration SR across all delays, tie mean V, tie lexical arm',
              'stop_if_rule_all_wins': 'No larger calibration SR is possible for any pure arm; no target tier can be certified',
              'treatment_validity': 'All scheduled intruders must enter world before terminal; if any seed misses a wave, entire timing setting is ineligible, all records retained',
              'targets': m['targets'], 'tolerance': m['target_tolerance'],
              'temperature': 0, 'thinking': False, 'plan_interval': 10,
              'decision_interval': 5, 'max_ticks': 1800, 'briefing': 'withheld'}
    freeze_file = a.output / 'protocol.json'
    if freeze_file.exists() and read(freeze_file) != frozen:
        raise ValueError('Frozen protocol changed; resume rejected')
    write(freeze_file, frozen)
    progress = {'started_at': time.time(), 'phase': 'calibration-rule', 'done': 0, 'total': 0}

    def batch(jobs, phase):
        progress.update(phase=phase, done=0, total=len(jobs))
        write(a.output / 'progress.json', progress)

        def run(job):
            row, seed, arm = job
            out = a.output / phase / row['public_id'] / arm / f'seed-{seed}'
            config = {'variant': row['public_id'], 'seed': seed, 'arm': arm,
                      'protocol_sha256': digest(freeze_file)}
            if (out / 'completion.json').exists():
                old = read(out / 'completion.json')
                if old['config'] == config and old['exit_code'] == 0 and digest(out / 'report.json') == old['report_sha256']:
                    outcomes(read(out / 'report.json'))
                    return {'job': config, 'output': str(out), 'reused': True}
                raise ValueError(f'Incomplete/changed episode retained, not overwritten: {out}')
            if out.exists():
                raise ValueError(f'Interrupted episode retained; inspect before explicit retry: {out}')
            out.mkdir(parents=True)
            cmd = [sys.executable, '-B', str(script), '--repo', str(a.repo), '--engine', m['engine'],
                   '--scenario', row['public_id'], '--seed', str(seed), '--arm', arm,
                   '--output', str(out), '--endpoint', frozen['endpoints'][seed % 2]]
            start = time.time()
            with (out / 'stdout.log').open('w') as log:
                try:
                    result = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=7200)
                    code = result.returncode
                except subprocess.TimeoutExpired:
                    code = -99
            record = {'config': config, 'exit_code': code, 'elapsed_s': time.time()-start,
                      'report_sha256': digest(out / 'report.json') if (out / 'report.json').exists() else None}
            write(out / 'completion.json', record)
            if code != 0:
                return {'job': config, 'output': str(out), 'error': f'exit {code}'}
            try:
                outcomes(read(out / 'report.json'))
            except Exception as error:
                return {'job': config, 'output': str(out), 'error': str(error)}
            return {'job': config, 'output': str(out), 'elapsed_s': record['elapsed_s']}

        completed = []
        with futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
            for future in futures.as_completed([pool.submit(run, j) for j in jobs]):
                try:
                    completed.append(future.result())
                except Exception as error:
                    completed.append({'error': repr(error)})
                progress['done'] += 1
                progress['last_completed_at'] = time.time()
                write(a.output / 'progress.json', progress)
                write(a.output / f'{phase}_jobs.json', completed)
                print(json.dumps(progress), flush=True)
        if any('error' in r for r in completed):
            write(a.output / 'status.json', {'state': 'engineering-gate-failed', 'phase': phase, 'jobs': completed})
            raise RuntimeError('Engineering failures retained; do not analyze as scores')
        return completed

    seeds = m['calibration_seeds']
    jobs = [(row, s, 'rule') for row in m['variants'] for s in seeds]
    batch(jobs, 'calibration-rule')

    def table(arm, phase, rows):
        answer = []
        for row in rows:
            cases = [outcomes(read(a.output / phase / row['public_id'] / arm / f'seed-{s}' / 'report.json')) for s in seeds]
            answer.append({**row, 'arm': arm, 'SR': estimate([c[0] for c in cases]),
                           'V': estimate([c[1] for c in cases]), 'per_seed': dict(zip(map(str,seeds), cases))})
        return answer

    rules = table('rule', 'calibration-rule', m['variants'])
    # Moving a wave beyond an early native terminal is NOT legitimate pressure calibration.
    # Validate whole settings, never delete individual unfavorable seeds.
    import yaml
    for row in rules:
        scene=yaml.safe_load((Path(m['engine'])/'scenarios/formal'/row['package']/'scenario.yaml').read_text())['scenario']
        spawns=[e for e in scene['events'] if e['event_type']=='spawn']
        inventory=[*scene['entities'], *(e['payload']['entity'] for e in spawns)]
        expected=sum(e['faction_id']=='coalition.intruder' for e in inventory)
        latest=max([0,*[e['trigger']['tick'] for e in spawns]])
        invalid=[]
        for seed in seeds:
            card=read(a.output/'calibration-rule'/row['public_id']/'rule'/f'seed-{seed}'/'report.json')['strategy_scorecard']
            actual=sum(v['total'] for v in card['force']['coalition.intruder'].values())
            if actual!=expected or card['terminal']['tick']<latest:
                invalid.append({'seed':seed,'actual_intruders':actual,'expected_intruders':expected,
                                'terminal_tick':card['terminal']['tick'],'latest_spawn':latest})
        row['treatment_eligible']=not invalid
        row['missed_wave_cases']=invalid
    write(a.output / 'calibration_rule_analysis.json', rules)
    saturated = [f for f in sorted({r['family'] for r in rules})
                 if all(r['SR']['mean'] == 1 for r in rules if r['family'] == f and r['treatment_eligible'])]
    if saturated:
        status = {'state': 'authorized-knob-infeasible', 'saturated_families': saturated,
                  'reason': 'Rule wins every calibrated timing; best-pure cannot have SR .4/.6/.8 here. No unauthorized knob added.',
                  'rule_rows': rules, 'confirmation_started': False,
                  'original_source_unchanged': all(digest(a.repo / 'openmd/source-code/source_codes' / n) == sha for n,sha in m['original_source_hashes'].items())}
        write(a.output / 'status.json', status)
        return
    # Only if rule calibration is feasible, spend model/learner budget selecting best-pure.
    eligible_variants=[row for row in m['variants'] if next(r for r in rules if r['public_id']==row['public_id'])['treatment_eligible']]
    additional = [(row, s, arm) for row in eligible_variants for s in seeds for arm in ['rl', 'pure-llm']]
    batch(additional, 'calibration-pure')
    rows = [r for r in rules if r['treatment_eligible']] + [r for arm in ['rl', 'pure-llm'] for r in table(arm, 'calibration-pure', eligible_variants)]
    selected = []
    for family in sorted({r['family'] for r in rows}):
        subset = [r for r in rows if r['family'] == family]
        ranking = sorted(['rule','rl','pure-llm'], key=lambda arm: (
            -sum(r['SR']['mean'] for r in subset if r['arm']==arm),
            -sum(r['V']['mean'] for r in subset if r['arm']==arm), arm))
        candidates = [r for r in subset if r['arm'] == ranking[0]]
        for target in m['targets']:
            best = min(candidates, key=lambda r: (abs(r['SR']['mean']-target), r['delay_ticks']))
            if abs(best['SR']['mean']-target) > m['target_tolerance']:
                write(a.output / 'status.json', {'state': 'authorized-knob-infeasible', 'family': family,
                     'target': target, 'calibration': rows, 'confirmation_started': False})
                return
            selected.append({**best, 'target_SR': target})
    write(a.output / 'frozen_tiers.json', selected)
    confirm = [(row, s, arm) for row in selected for s in m['confirmation_seeds']
               for arm in [row['arm'], 'llm', 'llm-rl']]
    batch(confirm, 'confirmation')
    write(a.output / 'status.json', {'state': 'confirmation-complete', 'n': len(confirm),
                                    'selected': selected, 'analysis_pending': True})


if __name__ == '__main__':
    main()
