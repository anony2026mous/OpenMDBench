"""D1 channel v2: development-coverage-selected eight observed public contacts.

Same-information motion control is always retained. No hidden truth in prompts.
"""
import argparse
import concurrent.futures as cf
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import numpy as np
from common import read,write,digest


def hashes(source):
    return {str(p.relative_to(source)):digest(p) for p in (source/'code/grid_env').rglob('*.py')}


def collect(source,out,seed):
    sys.path[:0]=[str(source/'code'),str(Path(__file__).parent/'archive-toolkit')]
    from grid_env.grid_env import GridEnv,MAX_STEPS
    from grid_env.agents.rule_agent import RuleAgent
    from grid_replay import fingerprint,plain
    import grid_env.grid_env as module
    if Path(module.__file__).resolve()!=source/'code/grid_env/grid_env.py':raise ValueError('Wrong engine')
    frozen=hashes(source);frames={};get=GridEnv._get_observation
    def observe(env,role='blue'):
        obs=get(env,role)
        if role!='blue':return obs
        locals={uid:plain(env.get_local_observation(uid)) for uid in env.blue_units if env.entities[uid].alive}
        for c in [*obs.get('situational_data',{}).get('detected_contacts',[]),*obs.get('situational_data',{}).get('unknown_contacts',[])]:
            e=env.entities.get(c['id'])
            if e is None or e.entity_type.name!='RED_TRANSPORT':continue
            key=(c['id'],env.step_count)
            frames[key]={'contact':c['id'],'tick':env.step_count,'position':plain(c['position']),
                         'heading':plain(c.get('heading')),'local_observations':copy.deepcopy(locals),
                         'gold_real':bool(e.is_real_threat)}
        return obs
    def rollout(instrument):
        random.seed(seed);np.random.seed(seed);GridEnv._get_observation=observe if instrument else get
        env=GridEnv(difficulty='medium',seed=seed,task_mode='continuous');agent=RuleAgent(role='blue',seed=seed,executor_checkpoint=None);agent.plan_interval=10
        trace=[]
        for _ in range(MAX_STEPS):
            obs=env._get_observation('blue');action={k:int(v) for k,v in agent.act(obs,env=env).items()}
            env.step(action,None);env.compute_reward('blue')
            trace.append({'tick':env.step_count,'actions':action,'done':bool(env.done),'state_sha':fingerprint(vars(env)),
                          'broker_sha':fingerprint({'active':agent.broker.active,'reports':agent.broker.reports,'stats':agent.broker.stats})})
            if env.done:break
        if not env.done:raise ValueError('No native terminal')
        return trace,plain(env.get_episode_metrics())
    out.mkdir(parents=True,exist_ok=False)
    try:t,metrics=rollout(True);shadow,sm=rollout(False)
    finally:GridEnv._get_observation=get
    write(out/'episode.json',{'seed':seed,'trace':t,'metrics':metrics,'source_hashes':frozen})
    write(out/'shadow.json',{'seed':seed,'trace':shadow,'metrics':sm})
    if t!=shadow or metrics!=sm:write(out/'audit.json',{'eligible':False});raise ValueError('Observer not read-only')
    if frozen!=hashes(source):raise ValueError('Source changed')
    write(out/'frames.json',{'seed':seed,'frames':sorted(frames.values(),key=lambda r:(r['contact'],r['tick']))})
    write(out/'audit.json',{'eligible':True,'exact_uninstrumented_shadow':True,'frames_sha':digest(out/'frames.json')})


def visible_local(frame):
    """Closest observer that actually displays the candidate, deterministic ties."""
    x,y=frame['position'];options=[]
    for uid,local in frame['local_observations'].items():
        own=np.asarray(local['own_state'],float);cx,cy=np.rint(own[:2]*20).astype(int)
        grid=np.asarray(local['grid']);lo=-4 if grid.shape==(8,8) else -2
        gx,gy=int(x-cx-lo),int(y-cy-lo)
        if 0<=gx<grid.shape[0] and 0<=gy<grid.shape[1] and grid[gx,gy]==4:
            options.append((abs(x-cx)+abs(y-cy),uid,local,gx,gy))
    return min(options,key=lambda r:(r[0],r[1])) if options else None


