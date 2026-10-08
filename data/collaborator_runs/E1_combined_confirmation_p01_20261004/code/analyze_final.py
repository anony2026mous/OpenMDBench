"""Postprocess frozen E1 merge; no engine runs or protocol/score changes."""
import argparse
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def bootstrap(values, alpha=.05):
    x = np.asarray(values, dtype=float)
    if x.shape != (10,) or not np.isfinite(x).all():
        raise ValueError('Exactly ten finite paired seed observations required')
    draws = x[np.random.default_rng(20261001).integers(0, 10, size=(20000, 10))].mean(axis=1)
    return {'mean': float(x.mean()), 'ci': np.quantile(draws, [alpha / 2, 1 - alpha / 2]).tolist(),
            'confidence': 1-alpha, 'n_seeds': 10, 'bootstrap_draws': 20000,
            'positive_seed_count': int((x > 0).sum()), 'negative_seed_count': int((x < 0).sum())}


def contrast(high, low):
    return bootstrap(np.asarray(high) - np.asarray(low))


def fmt(value):
    ci = value.get('ci95', value.get('ci'))
    return f"{value['mean']:+.5f} [{ci[0]:+.5f}, {ci[1]:+.5f}]"


def main():
    parser = argparse.ArgumentParser()
    for name in ['bundle', 'merged', 'device-a', 'device-b', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.bundle / 'frozen/code'))
    from common import estimate
    args.output.mkdir(parents=True, exist_ok=False)
    merged = read(args.merged / 'combined_analysis.json')
    protocol = read(args.bundle / 'protocol/split_execution.json')
    conditions = read(args.bundle / 'protocol/conditions.json')
    counts = [17, 18, 19, 27]
    seeds = protocol['confirmation_seeds']
    cells = {c['count']: c for c in merged['conditions']}
    roots = {'device-a': args.device_a, 'device-b': args.device_b}
    reports = {}
    audit = {'cases': 0, 'valid_report_hashes': 0, 'eligible_cases': 0,
             'LLM_events': collections.Counter(), 'LLM_request_parameters_valid': True,
             'by_owner': {}, 'terminal_states': collections.Counter()}
    layers = ['terminal', 'facilities', 'depth', 'leak', 'exchange', 'ammo', 'surface']
    metrics = {n: {} for n in counts}
    seed_gains = {n: {} for n in counts}
    supplemental = []
    for n in counts:
        cell = cells[n]
        root = roots[cell['owner']]
        for arm in ['rule', 'llm', 'llm-rl']:
            native = []
            for i, seed in enumerate(seeds):
                folder = root / 'confirmation' / cell['scenario'] / (arm + '-strong-g0') / f'seed-{seed}'
                report = read(folder / 'report.json')
                completion = read(folder / 'completion.json')
                if hashlib.sha256((folder/'report.json').read_bytes()).hexdigest() != completion['report_sha']:
                    raise ValueError('Report hash mismatch')
                if completion['config']['seed'] != seed or report['seed'] != seed:
                    raise ValueError('Seed alignment mismatch')
                card = report['strategy_scorecard']
                if card['defender_score'] != cell['paired_raw_values'][arm][i]['V']:
                    raise ValueError('Merged score does not match native primary score')
                audit['cases'] += 1
                audit['valid_report_hashes'] += 1
                audit['eligible_cases'] += int(cell['paired_raw_values'][arm][i]['eligible'])
                audit['terminal_states'][card['terminal']['state']] += 1
                owner = audit['by_owner'].setdefault(cell['owner'], {'requests': 0, 'responses': 0,
                              'errors': 0, 'plan_calls': 0, 'parse_failures': 0,
                              'stale_plan_reuse': 0, 'fallback_count': 0})
                planner = report['defender']['planner']
                for key in ['plan_calls', 'parse_failures', 'stale_plan_reuse', 'fallback_count']:
                    owner[key] += planner.get(key, 0)
                call_file = folder / 'llm_calls.jsonl'
                if call_file.exists():
                    for line in call_file.read_text().splitlines():
                        if not line:
                            continue
                        event = json.loads(line)
                        kind = event['kind']
                        audit['LLM_events'][kind] += 1
                        if kind in ['request', 'response', 'error']:
                            owner[{'request': 'requests', 'response': 'responses', 'error': 'errors'}[kind]] += 1
                        if kind == 'request':
                            audit['LLM_request_parameters_valid'] &= bool(event['enable_thinking'] is False and event['temperature'] == 0 and event['model'] == 'Qwen3.8-27B')
                native.append({'seed': seed, 'V': card['defender_score'],
                               'SR': cell['paired_raw_values'][arm][i]['SR'],
                               'weighted_facility_health': card['facilities']['weighted_survival'],
                               'facilities_out_of_action': card['facilities']['out_of_action'],
                               'air_leak_rate': card['air_layer']['leak_rate'],
                               'defender_shots': report['total_fires_defender'],
                               'ammo_efficiency': card['fire']['defender_ammo_efficiency'],
                               'layers': card['layers'], 'layer_weights': card['layer_weights'],
                               'scored_weight': card['scored_weight'],
                               'elapsed_seconds': completion['elapsed_seconds'],
                               'terminal': card['terminal']['state'],
                               'report_sha256': completion['report_sha']})
                reports[n, arm, seed] = report
            metrics[n][arm] = {'native': native,
                              'summary': {k: estimate([r[k] for r in native]) for k in [
                                  'weighted_facility_health', 'facilities_out_of_action',
                                  'air_leak_rate', 'defender_shots', 'ammo_efficiency', 'elapsed_seconds']}}
        base = [v['V'] for v in cell['paired_raw_values']['rule']]
        for arm in ['llm', 'llm-rl']:
            values = [v['V'] for v in cell['paired_raw_values'][arm]]
            gain = np.asarray(values) - np.asarray(base)
            # Exact agreement with the primary frozen bootstrap.
            check = estimate(gain)
            if check != cell['paired_gains'][arm]:
                raise ValueError('Frozen bootstrap reproduction failed')
            seed_gains[n][arm] = gain.tolist()
            layer_delta = {}
            per_seed_sum = np.zeros(10)
            for layer in layers:
                weighted = []
                for seed in seeds:
                    a = reports[n, arm, seed]['strategy_scorecard']
                    b = reports[n, 'rule', seed]['strategy_scorecard']
                    if a['layer_weights'] != b['layer_weights'] or a['scored_weight'] != b['scored_weight']:
                        raise ValueError('Incompatible score decomposition')
                    weighted.append((a['layers'][layer] - b['layers'][layer]) * a['layer_weights'][layer] / a['scored_weight'])
                per_seed_sum += weighted
                layer_delta[layer] = float(np.mean(weighted))
            supplemental.append({'count': n, 'arm': arm, 'paired_gain': bootstrap(gain),
                                 'bonferroni_8_gain_sensitivity': bootstrap(gain, alpha=.05/8),
                                 'score_layer_contributions_mean': layer_delta,
                                 'score_rounding_residual_max_abs': float(np.max(np.abs(per_seed_sum-gain))),
                                 'layer_interpretation': 'Descriptive fixed-score decomposition, not causal layer attribution'})
    direction = []
    for low, high in [(17, 18), (19, 27)]:
        ca = next(c for c in conditions if c['count'] == low)
        cb = next(c for c in conditions if c['count'] == high)
        cal_headroom_delta = contrast([1-v['V'] for v in cb['cases']], [1-v['V'] for v in ca['cases']])
        for arm in ['llm', 'llm-rl']:
            result = contrast(seed_gains[high][arm], seed_gains[low][arm])
            sensitivity = bootstrap(np.asarray(seed_gains[high][arm])-np.asarray(seed_gains[low][arm]), alpha=.05/4)
            direction.append({'from': low, 'to': high, 'arm': arm,
                              'calibration_headroom_delta': cal_headroom_delta,
                              'gain_delta': result, 'bonferroni_4_direction_sensitivity': sensitivity,
                              'point_direction_matches_calibration': bool(result['mean']*cal_headroom_delta['mean']>0),
                              'paired_raw_gain_delta': (np.asarray(seed_gains[high][arm])-np.asarray(seed_gains[low][arm])).tolist(),
                              'same_host': cells[low]['owner'] == cells[high]['owner']})
    from scipy.stats import spearmanr
    correlation = {}
    for arm in ['llm', 'llm-rl']:
        gains = [cells[n]['paired_gains'][arm]['mean'] for n in counts]
        calibration_h = [1-cells[n]['calibration_V']['mean'] for n in counts]
        confirmation_h = [1-cells[n]['arms']['rule']['V']['mean'] for n in counts]
        correlation[arm] = {'calibration_H_spearman_descriptive': float(spearmanr(calibration_h, gains).statistic),
                            'confirmation_H_spearman_descriptive': float(spearmanr(confirmation_h, gains).statistic),
                            'n_conditions': 4,
                            'warning': 'Confirmation H and gain share the subtracted baseline; their correlation is algebraically coupled, not independent validation. No analytical f fitted.'}
    feasibility = read(args.bundle / 'analysis/calibration_feasibility.json')
    result = {'time': dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
              'source_merged_sha256': hashlib.sha256((args.merged/'combined_analysis.json').read_bytes()).hexdigest(),
              'primary_statistics': 'Unchanged frozen common.estimate: 20000 draws, seed20261001, percentile seed-bootstrap95%, same-seed within condition',
              'secondary_status': 'Post-confirmation diagnostic analyses; not newly preregistered primary tests',
              'audit': audit, 'condition_metrics': metrics, 'paired_gains_supplement': supplemental,
              'same_host_direction_contrasts': direction, 'descriptive_correlations': correlation,
              'calibration_ie09_endpoints': feasibility['IE09_rule_N18_minus_N6'],
              'decision': 'Mixed partial-direction evidence (v13 outcome B); not uniform headroom-law confirmation',
              'scope': 'Positive pointwise LLM+Rule gains in N17/N27, uncertain N18, no advantage N19; LLM+RL gains not distinguishable from zero in any condition; full-gate theorem not certified'}
    (args.output/'final_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n',encoding='utf-8')
    lines = ['# E1 双机正式确认：最终实验分析报告 v1', '', '统计时间：'+result['time'], '',
             '## 1. 结论摘要', '',
             '120局正式确认完整完成并通过校验。LLM+Rule在数量17和27的同seed得分收益点态95%置信区间高于零；数量18均值为正但区间跨零，数量19均值略负且区间跨零。LLM+RL在四个数量条件均未获得区间排除零的收益证据。', '',
             'headroom方向呈混合结果：独立校准预先显示17→18与19→27的得分空间均减小；前一对的两种混合收益点估计均减小，后一对均增大。四个变化量的95%区间都跨零。因此将本实验归为v13预案B（部分档方向不一致），不能以数量17、18的局部点方向代替完整四条件结论，也不能表述为完整分层定律已被证实。', '',
             '## 2. 设计、数据完整性与统计口径', '',
             '条件为IE-05数量17、18、19、27。1号设备负责17/18，2号负责19/27。每条件Rule、LLM+Rule、LLM+RL三栈，每栈同一组4201–4210共10seed；总计120局。所有四条件全部报告，无择优删局或重新选择条件。校准4101–4110、门禁4151–4160与确认4201–4210互不混用。', '',
             '冻结对照来自独立校准中三个纯架构的最高平均V，四条件均预先选中Rule。确认只重跑该固定纯对照，没有重跑另外两个纯架构；故本文记为固定Rule基线，不声称获得确认样本上的最大纯架构值V_m。', '',
             '主分数V严格取strategy_scorecard.defender_score，成功率SR严格取原生defender_success终局。报告中layered_metrics.performance_v是不同指标，本次没有替换冻结主分数。原始终局失败保留，不用胜负或波次资格筛选得分。', '',
             f"核验：{audit['cases']}局、{audit['valid_report_hashes']}份报告SHA通过、{audit['eligible_cases']}局满足原波次资格。引擎/场景/RL权重/LLM checkpoint/协议身份由冻结合并入口校验；两台原始输出完整ZIP每个文件SHA和CRC均通过，原始数据未更改。", '',
             '统计单位为seed：对每条件同seed相减后，用冻结函数进行20000次percentile bootstrap，随机数seed=20261001，给出95%区间；四个条件不是120个同分布独立样本。跨条件变化保持4201–4210配对。', '',
             '新增方向对比、分数分项和多重比较敏感性均明确标注为确认后的诊断分析，不冒称预注册主检验。8个混合收益附加Bonferroni式99.375% bootstrap区间，4个同机方向变化附加98.75%区间；此为近似敏感性分析，不改变冻结点态95%报告。', '',
             '## 3. 四条件正式确认结果', '',
             '|数量|设备|Rule V|LLM+Rule V|LLM+RL V|SR：Rule / LLM+Rule / LLM+RL|',
             '|---|---|---:|---:|---:|---|']
    for n in counts:
        c=cells[n]
        lines.append(f"|{n}|{c['owner']}|{c['arms']['rule']['V']['mean']:.5f}|{c['arms']['llm']['V']['mean']:.5f}|{c['arms']['llm-rl']['V']['mean']:.5f}|"+' / '.join(f"{c['arms'][a]['SR']['mean']:.0%}" for a in ['rule','llm','llm-rl'])+'|')
    lines += ['', '|数量|LLM+Rule − Rule：均值 [95% CI]|LLM+RL − Rule：均值 [95% CI]|', '|---|---|---|']
    for n in counts:
        lines.append(f"|{n}|{fmt(cells[n]['paired_gains']['llm'])}|{fmt(cells[n]['paired_gains']['llm-rl'])}|")
    lines += ['', '数量17与27的LLM+Rule分别提升约12.29和11.94个归一化得分百分点（不是成功率百分点）。数量27区间下界较接近零，须结合多重比较敏感性阅读。其余跨零区间表示目前数据不足以区分正负收益，不能写成“等效”或“证明没有作用”。', '',
              'SR=100%时经验bootstrap区间会退化为[1,1]，不表示总体成功概率确定为100%；10seed的尾部不确定性仍存在。完整各架构V/SR区间见冻结combined_analysis.json。', '',
              '### 3.1 多重比较敏感性（8个收益对比）', '',
              '|数量|架构|99.375% bootstrap区间|正向 / 负向seed数|', '|---|---|---|---|']
    for s in supplemental:
        z=s['bonferroni_8_gain_sensitivity'];pg=s['paired_gain']
        lines.append(f"|{s['count']}|{s['arm']}|[{z['ci'][0]:+.5f}, {z['ci'][1]:+.5f}]|{pg['positive_seed_count']} / {pg['negative_seed_count']}|")
    lines += ['', '## 4. headroom方向与清单成功判据', '',
              '将归一化分数上界1作为描述性参照，定义H_cal=1−独立校准固定纯基线V。这个1是评分尺度上界，不是本场景已认证可达oracle；H_cal也是代理量，不是对真实最优价值差的直接测量。', '',
              '|数量|校准Rule V|H_cal|确认Rule V|确认代理H_confirm|', '|---|---:|---:|---:|---:|']
    for n in counts:
        c=cells[n];lines.append(f"|{n}|{c['calibration_V']['mean']:.5f}|{1-c['calibration_V']['mean']:.5f}|{c['arms']['rule']['V']['mean']:.5f}|{1-c['arms']['rule']['V']['mean']:.5f}|")
    lines += ['', '四个校准SR都为80%，不能把它们写成已经实现40%/60%/80%的三个SR档。校准V的区间重叠，不能凭四个均值宣称获得彼此可区分的headroom档。数量增大也不保证得分或剩余空间单调。', '',
              '|同机对比|架构|校准H变化 [95% CI]|混合收益变化 [95% CI]|点方向与校准一致|', '|---|---|---|---|---|']
    for d in direction:
        lines.append(f"|{d['from']}→{d['to']}|{d['arm']}|{fmt(d['calibration_headroom_delta'])}|{fmt(d['gain_delta'])}|{'是' if d['point_direction_matches_calibration'] else '否'}|")
    lines += ['', '这里比较的是收益差的变化，例如(LLM+Rule−Rule)_18−(LLM+Rule−Rule)_17，不是两种混合架构得分之间的差。两台服务器各自的内部对比避免直接跨机比较，但数量变化仍可能同时改变任务负载、目标构成和可见联系，不能把它当作仅改变headroom的排他性干预。', '',
              '所有方向变化区间跨零：17→18只有点方向一致，19→27点方向相反。因而没有获得稳定、统计确定的“空间越小，收益越小”受控验证。该现象不等于理论普遍被证伪：门禁前提未满足，且headroom档位没有被稳定分离；但也不能把这些限制用于删去不一致结果或改写为成功。', '',
              '四条件的H_cal与收益描述性Spearman相关分别为：'+', '.join(f"{a}={v['calibration_H_spearman_descriptive']:+.2f}" for a,v in correlation.items())+'。仅4个条件且设备/条件绑定，不能作可靠总体或因果推断。', '',
              '确认H_confirm与收益描述性相关分别为：'+', '.join(f"{a}={v['confirmation_H_spearman_descriptive']:+.2f}" for a,v in correlation.items())+'。这两者都减去了同一个确认基线，存在代数耦合；只作事后描述，不能据此重新排档并宣称主判据通过。', '',
              '## 5. 得分来源与原生附加指标', '',
              '下表设施指标是原生weighted_survival（按权重计算健康保留），不等同于完整设施数量；漏防是air_layer.leak_rate；弹药为原生实际开火数与kills/shots效率，均为描述性结果。', '',
              '|数量|架构|设施加权健康均值|设施失能数量均值|空中漏防率均值|防守方开火均值|弹药效率均值|', '|---|---|---:|---:|---:|---:|---:|']
    for n in counts:
        for arm in ['rule','llm','llm-rl']:
            s=metrics[n][arm]['summary']
            lines.append(f"|{n}|{arm}|"+'|'.join(f"{s[k]['mean']:.4f}" for k in ['weighted_facility_health','facilities_out_of_action','air_leak_rate','defender_shots','ammo_efficiency'])+'|')
    lines += ['', '### 5.1 冻结评分分项对收益的算术贡献', '',
              '|数量|架构|终局|设施|深度|漏防|交换|弹药|水面|', '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in supplemental:
        lines.append(f"|{s['count']}|{s['arm']}|"+'|'.join(f"{s['score_layer_contributions_mean'][k]:+.5f}" for k in layers)+'|')
    lines += ['', '以上贡献严格按照原生layer_weights/scored_weight分解V差，保留四位评分及分项舍入残差，不修改评分。它回答“分数差记在哪些评分项”，不是“规划层/执行层造成了多少因果收益”的反事实归因。确认批次未执行LLM strong/hold或oracle替换，不能补写出这些归因结论。逐seed值、区间和舍入残差见final_analysis.json。', '',
              '## 6. 工程与LLM调用质量', '', '|设备|真实请求/响应|解析失败|旧计划复用|fallback|', '|---|---:|---:|---:|---:|']
    for owner,v in audit['by_owner'].items():
        lines.append(f"|{owner}|{v['requests']} / {v['responses']}|{v['parse_failures']}|{v['stale_plan_reuse']}|{v['fallback_count']}|")
    lines += ['', '全部请求与响应数量一致，无LLM调用error；请求记录核实关闭思考、temperature=0、Qwen3.8-27B。解析失败和旧计划复用意味着服务返回不等于每次计划都有效；这些对局全部保留，没有根据解析质量事后剔除。', '',
              '数量27的RL执行器原有MAX_CONTACTS=20容量限制仍然冻结，运行日志可见超过容量后截断联系的警告。这里不能断言27个实体始终全部可见，也不能把容量截断直接认定为弱收益的已证实原因；如需进一步归因，应另行冻结容量/执行器机制对照，不能修改已完成实验。', '',
              '## 7. 门禁与理论结论边界', '', '|数量|D1|D1′|D2校准|Rule执行器D3|RL执行器D3|确认Rule SR|', '|---|---|---|---|---|---|---|']
    for g in merged['gates']:
        lines.append(f"|{g['count']}|未认证|未通过|{'通过' if g['D2_calibration']['pass'] else '未通过'}|{'通过' if g['D3'][0]['pass'] else '未通过'}|{'通过' if g['D3'][1]['pass'] else '未通过'}|{cells[g['count']]['arms']['rule']['SR']['mean']:.0%}|")
    lines += ['', 'D2校准通过来自80%成功率，独立确认Rule成功率提高到90%–100%；若直接用原[40%,85%]规则筛查确认点估计，四条件都不在该窗口。这是分离样本上的漂移，必须记录；不追溯改写校准门禁，也不调整阈值追求通过。', '',
              'Rule执行器D3是规则规划器strong/hold的接口可操纵性筛查，不是实际LLM规划器的干预效应，更不是D1通过。RL执行器虽控制和状态可改变，但未达到冻结收益强度统计判据。', '',
              '所以本批次支持两项明确实证：其一，真实LLM+Rule在部分冻结数量条件有得分提升；其二，混合收益依赖条件和执行器，不是接入LLM后自动、普遍优于固定纯基线。它不能证明全部门禁成立、完整三档分层定律、LLM感知优势、已认证oracle归因或解析f。', '',
              '## 8. 校准证据与后续建议', '',
              '原960局校准已完整收尾，原数量菜单不能实现40%/60%/80% SR三档；IE-09三个纯架构全菜单SR均100%。IE-09 Rule数量18−6的同seedV差仍为'+fmt(feasibility['IE09_rule_N18_minus_N6'])+'，支持“SR饱和仍可能存在得分空间”，不代表全菜单单调或混合方向检验。', '',
              '建议将E1定稿为“校准可行性＋完整四条件确认＋混合方向诊断”。保留数量17的较稳健LLM+Rule收益与数量27的点态收益，同时如实报告未分离的档位、数量19及RL执行器结果。若要继续理论验证，应先在独立开发集建立可区分的headroom代理、冻结强基线并核验相应前提，再用新的确认seed检验；不要重排旧条件、降低门禁、择优重跑或拟合f。是否启动新实验另行决定，本次未启动新仿真。', '',
              '## 9. 文件管理与复现', '',
              '完整A/B原始确认输出保留于原服务器，新增合并目录不覆盖任何既有文件。原始ZIP包含全部逐tick记录、动作、LLM日志、报告、completion、protocol、run_manifest和attempt审计。', '',
              '冻结主统计：analysis/frozen-merge-v1/combined_analysis.json、E1双设备确认汇总_v1.md；新增诊断：analysis/final-v1/final_analysis.json、本报告及figures/。', '',
              '归档SHA：A=716904d85a1398b96841b6a19429ec351e0c14c9200838b1b02982e1e38e0dba；B=6aea3600257615b129f911c255d1e5147532f5886de3343eb9ce018d76bc4435。主协议与两机owner身份由原冻结merge入口完整校验。', '',
              '所有图均来自相同120局主统计；附加指标不替代主结论。设备与数量条件绑定，跨设备比较须披露硬件和模型服务差异。分析版本新增，不覆盖冻结结果。']
    (args.output/'E1双机正式确认最终分析报告_v1.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figdir=args.output/'figures';figdir.mkdir()
    fig,ax=plt.subplots(figsize=(8,4.5))
    for arm,offset,label,color in [('llm',-.12,'LLM + Rule','#2878a5'),('llm-rl',.12,'LLM + RL','#e08c32')]:
        means=np.array([cells[n]['paired_gains'][arm]['mean'] for n in counts]);ci=np.array([cells[n]['paired_gains'][arm]['ci95'] for n in counts])
        ax.errorbar(np.arange(4)+offset,means,yerr=np.array([means-ci[:,0],ci[:,1]-means]),fmt='o',capsize=4,label=label,color=color)
    ax.axhline(0,color='black',linewidth=.8);ax.set_xticks(range(4),counts);ax.set_xlabel('Frozen IE-05 intruder count');ax.set_ylabel('Paired gain relative to fixed Rule baseline');ax.legend();ax.set_title('E1 confirmation: 10 paired seeds per condition, pointwise 95% CI');fig.tight_layout();fig.savefig(figdir/'paired_gains_95ci.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.5))
    for arm,label,color in [('llm','LLM + Rule','#2878a5'),('llm-rl','LLM + RL','#e08c32')]:
        for owner,ns,marker in [('device-a',[17,18],'o'),('device-b',[19,27],'s')]:
            ax.plot([1-cells[n]['calibration_V']['mean'] for n in ns],[cells[n]['paired_gains'][arm]['mean'] for n in ns],marker=marker,color=color,label=label+' / '+owner)
            for n in ns:ax.annotate(str(n),(1-cells[n]['calibration_V']['mean'],cells[n]['paired_gains'][arm]['mean']),xytext=(4,5),textcoords='offset points')
    ax.axhline(0,color='black',linewidth=.8);ax.set_xlabel('Independent calibration proxy H = 1 - fixed pure V');ax.set_ylabel('Confirmation mean paired gain');ax.legend(fontsize=8);ax.set_title('Descriptive headroom directions; not an isolated causal manipulation');fig.tight_layout();fig.savefig(figdir/'independent_calibration_headroom_direction.png',dpi=180);plt.close(fig)
    print(json.dumps({'cases':audit['cases'],'eligible':audit['eligible_cases'],'directions':direction,'correlations':correlation,'gain_sensitivity':[{k:v for k,v in x.items() if k not in ['score_layer_contributions_mean']} for x in supplemental]},ensure_ascii=False))


if __name__ == '__main__':
    main()
