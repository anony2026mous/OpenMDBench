"""v14 trace-only work. Never calls an LLM, changes an engine, or reruns a sample.

Replay verification consumes already frozen responses, and is not new sampling.
Output roots must be new. Every input read is SHA-256 indexed.
"""
from __future__ import annotations
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import traceback

INPUTS = {}
GRID_UNITS = {'uav': 'air', 'usv': 'surface', 'auv': 'underwater', 'shore_radar': 'shore'}
DOMAIN_ALIASES = {'air':'air','aerial':'air','surface':'surface','sea':'surface',
                  'shore':'shore','land':'shore','ground':'shore','underwater':'underwater','subsurface':'underwater'}

def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def track(p):
    p = Path(p).resolve()
    value = sha(p)
    if str(p) in INPUTS and INPUTS[str(p)] != value: raise ValueError('Input changed: '+str(p))
    INPUTS[str(p)] = value
    return p

def read(p): return json.loads(track(p).read_text(encoding='utf-8-sig'))

def lines(p):
    with track(p).open(encoding='utf-8') as f:
        for line in f:
            if line.strip(): yield json.loads(line)

def write(p, obj):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def md(p, text):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(text+'\n', encoding='utf-8')

def start(a):
    if a.output.exists(): raise FileExistsError('Use a new versioned output root: '+str(a.output))
    for d in ('protocol','analysis','reports','code','logs'): (a.output/d).mkdir(parents=True)
    shutil.copy2(__file__, a.output/'code/v14_analysis.py')
    write(a.output/'protocol/design.json', {
        'frozen_at':now(),'task':a.task,'arguments':{k:str(v) for k,v in vars(a).items()},
        'code_sha256':sha(__file__),'unit':'seed, equal-weight per-seed mean within one arm/batch',
        'allocation':'one submitted upper-level decision; unique physical domains of accepted own-unit assignments',
        'holds':'included in primary; non-hold sensitivity reported separately',
        'passive_sites':'not counted without explicit accepted assignment',
        'unknown':'any unresolved accepted task/unit/domain makes that decision NA; no filename inference',
        'zero_accepted':'zero domains, retained in primary denominator',
        'sample_policy':'all designated existing cases, no outcome selection or new LLM requests',
        'CI':'20000-draw percentile seed bootstrap; N<2 => no CI',
        'intrinsic':'Appendix A family estimates, not re-estimated causal bounds; IE14-suite family=interception/response, 2.2; Grid=NA',
        'replay_policy':'strict existing evidence first; optional Grid exact offline replay of frozen LLM responses, separately labelled',
    })
    write(a.output/'status.json', {'state':'running','at':now()})

def finish(a, result):
    # Detect concurrent modification, not just record initial checksums.
    for path, digest in INPUTS.items():
        if sha(path) != digest: raise ValueError('Input changed during analysis: '+path)
    write(a.output/'protocol/input_manifest.json', {'frozen_at':now(),'files':INPUTS})
    write(a.output/'analysis/result.json', result)
    write(a.output/'status.json', {'state':result.get('status','complete'),'at':now(),'task':a.task})
    files={str(p.relative_to(a.output)):sha(p) for p in sorted(a.output.rglob('*')) if p.is_file()}
    write(a.output/'output_manifest.json', {'at':now(),'files':files})
    print(json.dumps({'task':a.task,'status':result.get('status','complete'),'output':str(a.output)},ensure_ascii=False),flush=True)

