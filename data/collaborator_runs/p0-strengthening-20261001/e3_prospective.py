"""Authorized new actual-Grid trajectories, observational self-replay gate.

No archived MAPPO weights, engine edits, scenario edits or label-informed policy.
Fixed seed menu before observation collection. Old E3 events are not pooled.
"""
import argparse
import concurrent.futures as futures
import copy
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import numpy as np
from common import read,write,digest


def source_hashes(source):
    return {str(p.relative_to(source)):digest(p) for p in sorted((source/'code/grid_env').rglob('*.py'))}


def collect(source,out,seed):
    sys.path[:0]=[str(source/'code'),str(Path(__file__).parent/'archive-toolkit')]
    from grid_env.grid_env import GridEnv,MAX_STEPS
    from grid_env.agents.rule_agent import RuleAgent
    from grid_replay import fingerprint,plain
    import grid_env.grid_env as module
    if Path(module.__file__).resolve()!=(source/'code/grid_env/grid_env.py').resolve():
        raise ValueError('Wrong Grid engine imported')
    hashes=source_hashes(source)
    frames={}; original_get=GridEnv._get_observation

    def observe(env,role='blue'):
        obs=original_get(env,role)
        if role=='blue':
            sit=obs.get('situational_data',{})
            for contact in [*sit.get('detected_contacts',[]),*sit.get('unknown_contacts',[])]:
                entity=env.entities.get(contact['id'])
                if entity is None or entity.entity_type.name!='RED_TRANSPORT': continue
                key=(contact['id'],env.step_count)
                if key in frames: continue
                # Only local-grid readout is requested; validated by full shadow rollout below.
                local={uid:env.get_local_observation(uid)['grid'].tolist()
                       for uid in env.blue_units if env.entities[uid].alive}
                frames[key]={'contact':contact['id'],'tick':env.step_count,
                    'position':copy.deepcopy(contact['position']),
                    'heading':copy.deepcopy(contact.get('heading')),'local_grid':local,
                    'gold_real':bool(entity.is_real_threat)}
        return obs

    def rollout(instrument):
        random.seed(seed); np.random.seed(seed)
        GridEnv._get_observation=observe if instrument else original_get
        env=GridEnv(difficulty='medium',seed=seed,task_mode='continuous')
        agent=RuleAgent(role='blue',seed=seed,executor_checkpoint=None)
        agent.plan_interval=10
        trace=[]
        for _ in range(MAX_STEPS):
            obs=env._get_observation('blue')
            action={k:int(v) for k,v in agent.act(obs,env=env).items()}
            env.step(action,None); env.compute_reward('blue')
            trace.append({'tick':env.step_count,'actions':action,'done':bool(env.done),
                 'env_sha256':fingerprint(vars(env)),
                 'broker_sha256':fingerprint({'active':agent.broker.active,'reports':agent.broker.reports,
                                              'stats':agent.broker.stats})})
            if env.done: break
        if not env.done: raise ValueError('Source trajectory did not terminate')
        return trace,plain(env.get_episode_metrics())

    out.mkdir(parents=True,exist_ok=False)
    try:
        trace,metrics=rollout(True)
        shadow,shadow_metrics=rollout(False)
    finally:
        GridEnv._get_observation=original_get
    exact=trace==shadow and metrics==shadow_metrics
    episode={'schema':'p0-e3-prospective-rule-goai@1','seed':seed,'source_hashes':hashes,
       'config':{'difficulty':'medium','task_mode':'continuous','planner':'rule','executor':'GOAI',
                 'plan_interval':10,'MAPPO_weights_used':False},
       'metrics':metrics,'steps':trace,'exact_uninstrumented_shadow':exact}
    write(out/'episode.json',episode)
    write(out/'shadow_episode.json',{'seed':seed,'steps':shadow,'metrics':shadow_metrics})
    if not exact:
        write(out/'audit.json',{'eligible':False,'reason':'Full state/broker/action/metrics mismatch'})
        raise ValueError('Observer changed trajectory; data excluded')
    if hashes!=source_hashes(source): raise ValueError('Grid source changed during collection')
    write(out/'frames.json',{'seed':seed,'variant':'prospective-rule-goai',
        'source_episode_sha256':digest(out/'episode.json'),'frames':plain(sorted(frames.values(),key=lambda x:(x['contact'],x['tick']))),
        'source_batch':'E3-prospective-independent'})
    write(out/'audit.json',{'eligible':True,'exact_replay':True,'frames':len(frames),
        'source_episode_sha256':digest(out/'episode.json'),'frame_file_sha256':digest(out/'frames.json'),
        'validation_level':'Exact full environment state, broker, actions, terminal and all metrics vs uninstrumented shadow'})
    print(json.dumps({'seed':seed,'frames':len(frames),'exact':exact}),flush=True)


