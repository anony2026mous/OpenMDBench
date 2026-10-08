"""E11: immutable E10 derivation + native scene coverage preflight.

Does not synthesize feint labels, pool batches, or alter engine/scenarios.
Existing E10 outcomes are known: first-layer contrasts are descriptive.
"""
import argparse
import ast
from collections import defaultdict
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

import numpy as np
import yaml

SCENES = ['IE-06-DECOY-MIXED', 'IE-11-DECOY-SCREEN']
SEEDS = [7, 11, 13, 17, 19]
ARMS = ['llm-rule', 'llm-rl', 'pure-llm', 'rule-rule', 'rl']
KEYS = {'llm-rule': 'llm', 'llm-rl': 'llmrl', 'pure-llm': 'purellm'}


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    tmp.replace(p)


def score_from_layers(d):
    card = d['strategy_scorecard']
    layers, weights, app = card['layers'], card['layer_weights'], card['layer_applicability']
    den = sum(v for k, v in weights.items() if app.get(k, True))
    if den <= 0:
        raise ValueError('No applicable score layers')
    result = sum(layers[k] * v for k, v in weights.items() if app.get(k, True)) / den
    if abs(result - card['defender_score']) > .0005:
        raise ValueError('Score is not reproducible')
    return float(card['defender_score'])


def aggregate(rows):
    by = defaultdict(list)
    for r in rows:
        by[int(r['seed'])].append(float(r['score']))
    values = [r['score'] for r in rows]
    return {'mean': float(np.mean(values)), 'n_episodes': len(rows),
            'n_seeds': len(by), 'seed_means': {str(k): float(np.mean(v)) for k, v in sorted(by.items())}}