def coupling(commands, accepted, unit_domains):
    # Do not carry stale task mappings forward to infer missing submissions.
    cmdmap={}; duplicates=set()
    for c in commands:
        key=c.get('task_id')
        if key in cmdmap: duplicates.add(key)
        cmdmap[key]=c
    domains=set(); active=set(); unresolved=[]; units=[]
    for task in accepted:
        c=cmdmap.get(task)
        if not c or task in duplicates:
            unresolved.append({'task':task,'reason':'missing_or_duplicate_command'}); continue
        uid=(c.get('parameters') or {}).get('unit_id',c.get('unit_id'))
        domain=unit_domains.get(uid)
        if not domain:
            unresolved.append({'task':task,'unit':uid,'reason':'unknown_own_unit_domain'}); continue
        domains.add(domain); units.append(uid)
        if c.get('goal_type') not in ('hold','loiter','patrol','return','disengage'): active.add(domain)
    return {'domains':sorted(domains),'count':None if unresolved else len(domains),
            'engagement_goal_count':None if unresolved else len(active),'units':units,
            'accepted_count':len(accepted),'unresolved':unresolved}

def seed_summary(cases):
    means=[r['effective_mean'] for r in cases if r.get('effective_mean') is not None]
    if not means: return {'n':0,'mean':None,'CI95':None}
    ci=None
    if len(means)>=2:
        import numpy as np
        rng=np.random.default_rng(20261007)
        arr=np.array(means); boots=arr[rng.integers(0,len(arr),(20000,len(arr)))].mean(axis=1)
        ci=[float(v) for v in np.quantile(boots,[.025,.975])]
    return {'n':len(means),'mean':statistics.mean(means),'CI95':ci,'seed_range':[r['seed'] for r in cases if r.get('effective_mean') is not None]}

def case_stats(decisions):
    good=[x['count'] for x in decisions if x['count'] is not None]
    return {'decisions':len(decisions),'resolved':len(good),'unresolved':len(decisions)-len(good),
            # With missing decisions report resolved-only descriptive mean separately.
            'effective_mean':statistics.mean(good) if good and len(good)==len(decisions) else None,
            'resolved_only_mean':statistics.mean(good) if good else None,
            'range':[min(good),max(good)] if good else None,
            'engagement_goal_mean':statistics.mean([x['engagement_goal_count'] for x in decisions]) if good and len(good)==len(decisions) else None}

def module(p, name):
    spec=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m; spec.loader.exec_module(m); return m