def campaign(source,out,workers,seed_start=1301,classifier=None):
    out.mkdir(parents=True,exist_ok=True)
    manifest={'schema':'p0-e3-new-trajectories@1','authorization':'User approved new unchanged-Grid trajectories and independent 400-event confirmation, 2026-10-01',
        'source':str(source),'source_hashes':source_hashes(source),'seeds':list(range(seed_start,seed_start+400)),
        'config':{'difficulty':'medium','task_mode':'continuous','planner':'rule','executor':'GOAI',
                  'plan_interval':10,'MAPPO_weights_used':False},
        'requested_events':400,'per_class':200,'window':'3 observed frames; non-overlap within seed/contact',
        'class_balancing':'Fixed RNG20261001 from whole seed menu; never selected by classifier correctness',
        'old_events_pooled':False,'no_engine_scenario_change':True,'workers':workers,
        'collector_sha256':digest(Path(__file__)),
        'support_script_hashes':{name:digest(Path(__file__).with_name(name)) for name in ['e3_classify.py','common.py']},
        'serialization_helper_sha256':digest(Path(__file__).parent/'archive-toolkit/grid_replay.py'),
        'classifier_sha256':digest(classifier or Path(__file__).with_name('e3_classify.py')),
        'no_guarantee_of_D1':'Keep strong kinematic numeric baseline, report if rule>60% or LLM<85%'}
    if (out/'manifest.json').exists() and read(out/'manifest.json')!=manifest:
        raise ValueError('Collection protocol changed')
    write(out/'manifest.json',manifest)
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
    def run(seed):
        folder=out/'frames'/f'seed-{seed}'
        if (folder/'audit.json').exists() and read(folder/'audit.json').get('eligible'):
            return {'seed':seed,'code':0,'resumed':True}
        if folder.exists(): raise ValueError('Failed/interrupted attempt retained; inspect before retry')
        log=out/'logs'/f'seed-{seed}.log'; log.parent.mkdir(parents=True,exist_ok=True)
        with log.open('w') as f:
            r=subprocess.run([sys.executable,'-B',str(Path(__file__)),'collect',
                  '--source',str(source),'--output',str(folder),'--seed',str(seed)],
                  env=env,stdout=f,stderr=subprocess.STDOUT,timeout=600)
        return {'seed':seed,'code':r.returncode}
    completed=[]
    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for future in futures.as_completed([pool.submit(run,seed) for seed in manifest['seeds']]):
            completed.append(future.result()); write(out/'collection_progress.json',completed)
            if len(completed)%20==0: print(json.dumps({'completed':len(completed),'total':len(manifest['seeds'])}),flush=True)
    write(out/'collection_summary.json',completed)
    if any(r['code'] for r in completed): raise RuntimeError('Engineering source/replay gate failed')
    if source_hashes(source)!=manifest['source_hashes']: raise ValueError('Source integrity failed')
    # Use unchanged classifier. Independent collection never points at old E3 frames.
    command=[sys.executable,'-B',str(classifier or Path(__file__).with_name('e3_classify.py')),
        '--frames',str(out/'frames'),'--output',str(out/'classification'),
        '--endpoints','http://127.0.0.1:8101/v1','http://127.0.0.1:8102/v1',
        '--workers','16','--per-class','200']
    # Freeze before actual LLM calls; demand full requested budget rather than silently shrinking.
    if classifier:
        import e3_classify
        import e3_classify_v2
        e3_classify.SYSTEM=e3_classify_v2.SYSTEM_V2
    from e3_classify import freeze
    events=freeze(out/'frames',out/'classification',200)
    audit=read(out/'classification/dataset_audit.json')
    audit['source']=f'New actual released Grid rule+GOAI trajectories, fixed seeds{seed_start}-{seed_start+399}; independent of previous events'
    audit['prospective_manifest_sha256']=digest(out/'manifest.json')
    write(out/'classification/dataset_audit.json',audit)
    if len(events)!=400:
        write(out/'status.json',{'state':'fixed-source-menu-insufficient','events':len(events),
            'available_counts':audit['available_counts'],'LLM_confirmation_started':False})
        return
    r=subprocess.run(command,env=env)
    if r.returncode: raise RuntimeError('Classification engineering failure')
    write(out/'status.json',{'state':'400-event-classification-complete','n_trajectories':400,
         'n_shadow_trajectories':400,'n_events':400,'old_data_pooled':False,
         'source_unchanged':source_hashes(source)==manifest['source_hashes'],
         'D1_pass':read(out/'classification/analysis.json')['D1_full_protocol_pass']})


def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    for name in ['collect','campaign']:
        q=sub.add_parser(name); q.add_argument('--source',type=Path,required=True); q.add_argument('--output',type=Path,required=True)
        if name=='collect': q.add_argument('--seed',type=int,required=True)
        else:
            q.add_argument('--workers',type=int,default=12)
            q.add_argument('--seed-start',type=int,default=1301)
            q.add_argument('--classifier',type=Path)
    a=p.parse_args()
    if a.cmd=='collect': collect(a.source.resolve(),a.output.resolve(),a.seed)
    else: campaign(a.source.resolve(),a.output.resolve(),a.workers,a.seed_start,a.classifier)


if __name__=='__main__': main()
