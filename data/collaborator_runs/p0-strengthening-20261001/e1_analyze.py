"""All-settings E1 audit and seed-paired confirmation analysis, never pooled."""
import argparse
from pathlib import Path
import json
import math
from common import read, write, estimate, digest
from e1_full_campaign import outcomes


def wilson(p,n):
    z=1.959963984540054
    denominator=1+z*z/n
    center=(p+z*z/(2*n))/denominator
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denominator
    return [center-half,center+half]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--campaign',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    state=read(a.campaign/'status.json')
    manifest=read(a.campaign/'variant_manifest.json')
    rule=read(a.campaign/'calibration_rule_analysis.json')
    allrows=[]
    for r in rule:
        pairs=[outcomes(read(a.campaign/'calibration-rule'/r['public_id']/'rule'/f'seed-{s}'/'report.json'))
               for s in manifest['calibration_seeds']]
        if r['SR']['mean']!=sum(p[0] for p in pairs)/len(pairs):
            raise ValueError('Calibration statistic does not match reports')
        allrows.append({**r,'SR_wilson_ci95':wilson(r['SR']['mean'],len(pairs)),
                        'headroom_SR':1-r['SR']['mean'],'headroom_V':1-r['V']['mean']})
    result={'state':state['state'],'rule_calibration':allrows,
            'coverage_bound_audit':read(a.campaign/'coverage_bound_audit.json') if (a.campaign/'coverage_bound_audit.json').exists() else None,
            'reader_correction':read(a.campaign/'reader_correction.json') if (a.campaign/'reader_correction.json').exists() else None,
            'headroom_definitions':{'headroom_SR':'1 minus observed native binary success rate; D2 proxy',
                'headroom_V':'1 minus mean score, a score-ceiling gap proxy, NOT a certified oracle normalized gap',
                'paper_normalized_headroom':'(V_star - V_m)/(V_star - V_min); V_star not certified by this experiment'},
            'equivalence':read(a.campaign/'equivalence_gate.json'),
            'protocol_sha256':digest(a.campaign/'protocol.json'),
            'source_integrity_unchanged':all(digest(Path(manifest['repo'])/'openmd/source-code/source_codes'/n)==sha
                    for n,sha in manifest['original_source_hashes'].items()),
            'confirmation':[],
            'limitations':['Rule calibration is a pure-baseline lower bound, not a hybrid outcome.',
                           'Per-setting 10 seeds do not give +/-3 percentage point population precision.',
                           'Pressure timing intervention does not isolate headroom as a causal mediator.',
                           'No pooled inference across scenes or prior P0/P1/P2/P3a batches.']}
    if state['state']=='confirmation-complete':
        selected=read(a.campaign/'frozen_tiers.json')
        seeds=manifest['confirmation_seeds']
        for row in selected:
            arms={arm:[outcomes(read(a.campaign/'confirmation'/row['public_id']/arm/f'seed-{s}'/'report.json'))
                    for s in seeds] for arm in [row['arm'],'llm','llm-rl']}
            baseline=arms[row['arm']]
            item={'family':row['family'],'delay_ticks':row['delay_ticks'],'target_SR':row['target_SR'],
                  'baseline_arm':row['arm'],'SR':estimate([x[0] for x in baseline]),
                  'V':estimate([x[1] for x in baseline]),'hybrids':{}}
            for arm in ['llm','llm-rl']:
                item['hybrids'][arm]={'SR':estimate([x[0] for x in arms[arm]]),
                    'V':estimate([x[1] for x in arms[arm]]),
                    'delta_SR':estimate([x[0]-b[0] for x,b in zip(arms[arm],baseline)]),
                    'delta_V':estimate([x[1]-b[1] for x,b in zip(arms[arm],baseline)])}
            result['confirmation'].append(item)
        # Re-sample complete seed vectors; high/low difference keeps all arms and tiers paired.
        result['tier_contrasts']=[]
        for family in sorted({r['family'] for r in selected}):
            tiers=sorted([r for r in selected if r['family']==family],key=lambda r:r['target_SR'])
            lo,hi=tiers[0],tiers[-1] # SR low => headroom high.
            for arm in ['llm','llm-rl']:
                differences=[]
                for seed in seeds:
                    def gain(r):
                        def v(k):
                            return outcomes(read(a.campaign/'confirmation'/r['public_id']/k/f'seed-{seed}'/'report.json'))[1]
                        return v(arm)-v(r['arm'])
                    differences.append(gain(lo)-gain(hi))
                result['tier_contrasts'].append({'family':family,'arm':arm,
                     'high_headroom_minus_low_headroom_delta_V':estimate(differences)})
    write(a.output/'analysis.json',result)
    lines=['# E1：已授权波次时序实验完整核算','',f"执行状态：`{state['state']}`。",'',
           '## 协议与检查','',
           '只在独立引擎副本中新增波次时序变体。原始 Python、catalog、武器、速度、实体装订、设施、评分和终局不变；无情报简报文本一致。',
           '标定 seeds 1101–1110；独立确认 seeds 1201–1210。目标是原生二元终局 SR=40%/60%/80%，容差±3个百分点。',
           f"原始源码哈希未变化：{result['source_integrity_unchanged']}；两场景完整逐 tick 实体状态和评分卡等价性通过。",'',
           '## 所有时序设置的规则基线标定','',
           '|场景|第二组时刻|n|终局 SR|Wilson 95% CI|平均 V|V 的 seed-bootstrap 95% CI|波次有效性|',
           '|---|---:|---:|---:|---|---:|---|---|']
    for r in allrows:
        lines.append(f"|{r['family']}|{r['delay_ticks']}|10|{r['SR']['mean']:.0%}|{r['SR_wilson_ci95']}|{r['V']['mean']:.5f}|{r['V']['ci95']}|{'全部来袭入场' if r['treatment_eligible'] else '有提前终局遗漏波次，不可用于标定'}|")
    lines+=['','## 结论边界','']
    if state['state']=='authorized-knob-infeasible':
        lines+=['预定的单一波次时序旋钮未能实现原协议要求的三个 SR 档位。因此没有把这些设置改名为合格档位，也没有启动不满足入场条件的 180 局确认。',
                '若同一场景族所有设置的规则基线均为100%，则“最好纯基线”的标定成功率不可能低于100%；继续更换纯基线也不能制造40%/60%/80%档。',
                '这限定的是当前载体和旋钮的可用性，不是已经证伪或证实完整的分层定律。连续 V 仍有可提升空间，不能把它冒充二元 SR。',
                '下一步若仍以三档 SR 为主终点，必须另外授权并预注册压力旋钮（如固定装备的实体数量）；不得调整评分、挑选 seed 或把来袭推迟到终局后。']
        if result['reader_correction']:
            lines+=['','统计器曾漏识别原生终局别名 attacker_success；其 outcome=intruder_success 表明防守失败。已补齐解析，把3局计为防守失败；全部110局无仿真abort，0局重跑，原始report/completion/hash不变。首次统计门禁错误与冻结旧代码均保留。',
                    'IE-05五个设置的实测SR为90%–100%；IE-09四个完整波次设置均100%。IE-09的300/400设置有部分seed提前结束且未来波次未入场，整个设置判为不合格。',
                    '固定最佳纯臂的全菜单平均SR至少等于规则基线。要同时覆盖40/60/80三档，在5个设置中其平均SR至多为(0.4+0.6+0.8+1+1)/5=0.76，低于IE-05规则的0.94；在4个有效设置中至多为0.70，低于IE-09规则的1.00。这是本冻结标定菜单的确定性不可达界，不是总体成功率定理。',
                    '因此无需花费模型预算再挑选一个更弱纯臂来凑档；那样的臂不能按已冻结准则叫“最佳纯基线”。未经新授权没有修改未来波次终局逻辑、增加兵力或改评分。']
    else:
        lines+=['独立确认的配对 SR、V 与 ΔV 全量结果见 analysis.json；须同时核算正向、反向与不显著设置。']
    lines+=['','## 记录位置','',f'完整远程实验根目录：`{a.campaign}`。',
            '理论公式使用 (V*−V_m)/(V*−V_min) 的 oracle 归一化余量；本实验的 1−SR 和 1−V 分别只是终局/评分上界代理，不能混用或宣称已认证 oracle。',
            '`calibration-rule/<变体>/rule/seed-<seed>/report.json` 是逐局评分；同目录有 episode.jsonl、stdout.log、completion.json。',
            '`variant_manifest.json` 与 `protocol.json` 冻结代码、场景、模型配置、权重和全部 seed。',
            '首次记录器错误对局单列保留在 equivalence/；修正后的成功回归在 equivalence-v2/，失败不进入统计。']
    (a.output/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,3.7))
    for family in sorted({r['family'] for r in allrows}):
        subset=sorted([r for r in allrows if r['family']==family and r['treatment_eligible']],key=lambda r:r['delay_ticks'])
        x=[r['delay_ticks'] for r in subset]
        axes[0].plot(x,[r['SR']['mean'] for r in subset],'o-',label=family)
        means=[r['V']['mean'] for r in subset]
        errors=[[r['V']['mean']-r['V']['ci95'][0] for r in subset],
                [r['V']['ci95'][1]-r['V']['mean'] for r in subset]]
        axes[1].errorbar(x,means,yerr=errors,fmt='o-',capsize=3,label=family)
        invalid=[r for r in allrows if r['family']==family and not r['treatment_eligible']]
        if invalid:
            axes[0].scatter([r['delay_ticks'] for r in invalid],[r['SR']['mean'] for r in invalid],marker='x',color='grey',label='Ineligible: missed wave')
            axes[1].scatter([r['delay_ticks'] for r in invalid],[r['V']['mean'] for r in invalid],marker='x',color='grey',label='Ineligible: missed wave')
    for target in manifest['targets']:
        axes[0].axhline(target,color='grey',alpha=.4,linestyle=':')
    axes[0].set(xlabel='Delayed group spawn tick',ylabel='Native terminal success rate',ylim=(0,1.06))
    axes[1].set(xlabel='Delayed group spawn tick',ylabel='Continuous score V (seed-bootstrap 95% CI)',ylim=(0,1.03))
    axes[1].legend(fontsize=8,loc='lower right')
    fig.tight_layout(); fig.savefig(a.output/'calibration.png',dpi=180); fig.savefig(a.output/'calibration.svg')
    print(json.dumps({'state':state['state'],'n_settings':len(allrows),'n_confirmation':len(result['confirmation'])}))


if __name__=='__main__':
    main()