def replay_grid(a):
    # A separate worker process per case ensures native global RNG/Torch state isolation.
    g=module(a.source/'code/grid_complex_campaign.py','frozen_grid_campaign')
    p=g.verify(a.source); selected=g.read(a.source/'confirmation'/a.case/'selected.json')
    folder=Path(selected['attempt_dir']); episode=g.read(folder/'episode.json')
    arm=episode['arm']; seed=episode['seed']; g.validate_attempt(a.source,folder,arm,seed)
    recorded_requests={}; responses={}
    if (folder/'requests.jsonl').exists():
        for r in lines(folder/'requests.jsonl'):
            if r.get('kind')=='request': recorded_requests[r['call_id']]=r['payload']
            elif r.get('kind')=='response': responses[r['call_id']]=r['data']['choices'][0]['message'].get('content') or ''
    class ReplayClient:
        def __init__(self): self.calls=0
        def chat(self,system_prompt,user_message,max_tokens=512,temperature=.1):
            self.calls+=1
            original=recorded_requests[self.calls]
            expected={'model':p['model'],'messages':[{'role':'system','content':system_prompt},{'role':'user','content':user_message}],
                      'max_tokens':max_tokens,'temperature':temperature,'chat_template_kwargs':{'enable_thinking':False}}
            if g.canonical(expected)!=g.canonical(original): raise ValueError('Prompt divergence at call '+str(self.calls))
            # Exhausted HTTP retries produce native empty response, not a fresh request.
            return responses.get(self.calls,'')
        def get_stats(self): return {'total_calls':self.calls}
    comp=g.imports(p); agent,_=g.make_agent(p,arm,seed,folder,'offline-no-network',comp)
    client=ReplayClient()
    if arm in g.LLM_ARMS: agent.llm=client
    # Detect actual client attribute instead of accidentally using the network client.
    for k,v in vars(agent).items():
        if isinstance(v,g.AuditedClient): setattr(agent,k,client)
    env=comp[0](difficulty=p['difficulty'],seed=seed,task_mode=p['task_mode'])
    frames=0; divergence=[]; got_goals=[]
    if hasattr(agent,'broker'):
        submit=agent.broker.submit_goals
        def capture(commands,*,step):
            receipt=submit(commands,step=step)
            got_goals.append({'step':step,'commands':[c.to_dict() for c in commands],'receipt':receipt}); return receipt
        agent.broker.submit_goals=capture
    try:
        for frame in lines(folder/'events.jsonl'):
            obs=env._get_observation('blue')
            if g.canonical(obs)!=g.canonical(frame['public_observation']): raise ValueError('Observation divergence')
            if g.canonical(g.state(env))!=g.canonical(frame['before']): raise ValueError('Before-state divergence')
            actions=agent.act(obs,env=env)
            if g.canonical(actions)!=g.canonical(frame['actions']): raise ValueError('Action divergence')
            env.step(actions,None);reward=env.compute_reward('blue')
            if g.canonical(g.state(env))!=g.canonical(frame['after']): raise ValueError('After-state divergence')
            if g.canonical(reward)!=g.canonical(frame['native_reward']): raise ValueError('Reward divergence')
            frames+=1
        if not env.done or frames!=episode['steps']: raise ValueError('Terminal length divergence')
        if env.get_episode_metrics()['blue_score']!=episode['V']: raise ValueError('Score divergence')
        if client.calls!=len(recorded_requests): raise ValueError('Request-count divergence')
        if hasattr(agent,'broker') and g.canonical(got_goals)!=g.canonical(list(lines(folder/'goals.jsonl'))): raise ValueError('Submitted-goal divergence')
    except Exception as exc: divergence.append({'next_frame':frames+1,'reason':str(exc),'traceback':traceback.format_exc()})
    result={'case':a.case,'passed':not divergence,'verified_frames':frames,'recorded_requests':len(recorded_requests),'consumed_responses':client.calls,
            'source_trace':str(folder),'episode_sha256':sha(folder/'episode.json'),'protocol_sha256':sha(a.source/'protocol/protocol.json'),
            'validation':'exact observation+state+action+reward+goal+terminal+prompt equality; no new LLM sampling','divergence':divergence,'at':now()}
    write(a.output,result); print(json.dumps({'case':a.case,'passed':result['passed'],'frames':frames}),flush=True)
    return 0 if result['passed'] else 2

