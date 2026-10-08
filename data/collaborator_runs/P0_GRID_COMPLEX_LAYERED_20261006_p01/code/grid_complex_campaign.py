"""Frozen Grid complex four-stack confirmation; unchanged remote native engine.

Independent process per episode. No training, scenario editing or outcome selection.
Commands: freeze, smoke, run, worker, analyze, status. Each attempt is retained.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import traceback

ARMS = ('rule', 'pure-mappo', 'llm-heuristic', 'llm-mappo')
LLM_ARMS = frozenset(('llm-heuristic', 'llm-mappo'))
RL_ARMS = frozenset(('pure-mappo', 'llm-mappo'))
EXPECTED_CHECKPOINT = '223dbf740163b652f221a6ef0885d69b8c975c53378a7e63c05388e1df8cd0a8'
ENV_THREADS = {k: '1' for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS')}


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def plain(v):
    if is_dataclass(v): return plain(asdict(v))
    if isinstance(v, Enum): return plain(v.value)
    if isinstance(v, dict): return {str(k):plain(a) for k,a in v.items()}
    if isinstance(v, (list,tuple)): return [plain(a) for a in v]
    if isinstance(v, (set,frozenset)): return sorted(plain(a) for a in v)
    if hasattr(v, 'tolist'): return plain(v.tolist())
    if v is None or isinstance(v,(str,int,float,bool)): return v
    raise TypeError('Unsupported log value '+type(v).__name__)


def canonical(v):
    return json.dumps(plain(v),ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':'))


def write(p,v):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+'.tmp')
    tmp.write_text(json.dumps(plain(v),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    tmp.replace(p)


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def append(p,v):
    with Path(p).open('a',encoding='utf-8') as f: f.write(canonical(v)+'\n')


def source_hashes(source):
    files=sorted((source/'code/grid_env').rglob('*.py'))
    files += [source/'code/evaluation/metrics.py']
    if not files or not (source/'code/grid_env/grid_env.py').is_file():
        raise FileNotFoundError('Native Grid source missing')
    return {p.relative_to(source).as_posix():sha(p) for p in files}


def protocol(root):
    return read(root/'protocol/protocol.json')


def verify(root):
    p=protocol(root)
    if sha(p['checkpoint']) != EXPECTED_CHECKPOINT: raise ValueError('Checkpoint SHA mismatch')
    if source_hashes(Path(p['source'])) != p['source_hashes']: raise ValueError('Source drift')
    if sha(Path(__file__)) != p['code_sha256']: raise ValueError('Campaign code drift')
    if p['seeds'] != list(range(63101,63106)) or p['arms'] != list(ARMS): raise ValueError('Frozen design mismatch')
    return p


def freeze(a):
    import platform
    import urllib.request
    if a.root.exists(): raise FileExistsError('New batch root required')
    if sha(a.checkpoint) != EXPECTED_CHECKPOINT: raise ValueError('Wrong medium weights')
    services={}
    for ep in a.endpoint:
        d=json.loads(urllib.request.urlopen(ep+'/models',timeout=15).read())
        if 'Qwen3.8-27B' not in [x['id'] for x in d['data']]: raise ValueError('Wrong model')
        services[ep]=d
    for folder in ('protocol','code','smoke','confirmation','attempts','analysis/a01','reports/r01','logs'):
        (a.root/folder).mkdir(parents=True,exist_ok=True)
    write(a.root/'protocol/protocol.json',{
        'schema':'grid-complex-four-stack@1','frozen_at':now(),
        'source':str(a.source.resolve()),'checkpoint':str(a.checkpoint.resolve()),
        'checkpoint_sha256':sha(a.checkpoint),'source_hashes':source_hashes(a.source),
        'code_sha256':sha(Path(__file__)),'checklist_sha256':sha(a.checklist),
        'arms':list(ARMS),'seeds':list(range(63101,63106)),'smoke_seed':63001,
        'difficulty':'complex','task_mode':'continuous','max_steps':150,
        'planner_interval':10,'rule_interval':10,'rule_interval_note':'Matches archived P1 grid_rolec6 clock, not default RuleAgent interval5',
        'model':'Qwen3.8-27B','temperature':0.1,'max_tokens':4096,'enable_thinking':False,
        'nl_mode':'nl','endpoint_list':a.endpoint,'models_response':services,
        'primary_V':'native GridEnv.get_episode_metrics().blue_score; same as archived P1 V',
        'primary_score_formula':'0.6*mission_success+0.2*(1-red_combatants_alive/max(red_combatants_total,1))+0.2*blue_alive/max(blue_total,1)',
        'SR':'mean(native mission_success == true); failed games are valid, not engineering errors',
        'secondary_metric':'MetricEngine(alpha=beta=0.5).composite_score, separately labelled; not substituted for V',
        'pure_mappo_contract':'native MAPPOAgent trained deterministic actor, no externally submitted goal; common observation polling cadence for all arms',
        'llm_mappo_contract':'native HybridAgent and native make_goai_controller, no goal_bound gating or heuristic substitution',
        'goal_handling':'unchanged native parse/fill/submit/rejection/fallback behaviour; all retained and audited',
        'LLM_request_timeout_s':120,'HTTP_retries':2,'episode_timeout_s':3600,
        'episode_attempt_limit':2,'retry_policy':'only process crash, timeout or native Python exception; completed loss, poor plan or deployment parse fallback never retried',
        'completed_HTTP_failure_policy':'retain completed deployment and fallback outcome, report service diagnostics; do not turn into silent missingness',
        'analysis':{'paired':'LLM+heuristic minus Rule; LLM+MAPPO minus Pure MAPPO','bootstrap_draws':20000,'bootstrap_seed':20261006,'unit':'5 environment seeds of one frozen model, not5 training seeds','interval':'percentile paired seed bootstrap95%','best_pure':'per-seed max(rule,pure-mappo) descriptive only, primary fixed counterparts always reported'},
        'workers':{'LLM':4,'pure':2,'per_endpoint':2},
        'smoke':'4 full native episodes on seed63001; no inclusion in confirm; controller positive action evidence required',
        'stop_rule':'run all20 valid designated episodes regardless effect direction; report missing and all retained attempts; no outcome-dependent selection',
        'runtime':{'python':sys.version,'executable':sys.executable,'platform':platform.platform()},
    })
    write(a.root/'status.json',{'state':'frozen','at':now(),'total_cases':20})
    return 0


def imports(p):
    for k,v in ENV_THREADS.items(): os.environ[k]=v
    source=Path(p['source']);sys.path.insert(0,str(source/'code'))
    import torch
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    from grid_env.grid_env import GridEnv, MAX_STEPS
    from grid_env.agents.rule_agent import RuleAgent
    from grid_env.agents.hybrid_agent import HybridAgent
    from grid_env.agents.mappo_agent import MAPPOAgent
    from evaluation.metrics import MetricEngine
    if MAX_STEPS != p['max_steps']: raise ValueError('Native step budget changed')
    for cls in (GridEnv,RuleAgent,HybridAgent,MAPPOAgent,MetricEngine):
        import inspect
        if not Path(inspect.getfile(cls)).resolve().is_relative_to(source): raise ValueError('Wrong source imported')
    return GridEnv,RuleAgent,HybridAgent,MAPPOAgent,MetricEngine,torch


class AuditedClient:
    def __init__(self,p,output,endpoint):
        self.p,self.output,self.endpoint=p,output,endpoint
        self.stats={'total_calls':0,'http_attempts':0,'errors':0,'empty_responses':0,'total_tokens':0,'total_latency':0.0,'reasoning_nonempty':0,'model':p['model']}

    def chat(self,system_prompt,user_message,max_tokens=512,temperature=.1):
        import requests
        # Check rather than silently override the native invocation defaults.
        if max_tokens!=self.p['max_tokens'] or temperature!=self.p['temperature']: raise ValueError('Native request drift')
        self.stats['total_calls']+=1;call=self.stats['total_calls'];tic=time.monotonic()
        body={'model':self.p['model'],'messages':[{'role':'system','content':system_prompt},{'role':'user','content':user_message}],
              'max_tokens':max_tokens,'temperature':temperature,'chat_template_kwargs':{'enable_thinking':False}}
        append(self.output/'requests.jsonl',{'kind':'request','call_id':call,'endpoint':self.endpoint,'at':now(),'payload':body})
        response=''
        for attempt in range(self.p['HTTP_retries']+1):
            self.stats['http_attempts']+=1;at=time.monotonic()
            try:
                api=requests.post(self.endpoint+'/chat/completions',json=body,timeout=self.p['LLM_request_timeout_s'])
                api.raise_for_status();data=api.json();m=data['choices'][0]['message'];response=m.get('content') or ''
                if m.get('reasoning_content') or m.get('reasoning'): self.stats['reasoning_nonempty']+=1
                self.stats['total_tokens']+=(data.get('usage') or {}).get('total_tokens',0)
                append(self.output/'requests.jsonl',{'kind':'response','call_id':call,'attempt':attempt+1,'seconds':time.monotonic()-at,'data':data})
                if not response:self.stats['empty_responses']+=1
                break
            except Exception as exc:
                append(self.output/'requests.jsonl',{'kind':'HTTP_error','call_id':call,'attempt':attempt+1,'error':repr(exc),'seconds':time.monotonic()-at})
                if attempt==self.p['HTTP_retries']:self.stats['errors']+=1
                else:time.sleep(attempt+1)
        self.stats['total_latency']+=time.monotonic()-tic
        return response

    def get_stats(self): return dict(self.stats)


def make_agent(p,arm,seed,output,endpoint,components):
    _,Rule,Hybrid,MAPPO,_,_=components
    client=AuditedClient(p,output,endpoint) if arm in LLM_ARMS else None
    if arm=='rule':
        agent=Rule(seed=seed);agent.plan_interval=p['rule_interval']
    elif arm=='pure-mappo':
        agent=MAPPO(seed=seed,trained=True,checkpoint_path=p['checkpoint'],device='cpu')
    else:
        agent=Hybrid(seed=seed,llm_client=client,planner_interval=p['planner_interval'],
            executor_checkpoint=p['checkpoint'] if arm=='llm-mappo' else None,nl_mode=p['nl_mode'])
    return agent,client


def state(env):
    # Offline telemetry only. Never supplied to the planner or actor.
    return {'step':env.step_count,'done':env.done,'winner':env.winner,
            'entities':{k:plain(v.to_dict()) for k,v in env.entities.items()},
            'metrics':plain(env.metrics),'spawned_waves':plain(env.waves_spawned)}


def worker(a):
    p=verify(a.root);out=a.output
    if out.exists(): raise FileExistsError('Attempt output exists')
    out.mkdir(parents=True)
    write(out/'config.json',{'arm':a.arm,'seed':a.seed,'phase':a.phase,'endpoint':a.endpoint,'protocol_sha256':sha(a.root/'protocol/protocol.json')})
    comp=imports(p);GridEnv,_,_,_,Metrics,_=comp
    agent,client=make_agent(p,a.arm,a.seed,out,a.endpoint,comp)
    policy=agent if a.arm=='pure-mappo' else getattr(agent,'mappo',None)
    calls={'actor_forwards':0,'controller_calls':0,'controller_actions':0,'controller_None_alive':0,'controller_None_dead':0,'native_controller_exceptions':[],'parsed_plans':0,'unparsed_plans':0,'accepted_goals':0}
    if policy is not None:
        if not policy.trained: raise ValueError('Weights not loaded')
        def hook(_module,_inputs):calls['actor_forwards']+=1
        policy.actor.register_forward_pre_hook(hook)
    if a.arm=='llm-mappo':
        native=agent.executor.controller
        def audited_controller(env,uid,goal):
            calls['controller_calls']+=1
            old_trace=sys.gettrace();exceptions=[]
            def trace(frame,event,arg):
                if event=='exception' and frame.f_code.co_filename.endswith('mappo_agent.py'):
                    exceptions.append({'type':arg[0].__name__,'message':str(arg[1]),'function':frame.f_code.co_name})
                return trace
            sys.settrace(trace)
            try:action=native(env,uid,goal)
            finally:sys.settrace(old_trace)
            alive=bool(env.entities.get(uid) and env.entities[uid].alive)
            if action is None:calls['controller_None_alive' if alive else 'controller_None_dead']+=1
            else:calls['controller_actions']+=1
            calls['native_controller_exceptions'].extend(exceptions)
            append(out/'controller.jsonl',{'step':env.step_count,'unit':uid,'goal':goal.command.to_dict(),'action':action,'alive':alive,'exceptions':exceptions})
            return action
        agent.executor.controller=audited_controller
    if hasattr(agent,'broker'):
        original_submit=agent.broker.submit_goals
        def submit(commands,*,step):
            # Pass through exact original objects; no edits or goal restrictions.
            result=original_submit(commands,step=step)
            calls['accepted_goals']+=len(result['accepted'])
            append(out/'goals.jsonl',{'step':step,'commands':[c.to_dict() for c in commands],'receipt':result})
            return result
        agent.broker.submit_goals=submit
    if a.arm in LLM_ARMS:
        original_parse=agent._parse_plan
        def parse(response):
            result=original_parse(response)
            calls['unparsed_plans' if result is None else 'parsed_plans']+=1
            append(out/'parsing.jsonl',{'step':agent.step_count,'parsed':result,'unparsed':result is None})
            return result
        agent._parse_plan=parse
    env=GridEnv(difficulty=p['difficulty'],seed=a.seed,task_mode=p['task_mode'])
    start=time.monotonic();aborted=None
    try:
        for _ in range(p['max_steps']):
            if env.done:break
            obs=env._get_observation('blue')
            # Audit from existing observation only; no extra sensor/RNG calls.
            before=state(env);actions=agent.act(obs,env=env)
            if any(not isinstance(int(v),int) or int(v) not in range(6) for v in actions.values()):raise ValueError('Invalid native action')
            env.step(actions,None);reward=env.compute_reward('blue')
            append(out/'events.jsonl',{'step':env.step_count,'public_observation':obs,'before':before,'actions':actions,'after':state(env),'native_reward':reward})
            write(out/'progress.json',{'at':now(),'step':env.step_count,'done':env.done,'seconds':time.monotonic()-start,'llm':client.get_stats() if client else None})
    except Exception as exc:
        aborted=repr(exc);(out/'exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
    if source_hashes(Path(p['source']))!=p['source_hashes']:aborted='Source changed during episode'
    if sha(p['checkpoint'])!=p['checkpoint_sha256']:aborted='Weights changed during episode'
    m=env.get_episode_metrics();complete=bool(env.done and not aborted)
    executor_clean=(calls['controller_None_alive']==0 and not calls['native_controller_exceptions'])
    meaningful=(calls['controller_actions']>0 if a.arm=='llm-mappo' else calls['actor_forwards']>0 if a.arm=='pure-mappo' else True)
    result={'schema':'grid-complex-episode@1','arm':a.arm,'seed':a.seed,'phase':a.phase,'complete':complete,'aborted':aborted,
            'started_at':read(out/'config.json').get('started_at'),'ended_at':now(),'seconds':time.monotonic()-start,'steps':env.step_count,
            'V':float(m['blue_score']) if complete else None,'success':bool(m['mission_success']) if complete else None,
            'native_metrics':m,'secondary_layered_metric':asdict(Metrics().compute(m,max_steps=p['max_steps'])),
            'agent_stats':agent.get_stats(),'audit':calls,'executor_audit_qualified':executor_clean and meaningful,
            'protocol_sha256':sha(a.root/'protocol/protocol.json'),'source_hashes':p['source_hashes'],'checkpoint_sha256':p['checkpoint_sha256'] if a.arm in RL_ARMS else None}
    write(out/'episode.json',result)
    files={f.name:sha(f) for f in out.iterdir() if f.is_file()}
    write(out/'completion.json',{'complete':complete,'files':files,'at':now()})
    print(canonical({'arm':a.arm,'seed':a.seed,'complete':complete,'V':result['V'],'seconds':result['seconds'],'executor_audit_qualified':result['executor_audit_qualified']}),flush=True)
    return 0 if complete else 2


def validate_attempt(root,out,arm,seed):
    if not (out/'completion.json').exists():return None
    c=read(out/'completion.json')
    if not c['complete']:return None
    for name,d in c['files'].items():
        if not (out/name).is_file() or sha(out/name)!=d:raise ValueError('Attempt checksum mismatch')
    r=read(out/'episode.json')
    if not r['complete'] or r['arm']!=arm or r['seed']!=seed or r['protocol_sha256']!=sha(root/'protocol/protocol.json'):raise ValueError('Case identity mismatch')
    if not math.isfinite(r['V']):raise ValueError('Invalid score')
    return r


def case_id(arm,seed): return f'{arm}__s{seed}'


def run_case(root,p,arm,seed,phase,endpoint):
    ident=case_id(arm,seed);case=root/phase/ident;case.mkdir(parents=True,exist_ok=True)
    selected=case/'selected.json'
    if selected.exists():
        s=read(selected);r=validate_attempt(root,Path(s['attempt_dir']),arm,seed)
        if r is None:raise ValueError('Selected episode invalid')
        return r
    # Resume can recover a completed attempt without launching another result.
    for attempt in range(1,p['episode_attempt_limit']+1):
        out=root/'attempts'/phase/ident/f'attempt-{attempt:02}'
        if out.exists():
            r=validate_attempt(root,out,arm,seed)
            if r:
                write(selected,{'attempt_dir':str(out),'episode_sha256':sha(out/'episode.json'),'at':now()});return r
            continue
        out.parent.mkdir(parents=True,exist_ok=True)
        cmd=[sys.executable,'-B',str(Path(__file__)),'worker','--root',str(root),'--output',str(out),'--arm',arm,'--seed',str(seed),'--phase',phase,'--endpoint',endpoint]
        log=root/'logs'/f'{phase}__{ident}__a{attempt}.log'
        tic=time.monotonic()
        with log.open('x') as f:
            proc=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,**ENV_THREADS})
            write(case/'running.json',{'pid':proc.pid,'command':cmd,'attempt_dir':str(out),'started_at':now()})
            try:exit_code=proc.wait(timeout=p['episode_timeout_s'])
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:proc.wait(timeout=10)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
                exit_code='timeout'
        write(case/f'attempt-{attempt:02}.json',{'exit_code':exit_code,'seconds':time.monotonic()-tic,'at':now(),'attempt_dir':str(out)})
        r=validate_attempt(root,out,arm,seed)
        if r:
            write(selected,{'attempt_dir':str(out),'episode_sha256':sha(out/'episode.json'),'at':now()});return r
    write(case/'failed.json',{'state':'engineering_incomplete','at':now()})
    return None


def snapshot(root,phase='confirmation'):
    p=protocol(root);seeds=[p['smoke_seed']] if phase=='smoke' else p['seeds']
    selected=[];failed=[];running=[]
    for arm in ARMS:
        for seed in seeds:
            c=root/phase/case_id(arm,seed)
            if (c/'selected.json').exists():selected.append({'arm':arm,'seed':seed,**read(c/'selected.json')})
            elif (c/'failed.json').exists():failed.append({'arm':arm,'seed':seed})
            elif (c/'running.json').exists():
                d=read(c/'running.json');progress=Path(d['attempt_dir'])/'progress.json'
                try:os.kill(d['pid'],0);live=True
                except ProcessLookupError:live=False
                running.append({'arm':arm,'seed':seed,**d,'process_exists':live,'progress':read(progress) if progress.exists() else None})
    return {'phase':phase,'total':len(seeds)*4,'complete':len(selected),'failed':failed,'running':running,'selected':selected,'at':now()}


def schedule(root,phase):
    p=verify(root);seeds=[p['smoke_seed']] if phase=='smoke' else p['seeds']
    jobs=[(arm,seed) for seed in seeds for arm in ARMS]
    write(root/'status.json',{'state':phase+'-running','at':now(),'pid':os.getpid(),'total_cases':len(jobs)})
    pure_pool=ThreadPoolExecutor(max_workers=2)
    # Two independent lanes per endpoint; at most4 LLM episodes concurrently.
    ep_pools=[ThreadPoolExecutor(max_workers=2) for _ in p['endpoint_list']]
    futures=[];idx=0
    try:
        for arm,seed in jobs:
            if arm in LLM_ARMS:
                lane=idx%len(ep_pools);idx+=1;pool=ep_pools[lane];endpoint=p['endpoint_list'][lane]
            else:pool=pure_pool;endpoint=p['endpoint_list'][0]
            futures.append(pool.submit(run_case,root,p,arm,seed,phase,endpoint))
        for future in as_completed(futures):
            future.result()
            write(root/'status.json',{'state':phase+'-running','pid':os.getpid(),**snapshot(root,phase)})
    finally:
        pure_pool.shutdown();[pool.shutdown() for pool in ep_pools]
    snap=snapshot(root,phase)
    if phase=='smoke':
        checks={}
        for item in snap['selected']:
            r=read(Path(item['attempt_dir'])/'episode.json')
            good=r['complete'] and r['executor_audit_qualified']
            if item['arm'] in LLM_ARMS:
                stats=r['agent_stats']['llm_stats']
                good=good and stats['total_calls']>0 and stats['errors']==0 and stats['empty_responses']==0 and stats['reasoning_nonempty']==0 and r['audit']['parsed_plans']>0 and r['audit']['accepted_goals']>0
            checks[item['arm']]={'pass':bool(good),'V':r['V'],'seconds':r['seconds'],'audit':r['audit'],'agent_stats':r['agent_stats']}
        passed=len(checks)==4 and all(d['pass'] for d in checks.values())
        write(root/'smoke/smoke_result.json',{'pass':passed,'checks':checks,'at':now()})
        write(root/'status.json',{'state':'smoke-passed' if passed else 'smoke-failed',**snap})
        return 0 if passed else 3
    analyze(root)
    state='completed' if snap['complete']==20 else 'incomplete-engineering'
    write(root/'status.json',{'state':state,**snap})
    return 0 if snap['complete']==20 else 3


def boot(values,draws=20000,seed=20261006):
    import numpy as np
    if not values:return None
    x=np.asarray(values,dtype=float)
    if not np.isfinite(x).all():raise ValueError('Nonfinite bootstrap input')
    rng=np.random.default_rng(seed);means=x[rng.integers(0,len(x),size=(draws,len(x)))].mean(axis=1)
    return {'n':len(x),'mean':float(x.mean()),'SD':float(x.std(ddof=1)) if len(x)>1 else None,'ci95':np.quantile(means,[.025,.975]).tolist()}


def analyze(root):
    p=verify(root);snap=snapshot(root);rows=[];by={}
    for item in snap['selected']:
        out=Path(item['attempt_dir']);r=validate_attempt(root,out,item['arm'],item['seed'])
        if r is None:raise ValueError('Invalid selected attempt')
        rows.append(r);by[(r['arm'],r['seed'])]=r
    summary={'complete':len(rows)==20,'n_completed':len(rows),'n_expected':20,'at':now(),'protocol_sha256':sha(root/'protocol/protocol.json'),'arms':{},'pairs':{}}
    for arm in ARMS:
        rs=[r for r in rows if r['arm']==arm]
        summary['arms'][arm]={'V':boot([r['V'] for r in rs]),'SR':boot([int(r['success']) for r in rs]),'unqualified_executor_seeds':[r['seed'] for r in rs if not r['executor_audit_qualified']]}
    for hybrid,pure in [('llm-heuristic','rule'),('llm-mappo','pure-mappo')]:
        pairs=[]
        for seed in p['seeds']:
            if (hybrid,seed) in by and (pure,seed) in by:
                h,b=by[(hybrid,seed)],by[(pure,seed)]
                pairs.append({'seed':seed,'hybrid_V':h['V'],'pure_V':b['V'],'delta_V':h['V']-b['V'],'hybrid_success':h['success'],'pure_success':b['success'],'delta_SR':int(h['success'])-int(b['success'])})
        summary['pairs'][hybrid+' minus '+pure]={'rows':pairs,'delta_V':boot([r['delta_V'] for r in pairs]),'delta_SR':boot([r['delta_SR'] for r in pairs])}
    summary['interpretation_limit']='5 environment seeds; fixed medium checkpoint transfer; conditional deployment evidence, not universal proof or isolated causal D1prime intervention.'
    write(root/'analysis/a01/summary.json',summary)
    write(root/'analysis/a01/per_seed.json',rows)
    lines=['# Grid complex四栈补实验报告','',f"统计时间：{now()}；完整局 {len(rows)}/20。",'',
           '主V为原生blue_score，与此前Grid P1一致；SR为mission_success。两种同seed固定对照分别报告，冒烟和失败尝试不混入确认。','',
           '| seed | Rule V/SR | Pure MAPPO V/SR | LLM+heuristic V/SR | LLM+MAPPO V/SR |','|---|---|---|---|---|']
    for seed in p['seeds']:
        cells=[]
        for arm in ARMS:
            r=by.get((arm,seed));cells.append(f"{r['V']:.6f}/{int(r['success'])}" if r else '未完成')
        lines.append('| '+str(seed)+' | '+' | '.join(cells)+' |')
    lines+=['','## 同seed配对差','']
    for name,data in summary['pairs'].items():
        d=data['delta_V']
        if not d:lines.append(name+'：暂无配对数据。');continue
        lo,hi=d['ci95'];direction='支持受测部署点负收益' if hi<0 else '支持受测部署点正收益' if lo>0 else '区间包含零，方向不确定'
        lines.append(f"- {name}：n={d['n']}，均值 {d['mean']:.6f}，seed-bootstrap95%CI [{lo:.6f}, {hi:.6f}]；{direction}。")
    lines+=['','所有20局均完成前仅作阶段核算。局数不全不以零补齐；未通过执行器审计的局保留原始数字并标记，不冒充纯净MAPPO架构。',
            '','固定权重的5个环境seed不是5个训练seed。CI采用20000次配对seed重采样，不能消除小样本限制。未改变引擎、场景、reward、检查点、GOAI规则或原始提示词。',
            '','本批不能单独证明“无论接口如何皆亏损”，也未单独操纵D1′以隔离其机制。所有正收益、负收益和有效输局均保留。']
    (root/'reports/r01/Grid_complex四栈补实验报告_v1.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(canonical({'analysis':str(root/'analysis/a01/summary.json'),'n_completed':len(rows)}),flush=True)
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['freeze','smoke','run','worker','analyze','status'])
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--checkpoint',type=Path)
    parser.add_argument('--checklist',type=Path)
    parser.add_argument('--endpoint',action='append')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--arm',choices=ARMS)
    parser.add_argument('--seed',type=int)
    parser.add_argument('--phase',choices=['smoke','confirmation'],default='confirmation')
    a=parser.parse_args();a.root=a.root.resolve()
    if a.command=='freeze':return freeze(a)
    if a.command=='worker':
        # Worker needs a scalar endpoint; parser uses append for freeze.
        a.endpoint=a.endpoint[0];return worker(a)
    if a.command=='status':print(canonical({'status':read(a.root/'status.json'),'snapshot':snapshot(a.root)}));return 0
    if a.command=='analyze':return analyze(a.root)
    # Linux advisory lock guarantees one supervisor per phase root.
    with (a.root/'logs/supervisor.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.command=='run':
            verify(a.root)
            if not read(a.root/'smoke/smoke_result.json')['pass']:raise ValueError('Smoke must pass before confirmation')
            eq=read(a.root/'smoke/passive_equivalence.json')
            if not eq['pass'] or eq['tests']!=10 or eq['test_code_sha256']!=sha(Path(__file__).with_name('test_grid_complex.py')):
                raise ValueError('Native passive-equivalence tests must pass before confirmation')
        return schedule(a.root,'smoke' if a.command=='smoke' else 'confirmation')


if __name__=='__main__':raise SystemExit(main())