def stability(h, b):
    hv = list(h['seed_means'].values())
    bv = list(b['seed_means'].values())
    order = sorted(h['seed_means'], key=int)
    halves = [order[:len(order)//2], order[len(order)//2:]]
    return {'mean_win': h['mean'] > b['mean'],
            'every_seed_win': min(hv) > max(bv),
            'split_half_win': all(np.mean([h['seed_means'][s] for s in part]) > b['mean'] for part in halves),
            'definition': 'original main-study mean / every-seed / sorted-seed split-half checks; not a significance test'}


def load_original_rules(repo):
    """Adapt ONLY the archival helper's Windows filesystem constant in memory."""
    path = repo/'openmd/code/eval/_w1_common.py'
    tree = ast.parse(path.read_text())
    replacement = ast.parse("FORMAL = Path(" + repr(str(repo/'openmd/source-code/source_codes/scenarios/formal')) + ")").body[0]
    replaced = 0
    for i, stmt in enumerate(tree.body):
        if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'FORMAL' for t in stmt.targets):
            tree.body[i] = replacement
            replaced += 1
    if replaced != 1:
        raise ValueError('Unexpected archive helper structure')
    mod = types.ModuleType('e11_archival_rules')
    exec(compile(ast.fix_missing_locations(tree), str(path), 'exec'), mod.__dict__)
    return mod


def inventory(repo, helper):
    formal = repo/'openmd/source-code/source_codes/scenarios/formal'
    rows = []
    for item in yaml.safe_load((formal/'registry.yaml').read_text())['scenarios']:
        if not item['public_id'].startswith('IE-'):
            continue
        p = formal/item['package']/'scenario.yaml'
        labels, issues = helper.labels_for(yaml.safe_load(p.read_text())['scenario'])
        nreal, nfeint = sum(labels.values()), sum(not v for v in labels.values())
        rows.append({'scene': item['public_id'], 'package': item['package'], 'scenario_sha256': sha(p),
                     'n_declared_real': nreal, 'n_declared_feint': nfeint, 'ambiguous': issues,
                     'both_classes_under_E10_contract': nreal > 0 and nfeint > 0 and not issues,
                     'contract': 'intruder, unarmed decoy/feint/diversion versus armed non-decoy facility attacker',
                     'does_not_assert_observed_air_window_coverage': True})
    return rows


def derive_values(repo, out, reference):
    rules = load_original_rules(repo)
    evaluation = repo/'openmd/code/eval'
    baseline = read(evaluation/'DATASET_5SEEDS.json')
    result = {}
    for scene in SCENES:
        raw = []
        for arm, key in KEYS.items():
            reports = sorted((evaluation/'_w1_runs').glob(f'ie_{key}_{scene.lower()}_n3*.json'))
            seeds = []
            for p in reports:
                d = read(p)
                ok, why = rules.is_usable(d)
                resolved, reason = rules.arm_of(d, allow_briefing='withheld', strict_arms=True)
                if not ok or resolved != arm or d['seed'] not in SEEDS or rules.scenario_of(d) != scene:
                    raise ValueError(f'Original primary cell invalid, not silently dropped: {p}: {why}, {reason}')
                seeds.append(d['seed'])
                raw.append({'arm': arm, 'seed': d['seed'], 'score': score_from_layers(d),
                            'source': str(p), 'source_sha256': sha(p), 'briefing': rules.briefing_of(d),
                            'checkpoint': rules.theta_name_of(d), 'checkpoint_meta': rules.checkpoint_meta_of(d)})
            if sorted(seeds) != SEEDS:
                raise ValueError('Expected exactly one original main episode per LLM seed: ' + scene + '/' + arm)
        for arm in ['rule-rule', 'rl']:
            rows = [r for r in baseline if r['scenario'] == scene and r['arm'] == arm]
            if not rows or any(r['dataset'] != 'declared' for r in rows):
                raise ValueError('Baseline is not the one archival partition')
            if arm == 'rl' and any(r['checkpoint_theta'] != 'theta_rl_legacy2.npz' or r['checkpoint_obs_dim'] != 2866 for r in rows):
                raise ValueError('Mixed or incompatible pure RL checkpoint')
            for i, r in enumerate(rows):
                raw.append({'arm': arm, 'seed': r['seed'], 'score': r['score'],
                            'source': str(evaluation/'DATASET_5SEEDS.json'), 'consolidated_row_index': baseline.index(r),
                            'source_sha256': sha(evaluation/'DATASET_5SEEDS.json'), 'consolidated_record': r,
                            'scope': 'archival baseline rows only; historical LLM rows from this consolidation NEVER used'})
        means = {a: aggregate([r for r in raw if r['arm'] == a]) for a in ARMS}
        # Validate exact source reconstruction against the rounded published cells.
        for arm in ARMS:
            if abs(means[arm]['mean'] - reference['values'][scene][arm]) > .00051:
                raise ValueError(f'Paper cell mismatch: {scene}/{arm}')
        pure = ['rule-rule', 'rl', 'pure-llm']
        best = max(pure, key=lambda k: means[k]['mean'])
        result[scene] = {'arm_statistics': means, 'best_pure': best, 'V_m': means[best]['mean'],
                         'delta_A': means['llm-rule']['mean'] - means[best]['mean'],
                         'delta_B': means['llm-rl']['mean'] - means[best]['mean'],
                         'original_stability': {h: {b: stability(means[h], means[b]) for b in pure} for h in ['llm-rule', 'llm-rl']},
                         'scope': 'original primary main-study means, descriptive only; E10 seeds and value seeds are NOT paired or pooled'}
        write(out/f'raw/values/{scene}/source_rows.json', raw)
    return result


def derive_perception(e10, out):
    if read(e10/'status.json')['state'] != 'completed':
        raise ValueError('E10 source not complete')
    summary = read(e10/'analysis/a01/summary.json')
    stimuli = read(e10/'raw/confirmation/frozen_stimuli.json')
    responses = read(e10/'raw/LLM/responses.json')
    ids = {r['id']: r for r in responses}
    if len(ids) != 800 or len(stimuli) != 800:
        raise ValueError('Keep complete E10 800-event dataset, not v8 typo400 total')
    for scene in SCENES:
        pred = read(e10/f'analysis/a01/{scene}/predictions.json')
        rows = [r for r in stimuli if r['scene'] == scene]
        if len(rows) != 400 or sum(r['gold_real'] for r in rows) != 200:
            raise ValueError('E10 original class balance invalid')
        if set(r['id'] for r in pred) != set(r['id'] for r in rows):
            raise ValueError('E10 event/prediction mismatch')
        for r in rows:
            v = ids[r['id']]
            if v['seed'] != r['seed'] or v['gold_real'] != r['gold_real'] or v['request']['messages'][-1]['content'] != r['prompt']:
                raise ValueError('E10 response/stimulus mismatch')
        metrics = summary[scene]
        y = np.array([r['gold_real'] for r in pred], bool)
        for key, label in [('numeric', 'numeric_restricted'), ('llm', 'LLM')]:
            correct = np.array([r[key] is not None and (r[key] > .5) == r['gold_real'] for r in pred])
            ba = .5*(correct[y].mean() + correct[~y].mean())
            if abs(ba - metrics[label]['balanced_accuracy']) > 1e-12:
                raise ValueError('E10 point estimate does not reproduce')
        write(out/f'raw/perception/{scene}/predictions_reused.json', pred)
        write(out/f'raw/perception/{scene}/summary_reused.json', metrics)
    return summary


def freeze(repo, e10, code, root):
    paths = [p for p in (repo/'openmd/source-code/source_codes').rglob('*') if p.is_file() and p.suffix in ['.py', '.yaml', '.json']]
    paths += list((repo/'openmd/code/eval').glob('*.py'))
    paths += list((repo/'openmd/code/eval/_w1_runs').glob('*_n3*.json'))
    paths += [repo/'openmd/code/eval/DATASET_5SEEDS.json']
    paths += [root/'code-d1-followup/hf_audit.py']
    paths += [p for p in code.rglob('*') if p.is_file() and p.suffix in ['.py', '.json', '.md', '.pdf']]
    for name in ['manifest/protocol.json','manifest/confirmation_freeze.json','manifest/frozen_models.json',
                 'analysis/a01/summary.json','raw/confirmation/frozen_stimuli.json','raw/LLM/responses.json']:
        paths.append(e10/name)
    paths += [e10/f'analysis/a01/{s}/predictions.json' for s in SCENES]
    return {str(p): sha(p) for p in sorted(set(paths))}


def plot(out, points):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.8))
    for i, p in enumerate(points):
        for arm, key, marker in [('LLM+Rule', 'delta_A', 'o'), ('LLM+RL', 'delta_B', 's')]:
            ax.scatter(p['Cinfo'], p[key], marker=marker, color=['tab:blue', 'tab:orange'][i], label=p['scene']+' '+arm)
    ax.axvline(0, color='gray', linestyle='--')
    ax.axhline(0, color='gray', linestyle='--')
    ax.set(xlabel='Controlled discrimination gap: LLM minus restricted numeric (BA)', ylabel='Layered score minus strongest pure baseline', title='E11: two-scene descriptive juxtaposition (NOT four independent scenes)')
    ax.legend(fontsize=7)
    fig.tight_layout()
    for ext in ['png', 'svg']:
        fig.savefig(out/f'analysis/a01/perception_value.{ext}', dpi=180)
    plt.close(fig)