def grid_b1(a):
    p=read(a.source/'protocol/protocol.json'); cases=[]
    selected=sorted((a.source/'confirmation').glob('*/selected.json'))
    if len(selected)!=20: raise ValueError('Expected 20 designated existing confirmation episodes')
    def replay(sel):
        ident=sel.parent.name; target=a.output/'analysis/replay'/f'{ident}.json'
        target.parent.mkdir(parents=True,exist_ok=True)
        log=a.output/'logs'/f'{ident}.log'
        with log.open('w') as f:
            proc=subprocess.run([sys.executable,'-B',__file__,'grid-replay','--source',str(a.source),'--case',ident,'--output',str(target)],
                                stdout=f,stderr=subprocess.STDOUT,timeout=300)
        return ident,proc.returncode
    if a.verify_replay:
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            for f in as_completed([pool.submit(replay,s) for s in selected]):
                print('replay',f.result(),flush=True)
    for sel in selected:
        s=read(sel); folder=Path(s['attempt_dir']); c=read(folder/'completion.json')
        for name,digest in c['files'].items():
            if sha(track(folder/name))!=digest: raise ValueError('Frozen trace hash mismatch')
        episode=read(folder/'episode.json')
        initial=next(lines(folder/'events.jsonl'))['before']['entities']
        domains={uid:GRID_UNITS.get(e.get('unit')) for uid,e in initial.items() if e.get('team')=='blue'}
        decisions=[]
        if (folder/'goals.jsonl').exists():
            for r in lines(folder/'goals.jsonl'):
                decisions.append({'step':r['step'],**coupling(r['commands'],r['receipt']['accepted'],domains)})
        gatefile=a.output/'analysis/replay'/f'{sel.parent.name}.json'
        gate=read(gatefile) if gatefile.exists() else {'passed':False,'reason':'no case-matched replay evidence'}
        case={'case':sel.parent.name,'arm':episode['arm'],'seed':episode['seed'],'trace':str(folder),
              'replay_passed':gate['passed'],'intrinsic_estimate':None,'unit_domains':domains,**case_stats(decisions)}
        if not decisions: case['reason']='architecture has no upper allocation channel; NA, not zero'
        cases.append(case);write(a.output/'analysis/decisions'/f'{sel.parent.name}.json',decisions)
    summary={arm:{'descriptive':seed_summary([c for c in cases if c['arm']==arm]),
                  'replay_qualified':seed_summary([c for c in cases if c['arm']==arm and c['replay_passed']])} for arm in p['arms']}
    result={'status':'complete' if all(c['replay_passed'] for c in cases) else 'partial_replay_gate',
            'batch':str(a.source),'cases':cases,'summary':summary,'actual_seeds':p['seeds'],
            'note':'New exact offline replay gate is dated this analysis, not retroactively claimed as old certification. No new experimental episodes or LLM calls.'}
    rows=['|架构|seed数|effective均值|seed-bootstrap 95% CI|回放合格seed数|','|---|---:|---:|---|---:|']
    for arm,s in summary.items():
        r=s['descriptive'];rows.append(f"|{arm}|{r['n']}|{r['mean']}|{r['CI95']}|{s['replay_qualified']['n']}|")
    md(a.output/'reports/B1_Grid报告.md','# B1 Grid complex：既有轨迹域数测量\n\n'+'\n'.join(rows)+
       '\n\n批次：'+str(a.source)+'；seed63101–63105，4架构20局。先每seed对所有分配决策取均值，再seed等权。'+
       '\n\n域从实体unit字段确定：UAV=air、USV=surface。只计被明确接收的分配单位，不计被动站点、任务编号暗示或敌方目标域。hold/patrol仍是资源分配，纳入主口径；交战型目标域数为独立敏感性统计。'+
       '\n\npure-MAPPO没有上层分配接口，因此为NA而非零。Grid intrinsic在附录A没有给定估计，不能填2.8。所有原始文件哈希核对；新增离线回放仅复用既有响应，并逐tick比对状态、动作、观测、奖励、提交目标与终局，不调用LLM。'+
       '\n\n此量体现跨域覆盖，不等于统计互信息、因果依赖强度或已证明的分层收益机制。5seed是该冻结批次实际规模，未冒充清单一般要求的10seed。')
    return result

def nested(v):
    if isinstance(v,dict):
        yield v
        for x in v.values(): yield from nested(x)
    elif isinstance(v,list):
        for x in v: yield from nested(x)

def hf_domains(snapshot, scenario):
    import yaml
    base=Path(snapshot)/'openmd/source-code/source_codes'
    name=scenario.lower().replace('-','_')
    sp=base/'scenarios/formal'/name/'scenario.yaml'
    doc=yaml.safe_load(track(sp).read_text(encoding='utf-8'))
    platforms={}
    for path in sorted((base/'catalog').rglob('*.yaml')):
        data=yaml.safe_load(track(path).read_text(encoding='utf-8'))
        for d in nested(data):
            identifier=d.get('id',d.get('platform_id',d.get('platform_ref')))
            if isinstance(identifier,str) and identifier.startswith('platform.'):
                domain=d.get('domain')
                if isinstance(domain,str): platforms[identifier.split('@')[0]]=DOMAIN_ALIASES.get(domain.lower())
    domains={};evidence={}
    for e in doc['scenario']['entities']:
        if e.get('faction_id')!='coalition.defender': continue
        pref=e.get('platform_ref',''); direct=e.get('domain')
        domain=DOMAIN_ALIASES.get(str(direct).lower()) if direct else platforms.get(pref.split('@')[0])
        domains[e['id']]=domain; evidence[e['id']]={'platform_ref':pref,'domain':domain,'scenario_source':str(sp)}
    return domains,evidence