def current_features(frame):
    """Strong local-only pre-Goal features with an observable candidate-cell pointer.

    Offline identity matches a visible code-4 cell; IDs/roles/history/Goal excluded.
    """
    visible=visible_local(frame)
    if visible is None:return None
    x,y=frame['position'];_,_,local,gx,gy=visible;grid=np.asarray(local['grid']);own=np.asarray(local['own_state'],float)
    plane=np.zeros((8,8));off=(8-grid.shape[0])//2;plane[off:off+grid.shape[0],off:off+grid.shape[1]]=grid/6.
    lk=local.get('lock_view') or {};age=float(lk.get('lock_age',0));unc=float(lk.get('uncertainty') or 0)
    # Candidate position is recoverable from current grid + own current position.
    target=lk.get('target_pos_est');tx,ty=target if target is not None else (0.,0.)
    extras=[x/20.,y/20.,(1-x)/20.,(18-y)/20.,gx/8.,gy/8.,float(local.get('kind')=='uav'),
            float(local.get('comm_delay',0))/10.,float(local.get('jammed_steps',0))/10.,float(lk.get('locked',False)),age/20.,unc/20.]
    return np.r_[plane.ravel(),own,[tx/20.,ty/20.,float(target is not None)],extras].tolist()


def events(folder):
    answer=[]
    for path in sorted(folder.glob('seed-*/frames.json')):
        a=read(path.with_name('audit.json'))
        if not a['eligible'] or digest(path)!=a['frames_sha']:raise ValueError('Ungated frames')
        meta=read(path);contacts={}
        for r in meta['frames']:contacts.setdefault(r['contact'],[]).append(r)
        for cid,history in contacts.items():
            for i in range(0,len(history)-7,8):
                window=history[i:i+8];last=window[-1]
                if window[-1]['tick']-window[0]['tick']>30 or any(r['heading'] is None for r in window):continue
                features=current_features(last)
                if features is None:continue # lower channel really sees this contact now
                texts=['Anonymous transport. Protected port at (1,18). Eight observed public contacts:']
                for r in window:texts.append(f"t={r['tick']} position={r['position']} observed_delta={r['heading']}")
                local=visible_local(last)[2]
                public_local={k:v for k,v in local.items() if k!='subgoal'}
                texts.append('Current candidate-visible local observation: '+json.dumps(public_local,separators=(',',':')))
                token=f"{meta['seed']}:{cid}:{[r['tick'] for r in window]}";event_id=hashlib.sha256(token.encode()).hexdigest()[:24]
                answer.append({'id':event_id,'seed':meta['seed'],'gold_real':last['gold_real'],'source_batch':'D1-channel-20261002-v2',
                               'local_features':features,'numeric':{'positions':[r['position'] for r in window],'headings':[r['heading'] for r in window]},
                               'prompt':'\n'.join(texts),'ticks':[r['tick'] for r in window],
                               'candidate_local_visible':True,'candidate_grid_cell':list(visible_local(last)[3:])})
    return answer


def design(x,quadratic):
    x=np.array(x,float)
    return np.c_[x,x[:,-12:]**2] if quadratic else x


def fit(x,y,lam,quadratic):
    x=design(x,quadratic);mean=x.mean(0);scale=np.maximum(x.std(0),1e-6);z=(x-mean)/scale
    z=np.c_[np.ones(len(z)),z];y=np.array(y,float);w=np.zeros(z.shape[1])
    if not np.any(y) or np.all(y):raise ValueError('Training requires both classes')
    sample_weight=np.where(y>0,.5/np.mean(y),.5/(1-np.mean(y)))
    # Deterministic full-batch convex logistic regression with Adam.
    m=np.zeros_like(w);v=np.zeros_like(w)
    for t in range(1,801):
        p=1/(1+np.exp(-np.clip(z@w,-30,30)));grad=z.T@((p-y)*sample_weight)/len(z)+lam*np.r_[0.,w[1:]]
        m=.9*m+.1*grad;v=.999*v+.001*grad**2;w-=.03*(m/(1-.9**t))/(np.sqrt(v/(1-.999**t))+1e-8)
    return {'weights':w.tolist(),'mean':mean.tolist(),'scale':scale.tolist(),'lambda':lam,'quadratic':quadratic}


def predict(model,x):
    z=(design(x,model['quadratic'])-np.array(model['mean']))/np.array(model['scale'])
    return (1/(1+np.exp(-np.clip(np.c_[np.ones(len(z)),z]@np.array(model['weights']),-30,30)))).tolist()


