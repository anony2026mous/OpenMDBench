"""Frozen E10 HF experiment, native scenes, restricted current continuous input."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

import numpy as np

SCENES = ['IE-06-DECOY-MIXED', 'IE-11-DECOY-SCREEN']
DEV = list(range(19001, 19011))
CONF = list(range(19101, 19111))


def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p, v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_name(p.name+'.tmp')
    temp.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temp.replace(p)


def restricted(pub):
    """Six instantaneous public contact numbers; never accepts gold or history."""
    return [*(float(x)/10000 for x in pub['estimated_position_m']),
            float(pub['confidence']),float(pub['quality']),float(pub['age_ticks'])/10]


def freeze_sources(repo, root):
    engine=repo/'openmd/source-code/source_codes'
    files=[p for p in engine.rglob('*') if p.is_file() and p.suffix in ['.py','.yaml','.json']]
    files += list((repo/'openmd/code/eval').glob('*.py'))
    files += [root/'code'/n for n in ['e1_trial.py','common.py']]
    files += list((root/'code-d1-followup').glob('*.py'))
    files += [root/'code-complex'/n for n in ['channel_experiment.py','common.py']]
    files += [p for p in Path(__file__).parent.iterdir() if p.is_file() and p.suffix in ['.py','.md']]
    return {str(p):sha(p) for p in sorted(set(files))}


def verify(frozen):
    for p,h in frozen.items():
        if sha(p)!=h:raise ValueError(f'Frozen source changed: {p}')


def events(folder, helper):
    rows=[]
    for path in sorted((folder/'sources').glob('*/seed-*/observed/public_frames.json')):
        meta=read(path);hist={}
        for frame in meta['frames']:
            dedup={}
            for q in frame['contacts']:
                pub=q['public']
                if float(pub['estimated_position_m'][2])<=10:continue
                target=q['offline_target'];previous=dedup.get(target)
                if previous is None or (-pub['confidence'],pub['contact_id'])<(-previous['public']['confidence'],previous['public']['contact_id']):
                    dedup[target]=q
            for target,q in dedup.items():hist.setdefault(target,[]).append((frame,q))
        for target,track in hist.items():
            # Overlap is explicitly frozen. Inference resamples seeds, not windows.
            for i in range(len(track)-7):
                w=track[i:i+8];frame,q=w[-1];pub=q['public']
                if w[-1][0]['tick']-w[0][0]['tick']>40:continue
                if len({a['public']['observed_tick'] for _,a in w})<4:continue
                if len({a['offline_gold_real'] for _,a in w})!=1:raise ValueError('Unstable role label')
                anon='c_'+hashlib.sha256(f"anonymous:{meta['seed']}:{target}".encode()).hexdigest()[:12]
                current={k:v for k,v in pub.items() if k not in ['contact_id','observer_entity_id']}
                public={'candidate':anon,'current':current,
                        'own_snapshot':[{k:v for k,v in o.items() if k!='entity_id'} for o in frame['own_public']],
                        'protected_facilities_m':[[-1200,-200,0],[700,-400,0]],
                        'other_current_contacts':[{k:v for k,v in z['public'].items() if k not in ['contact_id','observer_entity_id']} for z in frame['contacts']],
                        'contact_history':[{'tick':f['tick'],'observed_tick':a['public']['observed_tick'],
                            'estimated_position_m':a['public']['estimated_position_m'],'confidence':a['public']['confidence'],
                            'age_ticks':a['public']['age_ticks']} for f,a in w]}
                prompt=json.dumps(public,separators=(',',':'))
                for bad in ['intruder.','offline_gold','spawn_tick','loadout','ammunition','decoy-','target.facility']:
                    if bad in prompt:raise ValueError('Hidden label/identity in prompt')
                ticks=[f['tick'] for f,_ in w]
                eid=hashlib.sha256(f"{meta['scenario']}:{meta['seed']}:{target}:{ticks}".encode()).hexdigest()[:24]
                rows.append({'id':eid,'scene':meta['scenario'],'seed':meta['seed'],
                             'offline_target':target,'gold_real':q['offline_gold_real'],
                             'features':restricted(pub),'full_features':helper.local_features(frame,pub),
                             'prompt':prompt,'ticks':ticks})
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate events')
    return rows


def quotas(capacity, total=200):
    """Capped equal allocation; all seeds represented, no prediction input."""
    if not capacity or any(n<1 for n in capacity.values()):
        raise ValueError('Each seed requires both classes')
    if total<len(capacity) or sum(capacity.values())<total:
        raise ValueError(f'Total balanced coverage insufficient: {sum(capacity.values())}<{total}')
    q={s:1 for s in sorted(capacity)}
    while sum(q.values())<total:
        s=min((s for s in q if q[s]<capacity[s]),key=lambda s:(q[s],s))
        q[s]+=1
    return q


def select(rows, seeds, phase='confirmation'):
    """Within-seed class balance; between-seed count may differ by coverage."""
    selected=[];rng=random.Random(20261003);allocations={}
    for scene in SCENES:
        groups={(seed,gold):sorted([r for r in rows if r['scene']==scene and r['seed']==seed and r['gold_real']==gold],key=lambda r:r['id'])
                for seed in seeds for gold in [False,True]}
        capacity={s:min(len(groups[s,False]),len(groups[s,True])) for s in seeds}
        if phase=='development':
            if any(v<1 for v in capacity.values()):raise ValueError('Development seed missing a class')
            q={s:min(20,v) for s,v in capacity.items()}
        else:q=quotas(capacity,200)
        allocations[scene]={'phase':phase,'capacity':capacity,'per_class_quota':q}
        for seed in seeds:
            for gold in [False, True]:
                selected += rng.sample(groups[seed,gold],q[seed])
    return selected,allocations


def reuse_development(source, out, helper):
    if read(source/'status.json')['state']!='blocked-engineering-or-coverage':
        raise ValueError('Unexpected original source status')
    old=read(source/'manifest/protocol.json');verify(old['source_sha256'])
    audits=read(source/'raw/development/source_audits.json')
    if {(r['scene'],r['seed']) for r in audits}!={(s,k) for s in SCENES for k in DEV} or not all(r['eligible'] for r in audits):
        raise ValueError('Development audits incomplete')
    folder=source/'raw/development';references=[]
    for scene in SCENES:
        for seed in DEV:
            p=folder/f'sources/{scene}/seed-{seed}'
            # compare() rewrites audit.json; do NOT use it on immutable p01.
            existing=read(p/'observer_audit.json')
            if not existing['eligible']:raise ValueError('Observer audit failed')
            for name in ['state_fingerprints.jsonl']:
                if sha(p/'observed'/name)!=sha(p/'shadow'/name):raise ValueError('Physical trace mismatch')
            ar,br=read(p/'observed/report.json'),read(p/'shadow/report.json')
            if ar['terminal_result']!=br['terminal_result'] or ar['ticks_run']!=br['ticks_run'] or ar['strategy_scorecard']['defender_score']!=br['strategy_scorecard']['defender_score']:
                raise ValueError('Episode result mismatch')
            actions=lambda mode:[helper.clean(json.loads(s)) for s in (p/mode/'action_batches.jsonl').read_text().splitlines()]
            if actions('observed')!=actions('shadow'):raise ValueError('Control mismatch')
            f=p/'observed/public_frames.json';meta=read(f)
            if meta['scenario']!=scene or meta['seed']!=seed:raise ValueError('Wrong development metadata')
            for mode in ['observed','shadow']:
                for name in ['report.json','action_batches.jsonl','state_fingerprints.jsonl']:
                    file=p/mode/name;references.append({'path':str(file),'sha256':sha(file)})
            references.append({'path':str(f),'sha256':sha(f)})
    write(out/'manifest/reused_development.json',{'source_batch':str(source),'source_protocol_sha':sha(source/'manifest/protocol.json'),
        'scope':'reuse audited development only; p01 unchanged; no confirmation responses existed','files':references})
    return folder,references


def fit_model(rows, field, channel):
    y=np.asarray([r['gold_real'] for r in rows],bool)
    x=np.asarray([r[field] for r in rows],float)
    seeds=sorted({r['seed'] for r in rows});random.Random(20261003).shuffle(seeds)
    folds={s:i%4 for i,s in enumerate(seeds)};options=[]
    def shape(v,square):return np.c_[v,v*v] if square else v
    def ba(y,p):
        if not y.any() or y.all():raise ValueError('CV fold class missing')
        c=(np.asarray(p)>.5)==y;return float((c[y].mean()+c[~y].mean())/2)
    for square in [False,True]:
        for lam in [.01,.1,1.,10.]:
            vals=[];z=shape(x,square)
            for k in range(4):
                tr=np.array([folds[r['seed']]!=k for r in rows]);te=~tr
                m=channel.fit(z[tr],y[tr],lam,False)
                vals.append(ba(y[te],channel.predict(m,z[te])))
            options.append({'square':square,'lambda':lam,'balanced_CV':float(np.mean(vals))})
    best=min(options,key=lambda v:(-v['balanced_CV'],v['square'],-v['lambda']))
    return {'model':channel.fit(shape(x,best['square']),y,best['lambda'],False),
            'selection':best,'development_CV':options,'field':field,'n_train':len(rows),'seeds':seeds}


def predict(model,rows,channel):
    x=np.asarray([r[model['field']] for r in rows],float)
    if model['selection']['square']:x=np.c_[x,x*x]
    return channel.predict(model['model'],x)


def collect_phase(repo, root, out, phase, seeds, helper, workers):
    folder=out/f'raw/{phase}';jobs=[(s,k) for s in SCENES for k in seeds]
    results=[]
    write(out/'status.json',{'state':'running','phase':phase,'done':0,'total':len(jobs),'workers':workers,'updated_at':time.time()})
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(helper.source_job,repo,root/'code',folder,s,k):(s,k) for s,k in jobs}
        for future in as_completed(futures):
            scene,seed=futures[future]
            try:record=future.result()
            except Exception as e:record={'scene':scene,'seed':seed,'eligible':False,'error':repr(e)}
            results.append(record)
            write(out/f'raw/{phase}/source_audits.json',results)
            write(out/'status.json',{'state':'running','phase':phase,'done':len(results),'total':len(jobs),
                                   'errors':sum(not x['eligible'] for x in results),'updated_at':time.time()})
    if not all(r['eligible'] for r in results):raise ValueError(f'{phase}: source/shadow engineering failures; no invalid data analysed')
    return folder


def run(a):
    out=a.output;root=a.root;repo=a.repo
    import fcntl
    with (out/'logs/run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        sys.path.insert(0,str(root/'code-d1-followup'))
        import hf_pilot as helper
        sys.path.insert(0,str(root/'code-complex'))
        spec=importlib.util.spec_from_file_location('hf_channel',root/'code-complex/channel_experiment.py')
        channel=importlib.util.module_from_spec(spec);spec.loader.exec_module(channel)
        from grid_alignment import bootstrap_metrics, roc
        frozen=freeze_sources(repo,root)
        manifest={'protocol':'E10-HF-restricted-continuous-p02','scenes':SCENES,
                  'development_seeds':DEV,'confirmation_seeds':CONF,'events_per_scene':400,
                  'reuse_development':str(a.reuse_development) if a.reuse_development else None,
                  'source':'native Rule+GOAI plan10 decision5 full episode; each source paired with uninstrumented shadow',
                  'numerical_primary':['estimated_position_m.x/10000','estimated_position_m.y/10000','estimated_position_m.z/10000','confidence','quality','age_ticks/10'],
                  'channel_mapping':'instantaneous public contact subset exposed by world_view.observation; not a grid, not complete executor input',
                  'secondary':'full current public snapshot172 features; never used to choose primary model or threshold',
                  'history':'8 samples every5ticks, span<=40ticks, >=4 distinct sensor observation ticks, stride1, overlapping windows',
                  'sampling':'development min(20, balanced capacity) per seed; confirmation capped equal waterfill200/class, >=1/class/seed; within-seed class balance, counts may differ across seeds; fixed random20261003, no prediction-based selection',
                  'labels':'offline fixed declared unarmed decoy vs armed facility attacker contract; same observed air domain >10m',
                  'LLM':{'system':helper.SYSTEM,'model':'Qwen3.8-27B','temperature':0,'thinking':False,'max_tokens':128,'response_format':helper.SCHEMA,'workers':4},
                  'LLM_scope':'anonymous controlled historical briefing identical field policy to pilot; not certified exact native online prompt',
                  'statistics':'20000 paired seed-cluster bootstrap; primary event-weighted plus seed-equal accuracy sensitivity; effective10 seeds per scene, not400 independent events',
                  'gates':{'numeric_balanced_accuracy_max':.6,'LLM_balanced_accuracy_min':.85,'parse_error_rate_max':.05,'empty_response_rate_max':.05,'cutoff':.5},
                  'model':'development-only four seedfold CV; linear/elementwise-square L2 logistic .01/.1/1/10',
                  'source_sha256':frozen,'engine_scene_unchanged':True,'native_contact_ID_unchanged':True,
                  'branch_rule':'D1 thresholds plus engineering pass evaluated per scene; no result-based pooling or native-online claim',
                  'workers':a.workers}
        write(out/'manifest/protocol.json',manifest)
        started=time.time()
        try:
            references=[]
            if a.reuse_development:
                devfolder,references=reuse_development(a.reuse_development,out,helper)
            else:devfolder=collect_phase(repo,root,out,'development',DEV,helper,a.workers)
            verify(frozen);dev=events(devfolder,helper);write(out/'raw/development/candidate_events.json',dev)
            train,allocation=select(dev,DEV,'development');write(out/'raw/development/training_events.json',train)
            write(out/'manifest/development_allocation.json',allocation)
            write(out/'status.json',{'state':'running','phase':'development-model-training','n':len(train),'updated_at':time.time()})
            models={}
            for scene in SCENES:
                rows=[r for r in train if r['scene']==scene]
                models[scene]={field:fit_model(rows,field,channel) for field in ['features','full_features']}
            write(out/'manifest/frozen_models.json',models)
            model_sha=sha(out/'manifest/frozen_models.json')
            verify(frozen)
            cf=collect_phase(repo,root,out,'confirmation',CONF,helper,a.workers)
            verify(frozen);candidates=events(cf,helper);write(out/'raw/confirmation/candidate_events.json',candidates)
            selected,allocation=select(candidates,CONF);write(out/'raw/confirmation/frozen_stimuli.json',selected)
            write(out/'manifest/confirmation_allocation.json',allocation)
            write(out/'manifest/confirmation_freeze.json',{'dataset_sha256':sha(out/'raw/confirmation/frozen_stimuli.json'),
                    'models_sha256':model_sha,'protocol_sha256':sha(out/'manifest/protocol.json'),'before_LLM_calls':True})
            write(out/'status.json',{'state':'running','phase':'LLM-classification','n':len(selected),'updated_at':time.time()})
            responses=helper.classify(selected,out/'raw/LLM')
            write(out/'raw/LLM/responses.json',responses);byid={r['id']:r for r in responses}
            if len(byid)!=800:raise ValueError('Missing or duplicate responses')
            results={}
            for scene in SCENES:
                rows=[r for r in selected if r['scene']==scene]
                numeric=predict(models[scene]['features'],rows,channel)
                complete=predict(models[scene]['full_features'],rows,channel)
                pred=[];parse=0;empty=0;http=0
                for r,p,q in zip(rows,numeric,complete):
                    resp=byid[r['id']]
                    if resp['gold_real']!=r['gold_real'] or resp['seed']!=r['seed']:raise ValueError('Classification metadata mismatch')
                    content=((resp.get('raw_response') or {}).get('choices') or [{}])[0].get('message',{}).get('content')
                    if resp.get('status')==200:
                        empty+=int(not content or not str(content).strip())
                        parse+=int(resp['p_real'] is None)
                    else:http+=1
                    pred.append({'id':r['id'],'seed':r['seed'],'gold_real':r['gold_real'],'numeric':p,'full_numeric':q,'llm':resp['p_real']})
                write(out/f'analysis/a01/{scene}/predictions.json',pred)
                seeds=sorted({r['seed'] for r in pred});clusters=np.array([seeds.index(r['seed']) for r in pred])
                weights=np.random.default_rng(20261003).multinomial(len(seeds),np.ones(len(seeds))/len(seeds),size=20000)
                nm,nb,ok=bootstrap_metrics(pred,'numeric',weights,clusters)
                lm,lb,_=bootstrap_metrics(pred,'llm',weights,clusters)
                fm,_,_=bootstrap_metrics(pred,'full_numeric',weights,clusters)
                counts=np.array([sum(r['seed']==s for r in pred) for s in seeds])
                equal_weights=weights/counts[None,:]
                en,ebn,eok=bootstrap_metrics(pred,'numeric',equal_weights,clusters)
                el,ebl,_=bootstrap_metrics(pred,'llm',equal_weights,clusters)
                for metric,key in [(en,'numeric'),(el,'llm')]:
                    values=[np.mean([r[key] is not None and (r[key]>.5)==r['gold_real'] for r in pred if r['seed']==s]) for s in seeds]
                    metric['accuracy']=metric['balanced_accuracy']=float(np.mean(values))
                    metric.pop('auc',None);metric.pop('auc_ci95',None)
                    metric['scope']='seed-equal accuracy sensitivity, not primary gate or macro AUC'
                engineering=parse/400<=.05 and empty/400<=.05 and http==0
                passed=nm['balanced_accuracy']<=.6 and lm['balanced_accuracy']>=.85 and engineering
                results[scene]={'numeric_restricted':nm,'LLM':lm,'numeric_full_current_secondary':fm,
                    'n_seed_clusters':len(seeds),'Cinfo_difference':lm['balanced_accuracy']-nm['balanced_accuracy'],
                    'Cinfo_ci95':np.quantile((lb-nb)[ok],[.025,.975]).tolist(),
                    'per_seed_class_quota':allocation[scene]['per_class_quota'],
                    'seed_equal_sensitivity':{'numeric':en,'LLM':el,'Cinfo_difference':el['balanced_accuracy']-en['balanced_accuracy'],
                        'Cinfo_ci95':np.quantile((ebl-ebn)[eok],[.025,.975]).tolist()},
                    'parse_errors':parse,'empty_responses':empty,'HTTP_errors':http,'engineering_pass':engineering,
                    'D1_point_pass':passed,'suggested_branch':'A-controlled-stimulus-only' if passed else 'B-D1-not-demonstrated',
                    'scope':'restricted continuous subset versus anonymous briefing; controlled classification only; not certified native online recognition'}
                write(out/f'analysis/a01/{scene}/summary.json',results[scene])
                write(out/f'analysis/a01/{scene}/ROC.json',{key:roc(pred,key) for key in ['numeric','llm','full_numeric']})
                import csv
                for key in ['numeric','llm','full_numeric']:
                    with (out/f'analysis/a01/{scene}/ROC_{key}.csv').open('w',encoding='utf-8',newline='') as f:
                        w=csv.DictWriter(f,fieldnames=['threshold','fpr','tpr']);w.writeheader();w.writerows(roc(pred,key))
            verify(frozen)
            if sha(out/'manifest/frozen_models.json')!=model_sha:raise ValueError('Model changed during confirmation')
            for ref in references:
                if sha(ref['path'])!=ref['sha256']:raise ValueError('Reused source changed')
            write(out/'analysis/a01/summary.json',results)
            report(out,results)
            write(out/'status.json',{'state':'completed','elapsed_seconds':time.time()-started,'source_unchanged':True,'results':results})
        except Exception as e:
            write(out/'status.json',{'state':'blocked-engineering-or-coverage','error':repr(e),'elapsed_seconds':time.time()-started,'no_invalid_result_certified':True})
            raise


def report(out,results):
    lines=['# E10高保真受限连续通道正式判别报告','',
        '原生IE-06/IE-11各10开发seed、10独立确认seed。每场景固定200真实+200诱饵事件；以seed聚类而非窗口独立性计算95%CI。',
        '主数值仅当前估计位置、置信度、质量、年龄六维；辅助保留完整当前172维。LLM匿名8次历史简报，不称原生在线自主识别率。', '',
        '|场景|受限数值平衡准确率|LLM平衡准确率|配对Cinfo差及95%CI|D1|','|---|---:|---:|---|---|']
    for scene,r in results.items():
        lines.append(f"|{scene}|{r['numeric_restricted']['balanced_accuracy']:.2%}|{r['LLM']['balanced_accuracy']:.2%}|{r['Cinfo_difference']:+.4f} {r['Cinfo_ci95']}|{r['D1_point_pass']}|")
    lines+=['','窗口步长1有重叠；每seed内两类等量，seed之间允许配额不同。主结果事件加权，另报告seed等权敏感性；有效确认样本每场景10seed，不冒充400独立对局。',
        '相同编码/观察范围不等于不可预测。受限分类器低准确率也不能证明数值不可分；辅助完整当前数值结果必须一并披露。',
        '角色是离线声明标签，不保证冻结路线必然表现出相应转向行为。场景、接触ID和路线未改。',
        '统计、AUC与CI、ROC、逐事件预测见analysis/a01；真实请求响应与刺激见raw；prompt及模型/数据/协议哈希见manifest。',
        '阈值60/85未调整，未按成功结果筛选。不同场景独立给结论，不混合统计。路径建议仅针对上述受控协议；论文叙事由主理人决定。']
    dest=out/'reports/r01';dest.mkdir(parents=True,exist_ok=True)
    (dest/'E10_HF正式判别报告_v1.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['launch','run'])
    p.add_argument('--repo',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',type=int,default=4);p.add_argument('--reuse-development',type=Path);a=p.parse_args()
    if a.command=='launch':
        if a.output.exists():raise ValueError('Existing batch retained')
        (a.output/'logs').mkdir(parents=True)
        env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',TI_CPU_MAX_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
        cmd=[sys.executable,'-B','-u',str(Path(__file__)),'run','--repo',str(a.repo),'--root',str(a.root),'--output',str(a.output),'--workers',str(a.workers)]
        if a.reuse_development:cmd += ['--reuse-development',str(a.reuse_development)]
        with (a.output/'logs/supervisor.log').open('a') as f:proc=subprocess.Popen(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        write(a.output/'logs/launch.json',{'pid':proc.pid,'command':cmd,'started_at':time.time()})
        print(json.dumps({'pid':proc.pid,'output':str(a.output)}));return
    run(a)


if __name__=='__main__':main()