def parse_response(s):
    s=s.strip()
    if s.startswith('```'):
        s='\n'.join(s.splitlines()[1:-1]).strip()
    try: d=json.loads(s)
    except (ValueError,TypeError):
        begin=s.find('{');end=s.rfind('}')
        try:d=json.loads(s[begin:end+1])
        except (ValueError,TypeError):return None
    return d.get('goal_commands') if isinstance(d,dict) and isinstance(d.get('goal_commands'),list) else None

def hf_b1(a):
    manifests=sorted((a.source/'episodes').glob('*/manifest.json'));cases=[];domains_cache={}
    for path in manifests:
        m=read(path);info=m['case'];arm=info.get('arm',info.get('planner'))
        if arm not in ('llm-rule','llm-rl'):continue # pure-LLM direct-action interface is a different estimand
        row={'scenario':info['scenario'],'arm':arm,'seed':info['seed'],'trace':str(path.parent),
             'intrinsic_estimate':2.2,'intrinsic_provenance':'appendix0930 A, all14 IE interception-engagement family estimate',
             'effective_mean':None,'replay_passed':False,'decisions':0}
        if m.get('status')!='complete' or not m.get('eligible_for_main_score'):
            row['reason']='incomplete existing case; left untouched';cases.append(row);continue
        for name,digest in m['artifacts_sha256'].items():
            if sha(track(path.parent/name))!=digest:raise ValueError('HF artifact drift '+str(path.parent/name))
        key=(m['snapshot'],info['scenario'])
        if key not in domains_cache:domains_cache[key]=hf_domains(*key)
        domains,evidence=domains_cache[key]
        requests=list(lines(path.parent/'requests.jsonl')); responses=[r for r in requests if r.get('kind')=='response']
        plans=[r for r in lines(path.parent/'events.jsonl') if r.get('t')=='plan']
        # Records without explicit call->plan linkage are exploratory, never certified.
        decisions=[]
        if len(responses)==len(plans):
            for r,event in zip(responses,plans):
                commands=parse_response(r.get('response',''))
                if commands is None:
                    decisions.append({'tick':event.get('tick'),'count':None,'reason':'unparsed response/native fallback mapping unavailable'});continue
                decisions.append({'tick':event.get('tick'),'call_index':r.get('call_index'),
                                  **coupling(commands,event.get('accepted',[]),domains)})
            row.update(case_stats(decisions));row['linkage']='order-linked responses and plan receipts; provisional'
        else:row['reason']=f'response/receipt count mismatch {len(responses)}/{len(plans)}'
        row['unit_domain_evidence']=evidence;cases.append(row)
        write(a.output/'analysis/descriptive_decisions'/f"{info['id']}.json",decisions)
    # One historical self-replay has explicit submissions and established response gate.
    replay=a.replay_source
    certified=[]
    if replay and (replay/'manifest.json').exists():
        m=read(replay/'manifest.json'); original=read(Path(m['replay']['from'])/'manifest.json')
        valid=m.get('status')=='complete' and m.get('replay_divergence')==[] and m.get('natural_terminal') is True
        valid=valid and m.get('defender_score')==original.get('defender_score') and m.get('ticks_run')==original.get('ticks_run')
        for name,digest in m['artifacts_sha256'].items():
            if sha(track(replay/name))!=digest:raise ValueError('Historical replay artifact drift')
        domains,evidence=hf_domains(m['snapshot'],m['case']['scenario']); decisions=[]
        for frame in lines(replay/'decisions.jsonl'):
            for s in frame.get('submissions',[]):
                decisions.append({'tick':frame['tick'],**coupling(s['commands'],s['result']['accepted'],domains)})
        cert={'scenario':m['case']['scenario'],'arm':'llm-rl','seed':m['case']['seed'],'trace':str(replay),
              'replay_passed':bool(valid),'intrinsic_estimate':2.2,'unit_domain_evidence':evidence,**case_stats(decisions),
              'gate_scope':'historical self-response replay, zero recorded response divergence, same V and ticks; not a new exact full-state gate'}
        if valid and cert['effective_mean'] is not None: certified.append(cert)
        write(a.output/'analysis/historical_replay_case.json',cert)
        write(a.output/'analysis/historical_replay_decisions.json',decisions)
    scenarios=sorted({c['scenario'] for c in cases}); table=[]
    for sid in scenarios:
        desc={arm:seed_summary([c for c in cases if c['scenario']==sid and c['arm']==arm]) for arm in ('llm-rule','llm-rl')}
        cert=[c for c in certified if c['scenario']==sid]
        table.append({'scenario':sid,'intrinsic_estimate':2.2,'family':'interception/response',
                      'formal_effective':seed_summary(cert),'additional_seed_descriptive':desc,
                      'status':'historical_replay_single_seed' if cert else 'NA_no_case_matched_replay_evidence'})
    result={'status':'partial_missing_replay_coverage','table':table,'cases':cases,'certified_cases':certified,
            'main_five_seed':'no explicit allocation mapping/replay proof found; no substitution of additional seed31 as main5',
            'seed31_batch':str(a.source),'physical_domains':'explicit frozen platform catalog, not target_domains or unit ID prefix',
            'no_monotonicity_test':'intrinsic family estimate is constant2.2 for all14; rank correlation undefined'}
    rows=['|场景|回放证据下effective|intrinsic估计|额外seed31 LLM+Rule描述值|额外seed31 LLM+RL描述值|','|---|---|---:|---|---|']
    for r in table:
        rows.append(f"|{r['scenario']}|{r['formal_effective']['mean'] if r['formal_effective']['n'] else 'NA'} (n={r['formal_effective']['n']})|2.2|{r['additional_seed_descriptive']['llm-rule']['mean']}|{r['additional_seed_descriptive']['llm-rl']['mean']}|")
    md(a.output/'reports/B1_高保真报告.md','# B1 高保真14场景：覆盖审计与可测量部分\n\n'+'\n'.join(rows)+
       '\n\n正式主表5seed轨迹尚缺明确分配域映射/逐case回放准入证据，不能从任务ID猜单位，也不能把额外seed31冒充主表5seed。'+
       '\n\n描述列仅来自额外seed31冻结批次，按响应与接收日志顺序对应，原生解析回退或任务映射缺失时整次分配为NA；它不是正式B1全覆盖交付。历史IE08 LLM+RL自回放具有原生提交记录和零响应偏离，核对同分数同tick，可单独报告；其证据强度不是完整逐状态精确回放。单seed不提供置信区间。'+
       '\n\n物理域由场景实体引用的平台目录domain字段确定，不能使用武器target_domains代替平台物理域。所有14个IE按附录A属于拦截交战场景族，intrinsic=2.2为同族预估，不是14次独立测量。恒定intrinsic无法验证跨场景排序。'+
       '\n\n需要补交：论文主批次真实提交记录，以及每case回放门的冻结验证清单。此次不补采新轨迹、不修改场景、不干预旧进程。')
    return result

