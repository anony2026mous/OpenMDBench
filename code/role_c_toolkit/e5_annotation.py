"""E5 blind-annotation packets and result summary.

``packets``: one Markdown dossier per natural failure, built only from the original
episode (report, events, decisions, trajectory, LLM responses). Counterfactual runs,
reference scores and machine labels are never read, so annotators stay blind.
Case identities are replaced by random packet ids; the key file stays with us.

``summary``: machine attribution table; with ``--human`` (annotator CSV) also Cohen's
kappa, confusion matrix and the disagreement list required by the checklist.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
import json
from pathlib import Path
import secrets

LABELS = ('planning', 'execution', 'interface', 'balanced', 'undetermined')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def jsonl(path):
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def find_cases(campaigns):
    """Latest certified episode and latest complete attribution per failure case."""
    episodes, attributions, failures = {}, {}, []
    for campaign in campaigns:
        campaign = Path(campaign)
        status = load(campaign / 'status.json') if (campaign / 'status.json').exists() else {}
        failures += [c for c in status.get('rule_failures', []) if c not in failures]
        for manifest in campaign.glob('episodes/*/manifest.json'):
            m = load(manifest)
            if m.get('status') == 'complete' and m.get('eligible_for_main_score'):
                episodes[manifest.parent.name] = manifest.parent
        for path in campaign.glob('attribution/*/attribution.json'):
            a = load(path)
            if a.get('status') == 'complete' or path.parent.name not in attributions:
                attributions[path.parent.name] = path
    return failures, episodes, attributions


def short(goal):
    p = goal.get('parameters') or {}
    unit = str(p.get('unit_id', '?')).replace('defender.', '')
    target = p.get('target_id')
    if target:
        target = str(target).split('.')[-1]
        return f"{unit}:{goal.get('goal_type')}->{target}"
    pos = p.get('position')
    where = f"@{[round(float(x)) for x in pos][:2]}" if isinstance(pos, (list, tuple)) else ''
    return f"{unit}:{goal.get('goal_type')}{where}"


def lifecycle_changes(trajectory, ammo_every=50):
    last, rows, ammo = {}, [], []
    frame = None
    for frame in jsonl(trajectory):
        if frame['tick'] % ammo_every == 0:
            ammo.append(defender_ammo(frame))
        for e in frame['entities']:
            state = e['lifecycle']
            if last.get(e['entity_id']) not in (None, state):
                rows.append((frame['tick'], e['entity_id'], last[e['entity_id']], state))
            last[e['entity_id']] = state
    if frame is not None and frame['tick'] % ammo_every:
        ammo.append(defender_ammo(frame))
    return rows, ammo


def defender_ammo(frame):
    units = {e['entity_id'].replace('defender.', ''): sum((e.get('ammunition') or {}).values())
             for e in frame['entities'] if e['entity_id'].startswith('defender.') and e.get('ammunition')}
    return frame['tick'], sum(units.values()), units


def packet(folder, packet_id):
    report = load(folder / 'report.json')
    terminal = report.get('terminal_result') or {}
    card = report.get('strategy_scorecard') or {}
    metrics = report.get('layered_metrics') or {}
    lines = [f'# 案例 {packet_id}', '',
             '> 盲标材料：只包含原始失败对局本身的记录，不含任何归因分析结果。', '',
             '## 1. 对局概况', '',
             f"- 场景：`{report['scenario']}`；防守方系统：LLM 规划层 + RL 执行层（每 10 tick 重规划）",
             f"- 终局：tick {terminal.get('tick')}，规则 `{terminal.get('rule_id')}`，结果 `{terminal.get('outcome')}`",
             f"- 防守方单局评分：{card.get('defender_score')}（判负阈值 < 0.6）",
             f"- 防守方开火 {report.get('total_fires_defender')} 次；进攻方开火 {report.get('total_fires_intruder')} 次；"
             f"开火被拒 {sum((report.get('fire_rejections') or {}).values())} 次 {report.get('fire_rejections') or ''}",
             f"- 威胁消灭率 {metrics.get('threat_neutralization_rate')}；防守方存活率 {metrics.get('defender_survival_rate')}",
             f"- 火力分配（按目标）：{report.get('engagements_by_target')}",
             f"- 规划/执行统计：{json.dumps((report.get('defender') or {}).get('broker'), ensure_ascii=False)}；"
             f"规划器 {json.dumps(((report.get('defender') or {}).get('planner') or {}), ensure_ascii=False)[:300]}", '',
             '## 2. 实体状态变化（毁伤/失能）', '', '| tick | 实体 | 变化 |', '|---|---|---|']
    changes_rows, ammo_rows = lifecycle_changes(folder / 'trajectory.jsonl')
    for tick, entity, before, after in changes_rows:
        lines.append(f'| {tick} | {entity} | {before} → {after} |')
    lines += ['', '## 2b. 防守方剩余弹药（每 50 tick）', '', '| tick | 合计 | 各单位 |', '|---|---|---|']
    for tick, total, units in ammo_rows:
        lines.append(f"| {tick} | {total} | {', '.join(f'{k}:{v}' for k, v in units.items())} |")
    lines += ['', '## 3. 开火记录', '', '| tick | 方 | 射手 | 目标 | 状态 |', '|---|---|---|---|---|']
    for e in jsonl(folder / 'events.jsonl'):
        if e.get('t') == 'fire':
            lines.append(f"| {e.get('tick')} | {e.get('side')} | {e.get('entity_id')} | "
                         f"{str(e.get('contact_id')).split('.')[-1]} | {e.get('status')} |")
    lines += ['', '## 4. 规划—执行时间线', '',
              '每个规划时刻：规划器可见接触数、下发目标（单位:类型->目标）、接口接受/拒绝；'
              '其后 10 tick 内执行层上报的目标状态变化。', '',
              '| tick | 可见接触 | 下发目标 | 接受/拒绝 | 期间目标状态变化 |', '|---|---|---|---|---|']
    pending = None; changes = Counter()

    def flush():
        if pending:
            lines.append(pending + ' | ' + (', '.join(f'{k}×{v}' for k, v in sorted(changes.items())) or '—') + ' |')

    for d in jsonl(folder / 'decisions.jsonl'):
        if d['submissions']:
            flush(); changes = Counter()
            sub = d['submissions'][-1]
            visible = sum(len(o.get('contacts') or []) for o in d['planner_observations'])
            goals = '; '.join(short(g) for g in sub['commands'])
            result = sub['result'] or {}
            pending = (f"| {d['tick']} | {visible} | {goals} | "
                       f"{len(result.get('accepted') or [])}/{len(result.get('rejected') or [])}")
        for status in d['goal_status_changes'].values():
            changes[status] += 1
    flush()
    responses = [r for r in jsonl(folder / 'requests.jsonl') if r['kind'] == 'response']
    lines += ['', '## 5. LLM 规划器原始输出', '',
              f'共 {len(responses)} 次调用，完整原文见同目录 `{packet_id}_llm_outputs.md`。', '']
    full = [f'# 案例 {packet_id} — LLM 规划器原始输出', '']
    for r in responses:
        full += [f"## 调用 {r['call_index']}（tick {r.get('tick')}）", '', '```', r['response'], '```', '']
    return '\n'.join(lines) + '\n', '\n'.join(full) + '\n'


def grid_packet(folder, packet_id):
    """Blind dossier for a grid original episode (LLM planner + GOAI rule executor)."""
    episode = load(folder / 'episode.json')
    m = episode['metrics']
    lines = [f'# 案例 {packet_id}', '',
             '> 盲标材料：只包含原始失败对局本身的记录，不含任何归因分析结果。', '',
             '## 1. 对局概况', '',
             '- 环境：grid 概念验证，medium 难度，continuous 任务；防守方（blue）= LLM 规划层 + GOAI 规则执行层，每 10 步重规划',
             f"- 终局：第 {m.get('steps')} 步，胜方 {m.get('winner')}；防守方得分 V = {episode.get('V')}（判负阈值 < 0.6）",
             f"- 红方战斗单位 {m.get('red_combatants_total')} 个，剩余 {m.get('red_combatants_alive')}；发现 {m.get('red_detected')}，拦截 {m.get('red_intercepted')}；"
             f"港口突破 {m.get('port_penetrations')} 次",
             f"- 防守方存活 {m.get('blue_alive')}/{m.get('blue_total')}；弹药消耗 {m.get('ammo_used')}；干扰事件 {m.get('jam_events')}；"
             f"民船遭遇 {m.get('civilian_encounters')}，误拦民船 {m.get('civilian_intercepted')}；规则违规率 {m.get('rule_violation_rate')}", '',
             '## 2. 规划—执行时间线', '',
             '每个规划时刻：下发目标（单位:类型->目标或位置）、接口接受/拒绝；其后执行层的目标状态报告与己方单位状态。', '',
             '| 步 | 下发目标 | 接受/拒绝 | 期间目标报告 | 己方单位（位置/弹药/存活/被干扰） |', '|---|---|---|---|---|']
    pending, reports, own = None, Counter(), {}

    def flush():
        if pending:
            units = '; '.join(f"{k}@({v.get('x')},{v.get('y')}) ammo{v.get('ammo')}{'' if v.get('alive') else ' 阵亡'}"
                              f"{' 干扰' if v.get('jammed_steps') else ''}" for k, v in sorted(own.items()))
            lines.append(pending + ' | ' + (', '.join(f'{k}×{v}' for k, v in sorted(reports.items())) or '—')
                         + ' | ' + units + ' |')

    for e in jsonl(folder / 'events.jsonl'):
        if e['kind'] == 'decision':
            flush(); reports = Counter()
            goals = '; '.join(short(g) for g in e['commands'])
            r = e.get('receipt') or {}
            pending = f"| {e['step']} | {goals} | {len(r.get('accepted') or [])}/{len(r.get('rejected') or [])}"
        elif e['kind'] == 'transition':
            for rep in e.get('goal_reports') or []:
                reports[str(rep.get('status', rep))] += 1
            own = e.get('own_after') or own
    flush()
    responses = [r for r in jsonl(folder / 'requests.jsonl') if r.get('kind') == 'response']
    lines += ['', '## 3. LLM 规划器原始输出', '',
              f'共 {len(responses)} 次调用，完整原文见同目录 `{packet_id}_llm_outputs.md`。', '']
    full = [f'# 案例 {packet_id} — LLM 规划器原始输出', '']
    for i, r in enumerate(responses):
        full += [f'## 调用 {i}', '', '```', str(r.get('text') or r.get('response') or ''), '```', '']
    return '\n'.join(lines) + '\n', '\n'.join(full) + '\n'


GUIDE = """# E5 自然故障盲标说明