def train(rows):
    if len(rows)<80 or len({r['seed'] for r in rows})<20:raise ValueError('Numeric development sample too small')
    seeds=sorted({r['seed'] for r in rows});random.Random(20261002).shuffle(seeds);fold={s:i%4 for i,s in enumerate(seeds)}
    x=[r['local_features'] for r in rows];y=np.array([r['gold_real'] for r in rows]);grid=[]
    for quadratic in [False,True]:
        for lam in [.01,.1,1.,10.]:
            correct=0;n=0
            for k in range(4):
                tr=[i for i,r in enumerate(rows) if fold[r['seed']]!=k];te=[i for i,r in enumerate(rows) if fold[r['seed']]==k]
                model=fit([x[i] for i in tr],y[tr],lam,quadratic);probs=np.array(predict(model,[x[i] for i in te]))
                # Balanced accuracy prevents a majority-class weak comparator.
                truth=y[te]
                if not np.any(truth) or np.all(truth):raise ValueError('CV fold lacks a class')
                correct+=.5*(np.mean((probs[truth]>.5)==truth[truth])+np.mean((probs[~truth]>.5)==truth[~truth]));n+=1
            grid.append({'quadratic':quadratic,'lambda':lam,'group_CV_accuracy':correct/n})
    best=min(grid,key=lambda r:(-r['group_CV_accuracy'],r['quadratic'],-r['lambda']))
    return {'model':fit(x,y,best['lambda'],best['quadratic']),'selection':best,'CV_grid':grid,'n_train_events':len(rows),'n_train_seed_clusters':len(seeds)}