def e1_audit(a):
    calibration=read(a.source/'analysis/calibration_cases.json'); final=read(a.final_source/'analysis/final-v1/final_analysis.json')
    missing=[]
    for r in calibration:
        p=Path(r['source'])/'report.json'
        if not p.exists() or sha(track(p))!=r['report_sha256']:missing.append(str(p))
    result={'status':'complete' if not missing else 'partial_hash_audit','calibration_cases':len(calibration),'calibration_report_mismatches':missing,
            'final_confirmation':final,'calibration_source':str(a.source),'confirmation_source':str(a.final_source),
            'action':'no rerun; v14 progress is stale, historical complete result retained'}
    md(a.output/'reports/E1状态核实.md','# E1完成情况核实\n\n'+
       f"校准索引含{len(calibration)}局，逐文件SHA核验异常{len(missing)}项。双机正式确认最终分析已存在，详见analysis/result.json原样保留的统计与审计字段。\n\n"+
       'v14清单引用的949局、11局待补、17/18/19/27待确认是旧状态；此次不重复启动已完成任务。原有负向结果、工程记录和最终结论保持不变。')
    return result

def g3_audit(a):
    import yaml
    src=a.source/'openmd/code/eval/run_episode.py';text=track(src).read_text(encoding='utf-8')
    tree=ast.parse(text);funcs={x.name:x for x in tree.body if isinstance(x,ast.FunctionDef)}
    excerpt=ast.get_source_segment(text,funcs['_build_roe_notes'])
    md(a.output/'analysis/current_roe_source.txt',excerpt)
    entries=[]
    tokens=('decoy','feint','diversion','civilian')
    formal=a.source/'openmd/source-code/source_codes/scenarios/formal'
    for ap in sorted(formal.glob('ie_*/agents.yaml')):
        d=yaml.safe_load(track(ap).read_text(encoding='utf-8'))
        for item in (d.get('attack') or {}).get('timeline',[]):
            label=str(item.get('label','wave')); behavior=str(item.get('behavior',''))
            matched=[t for t in tokens if t in (label+' '+behavior).lower()]
            if matched and not any(t in label.lower() for t in tokens):
                entries.append({'scenario_package':ap.parent.name,'label':label,'behavior':behavior,'count':item.get('count'),
                                'tokens_in_behavior_only':matched,'legacy_rule':'non-threat token anywhere in label+behavior',
                                'evidence_kind':'frozen config + historical predicate audit; not an archived actual request',
                                'source':str(ap)})
    requests=[]
    if a.request_source and a.request_source.exists():
        for folder in sorted((a.request_source/'attempts/confirmation').glob('llm-*/*')):
            # Grid requests are not HF no-intel evidence. Deliberately not used.
            pass
    # Two components of one root failure, not two independent causal interventions.
    directives=[{'id':'K1','excerpt':'real air package ... declared NON-THREAT',
                 'source':'run_episode._build_roe_notes docstring','kind':'historical code-comment excerpt, not verbatim archived request',
                 'meaning':'A true armed package was falsely designated non-threatening by substring matching.'},
                {'id':'K2','excerpt':'do NOT intercept or fire at it',
                 'source':'same historical docstring','kind':'second component of the same failure',
                 'meaning':'Suppresses correct engagement; not an independent second diagnosed bug.'},
                {'id':'K3','excerpt':'spawn_tick / count / axis / behavior',
                 'source':'declared-mode implementation and historical docstring','kind':'privileged future information, not necessarily a misleading directive',
                 'meaning':'Makes the briefing channel different from no-intel. Do not claim it independently caused losses.'}]
    result={'status':'partial_historical_request_and_csv_needed','historical_candidates':entries,'audit_entries':directives,
            'current_source':str(src),'source_sha256':sha(src),'reference_effects':{'rule':0.000,'llm-rule':0.021,'llm-rl':-0.085},
            'effects_provenance':'v14 leadership checklist reports CSV-verified tab:nointel; exact target CSV subset not located here, numbers preserved as references, not newly re-certified',
            'interpretation':'no-intel versus legacy changes multiple briefing features; audit identifies content defects, does not isolate directive-specific causal effects'}
    md(a.output/'reports/G3_prompt审计.md','# G3 no-intelligence prompt审计材料\n\n'+
       '方法：对冻结场景timeline、历史谓词审计脚本及当前ROE实现逐项对照；区分配置事实、历史注释、现行实现和实际请求记录。当前declared分支已经修复分类缺陷，不能把它重建为旧错误提示词。\n\n'+
       '\n\n'.join(f"{x['id']}：`{x['excerpt']}`。{x['meaning']} 来源类别：{x['kind']}。" for x in directives)+
       '\n\n行为文本命中非威胁关键词、但label自身未命中的候选波次详见analysis/result.json；候选不自动等于实测错误指令。K1/K2是同一根因的两个组件，不凑成两项独立因果发现。'+
       '\n\n清单给定tab:nointel效果量：Rule +0.000、LLM+Rule +0.021、LLM+RL −0.085。此处保留引用值，未找到精确CSV筛选契约前不另行替换或宣称重算认证。'+
       '\n\n尚缺：legacy实际请求原文及对应批次、tab:nointel的准确CSV/筛选规则。没有编辑论文稿件。现有证据支持“识别出误导性内容与信息不对等”，不支持“逐条指令的独立因果效应已被隔离”。')
    return result