请只依据案例材料，独立判断每个失败对局的**主要故障层**，填写 `annotation_form.csv`。
不要与其他标注人或归因工具作者讨论具体案例。

| 标签 | 含义 |
|---|---|
| planning | 主要因规划层（LLM 下发的目标）错误：目标分配、优先级、遗漏威胁、误判诱饵/民船、时机等 |
| execution | 规划合理，但执行层未能完成：未接近目标、开火时机/射程不当、目标不可行或失败 |
| interface | 两层各自看似合理，但目标表达与执行能力不匹配：目标被拒、频繁替换、执行层无法理解或完成所下发的目标形式 |
| balanced | 规划与执行问题都显著且难分主次 |
| undetermined | 材料不足以判断 |

`confidence` 填 1（低）到 3（高）；`rationale` 用一两句话写出关键证据（tick 与事件）。
"""


def build_packets(cases, output):
    """``cases``: list of (case_id, kind, folder) with kind 'hifi' or 'grid'; one shuffled blind set."""
    output = Path(output)
    if output.exists():
        raise FileExistsError('Packets are immutable; choose a new output directory')
    (output / 'packets').mkdir(parents=True)
    order = list(cases); secrets.SystemRandom().shuffle(order)
    key = {}
    for index, (case_id, kind, folder) in enumerate(order, 1):
        packet_id = f'E5-{index:02d}-{secrets.token_hex(2)}'
        key[packet_id] = case_id
        text, full = (packet if kind == 'hifi' else grid_packet)(Path(folder), packet_id)
        (output / 'packets' / f'{packet_id}.md').write_text(text, encoding='utf-8')
        (output / 'packets' / f'{packet_id}_llm_outputs.md').write_text(full, encoding='utf-8')
    (output / 'packets' / 'README_标注说明.md').write_text(GUIDE, encoding='utf-8')
    with (output / 'packets' / 'annotation_form.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.writer(stream)
        writer.writerow(['packet_id', 'label', 'confidence', 'rationale'])
        for packet_id in sorted(key):
            writer.writerow([packet_id, '', '', ''])
    (output / 'KEY_DO_NOT_SHARE.json').write_text(json.dumps(key, indent=2), encoding='utf-8')
    return {'packets': len(key), 'output': str(output)}


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    observed = sum(a == b for a, b in pairs) / n
    left, right = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(left[k] * right[k] for k in set(left) | set(right)) / (n * n)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def select_cases(campaigns, hifi_n, grid_summary=None):
    """Pre-registered selection: first ``hifi_n`` rule failures in plan (seed-major) order + grid selection."""
    failures, episodes, attributions = find_cases(campaigns)
    order = [c['id'] for c in load(Path(campaigns[0]) / 'plan.json')['cases']]
    hifi = sorted((c for c in failures if c in episodes), key=order.index)[:hifi_n]
    rows = []
    for case_id in hifi:
        a = load(attributions[case_id]) if case_id in attributions else {}
        m = load(episodes[case_id] / 'manifest.json')
        rows.append({'case_id': case_id, 'kind': 'hifi', 'folder': str(episodes[case_id]),
                     'scenario': m['case']['scenario'], 'seed': m['case']['seed'],
                     'score': m.get('defender_score'), 'outcome': (m.get('terminal_result') or {}).get('outcome'),
                     'attribution_file': str(attributions.get(case_id)), 'attribution_status': a.get('status'),
                     'replay_gate': (a.get('replay_gate') or {}).get('exact_match'),
                     'dP': a.get('delta_planning'), 'dE': a.get('delta_execution'), 'dI': a.get('delta_interface'),
                     'reference_scores': {k: v.get('score') for k, v in (a.get('runs') or {}).items()},
                     'frozen_plan_horizon': ((a.get('runs') or {}).get('reference_executor') or {})
                     .get('frozen_plan_horizon'),
                     'machine_label': a.get('machine_label')})
    if grid_summary:
        grid = load(grid_summary); root = Path(grid_summary).parent
        for r in grid['selected_failures']:
            rows.append({'case_id': f"grid__llm-rule__s{r['seed']}", 'kind': 'grid',
                         'folder': str(root / f"seed-{r['seed']}" / 'original'),
                         'scenario': 'grid medium/continuous', 'seed': r['seed'], 'score': r['V0'],
                         'outcome': 'red_win', 'attribution_file': str(root / f"seed-{r['seed']}" / 'summary.json'),
                         'attribution_status': 'complete', 'replay_gate': r['replay_gate'],
                         'dP': r['dP'], 'dE': r['dE'], 'dI': r['dI'], 'reference_scores': r['reference_scores'],
                         'frozen_plan_horizon': None, 'machine_label': r['machine_label']})
    return rows


def summary(rows, key_path=None, human_csv=None):
    result = {'cases': rows, 'n_cases': len(rows),
              'all_replay_gates_passed': all(r['replay_gate'] for r in rows),
              'all_attributions_complete': all(r['attribution_status'] == 'complete' for r in rows),
              'machine_label_counts': dict(Counter(r['machine_label'] for r in rows))}
    if human_csv:
        key = load(key_path)
        human = {}
        with Path(human_csv).open(encoding='utf-8-sig') as stream:
            for row in csv.DictReader(stream):
                if row['label'].strip():
                    human[key[row['packet_id']]] = row['label'].strip().lower()
        pairs = [(r['machine_label'], human[r['case_id']]) for r in rows
                 if r['machine_label'] and r['case_id'] in human]
        confusion = defaultdict(Counter)
        for machine, person in pairs:
            confusion[machine][person] += 1
        disagreements = [{'case_id': r['case_id'], 'machine': r['machine_label'], 'human': human[r['case_id']]}
                         for r in rows if r['case_id'] in human and r['machine_label'] != human[r['case_id']]]
        k = kappa(pairs)
        result.update(n_paired=len(pairs), cohen_kappa=k,
                      agreement=sum(a == b for a, b in pairs) / len(pairs) if pairs else None,
                      confusion={m: dict(v) for m, v in confusion.items()}, disagreements=disagreements,
                      success_criterion={'kappa_at_least': 0.6, 'disagreements_at_most': 2,
                                         'met': bool(k is not None and k >= 0.6 and len(disagreements) <= 2)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['packets', 'summary'])
    parser.add_argument('--campaign', type=Path, action='append', required=True,
                        help='hifi campaign directories, oldest first (first one supplies case order)')
    parser.add_argument('--grid-summary', type=Path)
    parser.add_argument('--hifi-cases', type=int, default=9)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--key', type=Path); parser.add_argument('--human', type=Path)
    args = parser.parse_args()
    rows = select_cases(args.campaign, args.hifi_cases, args.grid_summary)
    if args.action == 'packets':
        if not all(r['attribution_status'] == 'complete' for r in rows):
            raise RuntimeError('Attribution incomplete; packets are built only for the final selection')
        result = build_packets([(r['case_id'], r['kind'], r['folder']) for r in rows], args.output)
        (args.output / 'selection.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False))
    else:
        text = json.dumps(summary(rows, args.key, args.human), ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(text + '\n', encoding='utf-8')
        print(text)


if __name__ == '__main__':
    main()
