"""Audit only the requested four-arm, three-seed pilot; never launch episodes."""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import p1_6_analyze as audit
from p1_6_run import WEIGHTS, verify_freeze
from toolkit_paths import ENGINE, EVAL
from toolkit_seed_first_resume import ARMS, RUNNER, certified, id_for, load, queue_for, sha256


def write(path, text):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding='utf-8')
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    config, prov = load(out / 'toolkit_config.json'), load(out / 'provenance.json')
    if config['seeds'] != [601, 602, 603] or len(config['scenarios']) != 3:
        raise RuntimeError('This audit is scoped to the locked three-seed pilot')
    frozen = load(out / 'night_budget_plan.json')
    assert sha256(RUNNER) == frozen['hashes'][RUNNER.name], 'Runner changed'
    assert sha256(out / 'toolkit_config.json') == frozen['toolkit_config_sha256'], 'Config changed'
    sys.path.insert(0, str(ENGINE))
    sys.path.insert(0, str(EVAL))
    for scene in config['scenarios']:
        verify_freeze(prov, scene)
    audit.BASE_URL, audit.MODEL = config['base_url'], config['model']
    audit.GOAL_GRANULARITY = config['goal_granularity']
    cells, errors, limitations, manifests = [], [], [], {}
    for scene, seed, arm in queue_for(config):
        ident = id_for(scene, arm, seed)
        path = out / (ident + '_manifest.json')
        item = dict(run_id=ident, scenario=scene, seed=seed, arm=arm, status='pending',
                    strict_audit_pass=False, interpretation='not_a_completed_result',
                    defender_score=None, ticks_run=None, elapsed_seconds=None)
        if path.exists():
            try:
                manifest = load(path)
                manifests[ident] = manifest
                if manifest.get('status') == 'running':
                    item['status'] = 'running_unverified'
                else:
                    row, failure = audit.audit_cell(out, prov, scene, arm, seed)
                    role_label_limit = bool(failure and
                        failure.get('reason') == 'ie11_role_truth_in_actual_prompt')
                    if failure and not role_label_limit:
                        raise ValueError(failure)
                    if not certified(out, prov, scene, seed, arm, sha256(RUNNER)):
                        raise ValueError('Execution integrity certification failed')
                    item['strict_audit_pass'] = not bool(failure)
                    item['interpretation'] = ('public_role_labels_only_NOT_unlabeled_deception'
                                              if role_label_limit else 'strict_audit_pass')
                    if role_label_limit:
                        limitations.append(failure)
                    expected = {'scenario': scene, 'seed': seed, 'arm': arm,
                                'plan_interval': config['plan_interval'],
                                'decision_interval': config['decision_interval'],
                                'max_tokens': config['llm_max_tokens'],
                                'temperature': 0.1,
                                'speed_source': 'legacy_tags' if arm in WEIGHTS else None}
                    for key, value in expected.items():
                        if manifest.get(key) != value:
                            raise ValueError(f'{key}: expected {value!r}, got {manifest.get(key)!r}')
                    report = load(out / (ident + '.json'))
                    score = report['strategy_scorecard']
                    if (not manifest.get('natural_terminal') or report.get('error')
                            or manifest.get('defender_score') != score.get('defender_score')
                            or report['ticks_run'] != manifest.get('ticks_run')
                            or score['scenario_horizon']['max_ticks'] != config['max_ticks']):
                        raise ValueError('Manifest/raw report or natural-terminal mismatch')
                    item.update(status='execution_complete', defender_score=score['defender_score'],
                                ticks_run=report['ticks_run'], elapsed_seconds=report['elapsed_seconds'])
            except (ValueError, KeyError, OSError, TypeError) as exc:
                item['status'] = 'invalid'
                errors.append({'run_id': ident, 'reason': str(exc)})
        cells.append(item)
    seed_progress = {}
    for index, seed in enumerate(config['seeds']):
        selected = [c for c in cells if c['seed'] == seed]
        done = sum(c['status'] == 'execution_complete' for c in selected)
        seed_progress[str(seed)] = {'execution_completed': done, 'required': 12,
            'strict_audit_passed': sum(c['status'] == 'execution_complete' and c['strict_audit_pass'] for c in selected),
            'execution_complete': done == 12}
        starts = [manifests[c['run_id']]['created_utc'] for c in selected
                  if c['run_id'] in manifests]
        if index and starts:
            prior = [c for c in cells if c['seed'] in config['seeds'][:index]]
            if not all(c['status'] == 'execution_complete' for c in prior):
                errors.append({'seed': seed, 'reason': 'Later seed started before prior seed complete'})
            else:
                last_finish = max(manifests[c['run_id']]['finished_utc'] for c in prior)
                if min(starts) < last_finish:
                    errors.append({'seed': seed, 'reason': 'Seed execution ordering violated'})
    complete = len(cells) == 36 and all(c['status'] == 'execution_complete' for c in cells) and not errors
    result = {'audited_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'Three scenes x seeds 601,602,603 x llm-rl,llm,rl,pure-llm only',
              'arm_labels': {'llm-rl': 'LLM+RL', 'llm': 'LLM+rules', 'rl': 'Pure RL', 'pure-llm': 'Pure LLM'},
              'expected': 36, 'execution_completed': sum(c['status'] == 'execution_complete' for c in cells),
              'execution_complete': complete, 'strict_audit_complete': complete and not limitations,
              'source_freeze_verified': True, 'limitations': limitations,
              'seed_progress': seed_progress, 'errors': errors, 'cells': cells,
              'note': 'A running manifest is not proof of a live process. Audit processes separately. '
                      'Execution completion does not imply leakage-free scientific validity. '
                      'IE11 role-labelled prompts are excluded by the original strict analyzer; '
                      'per the frozen TONIGHT_PLAN.md they can describe public-information use only, '
                      'NOT autonomous unlabeled deception recognition. No strict gate is changed. '
                      'The original six-arm pilot remains a separate 54-cell design; no old gaps are filled.'}
    target = out / 'four_arm_audit'
    target.mkdir(exist_ok=True)
    write(target / 'summary.json', json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(cells[0]))
    writer.writeheader()
    writer.writerows(cells)
    write(target / 'cells.csv', '\ufeff' + stream.getvalue())
    lines = ['# Four-arm pilot progress', '', 'Snapshot: ' + result['audited_utc'], '',
             '| Seed | Execution complete | Required | Strict audit passed |', '|---|---:|---:|---:|']
    lines += [f"| {seed} | {v['execution_completed']} | {v['required']} | {v['strict_audit_passed']} |"
              for seed, v in seed_progress.items()]
    lines += ['', f"Executed: {result['execution_completed']}/36; execution_complete={complete}; errors={len(errors)}; role-label limitations={len(limitations)}",
              '', result['note']]
    write(target / 'PROGRESS.md', '\n'.join(lines) + '\n')
    print(json.dumps({k: result[k] for k in ['execution_completed', 'expected', 'execution_complete',
                                          'strict_audit_complete', 'seed_progress', 'errors', 'limitations']},
                     ensure_ascii=False))
    return 2 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
