"""Frozen count calibration, best-pure selection, D1'/D3, held-out E1 confirmation."""
import argparse
import concurrent.futures as cf
import os
from pathlib import Path
import subprocess
import sys
import time
import json
import numpy as np
from common import read,write,digest,estimate
from pressure_variants import prepare


def outcome(path,row):
    r=read(path)
    if r.get('aborted'):raise ValueError('Aborted simulation')
    c=r['strategy_scorecard'];state=c['terminal']['state']
    if state not in ['defender_success','attacker_success','intruder_success','draw']:raise ValueError('Unclassified native end')
    actual=sum(v['total'] for v in c['force']['coalition.intruder'].values())
    return {'SR':int(state=='defender_success'),'V':float(c['defender_score']),
            'eligible':actual==row['count'] and c['terminal']['tick']>=row['latest_spawn'],
            'tick':c['terminal']['tick'],'actual_intruders':actual}


def d3(values):
    x=np.array(values,float);s=float(x.std(ddof=1));mean=float(x.mean())
    z=mean/s if s>0 else (1e9 if mean>0 else 0.)
    ci=estimate(x)
    return {'paired_gain':ci,'paired_SD':s,'effect_to_SD':z,
            'pass':mean>=s and ci['ci95'][0]>0,'rule':'mean paired gain >= one paired seed SD AND 95% CI lower bound > 0'}