def campaign(source,out,workers):
    out.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(out/'campaign.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    protocol={'date':'2026-10-02','source':str(source),'source_hashes':hashes(source),'history':{'observed_contacts':8,'maximum_tick_span':30,'nonoverlap':True},
       'history_selection':'largest among 10/8/5/3 with >=40 development events and >=20 seed clusters per class; coverage only, no classifier outcomes inspected',
       'development_coverage_sha':digest(Path(__file__).with_name('development_coverage.json')),
       'reused_development':'raw observationally verified 400 source episodes from failed 10-contact development; no confirmation responses existed',
       'development_seeds':list(range(5101,5501)),'confirmation_initial_seeds':list(range(5601,6401)),
       'confirmation_extension_seeds':list(range(6401,7201)),'extension_rule':'before model calls only, if fewer than 200 eligible candidates in either class',
       'numeric_model':'L2 logistic + current-coordinate quadratic candidates, strongest declared group-CV model; no Goal/history/IDs/gold at prediction',
       'numeric_feature_scope':'current complete local grid/own state/kind/comm/jam/lock summaries and candidate cell; pre-Goal channel, not Goal-enriched executor',
       'thresholds':{'rule_max':.6,'LLM_min':.85,'class_balance':[200,200]},'LLM':'frozen previously developed motion-rule-guided prompt; no new tuning on confirmation',
       'strong_motion_control_retained':True,'no_engine_edits':True,'old_confirm_events_pooled':False,
       'training_prior':'balanced development subset; class-balanced loss in every seed-CV fold',
       'script_hashes':{n:digest(Path(__file__).with_name(n)) for n in ['channel_experiment.py','e3_classify.py','e3_classify_v2.py','common.py','gate_protocol.json']},
       'observer_helper_sha':digest(Path(__file__).parent/'archive-toolkit/grid_replay.py')}
    if (out/'protocol.json').exists() and read(out/'protocol.json')!=protocol:raise ValueError('Frozen protocol changed')
    write(out/'protocol.json',protocol)
    env=dict(os.environ,OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
    def block(seeds,folder,label=None):
        label=label or folder
        def run(seed):
            target=out/folder/f'seed-{seed}'
            if (target/'audit.json').exists() and read(target/'audit.json').get('eligible'):return {'seed':seed,'resumed':True}
            if target.exists():raise ValueError('Interrupted collection retained')
            log=out/'logs'/f'{folder}-{seed}.log';log.parent.mkdir(parents=True,exist_ok=True)
            with log.open('w') as f:
                code=subprocess.run([sys.executable,'-B',str(Path(__file__)),'collect','--source',str(source),'--output',str(target),'--seed',str(seed)],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=600).returncode
            if code:raise RuntimeError(f'Collector failed seed{seed}')
            return {'seed':seed,'code':code}
        records=[]
        with cf.ThreadPoolExecutor(max_workers=workers) as pool:
            for f in cf.as_completed([pool.submit(run,s) for s in seeds]):
                records.append(f.result());write(out/'progress.json',{'phase':label,'done':len(records),'total':len(seeds)})
        write(out/f'{label}_jobs.json',records)
    block(protocol['development_seeds'],'development')
    dev=events(out/'development');write(out/'development_events.json',dev)
    if (out/'numeric_model.json').exists():
        trained=read(out/'numeric_model.json')
        if trained['development_events_sha']!=digest(out/'development_events.json'):raise ValueError('Numeric development sample changed')
    else:
        # Equal training priors, selected only on development labels. Preserve
        # the entire candidate pool and selection IDs for audit.
        rng=random.Random(20261002);groups=[[r for r in dev if r['gold_real']==v] for v in [False,True]]
        n=min(map(len,groups));balanced=[]
        for group in groups:rng.shuffle(group);balanced+=group[:n]
        trained=train(balanced);trained['development_events_sha']=digest(out/'development_events.json')
        trained['training_event_ids']=[r['id'] for r in balanced];trained['training_class_counts']=[n,n]
        write(out/'numeric_model.json',trained)
    block(protocol['confirmation_initial_seeds'],'confirmation_sources')
    candidates=events(out/'confirmation_sources')
    def counts(rows):return {str(v):sum(r['gold_real']==v for r in rows) for v in [False,True]}
    if min(counts(candidates).values())<200:
        block(protocol['confirmation_extension_seeds'],'confirmation_sources','confirmation_sources_extension')
        candidates=events(out/'confirmation_sources')
    counts_now=counts(candidates);write(out/'candidate_audit.json',{'counts':counts_now,'model_frozen_before_confirmation':True})
    if min(counts_now.values())<200:write(out/'status.json',{'state':'predeclared-source-pool-insufficient','LLM_started':False,'counts':counts_now});return
    rng=random.Random(20261002);selected=[]
    for value in [False,True]:
        group=[r for r in candidates if r['gold_real']==value];rng.shuffle(group);selected+=group[:200]
    rng.shuffle(selected);classification=out/'classification'
    if (classification/'dataset.json').exists():
        if read(classification/'dataset.json')!=selected:raise ValueError('Frozen event selection changed')
    else:write(classification/'dataset.json',selected)
    audit={'available_counts':counts_now,'actual_per_class':200,'full_400_event_budget_met':True,'full_requested_protocol_complete':True,
        'seed_clusters':sorted({r['seed'] for r in selected}),'dataset_sha256':digest(classification/'dataset.json'),
        'source':'Independent current remote Grid predeclared source pool; exact observer/shadow verification',
        'truth_boundary':'gold roles only offline; no candidate IDs or seeds in prompts','history_window':protocol['history'],
        'numeric_model_sha256':digest(out/'numeric_model.json'),'protocol_sha256':digest(out/'protocol.json')}
    write(classification/'dataset_audit.json',audit)
    # Raw helper output retains matched-information motion control and its own D1.
    cmd=[sys.executable,'-B',str(Path(__file__).with_name('e3_classify_v2.py')),'--frames',str(out/'confirmation_sources'),
      '--output',str(classification),'--endpoints','http://127.0.0.1:8101/v1','http://127.0.0.1:8102/v1','--workers','8','--per-class','200']
    if subprocess.run(cmd,env=env).returncode:raise RuntimeError('Classifier failed')
    import e3_classify
    pred=read(classification/'predictions.json');mapping={r['id']:r for r in selected}
    probs=predict(trained['model'],[mapping[r['id']]['local_features'] for r in pred])
    for row,prob in zip(pred,probs):row['local_p_real']=prob
    numeric=e3_classify.metrics(pred,'local_p_real');llm=e3_classify.metrics(pred,'llm_p_real');motion=e3_classify.metrics(pred,'rule_p_real')
    errors=sum(r['llm_p_real'] is None for r in pred)
    result={'state':'independent-confirmation-complete','local_numeric':numeric,'LLM':llm,'strong_same_information_motion':motion,
        'D1_channel_point_pass':numeric['accuracy']<=.6 and llm['accuracy']>=.85 and errors==0,
        'D1_matched_information_point_pass':motion['accuracy']<=.6 and llm['accuracy']>=.85 and errors==0,
        'errors':errors,'scope':'offline current local pre-Goal vs 8 public contacts; not high-fidelity D1 or online autonomous accuracy',
        'source_unchanged':hashes(source)==protocol['source_hashes'],'old_events_pooled':False,'numeric_model_sha':digest(out/'numeric_model.json')}
    write(out/'channel_predictions.json',pred);write(out/'channel_analysis.json',result);write(out/'status.json',result)
    if not result['source_unchanged']:raise ValueError('Remote source changed during confirmation')


def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True)
    for name in ['collect','campaign']:
        q=s.add_parser(name);q.add_argument('--source',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
        if name=='collect':q.add_argument('--seed',type=int,required=True)
        else:q.add_argument('--workers',type=int,default=12)
    a=p.parse_args()
    if a.cmd=='collect':collect(a.source.resolve(),a.output.resolve(),a.seed)
    else:campaign(a.source.resolve(),a.output.resolve(),a.workers)


if __name__=='__main__':main()
