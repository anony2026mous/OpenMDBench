"""Read-only analysis of a separately retained complex replication."""
import argparse
from pathlib import Path
from common import read, write


def report(campaign):
    state = read(campaign / 'status.json') if (campaign / 'status.json').exists() else {'state': 'incomplete'}
    protocol = read(campaign / 'protocol.json')
    lines = ['# Grid P0 E3：困难难度独立复测', '',
        '本批次由用户在已知medium未通过后提出，是公开的难度敏感性复测，非盲选难度；medium数据与结论保留。', '',
        '## 协议', '',
        '当前远程原生complex/continuous，Rule+GOAI生成轨迹、间隔10；插桩/影子动作与状态逐tick一致。'
        '完整合法当前局部数值对照、固定8次公开历史、同历史运动对照均保留。'
        'LLM为实际Qwen3.8-27B双实例，temp0、128-token、关闭thinking；JSON schema修复在本批次前冻结。', '',
        '开发11001–11800；确认来源12001–15200，预声明不足时追加15201–16800；不复用中等事件或权重。'
        '固定200+200事件、p_real>0.5分类，20,000次seed聚类bootstrap。', '',
        f"当前状态：`{state['state']}`。", '']
    if (campaign / 'channel_analysis.json').exists():
        result = read(campaign / 'channel_analysis.json')
        lines += ['## 结果', '', '|判别器|准确率|95%CI|AUC|', '|---|---:|---|---:|']
        for key, label in [('local_numeric', '当前局部数值'), ('LLM', 'LLM当前局部+历史'), ('strong_same_information_motion', '同历史运动几何')]:
            m = result[key]
            lines.append(f"|{label}|{m['accuracy']:.2%}|{m['accuracy_ci95']}|{m['auc']:.4f}|")
        lines += ['', f"D1通道点门通过：{result['D1_channel_point_pass']}；同信息量通过：{result['D1_matched_information_point_pass']}；"
                  f"严格置信区间敏感性通过：{result['D1_CI_strict_pass']}。",
                  f"工程错误：{result['errors']}/400；工程门通过：{result['engineering_gate_pass']}；源代码未变：{result['source_unchanged']}。", '',
                  '60%/85%为论文点阈值，95%CI另报，不冒称点门等同总体置信认证。失败输出算错误。'
                  '同信息量数值对照必须与LLM同时解读，不能用通道门替代它。', '',
                  '## 对中等难度的比较边界', '',
                  'medium局部数值87.00%、运动93.50%；medium原LLM23.50%受275次格式失败影响；'
                  '同400刺激格式诊断LLM78.25%、AUC0.96015、零解析失败，不是新的独立确认。'
                  'complex是全新独立批次，不能把难度与格式修复混合后的变化全部归因于难度，也不能拼接统计。']
        if not result['D1_channel_point_pass']:
            lines += ['', '## 下一步', '',
                '困难复测仍未满足D1：继续E1；分析已有Grid开发数据代理线索/采样与先前动作；'
                '审计高保真诱饵契约；小规模开发验证；冻结后独立新确认。保留本次失败，不再凭确认结果改阈值。']
        else:
            lines += ['', '## 结论范围', '',
                '通过仅针对当前受控Grid刺激分布与预设通道，不代表在线识骗、高保真D1或四门全部通过。'
                '若同信息量对照未通过，不能据此宣称LLM独占优势。']
    else:
        lines += ['未形成400事件确认成绩，不冒称D1通过/失败；当前可用性或工程问题见status、campaign.log。']
    lines += ['', '## 留存位置', '', f'远程数据：`{campaign}`。',
              'protocol.json、numeric_model.json、development_events.json、candidate_audit.json、'
              'classification/dataset.json、classification/responses/、channel_predictions.json及原始源轨迹保留。']
    out = campaign / 'reports'
    out.mkdir(exist_ok=True)
    (out / 'E3_complex_D1_report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    write(out / 'summary.json', {'status': state, 'protocol': protocol})
    print(str(out / 'E3_complex_D1_report.md'), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--campaign', type=Path, required=True)
    report(parser.parse_args().campaign)
