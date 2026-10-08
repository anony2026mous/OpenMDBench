"""Evidence-only report for completed remote E3-v3; no engine/model calls."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def contrast(rows,a,b):
    seeds=sorted({r['seed'] for r in rows});counts=[];diff=[]
    for seed in seeds:
        group=[r for r in rows if r['seed']==seed];counts.append(len(group));value=0
        for r in group:
            ca=r[a] is not None and ((r[a]>.5)==r['gold_real']);cb=r[b] is not None and ((r[b]>.5)==r['gold_real'])
            value+=int(ca)-int(cb)
        diff.append(value)
    weights=np.random.default_rng(20261001).multinomial(len(seeds),np.ones(len(seeds))/len(seeds),size=20000)
    z=(weights@np.array(diff))/(weights@np.array(counts))
    return {'mean_accuracy_difference':sum(diff)/sum(counts),'ci95':np.quantile(z,[.025,.975]).tolist(),'seed_clusters':len(seeds),'paired':True}


def main():
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.campaign.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    result=read(root/'channel_analysis.json');rows=read(root/'channel_predictions.json');audit=read(root/'classification/dataset_audit.json');model=read(root/'numeric_model.json')
    if result['state']!='independent-confirmation-complete' or not result['source_unchanged'] or len(rows)!=400:raise ValueError('Not complete source-valid confirmation')
    if sha(root/'classification/dataset.json')!=audit['dataset_sha256']:raise ValueError('Dataset hash mismatch')
    if sha(root/'numeric_model.json')!=result['numeric_model_sha']:raise ValueError('Numeric model changed')
    if sum(r['gold_real'] for r in rows)!=200 or len({r['id'] for r in rows})!=400:raise ValueError('Unbalanced or duplicate events')
    paired={key:contrast(rows,'llm_p_real',key) for key in ['local_p_real','rule_p_real']}
    endpoints={}
    for endpoint in sorted({r['endpoint'] for r in rows}):
        group=[r for r in rows if r['endpoint']==endpoint];lat=[r['elapsed_seconds'] for r in group]
        endpoints[endpoint]={'calls':len(group),'errors':sum(r['llm_p_real'] is None for r in group),'median_seconds':float(np.median(lat)),'p95_seconds':float(np.quantile(lat,.95)),'max_seconds':max(lat)}
    summary={'result':result,'paired_accuracy_contrasts':paired,'endpoints':endpoints,'dataset_audit':audit,'numeric_selection':model['selection'],
        'CI_strict_channel':result['local_numeric']['accuracy_ci95'][1]<=.6 and result['LLM']['accuracy_ci95'][0]>=.85,
        'source_pool_seeds':len(read(root/'protocol.json')['confirmation_initial_seeds']),
        'raw_source_reuse':read(root/'acquisition_reuse_audit.json'),
        'manifest':{name:sha(root/name) for name in ['protocol.json','channel_analysis.json','channel_predictions.json','numeric_model.json','classification/dataset.json']}}
    lines=['# P0 E3：独立400事件观测通道判别报告','','## 结论范围','',
        f"当前局部数值对照正确率{result['local_numeric']['accuracy']:.2%}；LLM（同局部状态+8次真实接触历史）{result['LLM']['accuracy']:.2%}；同历史运动几何对照{result['strong_same_information_motion']['accuracy']:.2%}。",
        f"原冻结代码通道D1判定：{result['D1_channel_point_pass']}；同信息量D1判定：{result['D1_matched_information_point_pass']}；服务/解析错误{result['errors']}/400。",
        '', '测的是不同公开观测通道下的受控判别，不是在线自主识骗、LLM独占推理能力或高保真四门认证。保留强同信息量数值对照，通道门通过也不能覆盖其结果。',
        '', '## 1. 数据与开发/确认隔离','',
        '原10次开发窗口在400局中只有36/42类事件，未达到数值训练最低80平衡事件；依据开发覆盖率选8次，获得60/64类事件。此为公开开发阶段调整，未查看确认分类成绩，不冒称原稿已明确规定历史长度。',
        '开发seeds5101–5500，平衡训练120事件，4折按seed分组CV选择线性/二次L2模型，当前局部观测不含Goal、历史、身份和真值；模型在确认之前冻结。',
        'v2来源seeds5601–7200的1600局仅151/286类事件，按预算停在LLM调用之前。v3不改变任何门槛、输入/窗口、权重或提示，只扩展真实来源为5601–8800，逐文件hash复用未评分原轨迹和原数值模型。旧尝试保留。',
        f"确认候选池：{read(root/'candidate_audit.json')['counts']}；独立平衡选择200诱饵+200真实事件，共{len(audit['seed_clusters'])}个seed聚类。所有源局均有插桩与未插桩逐tick动作、物理/环境状态、broker及终局一致性审计。", 
        '', '## 2. 冻结判定与成绩','',
        '|判别器|准确率|95% seed-cluster CI|AUC|AUC 95%CI|','|---|---:|---|---:|---|']
    for name,key in [('局部数值模型','local_numeric'),('Qwen3.8-27B局部+历史','LLM'),('同历史运动几何','strong_same_information_motion')]:
        r=result[key];lines.append(f"|{name}|{r['accuracy']:.2%}|{r['accuracy_ci95']}|{r['auc']}|{r['auc_ci95']}|")
    lines+=['',f"门槛来自0930正文：数值≤60%，LLM≥85%。原代码完整请求门另要求无解析/服务错误；置信区间严格敏感性（局部上界≤60%且LLM下界≥85%）：{summary['CI_strict_channel']}。不把点门等同总体门槛被95%置信认证。",'',
        '|同事件配对准确率差|均值|95% seed-cluster CI|','|---|---:|---|']
    for key,name in [('local_p_real','LLM−局部数值'),('rule_p_real','LLM−同历史运动几何')]:
        r=paired[key];lines.append(f"|{name}|{r['mean_accuracy_difference']:.2%}|{r['ci95']}|")
    lines+=['','区间使用20,000次seed聚类重采样（随机种子20261001），事件在重采样cluster内等权；400事件不是400独立对局。配对差采用同一事件/seed的共同重采样权重，未相减两份独立CI。', '', '## 3. vLLM返回与审计','',
        '两个端点为同一Qwen3.8-27B的实例，不构成跨模型验证。请求temperature0、max_tokens128、enable_thinking=false；原始请求、正文返回、usage及错误逐事件保存。',
        '|实例|调用数|错误|中位秒|P95秒|最大秒|','|---|---:|---:|---:|---:|---:|']
    for k,r in endpoints.items():lines.append(f"|{k}|{r['calls']}|{r['errors']}|{r['median_seconds']:.3f}|{r['p95_seconds']:.3f}|{r['max_seconds']:.3f}|")
    lines+=['',f"数值模型CV选择：{model['selection']}。确认模型hash：`{result['numeric_model_sha']}`。原Grid源码前后hash一致：{result['source_unchanged']}。",'',
        '## 4. 理论产出的适用边界','',
        '本实验为C_info的行为探针：区分当前局部与重复接触通道，也直接核验运动信息能否被数值压缩。同信息量对照结果必须与LLM同时报告；若它也很准，应解释为公开运动信息的可利用性，而非LLM唯一优势。',
        '不直接测量信息bits、不估计KSG、不拟合f、不测Goal接口B_if，也不证明净混合部署增益。D3/接口机制、E1/headroom压力条件与归因参考组件有效性仍需各自独立实验，不能由D1分类替代。',
        '当前高保真IE05/IE09没有冻结的feint/genuine标签契约，不能将Grid本结果自动认证为高保真D1。角色定义按真实源轨迹，未修改引擎、场景、装备或评分。',
        '', '## 5. 文件位置','',f"运行根：`{root}`。",'',
        '`classification/dataset.json`及dataset_audit.json：冻结400事件与来源；`classification/responses/`：全部真实请求返回；`channel_predictions.json`：三对照逐事件分数；`channel_analysis.json`：主统计；`numeric_model.json`：冻结权重/CV；`protocol.json`：窗口/预算/hash；`acquisition_reuse_audit.json`：8002复制文件及原模型一致性；development与confirmation_sources：真实源轨迹及影子对照。']
    (out/'E3_D1_channel_report.md').write_text('\n'.join(lines)+'\n',encoding='utf8');(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'report':str(out/'E3_D1_channel_report.md'),'D1_channel':result['D1_channel_point_pass'],'D1_matched_information':result['D1_matched_information_point_pass']}))


if __name__=='__main__':main()
