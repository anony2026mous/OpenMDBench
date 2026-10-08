"""Auditable engineering-only E1 recovery; never change frozen experiment inputs."""
import argparse
import concurrent.futures as cf
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temp.replace(path)


def file_inventory(folder):
    return {str(p.relative_to(folder)): digest(p) for p in sorted(folder.rglob('*')) if p.is_file()}


def is_step_timeout(report):
    aborted = report.get('aborted')
    if isinstance(aborted, dict):
        return aborted.get('reason') == 'step_timeout'
    return isinstance(aborted, str) and aborted.startswith('step_timeout at tick ')


def verify(code, out):
    protocol = read(out / 'protocol.json')
    for name, sha in protocol['script_hashes'].items():
        if digest(code / name) != sha:
            raise ValueError(f'Frozen source changed: {name}')
    if digest(out / 'variants.json') != protocol['variants_sha']:
        raise ValueError('Frozen variant manifest changed')
    return protocol


def classify_completion(folder, row, protocol_sha, outcome):
    completion = read(folder / 'completion.json')
    config = completion['config']
    if config['protocol_sha'] != protocol_sha or config['scenario'] != row['public_id']:
        raise ValueError(f'Completion protocol mismatch: {folder}')
    expected = f"{config['arm']}-{config['dose']}-g{int(config['greedy'])}"
    if folder.name != f"seed-{config['seed']}" or folder.parent.name != expected or folder.parent.parent.name != config['scenario']:
        raise ValueError('Completion path mismatch')
    report_path = folder / 'report.json'
    if not report_path.exists() or digest(report_path) != completion['report_sha']:
        raise ValueError(f'Missing/changed report: {folder}')
    report = read(report_path)
    if completion['exit_code'] == 0:
        # All scientifically valid scores, wins AND losses, are retained.
        return 'valid', outcome(report_path, row)
    if not is_step_timeout(report):
        raise ValueError(f'Failure needs separate review, not automatic retry: {folder}')
    return 'step_timeout', None


