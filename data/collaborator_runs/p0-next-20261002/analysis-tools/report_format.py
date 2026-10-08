"""Report paired format diagnostic without replacing the original confirmation."""
import argparse
from collections import Counter
import json
from pathlib import Path
from report_channel import contrast


def read(p):return json.loads(p.read_text(encoding='utf8'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.root;out=a.output;out.mkdir(parents=True,exist_ok=True)
    original=read(root/'E3-channel-v3/channel_analysis.json');rows=read(root/'E3-channel-v3/channel_predictions.json');diag=read(root/'E3-format-engineering-full/summary.json');new=read(root/'E3-format-engineering-full/results.json');mapping={r['id']:r for r in new}
    if len(rows)!=400 or set(mapping)!={r['id'] for r in rows}:raise ValueError('Different stimulus sets')
    paired=[]
    for r in rows:paired.append({**r,'original_p_real':r['llm_p_real'],'structured_p_real':mapping[r['id']]['p_real']})
    deltas={k:contrast(paired,'structured_p_real',k) for k in ['original_p_real','local_p_real','rule_p_real']}
    confusion=Counter((r['gold_real'],r['p_real']>.5) for r in new if r['p_real'] is not None)
    errors=Counter(r.get('error','OK') for r in read(root/'E3-channel-v3/classification/predictions.json'))
    result={'original':original,'structured_diagnostic':diag,'paired_accuracy_changes':deltas,'original_error_types':dict(errors),'confusion':{str(k):v for k,v in confusion.items()},'formal_D1_pass':False,'not_independent_confirmation':True}
    lines=['# E3 格式工程诊断：保留原确认，不更换门禁','','## 核心事实','',
        '原400事件确认中275/400响应无法解析，全部finish_reason=length：模型先输出解释，128-token到限前尚未完整输出JSON。HTTP/vLLM连接本身正常。关闭thinking不等于模型必然只输出JSON。',
        '依据vLLM结构化输出协议增加response_format/json_schema，保持同一模型、系统/用户提示、temperature0、128-token、8次历史、400个事件及原真值，不改数值对照。16例格式冒烟零错误；再测同400刺激为配对工程诊断，不是独立新确认。原275失败请求及原统计不覆盖、不剔除。',
        '', '|协议/对照|准确率|AUC|解析/服务错误|','|---|---:|---:|---:|',
        f"|原未约束LLM（正式确认，失败算错误）|{original['LLM']['accuracy']:.2%}|{original['LLM']['auc']:.4f}|{original['errors']}/400|",
        f"|格式约束LLM（同刺激工程诊断）|{diag['metrics']['accuracy']:.2%}|{diag['metrics']['auc']:.4f}|{diag['errors']}/400|",
        f"|当前局部数值对照（未改）|{original['local_numeric']['accuracy']:.2%}|{original['local_numeric']['auc']:.4f}|不适用|",
        f"|同历史运动几何（未改）|{original['strong_same_information_motion']['accuracy']:.2%}|{original['strong_same_information_motion']['auc']:.4f}|不适用|",
        '',f"格式约束LLM准确率95%CI：{diag['metrics']['accuracy_ci95']}；AUC95%CI：{diag['metrics']['auc_ci95']}。",'',
        '## 判定与解读','',
        '格式工程修复有效：400次全部形成可解析、一致标签/概率，不能将原23.5%总正确率解释成模型纯识别能力。但这不使D1通过：数值对照87%高于60%上限；约束格式后的LLM固定0.5截点正确率78.25%也低于85%。强同信息量运动对照93.5%必须保留。',
        'LLM概率排序AUC约0.960，显示有较强判别信号；固定截点下200个诱饵均判对，而200个真实目标仅113个判对、87个漏判，提示概率/判定偏保守。不能在这400个已看结果的刺激上寻找更有利截点并重新宣称通过。若后续校准，要只在独立开发集选择、冻结，再在新确认集检验；即使LLM达到85%，当前数值通道的87%仍不满足D1前半门。',
        '本结果只覆盖当前真实轨迹/可见性筛选产生的受控刺激分布，不能证明引擎任何状态都没有信息不对称。格子里两类都编码为4，不等于完整当前观测统计不可分；位置、观察者状态、锁定及既往动作痕迹都可能产生代理线索。后续需要开发集特征审计、合适的状态匹配/前接口采集，而不是隐藏实际合法输入以获得低对照正确率。',
        '', '|同事件准确率配对差|均值|95% seed-cluster CI|','|---|---:|---|']
    for k,name in [('original_p_real','格式约束−原输出'),('local_p_real','格式约束LLM−局部数值'),('rule_p_real','格式约束LLM−同历史数值')]:
        r=deltas[k];lines.append(f"|{name}|{r['mean_accuracy_difference']:.2%}|{r['ci95']}|")
    lines+=['', '20,000次共同seed聚类重采样，固定随机种子20261001；同刺激配对，不是两独立批次成绩相减。', '', '## 与高保真队列的关系','',
        '本诊断没有修改运行中的E1冻结代码、模型服务、引擎或场景。E1单次生成预算是1024，不是这里128，不能据本次失败率推断其失败率；进入LLM阶段须核查自身raw响应/usage/解析统计，若触发工程门，应保留批次并以独立新协议修复。不得在后台悄悄修改冻结请求。',
        '', '原确认见E3-channel-v3；格式冒烟见E3-format-engineering-smoke；完整配对诊断见E3-format-engineering-full。完整请求/原始响应与协议均保留。']
    (out/'E3格式工程诊断与门禁判定.md').write_text('\n'.join(lines)+'\n',encoding='utf8');(out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(str(out/'E3格式工程诊断与门禁判定.md'))


if __name__=='__main__':main()
