"""Execute the unchanged remote route selector on actual scene tags/ticks."""
import argparse
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import yaml


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    engine=a.repo/'openmd/source-code/source_codes';os.environ['OPENMDBENCH_ROOT']=str(engine)
    sys.path[:0]=[str(engine),str(a.repo/'openmd/code/eval')]
    import attack_driver
    if not Path(attack_driver.__file__).resolve().is_relative_to(a.repo):raise ValueError('Wrong driver')
    rows=[]
    for slug in ['ie_06_decoy_mixed','ie_11_decoy_screen']:
        folder=engine/'scenarios/formal'/slug
        s=yaml.safe_load((folder/'scenario.yaml').read_text())['scenario'];profile=yaml.safe_load((folder/'agents.yaml').read_text())
        dummy=SimpleNamespace(routes=tuple(profile['attack']['routes']))
        for e in s['entities']:
            if 'decoy' not in e.get('tags',[]):continue
            for tick in [0,149,150,200]:
                route=attack_driver.AttackProfileDriverV2._route_for(dummy,e['tags'],tick)
                declared=[r for r in dummy.routes if r.get('match_tag')=='decoy' and tick>=r.get('start_tick',0) and (r.get('until_tick') is None or tick<r['until_tick'])]
                rows.append({'scene':slug,'entity':e['id'],'tick':tick,'tags':e['tags'],'actual_route':route,
                             'specific_declared_route':declared[0] if declared else None,
                             'specific_route_shadowed':bool(declared and route!=declared[0])})
    a.output.mkdir(parents=True,exist_ok=True)
    result={'kind':'execution-of-original-route-method-no-rollout-change','rows':rows,
            'shadowed_cases':sum(r['specific_route_shadowed'] for r in rows),
            'original_driver':str(Path(attack_driver.__file__).resolve()),
            'conclusion':'generic uav route appears first and returns before decoy segments; declared turn-away at tick150 is not selected'}
    (a.output/'route_selector_probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 高保真诱饵路由选择审计','',
        '直接执行远程原始AttackProfileDriverV2._route_for，不改代码、不启动LLM、不改变现有仿真。', '',
        '|场景|诱饵|tick|实际match_tag|实际目标|声明的诱饵目标|被通用路由遮蔽|',
        '|---|---|---:|---|---|---|---|']
    for r in rows:lines.append(f"|{r['scene']}|{r['entity']}|{r['tick']}|{r['actual_route'].get('match_tag')}|{r['actual_route'].get('objective_m')}|{(r['specific_declared_route'] or {}).get('objective_m')}|{r['specific_route_shadowed']}|")
    lines+=['','原函数遍历routes并返回第一条满足标签和时间的路由；场景将通用uav放在decoy前，诱饵同时有uav/decoy标签。'
        '因此tick150之后仍选择设施方向，而非[32000,-9000]退出路线。', '',
        '这不改变离线“无武器诱饵”标签，却破坏了文档期望的转向行为证据。'
        '不能拿声明路线当已经发生的公开历史，更不能为了过D1给LLM披露未来真值。', '',
        '修复应为明确的独立分支/副本变更，先冻结所有架构同用的版本，验证正常目标路线、转向与计分不意外改变，再重新开发和确认。'
        '不应在当前运行E1期间改共享attack_driver。原始引擎与E1保持不变。']
    (a.output/'高保真_诱饵路由遮蔽审计.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'shadowed_cases':result['shadowed_cases'],'n':len(rows),'output':str(a.output)}),flush=True)


if __name__=='__main__':main()