def manipulation_audit(strong,hold):
    def lines(p):return [json.loads(s) for s in p.read_text().splitlines() if s]
    def clean(v):
        if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if k not in ['command_id','action_id','operation_id','idempotency_key']}
        if isinstance(v,list):return [clean(x) for x in v]
        return v
    def actions(folder):
        answer={}
        for r in lines(folder/'action_batches.jsonl'):
            if r['faction']=='coalition.defender':answer.setdefault(r['tick'],[]).append(clean(r))
        return answer
    sa,ha=actions(strong),actions(hold);ticks=set(sa)&set(ha)
    ss={r['tick']:r['sha256'] for r in lines(strong/'defender_states.jsonl')};hs={r['tick']:r['sha256'] for r in lines(hold/'defender_states.jsonl')}
    history=read(hold/'goal_interventions.json')['records']
    changed=sum(r['before']!=r['after'] for r in history)
    legal=all(g['goal_type']=='hold' for r in history for g in r['after'])
    accepted={d:read(f/'report.json')['defender']['broker']['goals_accepted'] for d,f in [('strong',strong),('hold',hold)]}
    controls_changed=any(sa[t]!=ha[t] for t in ticks)
    state_changed=any(ss[t]!=hs[t] for t in set(ss)&set(hs))
    return {'changed_goal_rounds':changed,'legal_full_hold':legal,'goals_accepted':accepted,
            'common_control_ticks':len(ticks),'submitted_controls_changed':controls_changed,'physical_states_changed':state_changed,
            'pass':bool(changed and legal and min(accepted.values())>0 and controls_changed and state_changed)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',type=int,default=24);a=p.parse_args();repo=a.repo.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(out/'campaign.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    m=prepare(repo,out);engine=Path(m['engine']);cal=list(range(4101,4111));screen=list(range(4151,4161));confirm=list(range(4201,4211))
    frozen={'variants_sha':digest(out/'variants.json'),'script_hashes':{n:digest(Path(__file__).with_name(n)) for n in ['count_campaign.py','pressure_variants.py','episode_adapter.py','e1_trial.py','common.py','gate_protocol.json']},
      'calibration_seeds':cal,'gate_seeds':screen,'confirmation_seeds':confirm,'targets':[.4,.6,.8],'tolerance':.03,
      'baseline_selection':'at each count condition, pure arm with largest calibration mean V; ties mean SR then lexical arm; D2 uses that arm SR',
      'count_menu':'coarse first, then every remaining predeclared integer for equal full-menu pure-arm ranking; no hybrid outcomes used',
      'pure_selection_budget':'all three pure arms over same full Rule-wave-complete menu; retain and audit all attempted settings',
      'D1_prime_ratio':.90,'D3':'mean paired gain >= paired SD and seed bootstrap lower CI > 0; each executor separately',
      'D1_scope':'E3 Grid channel result is not a high-fidelity per-scenario D1 certification',
      'runtime_threads':{'TI_CPU_MAX_NUM_THREADS':1,'OMP_NUM_THREADS':1,'OPENBLAS_NUM_THREADS':1,'MKL_NUM_THREADS':1},
      'weights':{n:digest(repo/'openmd/code/eval/_w1_runs/rl'/n) for n in ['theta_rl_legacy2.npz','theta_arm5_v12.npz']},
      'LLM':{'temperature':0,'thinking':False,'max_tokens':1024,'model':'Qwen3.8-27B','endpoints':['http://127.0.0.1:8101/v1','http://127.0.0.1:8102/v1']}}
    if (out/'protocol.json').exists() and read(out/'protocol.json')!=frozen:raise ValueError('Frozen protocol changed')
    write(out/'protocol.json',frozen)
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',TI_CPU_MAX_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg',MPLCONFIGDIR=str(out/'mpl'))
    def run_batch(jobs,phase):
        def run(job):
            row,seed,arm,dose,greedy=job;folder=out/phase/row['public_id']/f'{arm}-{dose}-g{int(greedy)}'/f'seed-{seed}'
            config={'scenario':row['public_id'],'seed':seed,'arm':arm,'dose':dose,'greedy':greedy,'protocol_sha':digest(out/'protocol.json')}
            done=folder/'completion.json'
            if done.exists():
                c=read(done)
                if c['config']!=config or c['exit_code']!=0 or digest(folder/'report.json')!=c['report_sha']:raise ValueError('Incomplete/modified attempt retained')
                return {**config,'outcome':outcome(folder/'report.json',row),'reused':True}
            if folder.exists():raise ValueError('Interrupted attempt retained')
            folder.mkdir(parents=True)
            cmd=[sys.executable,'-B',str(Path(__file__).with_name('episode_adapter.py')),'--repo',str(repo),'--engine',str(engine),
              '--scenario',row['public_id'],'--seed',str(seed),'--arm',arm,'--dose',dose,'--output',str(folder),'--endpoint',frozen['LLM']['endpoints'][seed%2]]
            if greedy:cmd.append('--greedy')
            start=time.time()
            with (folder/'stdout.log').open('w') as log:
                code=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=7200).returncode
            write(done,{'config':config,'exit_code':code,'elapsed_seconds':time.time()-start,'report_sha':digest(folder/'report.json') if (folder/'report.json').exists() else None})
            if code:raise RuntimeError(f'Episode exit {code}: {folder}')
            return {**config,'outcome':outcome(folder/'report.json',row)}
        records=[];write(out/'progress.json',{'phase':phase,'done':0,'total':len(jobs),'started_at':time.time()})
        with cf.ThreadPoolExecutor(max_workers=a.workers if all(j[2] in ['rule','rl','rule-rl'] for j in jobs) else 8) as pool:
            for f in cf.as_completed([pool.submit(run,j) for j in jobs]):
                try:records.append(f.result())
                except Exception as e:records.append({'error':repr(e)})
                write(out/f'{phase}_jobs.json',records);write(out/'progress.json',{'phase':phase,'done':len(records),'total':len(jobs),'updated_at':time.time()})
        if any('error' in r for r in records):write(out/'status.json',{'state':'engineering-review-required','phase':phase});raise RuntimeError('Engineering failures retained')
        return records
    def table(rows,seeds,arms,phase):
        answer=[]
        for row in rows:
            for arm in arms:
                cases=[outcome(out/phase/row['public_id']/f'{arm}-strong-g0'/f'seed-{s}'/'report.json',row) for s in seeds]
                answer.append({**row,'arm':arm,'SR':estimate([r['SR'] for r in cases]),'V':estimate([r['V'] for r in cases]),'eligible':all(r['eligible'] for r in cases),'cases':cases})
        return answer
    rows=m['variants'];coarse=[r for r in rows if r['coarse']]
    run_batch([(r,s,'rule','strong',False) for r in coarse for s in cal],'calibration-rule')
    coarse_stats=table(coarse,cal,['rule'],'calibration-rule');write(out/'coarse_analysis.json',coarse_stats)
    def misses(stats):return any(not any(r['eligible'] and abs(r['SR']['mean']-t)<=.03 for r in stats if r['family']==f) for f in ['IE-05-MULTI-AXIS','IE-09-STAGGERED-WAVES'] for t in [.4,.6,.8])
    # Pure-arm global selection requires the same full frozen menu for all arms.
    remaining=[r for r in rows if not r['coarse']]
    run_batch([(r,s,'rule','strong',False) for r in remaining for s in cal],'calibration-rule')
    rules=table(rows,cal,['rule'],'calibration-rule');write(out/'calibration_rule_analysis.json',rules)
    # Vm is defined by mean score, not mean success rate. A Rule-only SR
    # ceiling therefore does NOT certify infeasibility of the best-score arm.
    eligible=[r for r in rows if next(x for x in rules if x['public_id']==r['public_id'])['eligible']]
    run_batch([(r,s,arm,'strong',False) for r in eligible for s in cal for arm in ['rl','pure-llm']],'calibration-pure')
    stats=[r for r in rules if r['eligible']]+table(eligible,cal,['rl','pure-llm'],'calibration-pure');write(out/'calibration_all_analysis.json',stats)
    complete={r['public_id'] for r in eligible if all(x['eligible'] for x in stats if x['public_id']==r['public_id'])}
    stats=[r for r in stats if r['public_id'] in complete]
    selected=[]
    for family in ['IE-05-MULTI-AXIS','IE-09-STAGGERED-WAVES']:
        subset=[r for r in stats if r['family']==family]
        if not subset:write(out/'status.json',{'state':'no-arm-complete-settings','family':family,'confirmation_started':False});return
        best=[]
        for setting in sorted({r['public_id'] for r in subset}):
            peers=[r for r in subset if r['public_id']==setting]
            r=min(peers,key=lambda r:(-r['V']['mean'],-r['SR']['mean'],r['arm']))
            best.append({**r,'all_pure_SR':{x['arm']:x['SR']['mean'] for x in peers},'maximum_pure_SR_sensitivity':max(x['SR']['mean'] for x in peers)})
        write(out/f'best_pure_calibration_{family}.json',best)
        for target in [.4,.6,.8]:
            options=best
            if not options:raise ValueError('No complete eligible family')
            r=min(options,key=lambda r:(abs(r['SR']['mean']-target),r['count']))
            if abs(r['SR']['mean']-target)>.03:write(out/'status.json',{'state':'count-menu-infeasible','family':family,'target':target,'closest_best_arm':r['arm'],'closest_count':r['count'],'closest_SR':r['SR']['mean'],'confirmation_started':False});return
            selected.append({**r,'target_SR':target})
    write(out/'frozen_tiers.json',selected)
    mids=[r for r in selected if r['target_SR']==.6]
    gate_jobs=[(r,s,arm,dose,False) for r in mids for s in screen for arm in ['rule','rule-rl'] for dose in ['strong','hold']]
    gate_jobs += [(r,s,'rule','strong',True) for r in mids for s in screen]
    gates=run_batch(gate_jobs,'gate-screening');d3rows=[];prime=[]
    for row in mids:
        subset=[r for r in gates if r['scenario']==row['public_id']]
        for arm in ['rule','rule-rl']:
            delta=[next(r['outcome']['V'] for r in subset if r['seed']==s and r['arm']==arm and r['dose']=='strong' and not r['greedy'])-next(r['outcome']['V'] for r in subset if r['seed']==s and r['arm']==arm and r['dose']=='hold') for s in screen]
            audits=[manipulation_audit(out/'gate-screening'/row['public_id']/f'{arm}-strong-g0'/f'seed-{s}',out/'gate-screening'/row['public_id']/f'{arm}-hold-g0'/f'seed-{s}') for s in screen]
            complete=all(r['outcome']['eligible'] for r in subset if r['arm']==arm and not r['greedy'])
            test=d3(delta);test['statistical_pass']=test['pass'];test['pass']=test['pass'] and all(r['pass'] for r in audits) and complete
            d3rows.append({'family':row['family'],'arm':arm,**test,'manipulation_audits':audits,'wave_complete':complete})
        regular=np.mean([r['outcome']['V'] for r in subset if r['arm']=='rule' and r['dose']=='strong' and not r['greedy']]);greedy=np.mean([r['outcome']['V'] for r in subset if r['greedy']])
        complete=all(r['outcome']['eligible'] for r in subset if r['arm']=='rule' and r['dose']=='strong')
        prime.append({'family':row['family'],'greedy_V':float(greedy),'rule_V':float(regular),'pass':bool(greedy<.9*regular and complete),'ratio':float(greedy/regular) if regular else None,'wave_complete':complete})
    write(out/'gates.json',{'D3':d3rows,'D1_prime':prime,'D1_highfi':'not certified by Grid; scenarios have no declared feint/genuine label contract'})
    # Gate failures remain part of the experiment; E1 headroom-only comparison is
    # reported as diagnostic, never silently promoted to an all-gates positive region.
    # 180 originally specified comparisons + 120 other-pure checks. Vm uses
    # actual highest confirmation mean score; calibration selector is for D2 only.
    run_batch([(r,s,arm,'strong',False) for r in selected for s in confirm for arm in ['rule','rl','pure-llm','llm','llm-rl']],'confirmation')
    result={'state':'confirmation-complete','n_confirmation':300,'n_primary_comparisons':180,'n_additional_pure_checks':120,'all_gates_positive_region_claim':False,
            'D1_highfi':'not certified','D3':d3rows,'D1_prime':prime,'source_unchanged':all(digest(repo/'openmd/source-code/source_codes'/n)==h for n,h in m['original_hashes'].items())}
    write(out/'status.json',result)


if __name__=='__main__':main()
