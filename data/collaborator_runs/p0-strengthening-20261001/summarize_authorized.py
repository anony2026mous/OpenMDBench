"""Current authorized P0 handoff, including every unsuccessful protocol stage."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
from common import read,write,digest


def summarize(root):
    e1=root/'E1-authorized-20261001'; v1=root/'E3-prospective-20261001'; v2=root/'E3-prospective-v2-20261001'
    status={'updated_utc':datetime.now(timezone.utc).isoformat(),'E2':'analysis-complete',
            'E1':read(e1/'status.json') if (e1/'status.json').exists() else read(e1/'progress.json'),
            'E3_v1':read(v1/'status.json'),'E3_v2':read(v2/'status.json'),
            'old_negative_results_retained':True,'formal_engine_edited':False,
            'all_P0_success_criteria_passed':False}
    a1=read(v1/'classification/analysis.json');a2=read(v2/'classification/analysis.json')
    control=read(v2/'original-prompt-control/analysis.json');pair=read(v2/'prompt_comparison.json')
    robustness=read(v2/'classification/numeric_robustness.json')
    status['E3_v2_prompt_contrast']=pair
    if 'rule_rows' in status['E1']:
        status['E1']={k:status['E1'][k] for k in ['state','saturated_families','reason','confirmation_started','original_source_unchanged'] if k in status['E1']}
    write(root/'P0_authorized_status.json',status)
    lines=['# 角色C：P0 授权续实验与独立确认汇总','',f"核算 UTC：{status['updated_utc']}。",'',
      '本报告对应 20260930 强化清单 P0=E1/E2/E3，不是旧的工程 P0。正式引擎、权威 Git 分支、评分、武器、速度和原始场景未修改。',
      '所有正向、不显著、负向和入场不合格结果均保留；没有按模型成绩选择 seed 或删去失败确认轮次。','',
      '## 一、结论先行','',
      '1. **Goal 通道有效性**：既有 P2 的完整 Goal 相对 hold 有显著配对增益，E2 的四点代理形状已重算并绘图。它是接口作用证据，不是 LLM 胜过纯基线或解析 f 已拟合。',
      f"2. **LLM 判别方法改进有效**：在新的同一 400 事件确认集，运动规则指导提示词使正确率从 {pair['original']['accuracy']:.2%} 升至 {pair['rule_guided']['accuracy']:.2%}；配对提升 {pair['accuracy_delta']['mean']:.2%}，95% CI {pair['accuracy_delta']['ci95']}。",
      '3. **D1 信息不对称没有建立**：运动数值规则也能高准确率判别，故不能用“LLM 超过85%”代替规则≤60%与LLM≥85%的联合门禁，更不能把判别成绩写成在线自主识骗率。',
      f"4. **E1 当前状态**：`{status['E1'].get('state',status['E1'].get('phase'))}`。完整 headroom 配对比较只有在三档标定合格后才启动。",'',
      '## 二、E1：受控波次标定','',
      '独立副本有 11 个预定设置：IE-05 南侧3个来袭延时0/50/100/150/200；IE-09既有第二组2个UAV出现于0/100/200/250/300/400。实际总来袭分别是9与6，装备与起点不变。',
      '原始时序副本与原版各完整回归一次：IE-05=973 tick、IE-09=999 tick，所有已记录实体状态指纹与策略评分卡一致。首次记录器兼容错误的4次尝试隔离保留，不计入实验结果。',
      '规则标定为11×10=110局，seeds1101–1110，32个独立对局进程。标定仅看纯基线。候选若有任意seed在未来波次出现前提前终局，整个设置标记不合格，不删除该seed或修改终局。',
      '若可达40%/60%/80%三档，再选择并冻结同一场景的纯基线臂，确认用独立seeds1201–1210，三栈配对180局。高保真执行器是固定PPO，不是Grid MAPPO；纯PPO与Goal-conditioned PPO的权重和观测契约分别记录。',
      '若规则在每个有效设置都全胜，则最好纯基线在该标定集无法被降到目标档。此时按已授权方案停止确认，不擅自增添来袭数量/武器/速度等新旋钮。',
      '论文 headroom 是 (V*−V_m)/(V*−V_min)；实验1−SR仅为D2代理，1−V仅为评分上界gap。SR饱和不等于连续V没有可提升空间；未认证oracle时不能冒充精确理论余量。','',
      '最新 E1 逐局核算：`results/E1-authorized-analysis/report.md`（只有标定/确认终态后生成）。当前队列记录：`E1-authorized-20261001/progress.json`。','',
      '## 三、E2：剂量—增益代理形状','',
      '|批次|数据规模|主要量|证据边界|','|---|---:|---|---|',
      '|P2，512–521|2栈×4剂量×10seed=80局|rule-rl strong−hold +0.4567，CI[0.2467,0.6633]；llm-rl +0.5367，CI[0.3167,0.7234]|接口阻断与开放的因果差；剂量是单位可用性，不是bits|',
      '|P1，501–510|6臂×10seed=60局|ΔV_A=−0.2133；ΔV_B=−0.2400|独立部署排名，不与P2合并成优势统计|','',
      '规则规划mask1均值0.8333高于strong0.6700，但相邻差CI含0：只能报告样本均值非单调，不能宣称显著证伪单调函数。E2支持方向性代理，不估计解析 f，也不把MI关联估计等同于干预效果。','',
      '## 四、E3：完整刺激集与独立提示词确认','',
      '用户额外授权后，在当前发布Grid源码上补采两批真实轨迹。每批预先固定400个源seed，规则+GOAI，medium/continuous、plan_interval=10；没有使用缺失的MAPPO训练权重。',
      '每条轨迹都有一次未加观测记录器的影子对局，逐tick环境状态、broker、动作、终局与全部metrics精确一致。每批400源+400影子=800次对局；两批均无工程失败，源码哈希不变。',
      '只从真实已经可观测的接触里抽取三个观测帧窗口；同一seed/接触/tick不重用。匿名运动与局部网格进入请求，角色真值与原始接触ID仅用于离线核算。',
      'v1固定seeds1301–1700；v2固定seeds1701–2100。每批各200诱饵/200真实事件；不同批次不拼接。v2只进行一次提示词改进，且在新轨迹/新响应之前冻结。',
      'v2提示词明确说明随机停顿/侧移不等于诱饵，并给出平均heading的朝港口投影计算方法。这是**可观测运动规则指导**，不是新情报、真值标签、已认证oracle或无规则指导的自主识骗。',
      '两个 Qwen3.8-27B 实例分配调用，enable_thinking=false、temperature=0、max_tokens=128。每批主判别各400次，v2同事件原提示词附加对照另400次，共1200次新真实调用；全部无服务/JSON错误。',
      '同事件原提示词对照加入于v2响应队列启动后、汇总结果读取前，属于附加诊断对照，并非原始预注册主终点；所有原始请求/响应均保存。','',
      '|独立批次/对照|事件数|seed聚类|规则正确率|LLM正确率及95% CI|LLM AUC|D1整体|',
      '|---|---:|---:|---:|---|---:|---|']
    for name,analysis in [('v1 原提示词',a1),('v2 运动规则指导',a2),('v2 同事件原提示词附加对照',control)]:
        m=analysis['llm_all_attempts_accuracy']; r=analysis['rule']
        lines.append(f"|{name}|400|{r['n_seed_clusters']}|{r['accuracy']:.2%}|{m['accuracy']:.2%}；{m['accuracy_ci95']}|{m['auc']:.4f}|未通过|")
    lines+=['',f"v2与其同事件原提示词对照：正确率配对差 {pair['accuracy_delta']}；AUC配对差 {pair['auc_delta']}。seed-cluster bootstrap=20,000次，所有同seed事件/判别器共同重采样。",
      f"v2 诱饵正确{pair['rule_guided']['confusion']['feint']['correct']}/200、真实目标正确{pair['rule_guided']['confusion']['real']['correct']}/200。因此仍有43/200真实目标误判为诱饵，不能用整体89.25%掩盖这种不对称错误。",'',
      '### 连续数值规则稳健性检查','',
      '原规则把投影压成0/0.5/1概率，会丢失排序分辨率；LLM连续概率的AUC更高不能直接解释为独占信息。增加不调参、不改阈值的连续投影/方向余弦对照，分类符号与原规则一致。',
      '|v2 评分器|正确率|AUC|','|---|---:|---:|']
    for key,label in [('rule_p_real','原二值运动规则'),('continuous_projection','连续投影'),('continuous_cosine','方向余弦'),('llm_p_real','LLM')]:
        r=robustness['controls'][key]; lines.append(f"|{label}|{r['accuracy']:.2%}|{r['auc']:.4f}|")
    lines+=['','连续投影AUC已接近LLM，不能夸大LLM对强数值规则的排序优势。稳健性检查为事后诊断，原主对照、门槛和原始响应均未替换。','',
      '## 五、对论文可以支持与不能支持的主张','',
      '- 可以支持：完整Goal通道有可测的干预效果；运动描述/决策说明会显著影响LLM判别；完整事件集、观测无扰动重放和seed聚类统计可复现；理论的入场条件必须实测而非默认通过。',
      '- 不能支持：当前Grid已实现D1信息不对称；LLM在线自主识骗率89.25%；混合栈已在E1三档占优；已拟合f解析式；已得到认证oracle或严格的理论证明。',
      '- 本次不新增E4–E9，不把新P0当作旧P3a/P3b归因实验，也不将未测D1′/D3自动写为通过。',
      '- 如果E1单旋钮最终不达标，后续需另行授权更强压力旋钮并预注册标定，或明确更改主终点协议；若要使D1成为正区，应由场景设计提供不可由同份运动数据直接恢复的真实语义信息，不应削弱数值对照。','',
      '## 六、文件导航','',
      '`E1-authorized-20261001/`：独立实验引擎、变体/协议manifest、等价性回归、逐局标定/确认。',
      '`results/E2/`：代理曲线、逐seed数值、原始批次复核报告。',
      '`E3-prospective-20261001/`：首轮400事件及全部400源/400影子轨迹、原始模型响应。',
      '`E3-prospective-v2-20261001/`：独立确认及同事件原提示词对照、prompt_comparison.json、连续数值稳健性诊断。',
      '`frames/`与`results/E3-expanded/`：原50条发布轨迹的精确重放/66事件历史实测，保持独立，不替换或删除。',
      '`P0_authorized_status.json`：最新机器可读状态；旧P0_status.json是前一阶段快照，不代表本次最新进度。',
      '代码及结果只在独立实验目录中新增；未提交/推送Git，未修改模型服务启动参数。']
    if status['E1'].get('state')=='authorized-knob-infeasible':
        lines+=['','## 七、E1最终核算补充','',
           '110/110局完整结束，无仿真abort；原生终局107局防守成功、3局失败。统计器的 attacker_success 别名漏识别已修正，这3局仍计入失败，原始分数和文件未修改、没有重跑。',
           'IE-05五个设置SR=100%/90%/100%/90%/90%；IE-09完整波次的四个设置均100%。300/400tick设置有提前终局遗漏后续波次，整档不合格，所有数据仍保留。',
           '这些是10seed点估计的标定结论，不是证明总体成功概率必为上述数值。原SR三档的180局混合栈确认未启动，不把未入场标定当作正区因果验证。',
           '固定最佳纯基线按全菜单平均SR选择：规则平均IE-05=0.94、IE-09=1.00；同时覆盖40/60/80三档的任何固定臂在5/4个有效设置中平均最多0.76/0.70。因此当前菜单不能既称“最佳纯基线”又满足三个目标档。完整界限在 coverage_bound_audit.json。',
           '下一步需要新的明确授权：只在独立副本增加另一种压力旋钮（建议相同装备的来袭数量）并预注册；D1还需要独立的语义信息通道设计授权，单改运动措辞无法建立信息不对称。']
    (root/'P0授权续实验与独立确认汇总报告.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print({'E1':status['E1'].get('state',status['E1'].get('phase')),'E3_v2':a2['llm_all_attempts_accuracy']['accuracy'],'D1':False})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).parent);a=p.parse_args();summarize(a.root)