def g2_inventory(a):
    matches=[]
    for base in a.search_root:
        for name in ('e1_2x2_option1.json','e1_2x2_option2.json'):
            for p in Path(base).rglob(name):
                if '/envs/' in str(p) or '/.git/' in str(p): continue
                data=read(p);matches.append({'path':str(p),'sha256':sha(p),'summary':data})
    expected={'seeds':list(range(64101,64106)),'files':594,'required':['e1_2x2_option1.json','e1_2x2_option2.json'],
              'reproduction_targets':'V approximately .18 and full-degraded +.62..+.73 across 5tiers'}
    # Never replace the requested coauthor study by an earlier similarly named file.
    result={'status':'blocked_missing_coauthor_Study2','required':expected,'found_named_files':matches,
            'reason':'actual 594-file SHA-manifested Study2 bundle and option2 are not supplied; older option1 is not the requested study',
            'release_change':'none; no guessed or partial archive placed into paper/data'}
    md(a.output/'reports/G2归档缺件清单.md','# G2 Study2归档：缺件\n\n'+
       '需要合作者提供：64101–64105批次全部594文件、原SHA清单、两个option JSON及运行协议。两台服务器既有材料中的旧option1不等于该Study2，不能用来复现指定的0.18与+0.62～+0.73。\n\n'+
       '当前不修改paper/data正式释放区。收到完整包后先验证文件数、哈希与seed/条件边界，再从原生分数逐seed重算两个数字，最后冻结归档、补索引。')
    return result

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='task',required=True)
    for task in ('grid-b1','hf-b1','e1-audit','g3-audit','g2-inventory','grid-replay'):
        q=sub.add_parser(task);q.add_argument('--output',type=Path,required=True)
        q.add_argument('--source',type=Path)
        if task=='grid-b1':q.add_argument('--verify-replay',action='store_true');q.add_argument('--workers',type=int,default=4)
        if task=='grid-replay':q.add_argument('--case',required=True)
        if task=='hf-b1':q.add_argument('--replay-source',type=Path)
        if task=='e1-audit':q.add_argument('--final-source',type=Path,required=True)
        if task=='g3-audit':q.add_argument('--request-source',type=Path)
        if task=='g2-inventory':q.add_argument('--search-root',type=Path,action='append',required=True)
    a=parser.parse_args()
    if a.task=='grid-replay':return replay_grid(a)
    start(a)
    try:
        result={'grid-b1':grid_b1,'hf-b1':hf_b1,'e1-audit':e1_audit,'g3-audit':g3_audit,'g2-inventory':g2_inventory}[a.task](a)
        finish(a,result);return 0
    except Exception as exc:
        md(a.output/'logs/error.txt',traceback.format_exc());write(a.output/'status.json',{'state':'error','error':repr(exc),'at':now()});raise

if __name__=='__main__':raise SystemExit(main())