def analysis(out, recovery, campaign):
    status = read(out / 'status.json')
    result = {'status': status, 'protocol_sha': digest(out / 'protocol.json'),
              'scope': 'E1 count/headroom; no automatic all-gates theorem certification',
              'attempt_audit': str(recovery), 'generated_at': time.time()}
    if (out / 'calibration_all_analysis.json').exists():
        result['calibration_conditions'] = read(out / 'calibration_all_analysis.json')
    if (out / 'gates.json').exists():
        result['gates'] = read(out / 'gates.json')
    if status['state'] == 'confirmation-complete':
        protocol = read(out / 'protocol.json')
        seeds = protocol['confirmation_seeds']
        comparisons = []
        for row in read(out / 'frozen_tiers.json'):
            vals = {}
            for arm in ['rule', 'rl', 'pure-llm', 'llm', 'llm-rl']:
                vals[arm] = [campaign.outcome(out / 'confirmation' / row['public_id'] /
                             f'{arm}-strong-g0' / f'seed-{s}' / 'report.json', row) for s in seeds]
            best = min(['rule', 'rl', 'pure-llm'], key=lambda a: (-sum(x['V'] for x in vals[a]), a))
            fixed = row['arm']
            comparisons.append({'family': row['family'], 'scenario': row['public_id'],
                'target_SR': row['target_SR'], 'count': row['count'], 'calibration_selected_pure': fixed,
                'confirmation_best_mean_pure': best,
                'arms': {arm: {'V': campaign.estimate([x['V'] for x in cases]),
                               'SR': campaign.estimate([x['SR'] for x in cases]),
                               'all_wave_complete': all(x['eligible'] for x in cases)} for arm, cases in vals.items()},
                'paired_gain_against_calibration_selected_pure': {
                    arm: campaign.estimate([x['V'] - y['V'] for x, y in zip(vals[arm], vals[fixed])])
                    for arm in ['llm', 'llm-rl']},
                'descriptive_gain_against_confirmation_best_pure': {
                    arm: sum(x['V'] - y['V'] for x, y in zip(vals[arm], vals[best])) / len(seeds)
                    for arm in ['llm', 'llm-rl']},
                'inference_note': 'Paired CIs use independently calibration-selected fixed comparator; confirmation maximum is descriptive, without selection-adjusted CI.'})
        result['confirmation_comparisons'] = comparisons
    write(recovery / 'analysis' / 'E1阶段统计_v1.json', result)
    lines = ['# E1 续跑阶段报告', '', f"当前状态：`{status['state']}`。", '',
        '冻结代码、场景、seed、模型参数及门禁保持不变。仅将 LLM 对局调度从8路降至2路；CPU-only阶段仍使用原24路。', '',
        '旧有效对局（包括失败终局）全部保留。仅对明确的 step_timeout 工程中止进行有限补跑；每局接受首次有效补跑，不按得分择优。原中止记录及每次重试均留存。', '',
        '工程恢复不等于门禁通过。若预设压力菜单无法覆盖40%、60%、80%目标，按原协议报告不可行，不更改目标或选种子。D1未获高保真认证，不能据此声称全部理论条件已满足。', '']
    if status['state'] == 'count-menu-infeasible':
        lines += [f"当前菜单不可行：{status['family']}，目标SR={status['target']}，最近条件count={status['closest_count']}，SR={status['closest_SR']}，纯架构={status['closest_best_arm']}。正式确认未启动。", '']
    for row in result.get('confirmation_comparisons', []):
        lines += [f"## {row['scenario']} / 目标SR={row['target_SR']}", '',
                  '|架构|平均V|SR|完整波次|', '|---|---:|---:|---|']
        for arm, val in row['arms'].items():
            lines.append(f"|{arm}|{val['V']['mean']:.6f}|{val['SR']['mean']:.3f}|{val['all_wave_complete']}|")
        lines += ['', f"独立校准选定对照：{row['calibration_selected_pure']}。确认集最高平均分纯架构：{row['confirmation_best_mean_pure']}（仅描述）。", '']
        for arm, val in row['paired_gain_against_calibration_selected_pure'].items():
            lines += [f"{arm}相对独立校准对照的配对收益：{val['mean']:.6f}，seed bootstrap 95% CI={val['ci95']}。", '']
    (recovery / 'reports').mkdir(exist_ok=True)
    (recovery / 'reports' / 'E1续跑阶段报告_v1.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--code', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--recovery', type=Path, required=True)
    p.add_argument('--audit-only', action='store_true')
    args = p.parse_args()
    code, out, recovery, repo = [x.resolve() for x in (args.code, args.output, args.recovery, args.repo)]
    sys.path.insert(0, str(code))
    campaign = importlib.import_module('count_campaign')
    protocol = verify(code, out)
    sha = digest(out / 'protocol.json')
    manifest = read(out / 'variants.json')
    rows = {r['public_id']: r for r in manifest['variants']}
    if args.audit_only:
        counts = {}
        for f in sorted(out.glob('*/*/*/seed-*/completion.json')):
            kind, _ = classify_completion(f.parent, rows[read(f)['config']['scenario']], sha, campaign.outcome)
            counts[kind] = counts.get(kind, 0) + 1
        print(json.dumps({'completion_counts': counts, 'frozen_sources_verified': True}), flush=True)
        return
    import fcntl
    recovery.mkdir(parents=True, exist_ok=True)
    supervisor_lock = (recovery / 'supervisor.lock').open('a')
    fcntl.flock(supervisor_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if not (recovery / 'manifest.json').exists():
        write(recovery / 'manifest.json', {'created_at': time.time(), 'pid': os.getpid(), 'original_protocol_sha': sha,
            'original_source_hashes': protocol['script_hashes'], 'recovery_code_sha': digest(__file__),
            'LLM_episode_workers': 2, 'CPU_only_workers': 24, 'max_engineering_retries_per_case': 2,
            'retry_policy': 'step_timeout only; first valid attempt, regardless of outcome',
            'scientific_inputs_changed': False, 'original_timeouts_changed': False})
    elif read(recovery / 'manifest.json')['original_protocol_sha'] != sha:
        raise ValueError('Recovery protocol mismatch')
    # Override only runner scheduling in memory. Frozen source bytes are untouched.
    original_executor = cf.ThreadPoolExecutor
    class CappedExecutor(original_executor):
        def __init__(self, max_workers=None, *a, **kw):
            super().__init__(2 if max_workers == 8 else max_workers, *a, **kw)
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               TI_CPU_MAX_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg', MPLCONFIGDIR=str(out / 'mpl'))
    progress_lock = threading.Lock()
    try:
        for cycle in range(4):
            lock = (out / 'campaign.lock').open('a')
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                verify(code, out)
                campaign.prepare(repo, out)
                failures = []
                valid = 0
                for f in sorted(out.glob('*/*/*/seed-*/completion.json')):
                    config = read(f)['config']
                    row = rows[config['scenario']]
                    kind, _ = classify_completion(f.parent, row, sha, campaign.outcome)
                    if kind == 'valid':
                        valid += 1
                    else:
                        failures.append((f.parent, config, row))
                snapshot = recovery / 'snapshots' / f'cycle-{cycle:02d}'
                snapshot.mkdir(parents=True, exist_ok=False)
                for f in [out / 'status.json', out / 'progress.json', *out.glob('*_jobs.json')]:
                    if f.exists(): shutil.copy2(f, snapshot / f.name)
                write(snapshot / 'inventory.json', {'valid_cases': valid,
                    'engineering_failures': [{'folder': str(f), 'config': c, 'file_hashes': file_inventory(f)} for f, c, r in failures]})
                write(recovery / 'status.json', {'state': 'repairing', 'cycle': cycle, 'valid_cases': valid,
                    'failures': len(failures), 'repaired': 0, 'pid': os.getpid(), 'updated_at': time.time()})
                repaired = []
                def repair(job):
                    folder, config, row = job
                    relative = folder.relative_to(out)
                    old_hashes = file_inventory(folder)
                    base = recovery / 'attempts' / relative
                    base.mkdir(parents=True, exist_ok=True)
                    for attempt in range(1, 3):
                        trial = base / f'try-{attempt:02d}'
                        if trial.exists():
                            # Never silently overwrite or reinterpret an old retry.
                            continue
                        trial.mkdir()
                        cmd = [sys.executable, '-B', str(code / 'episode_adapter.py'), '--repo', str(repo),
                            '--engine', manifest['engine'], '--scenario', config['scenario'], '--seed', str(config['seed']),
                            '--arm', config['arm'], '--dose', config['dose'], '--output', str(trial),
                            '--endpoint', protocol['LLM']['endpoints'][config['seed'] % 2]]
                        if config['greedy']: cmd.append('--greedy')
                        start = time.time()
                        write(trial / 'retry_manifest.json', {'original_folder': str(folder), 'command': cmd,
                            'original_file_hashes': old_hashes, 'started_at': start, 'attempt': attempt})
                        try:
                            with (trial / 'stdout.log').open('w') as log:
                                exit_code = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=7200).returncode
                        except subprocess.TimeoutExpired:
                            write(trial / 'retry_failure.json', {'reason': 'process_timeout', 'seconds': 7200})
                            continue
                        completion = {'config': config, 'exit_code': exit_code, 'elapsed_seconds': time.time() - start,
                                      'report_sha': digest(trial / 'report.json') if (trial / 'report.json').exists() else None}
                        write(trial / 'completion.json', completion)
                        if exit_code:
                            if not (trial / 'report.json').exists() or not is_step_timeout(read(trial / 'report.json')):
                                raise RuntimeError(f'New failure requires review: {trial}')
                            continue
                        campaign.outcome(trial / 'report.json', row)
                        archive = recovery / 'original-failures' / relative
                        archive.parent.mkdir(parents=True, exist_ok=True)
                        if archive.exists() or file_inventory(folder) != old_hashes:
                            raise ValueError('Original changed or archive exists; no promotion')
                        folder.rename(archive)
                        try:
                            trial.rename(folder)
                        except BaseException:
                            archive.rename(folder)
                            raise
                        write(base / 'promotion.json', {'original_archived_at': str(archive), 'accepted_attempt': attempt,
                             'accepted_folder': str(folder), 'report_sha': completion['report_sha'], 'promoted_at': time.time()})
                        with progress_lock:
                            repaired.append(str(folder))
                            write(recovery / 'status.json', {'state': 'repairing', 'cycle': cycle, 'failures': len(failures),
                                 'repaired': len(repaired), 'valid_cases_before': valid, 'pid': os.getpid(), 'updated_at': time.time()})
                        return
                    raise RuntimeError(f'Bounded retries exhausted: {folder}')
                with original_executor(max_workers=2) as pool:
                    list(pool.map(repair, failures))
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
                lock.close()
            verify(code, out)
            cf.ThreadPoolExecutor = CappedExecutor
            sys.argv = [str(code / 'count_campaign.py'), '--repo', str(repo), '--output', str(out), '--workers', '24']
            try:
                campaign.main()
            except RuntimeError:
                if read(out / 'status.json').get('state') == 'engineering-review-required':
                    continue
                raise
            finally:
                cf.ThreadPoolExecutor = original_executor
            analysis(out, recovery, campaign)
            write(recovery / 'status.json', {'state': 'finished', 'campaign_status': read(out / 'status.json'),
                  'finished_at': time.time(), 'pid': os.getpid()})
            return
        raise RuntimeError('Recovery cycle limit reached; manual review required')
    except BaseException as exc:
        write(recovery / 'status.json', {'state': 'review-required', 'error': repr(exc), 'updated_at': time.time(), 'pid': os.getpid()})
        raise
    finally:
        cf.ThreadPoolExecutor = original_executor


if __name__ == '__main__':
    main()
