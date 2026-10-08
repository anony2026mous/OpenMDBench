"""E1 v13: calibration -> gates -> portable handoff -> explicit pause.

The original six experiment files and original protocol remain byte-for-byte frozen.
This addendum implements the newly authorized four fixed IE05 counts, not the
infeasible original two-family/three-SR-tier confirmation protocol.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import threading
import time
import zipfile


ASSIGNMENTS = {'device-a': [17, 18], 'device-b': [19, 27]}
PURE = ['rule', 'rl', 'pure-llm']
SCIENTIFIC_FILES = ['count_campaign.py', 'pressure_variants.py', 'episode_adapter.py',
                    'e1_trial.py', 'common.py', 'gate_protocol.json']


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(p, value):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    tmp.replace(p)


def now():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()


def inventory(folder, suffixes=None):
    return {p.relative_to(folder).as_posix(): sha(p) for p in sorted(Path(folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts
            and (suffixes is None or p.suffix in suffixes)}


def load_campaign(code):
    sys.path.insert(0, str(code))
    return importlib.import_module('count_campaign')


def check_inventory(folder, hashes):
    for name, h in hashes.items():
        if sha(Path(folder) / name) != h:
            raise ValueError('Frozen file changed: ' + str(Path(folder) / name))


def selected(stats, counts):
    rows = []
    for count in counts:
        peers = [r for r in stats if r['family'] == 'IE-05-MULTI-AXIS' and r['count'] == count]
        if {r['arm'] for r in peers} != set(PURE) or len(peers) != 3:
            raise ValueError('Incomplete independent calibration at count ' + str(count))
        if not all(r['eligible'] and r['V']['n_seeds'] == 10 and r['SR']['n_seeds'] == 10 for r in peers):
            raise ValueError('Incomplete/wave-ineligible calibration')
        best = min(peers, key=lambda r: (-r['V']['mean'], -r['SR']['mean'], r['arm']))
        rows.append({**best, 'calibration_selected_pure': best['arm'],
                     'all_pure_SR': {r['arm']: r['SR']['mean'] for r in peers},
                     'maximum_pure_SR_sensitivity': max(r['SR']['mean'] for r in peers)})
    return rows


def job_spec(row, seed, arm, dose='strong', greedy=False):
    return {'scenario': row['public_id'], 'seed': seed, 'arm': arm, 'dose': dose, 'greedy': greedy}


def gate_jobs(rows, seeds):
    return [job_spec(r, s, arm, dose) for r in rows for s in seeds
            for arm in ['rule', 'rule-rl'] for dose in ['strong', 'hold']] + [
                job_spec(r, s, 'rule', greedy=True) for r in rows for s in seeds]


def confirmation_jobs(rows, seeds):
    return [job_spec(r, s, arm) for r in rows for s in seeds
            for arm in [r['calibration_selected_pure'], 'llm', 'llm-rl']]


def folder_for(root, j):
    return Path(root) / j['scenario'] / f"{j['arm']}-{j['dose']}-g{int(j['greedy'])}" / f"seed-{j['seed']}"


def completion_config(j, protocol_sha, split_sha):
    return {**j, 'protocol_sha': protocol_sha, 'split_manifest_sha': split_sha}


def checked_case(folder, row, expected, campaign):
    c = read(folder / 'completion.json')
    if c['config'] != expected or c['exit_code'] != 0 or sha(folder / 'report.json') != c['report_sha']:
        raise ValueError('Invalid or modified completion: ' + str(folder))
    value = campaign.outcome(folder / 'report.json', row)
    # Native terminal losses, including endings before all waves, remain valid
    # observations. Eligibility is a gate field, NEVER a score-selection filter.
    return {**expected, 'outcome': value, 'elapsed_seconds': c['elapsed_seconds'],
            'report_sha256': c['report_sha']}


def model_record(folder):
    """Full shard + tokenizer hashes; never trust just a served model alias."""
    names = [p for p in sorted(folder.iterdir()) if p.is_file() and
             (p.suffix == '.safetensors' or p.name in ['config.json', 'generation_config.json',
              'model.safetensors.index.json', 'tokenizer.json', 'tokenizer_config.json',
              'chat_template.jinja', 'merges.txt', 'vocab.json'])]
    if not any(p.suffix == '.safetensors' for p in names):
        raise ValueError('Actual model checkpoint shards required')
    return {'files': {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in names}}


def freeze(a):
    batch = a.batch.resolve()
    batch.mkdir(parents=True, exist_ok=False)
    (batch / 'code').mkdir()
    shutil.copy2(__file__, batch / 'code/e1_split.py')
    code = a.code.resolve()
    source = a.source.resolve()
    p = read(source / 'protocol.json')
    check_inventory(code, p['script_hashes'])
    m = read(source / 'variants.json')
    if sha(source / 'variants.json') != p['variants_sha']:
        raise ValueError('Variant manifest changed')
    check_inventory(a.repo / 'openmd/source-code/source_codes', m['original_hashes'])
    engine = Path(m['engine'])
    relevant = [r for r in m['variants'] if r['family'] == 'IE-05-MULTI-AXIS' and r['count'] in [17, 18, 19, 27]]
    if sorted(r['count'] for r in relevant) != [17, 18, 19, 27]:
        raise ValueError('Frozen four-count menu missing')
    (batch / 'protocol').mkdir()
    shutil.copy2(a.checklist, batch / 'protocol/checklist_v13.md')
    shutil.copy2(source / 'protocol.json', batch / 'protocol/original_protocol.json')
    shutil.copy2(source / 'variants.json', batch / 'protocol/original_variants.json')
    write(batch / 'status.json', {'state': 'freezing-model-identity', 'time': now()})
    model = model_record(a.model_dir.resolve())
    frozen = {'schema': 'E1-v13-split@1', 'frozen_at': now(),
              'checklist_sha256': sha(a.checklist), 'original_protocol_sha256': sha(source / 'protocol.json'),
              'original_variants_sha256': sha(source / 'variants.json'),
              'toolkit_sha256': sha(batch / 'code/e1_split.py'),
              'original_code_hashes': p['script_hashes'],
              'engine_hashes': inventory(engine),
              'native_hashes': m['original_hashes'],
              'eval_python_hashes': inventory(a.repo / 'openmd/code/eval', {'.py'}),
              'weights': p['weights'], 'model_checkpoint': model,
              'model_runtime_required': {'served_name': 'Qwen3.8-27B', 'dtype': 'bfloat16',
                  'KV_cache_dtype': 'fp8', 'temperature': 0, 'enable_thinking': False,
                  'max_tokens': 1024, 'plan_interval': 10, 'decision_interval': 5,
                  'max_ticks': 1800, 'llm_briefing': 'withheld', 'episode_timeout': 7200},
              'fixed_conditions': relevant, 'assignments': ASSIGNMENTS,
              'calibration_seeds': p['calibration_seeds'], 'gate_seeds': p['gate_seeds'],
              'confirmation_seeds': p['confirmation_seeds'],
              'seed_allocation': 'Each condition has ALL 4201-4210 on exactly one owner; no 5+5 seed split. Same seeds across conditions deliberately align the final bootstrap.',
              'gate_screening': {'jobs_per_condition': 50, 'total_jobs': 200,
                  'conditions': [17, 18, 19, 27], 'arms': ['rule strong', 'rule hold', 'rule-rl strong', 'rule-rl hold', 'greedy rule'],
                  'D1_prime': 'greedy V < 0.90 * Rule V AND wave-complete',
                  'D2': 'calibration-selected pure SR in [0.40, 0.85]; confirmation SR separately reported',
                  'D3': 'unchanged frozen d3 + goal/action/physical-state audit + complete waves',
                  'D1': 'not certified for these HF scene families'},
              'confirmation': {'jobs_per_condition': 30, 'total_jobs': 120,
                  'comparator': 'fixed highest-mean-V pure architecture selected ONLY from all-three-pure independent calibration',
                  'not_a_reestimated_confirmation_Vm': True,
                  'condition_order_device_a': [17, 18], 'condition_order_device_b': [19, 27]},
              'stop_after': 'all calibration statistics + all 200 gates + verified handoff export; NO automatic confirmation',
              'scope': 'New v13 partial direction addendum. Original impossible 40/60/80 protocol remains immutable and its infeasibility is retained.',
              'pooling': 'Separate condition/arm tables; within-condition pairing. Only compatible preassigned blocks can join the final condition table; never pool conditions as exchangeable episodes.',
              'hardware_caveat': 'Owner and count are confounded across hosts. Preserve runtimes/model server settings; compare stacks within conditions and disclose possible host-by-treatment effects.',
              'retry_policy': 'step_timeout only, at most 2 total attempts; first valid result, irrespective of score; preserve every failure',
              'selection_provenance': 'counts fixed by v13 checklist, before new hybrid confirmation outcomes'}
    write(batch / 'protocol/split_execution.json', frozen)
    write(batch / 'status.json', {'state': 'frozen-awaiting-calibration', 'time': now(),
                                 'split_manifest_sha256': sha(batch / 'protocol/split_execution.json')})
    print(json.dumps({'batch': str(batch), 'manifest_sha256': sha(batch / 'protocol/split_execution.json')}, ensure_ascii=False))


def process_running(pid):
    p = Path(f'/proc/{pid}/stat')
    if not p.exists():
        return False
    text = p.read_text()
    tail = text[text.rfind(')') + 2:].split()
    return tail[0] != 'Z'


def run_jobs(jobs, rows, root, repo, engine, code, psha, ssha, campaign, endpoints, status_path):
    """CPU24 and endpoint-specific LLM2; entire jobs finish before a phase ends."""
    lock = threading.Lock()
    records, failures = [], []
    lookup = {r['public_id']: r for r in rows}
    env = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               TI_CPU_MAX_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg',
               MPLCONFIGDIR=str(root.parent / 'mpl'))
    def update():
        write(status_path, {'state': 'running', 'phase': root.name, 'time': now(),
                            'done': len(records), 'failed': len(failures), 'total': len(jobs),
                            'scheduler': {'cpu': 24, 'LLM_per_endpoint': 2}})
    def run(j):
        folder = folder_for(root, j)
        expected = completion_config(j, psha, ssha)
        row = lookup[j['scenario']]
        if folder.exists():
            answer = checked_case(folder, row, expected, campaign)
        else:
            attempts = root.parent / 'attempts' / root.name / folder.relative_to(root)
            answer = None
            for attempt in [1, 2]:
                trial = attempts / f'try-{attempt:02d}'
                if trial.exists():
                    if not (trial / 'completion.json').exists():
                        raise ValueError('Interrupted attempt retained for review: ' + str(trial))
                    c = read(trial / 'completion.json')
                    if c['config'] != expected or c['report_sha'] != sha(trial / 'report.json'):
                        raise ValueError('Attempt changed')
                    if c['exit_code'] == 0:
                        checked_case(trial, row, expected, campaign)
                        folder.parent.mkdir(parents=True, exist_ok=True)
                        trial.rename(folder)
                        answer = checked_case(folder, row, expected, campaign)
                        break
                    aborted = read(trial / 'report.json').get('aborted')
                    if not (isinstance(aborted, str) and aborted.startswith('step_timeout at tick ') or
                            isinstance(aborted, dict) and aborted.get('reason') == 'step_timeout'):
                        raise ValueError('Non-engineering failure retained: ' + str(trial))
                    continue
                trial.mkdir(parents=True)
                cmd = [sys.executable, '-B', str(code / 'episode_adapter.py'), '--repo', str(repo),
                       '--engine', str(engine), '--scenario', j['scenario'], '--seed', str(j['seed']),
                       '--arm', j['arm'], '--dose', j['dose'], '--output', str(trial),
                       '--endpoint', endpoints[j['seed'] % 2]]
                if j['greedy']:
                    cmd.append('--greedy')
                started = time.time()
                write(trial / 'attempt_manifest.json', {'started_at': now(), 'command': cmd,
                      'attempt': attempt, 'config': expected})
                with (trial / 'stdout.log').open('w') as log:
                    try:
                        proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
                        exit_code = proc.wait(timeout=7200)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                        write(trial / 'process_timeout.json', {'seconds': 7200})
                        raise RuntimeError('Wall timeout retained for review')
                rp = trial / 'report.json'
                write(trial / 'completion.json', {'config': expected, 'exit_code': exit_code,
                      'elapsed_seconds': time.time() - started, 'report_sha': sha(rp) if rp.exists() else None})
                if exit_code:
                    aborted = read(rp).get('aborted') if rp.exists() else None
                    if not (isinstance(aborted, str) and aborted.startswith('step_timeout at tick ') or
                            isinstance(aborted, dict) and aborted.get('reason') == 'step_timeout'):
                        raise RuntimeError('New failure requires review: ' + str(trial))
                    continue
                checked_case(trial, row, expected, campaign)
                folder.parent.mkdir(parents=True, exist_ok=True)
                trial.rename(folder)
                write(attempts / 'promotion.json', {'accepted_attempt': attempt, 'canonical': str(folder),
                      'report_sha256': sha(folder / 'report.json'), 'policy': 'first valid, never score-selected'})
                answer = checked_case(folder, row, expected, campaign)
                break
            if answer is None:
                raise RuntimeError('Two engineering attempts exhausted')
        with lock:
            records.append(answer)
            update()
        return answer
    update()
    with cf.ThreadPoolExecutor(max_workers=24) as cpu, cf.ThreadPoolExecutor(max_workers=2) as llm0, cf.ThreadPoolExecutor(max_workers=2) as llm1:
        pools = {'cpu': cpu, 0: llm0, 1: llm1}
        fs = [pools['cpu' if j['arm'] in ['rule', 'rl', 'rule-rl'] else j['seed'] % 2].submit(run, j) for j in jobs]
        for f in cf.as_completed(fs):
            try:
                f.result()
            except Exception as error:
                with lock:
                    failures.append(repr(error))
                    update()
    write(root.parent / (root.name + '_jobs.json'), {'records': records, 'errors': failures})
    if failures:
        raise RuntimeError('Failures retained, cannot complete phase: ' + str(failures))
    return records


def calibration(source, code, campaign):
    p = read(source / 'protocol.json')
    m = read(source / 'variants.json')
    stats, cases = [], []
    for row in m['variants']:
        for arm in PURE:
            phase = 'calibration-rule' if arm == 'rule' else 'calibration-pure'
            values = []
            for seed in p['calibration_seeds']:
                j = job_spec(row, seed, arm)
                f = folder_for(source / phase, j)
                expected = {**j, 'protocol_sha': sha(source / 'protocol.json')}
                c = read(f / 'completion.json')
                if c['config'] != expected or c['exit_code'] != 0 or c['report_sha'] != sha(f / 'report.json'):
                    raise ValueError('All 960 valid canonical calibration cases required: ' + str(f))
                val = campaign.outcome(f / 'report.json', row)
                values.append(val)
                cases.append({**j, 'phase': phase, 'value': val, 'report_sha256': c['report_sha'], 'source': str(f)})
            stats.append({**row, 'arm': arm, 'SR': campaign.estimate([v['SR'] for v in values]),
                          'V': campaign.estimate([v['V'] for v in values]),
                          'eligible': all(v['eligible'] for v in values), 'cases': values})
    if len(cases) != 960:
        raise ValueError('Unexpected calibration size')
    return stats, cases


def summarize_gates(rows, records, root, campaign):
    result = []
    for row in rows:
        peers = [r for r in records if r['scenario'] == row['public_id']]
        d3rows = []
        seeds = sorted({r['seed'] for r in peers})
        for arm in ['rule', 'rule-rl']:
            def vals(dose):
                return [next(r['outcome']['V'] for r in peers if r['seed'] == s and r['arm'] == arm and r['dose'] == dose and not r['greedy']) for s in seeds]
            delta = [x - y for x, y in zip(vals('strong'), vals('hold'))]
            audits = [campaign.manipulation_audit(folder_for(root, job_spec(row, s, arm)),
                      folder_for(root, job_spec(row, s, arm, 'hold'))) for s in seeds]
            test = campaign.d3(delta)
            test['statistical_pass'] = test['pass']
            complete = all(r['outcome']['eligible'] for r in peers if r['arm'] == arm and not r['greedy'])
            test['pass'] = bool(test['pass'] and complete and all(a['pass'] for a in audits))
            d3rows.append({'arm': arm, **test, 'manipulation_audits': audits, 'wave_complete': complete})
        regular = sum(r['outcome']['V'] for r in peers if r['arm'] == 'rule' and r['dose'] == 'strong' and not r['greedy']) / len(seeds)
        greedy = sum(r['outcome']['V'] for r in peers if r['greedy']) / len(seeds)
        wave = all(r['outcome']['eligible'] for r in peers if r['arm'] == 'rule' and r['dose'] == 'strong')
        result.append({'scenario': row['public_id'], 'count': row['count'], 'n_seeds': len(seeds),
              'D1': 'not certified', 'D1_prime': {'pass': bool(greedy < 0.9 * regular and wave),
                  'rule_V': regular, 'greedy_V': greedy, 'ratio': greedy / regular if regular else None},
              'D2_calibration': {'pass': bool(0.4 <= row['SR']['mean'] <= 0.85),
                  'selected_pure': row['calibration_selected_pure'], 'SR': row['SR'],
                  'note': 'Confirmation SR still requires its own held-out reporting'}, 'D3': d3rows})
    return result


def menu_feasibility(stats, campaign):
    families = {}
    for family in ['IE-05-MULTI-AXIS', 'IE-09-STAGGERED-WAVES']:
        subset = [r for r in stats if r['family'] == family]
        best = []
        for count in sorted({r['count'] for r in subset}):
            peers = [r for r in subset if r['count'] == count]
            if len(peers) != 3 or {r['arm'] for r in peers} != set(PURE):
                raise ValueError('Missing pure-arm calibration cell')
            if all(r['eligible'] for r in peers):
                best.append(min(peers, key=lambda r: (-r['V']['mean'], -r['SR']['mean'], r['arm'])))
        targets = []
        for target in [.4, .6, .8]:
            if not best:
                targets.append({'target': target, 'feasible': False, 'reason': 'no complete settings'})
                continue
            closest = min(best, key=lambda r: (abs(r['SR']['mean'] - target), r['count']))
            targets.append({'target': target, 'feasible': abs(closest['SR']['mean'] - target) <= .03,
                'closest_count': closest['count'], 'closest_arm': closest['arm'], 'closest_SR': closest['SR']['mean']})
        families[family] = {'selected_pure_by_count': best, 'targets': targets,
                            'three_tiers_feasible': all(t['feasible'] for t in targets)}
    low = next(r for r in stats if r['family'] == 'IE-09-STAGGERED-WAVES' and r['count'] == 6 and r['arm'] == 'rule')
    high = next(r for r in stats if r['family'] == 'IE-09-STAGGERED-WAVES' and r['count'] == 18 and r['arm'] == 'rule')
    return {'families': families,
        'two_family_three_tier_menu_feasible': all(r['three_tiers_feasible'] for r in families.values()),
        'IE09_rule_N18_minus_N6': campaign.estimate([h['V'] - l['V'] for h, l in zip(high['cases'], low['cases'])]),
        'endpoint_contrast_scope': 'Previously exploratory endpoint contrast; not a preregistered hybrid-effect comparison or full-menu monotonicity proof'}


def report_calibration(stats, rows, source_status):
    lines = ['# E1 v13 冻结校准完成与部分档门禁报告', '', '数据时间：' + now(), '',
             '原40%/60%/80%双场景菜单不可行，原协议与不可行性状态保留。本批是v13指定的IE-05数量17/18/19/27部分档接续，不是把原完整三档实验改写为通过。', '',
             '全部960局校准按条件、架构分别统计，每单元10seed。原始工程中止与每次补跑保留；不计作额外独立样本。', '',
             '|场景族|数量|架构|平均V|V 95% CI|SR|波次完整|', '|---|---:|---|---:|---|---:|---|']
    for r in stats:
        lines.append(f"|{r['family']}|{r['count']}|{r['arm']}|{r['V']['mean']:.6f}|{r['V']['ci95']}|{r['SR']['mean']:.0%}|{r['eligible']}|")
    lines += ['', '## 已冻结的确认条件与对照', '', '|数量|独立校准选定纯架构|平均V|SR|负责设备|', '|---|---|---:|---:|---|']
    for r in rows:
        owner = next(k for k, v in ASSIGNMENTS.items() if r['count'] in v)
        lines.append(f"|{r['count']}|{r['calibration_selected_pure']}|{r['V']['mean']:.6f}|{r['SR']['mean']:.0%}|{owner}|")
    lines += ['', 'IE-09全部纯架构样本SR为100%不等于V=1；SR不能代替经认证的得分上界或headroom。四个IE-05数量即使同为80% SR，其平均V仍可能不同；不能称为四个已分离的成功率档。', '',
              '原队列终态（留存，不覆盖）：`' + str(source_status) + '`。', '',
              '门禁判定另见gates.json，失败照常披露。D1未认证；D1′、D3即使通过，也不意味着全门禁理论正区域成立。v13允许部分方向诊断，不以删掉负向门禁条件换取结论。', '',
              '确认对照由三种纯架构的独立校准均分选择；确认只跑选定纯架构+两种混合栈。该对照不是确认集上重新求得的三纯架构最大值Vm。', '',
              '双方按条件分工，不把同条件10seed拆为两台设备各5seed。每条件4201–4210全部同seed配对；不同条件共用seed有利于对齐统计，并不构成重复运行。', '',
              '完成门禁与交接包后暂停，等待明确启动命令。两台设备结果只能形成按条件的确认表，不能把120局合并成单个同分布样本。跨条件方向分析还须披露设备与数量绑定的潜在混杂。']
    return '\n'.join(lines) + '\n'


def export_handoff(a, rows, cases):
    batch = a.batch.resolve()
    target = batch / 'handoff-r01'
    target.mkdir(exist_ok=False)
    for name in ['protocol', 'analysis', 'reports', 'code']:
        shutil.copytree(batch / name, target / name)
    shutil.copytree(a.code, target / 'frozen/code', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    engine = Path(read(a.source / 'variants.json')['engine'])
    shutil.copytree(engine, target / 'frozen/engine', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    native = a.repo / 'openmd/source-code/source_codes'
    shutil.copytree(native, target / 'frozen/repo/openmd/source-code/source_codes', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git'))
    evaluation = a.repo / 'openmd/code/eval'
    for f in evaluation.rglob('*.py'):
        if '__pycache__' in f.parts:
            continue
        dest = target / 'frozen/repo/openmd/code/eval' / f.relative_to(evaluation)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
    for name in read(batch / 'protocol/split_execution.json')['weights']:
        dest = target / 'frozen/repo/openmd/code/eval/_w1_runs/rl' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(evaluation / '_w1_runs/rl' / name, dest)
    # All 960 canonical reports/completions, not just chosen counts or wins.
    for c in cases:
        folder = Path(c['source'])
        for name in ['report.json', 'completion.json']:
            dest = target / 'data/calibration' / folder.relative_to(a.source) / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(folder / name, dest)
    shutil.copytree(batch / 'gate-screening', target / 'data/gate-screening')
    shutil.copytree(batch / 'attempts', target / 'data/gate-attempts')
    # Preserve engineering audit entries without duplicating massive old tick logs.
    for rec in ['r01', 'r02']:
        folder = a.source / 'recovery' / rec
        for f in folder.rglob('*'):
            if f.is_file() and (f.suffix == '.json' or f.name == 'scheduler_events.jsonl'):
                dest = target / 'data/calibration-engineering-audit' / rec / f.relative_to(folder)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
    for f in [a.source / 'status.json', a.source / 'protocol.json', a.source / 'variants.json']:
        dest = target / 'data/original-campaign' / f.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
    write(target / 'runtime.json', {'python': sys.version, 'platform': platform.platform(),
        'pip_freeze': subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True).splitlines()})
    text = '''# E1 v13 双设备交接包

完整校准960局报告+completion、200局门禁完整轨迹、原工程失败审计、冻结实验代码/引擎/数量场景/两个RL权重均随包提供。
模型大权重与虚拟环境不随包传输：协议记录实际18个模型分片及tokenizer的SHA256。另一台设备必须锁定同一checkpoint，BF16/FP8、关闭思考，先执行verify再确认。
旧校准的全部逐tick大轨迹继续留在原服务器；本包未声称包含这部分大轨迹。门禁轨迹完整携带。
原不可行协议保留，新增split_execution.json只落实v13部分方向任务与暂停点，不修改原引擎、原场景、评分或门禁阈值。

## 操作（Linux，逐行）

将压缩包解压至新目录，进入解压后handoff根目录，使用已安装依赖的Python3.11虚拟环境。
以下模型目录仅为示例，替换为实际同版本权重位置；本机端点可用两个实例或都指向一个实例。

```bash
python -B code/e1_split.py verify --bundle . --model-dir /path/to/Qwen3.8-27B-BF16
python -B code/e1_split.py confirm --bundle . --owner device-b --output /path/to/E1-confirm-device-b-v1 --endpoint-0 http://127.0.0.1:8101/v1 --endpoint-1 http://127.0.0.1:8102/v1
```

device-b严格按数量19然后27，每数量3栈×10seed。device-a严格17然后18：

```bash
python -B code/e1_split.py confirm --bundle . --owner device-a --output /path/to/E1-confirm-device-a-v1 --endpoint-0 http://127.0.0.1:8101/v1 --endpoint-1 http://127.0.0.1:8102/v1
```

暂停状态不会自动执行上述命令。确认目录已有完成局会校验复用；工程step_timeout最多2次尝试、首次有效局，无择优；其他异常保留并停止复核。不得在两台设备上重复跑同一owner。
同一端点若写两次，应避免另启共享模型队列；总并发实际可能为4，请按服务器资源调整实例部署而不改科学参数。

## 汇总

分别复制两台设备的完整确认目录（包括run_manifest、protocol副本、attempts），然后：

```bash
python -B code/e1_split.py merge --bundle . --device-a /path/to/E1-confirm-device-a-v1 --device-b /path/to/E1-confirm-device-b-v1 --output /path/to/E1-merged-analysis-v1
```

merge严格检查owner、4条件×3栈×10seed共120个唯一case、协议/代码/场景/权重哈希，不把校准或门禁局混入确认样本。统计每条件seed-bootstrap95%CI及同seed混合减固定纯基线差。
确认纯对照来自独立校准，不宣称本次已重估确认Vm；D1未认证。只有4个数量条件，且owner与条件绑定，应报告机器环境并限制方向/因果解释。
门禁失败不删除，仍可按v13产出方向诊断，但不得声称满足全门禁定理。
'''
    (target / 'README.md').write_text(text, encoding='utf-8')
    files = inventory(target)
    write(target / 'DELIVERY_MANIFEST.json', {'created_at': now(), 'files': files,
          'counts': {'calibration_cases': 960, 'gate_cases': 200, 'confirmation_cases': 0},
          'source_original': str(a.source), 'source_followup': str(batch)})
    archive = batch / 'E1_v13_handoff_r01.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        for f in sorted(target.rglob('*')):
            if f.is_file():
                z.write(f, f.relative_to(target).as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC failed')
    write(batch / 'handoff_verification.json', {'archive': str(archive), 'bytes': archive.stat().st_size,
          'sha256': sha(archive), 'source_file_count': len(files), 'zip_crc_verified': True,
          'delivery_manifest_sha256': sha(target / 'DELIVERY_MANIFEST.json')})
    return archive


def screen(a):
    batch = a.batch.resolve()
    import fcntl
    handle = (batch / 'supervisor.lock').open('a')
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    frozen = read(batch / 'protocol/split_execution.json')
    if sha(__file__) != frozen['toolkit_sha256']:
        raise ValueError('Followup code changed after freezing')
    code, source, repo = a.code.resolve(), a.source.resolve(), a.repo.resolve()
    check_inventory(code, frozen['original_code_hashes'])
    if sha(source / 'protocol.json') != frozen['original_protocol_sha256']:
        raise ValueError('Original protocol changed')
    write(batch / 'status.json', {'state': 'waiting-calibration-supervisor', 'time': now(),
          'pid': os.getpid(), 'watch_pid': a.watch_pid, 'confirmation_auto_start': False})
    deadline = time.time() + 6 * 3600
    while process_running(a.watch_pid):
        if time.time() > deadline:
            raise RuntimeError('Calibration wait exceeded6h; review, do not launch confirmation')
        time.sleep(10)
    current = read(source / 'recovery/r02/status.json')
    if current['state'] != 'finished':
        raise ValueError('Calibration recovery not finished: ' + str(current))
    # Original three-tier plan must have stopped before its own gates/confirmation.
    original_status = read(source / 'status.json')
    if original_status['state'] != 'count-menu-infeasible':
        raise ValueError('Unexpected original phase; no side-by-side campaign')
    old_lock = (source / 'campaign.lock').open('a')
    fcntl.flock(old_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    campaign = load_campaign(code)
    campaign.prepare(repo, source)  # verifies original source + frozen cloned menu
    check_inventory(Path(read(source / 'variants.json')['engine']), frozen['engine_hashes'])
    check_inventory(repo / 'openmd/code/eval', frozen['eval_python_hashes'])
    for name, h in frozen['weights'].items():
        if sha(repo / 'openmd/code/eval/_w1_runs/rl' / name) != h:
            raise ValueError('RL weights changed')
    stats, cases = calibration(source, code, campaign)
    rows = selected(stats, [17, 18, 19, 27])
    write(batch / 'analysis/calibration_all.json', stats)
    write(batch / 'analysis/calibration_cases.json', cases)
    feasibility = menu_feasibility(stats, campaign)
    write(batch / 'analysis/calibration_feasibility.json', feasibility)
    write(batch / 'protocol/conditions.json', rows)
    report_dir = batch / 'reports'
    report_dir.mkdir(exist_ok=True)
    (report_dir / 'E1校准与部分档门禁报告_v1.md').write_text(report_calibration(stats, rows, original_status), encoding='utf-8')
    extra = ['\n## 原冻结菜单的正式可行性核算', '', '|场景族|原目标SR|最近数量|最近所选纯架构|其SR|匹配±3pp|', '|---|---:|---:|---|---:|---|']
    for family, value in feasibility['families'].items():
        for t in value['targets']:
            extra.append(f"|{family}|{t['target']:.0%}|{t.get('closest_count')}|{t.get('closest_arm')}|{t.get('closest_SR')}|{t['feasible']}|")
    endpoint = feasibility['IE09_rule_N18_minus_N6']
    extra += ['', f"IE-09 Rule数量18−6的同seed得分差：{endpoint['mean']:.6f}，95% CI={endpoint['ci95']}。该端点对照属既有探索性分析，不是预注册的混合收益检验，不证明全菜单单调。", '']
    rp = report_dir / 'E1校准与部分档门禁报告_v1.md'
    rp.write_text(rp.read_text(encoding='utf-8') + '\n'.join(extra), encoding='utf-8')
    records = run_jobs(gate_jobs(rows, frozen['gate_seeds']), rows, batch / 'gate-screening',
               repo, Path(read(source / 'variants.json')['engine']), code,
               frozen['original_protocol_sha256'], sha(batch / 'protocol/split_execution.json'),
               campaign, ['http://127.0.0.1:8101/v1', 'http://127.0.0.1:8102/v1'], batch / 'status.json')
    gates = summarize_gates(rows, records, batch / 'gate-screening', campaign)
    write(batch / 'analysis/gates.json', gates)
    lines = ['\n## 独立门禁筛查结果', '', '|数量|D1|D1′|D2校准|D3 Rule执行|D3 RL执行|', '|---|---|---|---|---|---|']
    for r in gates:
        lines.append(f"|{r['count']}|未认证|{r['D1_prime']['pass']}|{r['D2_calibration']['pass']}|{r['D3'][0]['pass']}|{r['D3'][1]['pass']}|")
    lines += ['', '以上各门阈值和manipulation_audit均复用原函数。D3受测规划器是规则规划器，不是LLM规划器，因而属于接口/执行器可操纵性筛查，不证明LLM接口上的干预效应等价。', '',
              '状态：200局门禁全部完成，任何不通过均保留。确认尚未启动；生成交接包后暂停。']
    path = report_dir / 'E1校准与部分档门禁报告_v1.md'
    path.write_text(path.read_text(encoding='utf-8') + '\n'.join(lines) + '\n', encoding='utf-8')
    write(batch / 'status.json', {'state': 'exporting-handoff', 'time': now(), 'valid_calibration': 960,
          'completed_gates': 200, 'confirmation_auto_start': False})
    archive = export_handoff(a, rows, cases)
    write(batch / 'status.json', {'state': 'paused-after-calibration-and-gates', 'time': now(),
          'valid_calibration': 960, 'completed_gates': 200, 'completed_confirmation': 0,
          'confirmation_auto_start': False, 'handoff_archive': str(archive),
          'note': 'Process exits here. Manual confirm commands needed on each owner; gate failures retained.'})
    print(json.dumps(read(batch / 'status.json'), ensure_ascii=False), flush=True)
    old_lock.close()
    handle.close()


def verify_bundle(bundle, verify_delivery=True):
    f = read(bundle / 'protocol/split_execution.json')
    if verify_delivery:
        check_inventory(bundle, read(bundle / 'DELIVERY_MANIFEST.json')['files'])
    if sha(bundle / 'code/e1_split.py') != f['toolkit_sha256']:
        raise ValueError('Toolkit changed')
    if sha(bundle / 'protocol/original_protocol.json') != f['original_protocol_sha256']:
        raise ValueError('Protocol changed')
    if sha(bundle / 'protocol/original_variants.json') != f['original_variants_sha256']:
        raise ValueError('Menu changed')
    check_inventory(bundle / 'frozen/code', f['original_code_hashes'])
    check_inventory(bundle / 'frozen/engine', f['engine_hashes'])
    check_inventory(bundle / 'frozen/repo/openmd/source-code/source_codes', f['native_hashes'])
    check_inventory(bundle / 'frozen/repo/openmd/code/eval', f['eval_python_hashes'])
    for name, h in f['weights'].items():
        if sha(bundle / 'frozen/repo/openmd/code/eval/_w1_runs/rl' / name) != h:
            raise ValueError('Checkpoint changed')
    return f


def verify(a):
    bundle = a.bundle.resolve()
    f = verify_bundle(bundle)
    if model_record(a.model_dir.resolve()) != f['model_checkpoint']:
        raise ValueError('Model shard/tokenizer checkpoint mismatch')
    write(bundle / 'MODEL_VERIFIED.json', {'time': now(), 'manifest_sha256': sha(bundle / 'protocol/split_execution.json'),
          'model_dir': str(a.model_dir.resolve()), 'model_checkpoint': f['model_checkpoint']})
    print('Verified bundle, engine, scenarios, weights and actual model shards. No episode or LLM request launched.')


def confirm(a):
    bundle, output = a.bundle.resolve(), a.output.resolve()
    frozen = verify_bundle(bundle)
    receipt = read(bundle / 'MODEL_VERIFIED.json')
    if receipt['manifest_sha256'] != sha(bundle / 'protocol/split_execution.json') or receipt['model_checkpoint'] != frozen['model_checkpoint']:
        raise ValueError('Run verify with actual checkpoint before confirmation')
    output.mkdir(parents=True, exist_ok=True)
    import fcntl
    lock = (output / 'supervisor.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    mh = sha(bundle / 'protocol/split_execution.json')
    manifest = output / 'run_manifest.json'
    settings = {'owner': a.owner, 'assigned_counts': ASSIGNMENTS[a.owner],
                'split_manifest_sha256': mh, 'original_protocol_sha256': frozen['original_protocol_sha256'],
                'model_checkpoint': frozen['model_checkpoint'], 'toolkit_sha256': frozen['toolkit_sha256'],
                'endpoints': [a.endpoint_0, a.endpoint_1], 'python': sys.version, 'platform': platform.platform()}
    if manifest.exists():
        if read(manifest) != settings:
            raise ValueError('Run manifest changed; do not mix attempts')
    else:
        write(manifest, settings)
        shutil.copytree(bundle / 'protocol', output / 'protocol')
    campaign = load_campaign(bundle / 'frozen/code')
    all_rows = read(bundle / 'protocol/conditions.json')
    for count in ASSIGNMENTS[a.owner]:
        row = next(r for r in all_rows if r['count'] == count)
        run_jobs(confirmation_jobs([row], frozen['confirmation_seeds']), [row], output / 'confirmation',
            bundle / 'frozen/repo', bundle / 'frozen/engine', bundle / 'frozen/code',
            frozen['original_protocol_sha256'], mh, campaign, [a.endpoint_0, a.endpoint_1], output / 'status.json')
        # One durable job ledger per count; the shared live status is not an analysis denominator.
        shutil.copy2(output / 'confirmation_jobs.json', output / f'confirmation_N{count:03d}_jobs.json')
    write(output / 'status.json', {'state': 'confirmation-complete', 'time': now(), 'owner': a.owner,
          'counts': ASSIGNMENTS[a.owner], 'cases': 60, 'split_manifest_sha256': mh})


def merge(a):
    bundle = a.bundle.resolve()
    frozen = verify_bundle(bundle)
    mh = sha(bundle / 'protocol/split_execution.json')
    campaign = load_campaign(bundle / 'frozen/code')
    rows = read(bundle / 'protocol/conditions.json')
    cells = []
    for owner, root in [('device-a', a.device_a.resolve()), ('device-b', a.device_b.resolve())]:
        m = read(root / 'run_manifest.json')
        if m['owner'] != owner or m['assigned_counts'] != ASSIGNMENTS[owner] or m['split_manifest_sha256'] != mh or m['model_checkpoint'] != frozen['model_checkpoint'] or m['toolkit_sha256'] != frozen['toolkit_sha256']:
            raise ValueError('Wrong owner/incompatible manifest')
        expected_jobs = confirmation_jobs([r for r in rows if r['count'] in ASSIGNMENTS[owner]], frozen['confirmation_seeds'])
        expected_paths = {folder_for(root / 'confirmation', j).relative_to(root / 'confirmation').as_posix() for j in expected_jobs}
        actual_paths = {p.parent.relative_to(root / 'confirmation').as_posix() for p in (root / 'confirmation').rglob('completion.json')}
        if expected_paths != actual_paths:
            raise ValueError('Missing/unexpected/duplicate condition blocks; cannot merge')
        for row in [r for r in rows if r['count'] in ASSIGNMENTS[owner]]:
            vals = {}
            for arm in [row['calibration_selected_pure'], 'llm', 'llm-rl']:
                vals[arm] = [checked_case(folder_for(root / 'confirmation', job_spec(row, s, arm)), row,
                              completion_config(job_spec(row, s, arm), frozen['original_protocol_sha256'], mh), campaign)['outcome']
                             for s in frozen['confirmation_seeds']]
            pure = row['calibration_selected_pure']
            cells.append({'count': row['count'], 'scenario': row['public_id'], 'owner': owner,
                'fixed_calibration_selected_pure': pure, 'calibration_V': row['V'],
                'calibration_SR': row['SR'], 'arms': {arm: {'V': campaign.estimate([x['V'] for x in v]),
                   'SR': campaign.estimate([x['SR'] for x in v])} for arm, v in vals.items()},
                'paired_gains': {arm: campaign.estimate([x['V'] - y['V'] for x, y in zip(vals[arm], vals[pure])]) for arm in ['llm', 'llm-rl']},
                'paired_raw_values': vals, 'host_runtime': m})
    if len(cells) != 4:
        raise ValueError('All four preassigned conditions required')
    a.output.mkdir(parents=True, exist_ok=False)
    result = {'schema': 'E1-v13-combined-conditions@1', 'time': now(), 'split_manifest_sha256': mh,
              'n_cases': 120, 'n_seeds_per_condition': 10, 'conditions': sorted(cells, key=lambda r: r['count']),
              'gates': read(bundle / 'analysis/gates.json'), 'interpretation': 'Partial direction evidence only, not full three-tier causal theorem proof; fixed pure comparator not confirmation maximum; owner/count host confounding disclosed.'}
    write(a.output / 'combined_analysis.json', result)
    text = ['# E1 v13 双设备确认汇总', '', '时间：' + now(), '', '每条件10个独立确认seed，120局；只在条件内同seed配对，不合并为120个同分布样本。', '',
            '|数量|设备|固定纯对照|纯V|LLM+Rule ΔV / CI|LLM+RL ΔV / CI|', '|---|---|---|---:|---|---|']
    for r in result['conditions']:
        pure = r['fixed_calibration_selected_pure']
        text.append(f"|{r['count']}|{r['owner']}|{pure}|{r['arms'][pure]['V']['mean']:.6f}|{r['paired_gains']['llm']}|{r['paired_gains']['llm-rl']}|")
    text += ['', result['interpretation'], '', '完整门禁及确认SR均见combined_analysis.json。跨条件方向检验需保留同seed相关性，不得以结果最好的两档替代全部四档。']
    (a.output / 'E1双设备确认汇总_v1.md').write_text('\n'.join(text) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    for name in ['freeze', 'screen-export']:
        q = sub.add_parser(name)
        for key in ['repo', 'code', 'source', 'batch']:
            q.add_argument('--' + key, type=Path, required=True)
        if name == 'freeze':
            q.add_argument('--checklist', type=Path, required=True)
            q.add_argument('--model-dir', type=Path, required=True)
        else:
            q.add_argument('--watch-pid', type=int, required=True)
    q = sub.add_parser('verify')
    q.add_argument('--bundle', type=Path, required=True)
    q.add_argument('--model-dir', type=Path, required=True)
    q = sub.add_parser('confirm')
    q.add_argument('--bundle', type=Path, required=True)
    q.add_argument('--owner', choices=list(ASSIGNMENTS), required=True)
    q.add_argument('--output', type=Path, required=True)
    q.add_argument('--endpoint-0', default='http://127.0.0.1:8101/v1')
    q.add_argument('--endpoint-1', default='http://127.0.0.1:8102/v1')
    q = sub.add_parser('merge')
    for key in ['bundle', 'device-a', 'device-b', 'output']:
        q.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args()
    try:
        {'freeze': freeze, 'screen-export': screen, 'verify': verify, 'confirm': confirm, 'merge': merge}[a.command](a)
    except Exception as error:
        if a.command == 'screen-export':
            write(a.batch / 'status.json', {'state': 'review-required', 'time': now(),
                  'error': repr(error), 'confirmation_auto_start': False})
        raise


if __name__ == '__main__':
    main()