def run(a):
    out, repo, e10, root = a.output, a.repo, a.e10, a.root
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    import fcntl
    with (out/'campaign.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (out/'manifest/protocol.json').exists():
            raise ValueError('Existing analysis retained; create a new version')
        try:
            sys.path.insert(0, str(root/'code-d1-followup'))
            import hf_audit
            frozen = freeze(repo, e10, Path(__file__).parent, root)
            coverage = inventory(repo, hf_audit)
            write(out/'manifest/scenario_coverage.json', coverage)
            reference = read(Path(__file__).parent/'paper_table_reference.json')
            protocol = {'protocol': 'E11-cross-scene-p01', 'governing_checklist': '20261003-1205 v8 section3.5',
                'layer1': 'zero new episodes/calls; reuse E10 400 events PER scene =800total; reconstruct original primary value rows',
                'known_outcomes': True, 'layer1_inference': 'two-scene descriptive mechanism evidence; not independent confirmation or causal identification of decision-form mediator',
                'layer2_target': '4-6 unique frozen scenes, 40-60 balanced events/additional scene; 10 source seeds, development/confirmation disjoint; same E10 feature and prompt policy',
                'sampling_unit': 'events sampled within each scene; seed clustered uncertainty within scene; scene is cross-scene comparison unit',
                'value_protocol': 'five original nondeterministic LLM seeds; reused pure baselines; original main-study means and three-part stability, no new seed-paired causal claim',
                'no_batch_pooling': True, 'no_new_LLM_calls': True, 'no_engine_or_scene_changes': True,
                'numeric_nomenclature': 'learned L2 logistic numeric discriminator, NOT native Rule controller',
                'majority_predefined': 'strictly more than half of unique scenes with Cinfo<=0 AND positive declared hybrid delta; report each hybrid separately plus both-positive conjunction; formal extension requires >=4 valid scenes',
                'thresholds_unchanged': [0.6, 0.85], 'source_sha256': frozen,
                'path_adaptation': 'archival _w1_common FORMAL constant redirected in-memory only; no original file edits',
                'paper_reference': reference, 'coverage_admission': 'both offline classes under SAME E10 armed/unarmed role contract; no declaring fog/escort automatically feint'}
            write(out/'manifest/protocol.json', protocol)
            write(out/'status.json', {'state': 'running', 'phase': 'layer1-derivation', 'updated_at': time.time()})
            values = derive_values(repo, out, reference)
            perception = derive_perception(e10, out)
            points = []
            for s in SCENES:
                r, v = perception[s], values[s]
                points.append({'scene': s, 'numeric_BA': r['numeric_restricted']['balanced_accuracy'],
                    'LLM_BA': r['LLM']['balanced_accuracy'], 'Cinfo': r['Cinfo_difference'], 'Cinfo_ci95': r['Cinfo_ci95'],
                    'delta_A': v['delta_A'], 'delta_B': v['delta_B'], 'V_m': v['V_m'], 'best_pure': v['best_pure'],
                    'descriptive_joint_A': r['Cinfo_difference'] <= 0 and v['delta_A'] > 0,
                    'descriptive_joint_B': r['Cinfo_difference'] <= 0 and v['delta_B'] > 0})
            additional = [r['scene'] for r in coverage if r['both_classes_under_E10_contract'] and r['scene'] not in SCENES]
            expansion = {'state': 'needs-additional-frozen-scenario-mapping' if len(additional) < 2 else 'needs-stage2-protocol-freeze',
                         'qualified_existing': [r['scene'] for r in coverage if r['both_classes_under_E10_contract']],
                         'qualified_additional': additional, 'formal_cross_scene_minimum': 4,
                         'no_scenario_modification_authorized_or_performed': True,
                         'not_equivalent_to_missing_observations': 'All other IE scenes lack the required offline feint class, before rollout.'}
            summary = {'layer1_state': 'completed', 'n_scenes': 2, 'perception_source_n_events': 800,
                       'value': values, 'points': points, 'expansion': expansion,
                       'formal_4to6_scene_claim_established': False, 'new_episodes': 0, 'new_LLM_calls': 0,
                       'scope': 'Controlled classifier disadvantage coexists with positive original mean hybrid gains in two scenes. Does NOT identify decision-form causal mechanism or exclude all perception advantages.'}
            write(out/'analysis/a01/summary.json', summary)
            with (out/'analysis/a01/perception_value.csv').open('w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(points[0]))
                writer.writeheader()
                writer.writerows(points)
            plot(out, points)
            report(out, summary, coverage)
            for p, digest in frozen.items():
                if sha(p) != digest:
                    raise ValueError('Immutable source changed: ' + p)
            write(out/'status.json', {'state': 'layer1-completed-layer2-blocked-coverage', 'elapsed_seconds': time.time()-started,
                  'source_unchanged': True, 'layer1_complete': True, 'layer2_started': False, 'expansion': expansion})
            print(json.dumps({'output': str(out), 'points': points, 'expansion': expansion}, ensure_ascii=False), flush=True)
        except Exception as e:
            write(out/'status.json', {'state': 'failed-engineering', 'error': repr(e), 'elapsed_seconds': time.time()-started})
            raise


def report(out, summary, coverage):
    lines = ['# E11 判别—价值跨场景对照：第一层完成与扩展场景核查', '',
        '执行依据：2026-10-03 12:05 v8 强化清单 §3.5。仅执行实验分析，不修改论文、引擎、场景或门禁。', '',
        '## 1. 数据与口径', '',
        '完整复用 E10 p02：IE-06、IE-11 各400事件（各200真实+200诱饵），合计800。清单“合计400、各200”视为数量笔误，不删减原冻结刺激集。',
        '判别按原10seed聚类20,000次bootstrap保留CI；分层价值来自原无情报主批次五seed及原归档基线；两条数据链分别保留，不把事件当对局、不做跨批次seed配对。',
        '当前可访问0930论文中对应高保真主表为Table5第8页，而不是该稿Table4（Grid干预表）。使用明确场景ID与可重建成绩对齐；不臆造未发布的HE编号。',
        '不使用DATASET_5SEEDS里混合历史LLM读数：LLM仅读原*_n3*.json；该数据集只提取已锁定纯基线分区。原得分已归一化，不再除scored_weight。', '',
        '## 2. 两场景对照', '',
        '|场景|数值BA|LLM BA|Cinfo [95%CI]|最好纯基线V|LLM+Rule Δ|LLM+RL Δ|',
        '|---|---:|---:|---|---:|---:|---:|']
    for p in summary['points']:
        ci = p['Cinfo_ci95']
        lines.append(f"|{p['scene']}|{p['numeric_BA']:.2%}|{p['LLM_BA']:.2%}|{p['Cinfo']:+.4f} [{ci[0]:+.4f},{ci[1]:+.4f}]|{p['V_m']:.6f}|{p['delta_A']:+.6f}|{p['delta_B']:+.6f}|")
    lines += ['', '两个场景均出现“受控判别劣势与分层均值优势并存”。这是有利于辨析简单感知优势解释的描述性证据；它本身不证明价值唯一来自决策形态，也不排除未测量的其他信息/规划机制。',
        '原主实验逐seed/分半稳定性细项见summary.json，不将均值为正自动等同三部分稳定性全通过。数值判别器是训练得到的逻辑回归模型，不等同仿真中原生Rule控制器。', '',
        '## 3. 冻结场景覆盖与扩展卡点', '',
        '|场景|真实角色数|诱饵角色数|同E10契约双类齐全|', '|---|---:|---:|---|']
    for r in coverage:
        lines.append(f"|{r['scene']}|{r['n_declared_real']}|{r['n_declared_feint']}|{r['both_classes_under_E10_contract']}|")
    lines += ['', '只有IE-06、IE-11具备同契约诱饵类。IE-12雾效不等于有诱饵，“decoy min / fog screen”等额外场景未能与该冻结注册表对应。继续两个场景的新seed不能把n=2变成n=4。',
        '第二层40–60事件/额外场景目前未启动：需提供额外已冻结场景编号/包路径与同等真假契约；否则须另行授权场景扩展并明确不同版本，不允许自行改造或将武装护航任意标为诱饵。',
        '当前n=2只给描述性结论，不发布4–6场景多数判据已通过、不计算n=2跨场景相关显著性、不把两种混合架构算成四个独立场景。', '',
        '## 4. 数据管理', '',
        'manifest保存协议与源文件哈希；raw/perception仅为原E10预测/摘要副本，完整800请求响应仍由来源批次引用；raw/values逐局溯源；analysis/a01保存统一表和散点PNG/SVG；reports/r01保存本报告。原输入全程只读并结束复核。']
    p = out/'reports/r01/E11第一层对照与场景覆盖报告_v1.md'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('\n'.join(lines)+'\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['launch', 'run'])
    for name in ['repo', 'root', 'e10', 'output']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'launch':
        if a.output.exists():
            raise ValueError('Existing batch retained')
        (a.output/'logs').mkdir(parents=True)
        env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', MPLCONFIGDIR=str(a.output/'logs/mpl'))
        cmd = [sys.executable, '-B', '-u', str(Path(__file__)), 'run']
        for name in ['repo', 'root', 'e10', 'output']:
            cmd += ['--'+name, str(getattr(a, name))]
        with (a.output/'logs/supervisor.log').open('a') as log:
            proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        write(a.output/'logs/launch.json', {'pid': proc.pid, 'command': cmd, 'started_at': time.time()})
        print(json.dumps({'pid': proc.pid, 'output': str(a.output)}))
    else:
        run(a)


if __name__ == '__main__':
    main()
