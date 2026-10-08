"""Sequential D1 follow-up; preserves unrelated running E1 queue."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from grid_diagnose import read,write,digest

REPO=Path('/root/openmd/releases/gitlab-ccabad00154e/repo')
ROOT=Path('/root/openmd/runs/p0-next-20261002')


def main():
    p=argparse.ArgumentParser();p.add_argument('cmd',choices=['launch','supervise']);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output
    if a.cmd=='launch':
        if out.exists():raise ValueError('Existing workflow retained')
        out.mkdir(parents=True)
        with (out/'supervisor.log').open('a') as log:
            child=subprocess.Popen([sys.executable,'-B',str(Path(__file__)),'supervise','--output',str(out)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        print(json.dumps({'supervisor_pid':child.pid,'output':str(out)}));return
    import fcntl
    lock=(out/'workflow.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    code=Path(__file__).parent;frozen={str(p.relative_to(code)):digest(p) for p in code.rglob('*') if p.is_file()};write(out/'code_freeze.json',frozen)
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',TI_CPU_MAX_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg')
    phases=[]
    for tier,name,folder in [('medium','E3-channel-v3','code-v3'),('complex','E3-channel-complex','code-complex')]:
        phases.append((f'grid-{tier}',[sys.executable,'-B',str(code/'grid_diagnose.py'),'--campaign',str(ROOT/name),'--code',str(ROOT/folder),'--output',str(out/f'grid-{tier}')]))
    phases += [('hf-static-audit',[sys.executable,'-B',str(code/'hf_audit.py'),'--repo',str(REPO),'--output',str(out/'hf-static-audit')]),
               ('hf-preflight',[sys.executable,'-B',str(code/'hf_preflight.py'),'--repo',str(REPO),'--base-code',str(ROOT/'code'),'--output',str(out/'hf-preflight')]),
               ('hf-pilot',[sys.executable,'-B',str(code/'hf_pilot.py'),'--repo',str(REPO),'--base-code',str(ROOT/'code'),
                  '--channel-code',str(ROOT/'code-complex'),'--output',str(out/'hf-pilot')])]
    results=[];start=time.time()
    for name,cmd in phases:
        for n,h in frozen.items():
            if digest(code/n)!=h:raise ValueError('Frozen followup code changed')
        with (out/f'{name}.log').open('a') as log:
            proc=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            write(out/'progress.json',{'phase':name,'pid':proc.pid,'completed_phases':len(results),'started_at':start,'E1_untouched':True})
            try:status=proc.wait(timeout=max(1,172800-(time.time()-start)))
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=20)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                status=proc.returncode
        results.append({'phase':name,'exit_code':status});write(out/'phase_results.json',results)
        if status:
            write(out/'completion.json',{'state':'engineering-review-required','phases':results,'E1_untouched':True});return
    audit=read(out/'hf-static-audit/audit.json');engine=REPO/'openmd/source-code/source_codes'
    bad=[n for n,h in audit['source_hashes'].items() if digest(engine/n)!=h]
    if bad:raise ValueError('Original source changed during pilot')
    pilot=read(out/'hf-pilot/status.json')
    write(out/'completion.json',{'state':'diagnosis-and-pilot-complete','phases':results,'source_unchanged':True,
        'elapsed_seconds':time.time()-start,'E1_untouched':True,'formal_confirmation_started':False,'readiness':pilot['readiness']})
    lines=['# D1后续诊断与高保真开发验证汇总','',
           '执行顺序：E1保持原队列 → 两个Grid开发数据诊断 → 高保真场景/观测审计 → 5seed/场景开发pilot。', '',
           f"当前正式确认就绪状态：{pilot['readiness']}。正式确认没有自动启动。", '',
           '全部原始源码哈希未变；旧确认结果、失败与原输入保留；不改门阈值、不删合法字段。', '',
           '报告入口：grid-medium/Grid_D1_开发线索诊断.md；grid-complex/Grid_D1_开发线索诊断.md；'
           'hf-static-audit/高保真_D1_场景审计.md；hf-pilot/高保真_D1_pilot报告.md。', '',
           '正式确认之前必须明确真实输入是否匿名、其变更范围及对所有架构一致性，'
           '确认两类数据覆盖、强数值基线、LLM开发信号和独立冻结来源。'
           '不能仅因匿名诊断返回正向就宣称原生D1成立，也不在旧确认集调判定规则。']
    (out/'D1后续实验阶段汇总.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'state':'completed','readiness':pilot['readiness'],'output':str(out)}),flush=True)


if __name__=='__main__':main()
