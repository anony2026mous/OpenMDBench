"""Analyze only actually retained remote P0-next observations, no imputation."""
import argparse
from pathlib import Path
import numpy as np
from common import read,write,estimate
from count_campaign import outcome


def bootstrap_condition(arrays,indices):
    pure=np.array([arrays[k] for k in ['rule','rl','pure-llm']]);pm=pure.mean(1);arm=int(np.argmax(pm))
    best=pure[:,indices].mean(2).max(0)
    result={'Vm':float(pm.max()),'Vm_arm':['rule','rl','pure-llm'][arm]}
    gains={}
    for name in ['llm','llm-rl']:
        values=np.array(arrays[name]);boot=values[indices].mean(1)-best;gains[name]=boot
        result[name]={'V':float(values.mean()),'delta_V':float(values.mean()-pm.max()),'ci95':np.quantile(boot,[.025,.975]).tolist()}
    return result,gains


def analyze(root):
    report=root/'analysis';report.mkdir(parents=True,exist_ok=True);summary={}
    lines=['# P0 远程下一阶段：自动状态与测量报告','','只对实际完成的独立批次核算。运行完成不等于门禁通过。']
    e1=root/'E1-count'
    if (e1/'status.json').exists():
        status=read(e1/'status.json');summary['E1_status']=status;lines+=['','## E1：压力/headroom诊断','',f"状态：`{status['state']}`。"]
    if (e1/'calibration_rule_analysis.json').exists():
        rows=read(e1/'calibration_rule_analysis.json');summary['E1_rule_calibration']=rows
        lines+=['','|场景族|入侵数|Rule SR|平均V|完整波次/实体|','|---|---:|---:|---:|---|']
        for r in rows:lines.append(f"|{r['family']}|{r['count']}|{r['SR']['mean']:.1%}|{r['V']['mean']:.4f}|{r['eligible']}|")
    if (e1/'status.json').exists() and read(e1/'status.json')['state']=='confirmation-complete':
        tiers=read(e1/'frozen_tiers.json');seeds=read(e1/'protocol.json')['confirmation_seeds'];rng=np.random.default_rng(20261001);idx=rng.integers(0,len(seeds),(20000,len(seeds)))
        comparisons=[];boots={}
        lines+=['','|场景族|校准目标SR|确认Vm|Vm架构|其确认SR|ΔV LLM+Rule及95%CI|ΔV LLM+PPO及95%CI|','|---|---:|---:|---|---:|---|---|']
        for row in tiers:
            records={arm:[outcome(e1/'confirmation'/row['public_id']/f'{arm}-strong-g0'/f'seed-{s}'/'report.json',row) for s in seeds] for arm in ['rule','rl','pure-llm','llm','llm-rl']}
            arrays={arm:[r['V'] for r in records[arm]] for arm in records};result,gains=bootstrap_condition(arrays,idx)
            sr=float(np.mean([r['SR'] for r in records[result['Vm_arm']]]))
            result.update(family=row['family'],count=row['count'],calibration_target_SR=row['target_SR'],SR_selected_score_best_pure=sr,H_SR_proxy=1-sr,D2_point_pass=.4<=sr<=.85,wave_complete=all(r['eligible'] for rs in records.values() for r in rs),raw=records)
            comparisons.append(result);boots[(row['family'],row['target_SR'])]=gains
            lines.append(f"|{row['family']}|{row['target_SR']:.0%}|{result['Vm']:.4f}|{result['Vm_arm']}|{sr:.0%}|{result['llm']['delta_V']:.4f} {result['llm']['ci95']}|{result['llm-rl']['delta_V']:.4f} {result['llm-rl']['ci95']}|")
        adjacent=[]
        for f in sorted({r['family'] for r in tiers}):
            for hi,lo in [(.4,.6),(.6,.8),(.4,.8)]:
                for arm in ['llm','llm-rl']:
                    z=boots[(f,hi)][arm]-boots[(f,lo)][arm]
                    a=next(r[arm]['delta_V'] for r in comparisons if r['family']==f and r['calibration_target_SR']==hi);b=next(r[arm]['delta_V'] for r in comparisons if r['family']==f and r['calibration_target_SR']==lo)
                    adjacent.append({'family':f,'higher_nominal_headroom_target':hi,'lower_nominal_headroom_target':lo,'arm':arm,'difference':a-b,'ci95':np.quantile(z,[.025,.975]).tolist()})
        summary['E1_comparisons']=comparisons;summary['E1_tier_contrasts']=adjacent
        lines+=['','实际确认Vm每次配对seed重采样内重新取三个纯栈的最大均值；三档对比共享seed索引。校准名义档位不保证确认SR仍落在目标点，实际headroom代理单独列示。当前高保真D1未认证，结果不构成四门正区证明。']
    e3=root/'E3-channel'
    if (e3/'channel_analysis.json').exists():
        data=read(e3/'channel_analysis.json');summary['E3']=data
        lines+=['','## E3：独立400事件通道判别','','|判别器|准确率|95% seed-cluster CI|AUC|','|---|---:|---|---:|']
        for name,key in [('当前局部数值模型','local_numeric'),('LLM：局部+历史','LLM'),('同信息量运动几何','strong_same_information_motion')]:
            r=data[key];lines.append(f"|{name}|{r['accuracy']:.2%}|{r['accuracy_ci95']}|{r['auc']}|")
        lines+=['',f"通道D1点门：{data['D1_channel_point_pass']}；同信息量D1点门：{data['D1_matched_information_point_pass']}；错误数：{data['errors']}。",'',data['scope']]
    elif (e3/'status.json').exists():summary['E3_status']=read(e3/'status.json');lines+=['','E3状态：'+str(summary['E3_status'])]
    else:lines+=['','E3尚无完整确认分析；不生成估计值。']
    write(report/'summary.json',summary);(report/'P0_remote_report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(str(report/'P0_remote_report.md'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);a=p.parse_args();analyze(a.campaign.resolve())


if __name__=='__main__':main()
