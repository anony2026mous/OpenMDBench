"""Pilot, not confirmation: raw-channel leakage plus anonymized discrimination."""
import argparse
from concurrent.futures import ThreadPoolExecutor
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
import requests
from grid_diagnose import read,write,digest,load_channel,accuracy

SCENES=['IE-06-DECOY-MIXED','IE-11-DECOY-SCREEN']
SEEDS=list(range(17001,17006))
SCHEMA={'type':'json_schema','json_schema':{'name':'contact_role','strict':True,'schema':{
    'type':'object','properties':{'label':{'type':'string','enum':['real','feint']},
    'p_real':{'type':'number','minimum':0,'maximum':1}},'required':['label','p_real'],'additionalProperties':False}}}
SYSTEM=('Classify one anonymous aerial contact as feint or real using only supplied public observations. '
        'Real aerial threats persistently approach protected facilities; a feint can plausibly approach '
        'and then turn or withdraw. Do not infer hidden weapons, true identity, future wave timing or a role '
        'from an identifier. Motion estimates can be noisy. Use all observed estimates, not just the last. '
        'Use equal class priors; p_real is probability of real. Return only JSON with label real iff '
        'p_real>0.5, otherwise feint; include p_real in [0,1].')


def clean(v):
    if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if k not in ['command_id','action_id','operation_id','idempotency_key']}
    if isinstance(v,list):return [clean(x) for x in v]
    return v


def compare(folder):
    a,b=folder/'observed',folder/'shadow'
    ra,rb=read(a/'report.json'),read(b/'report.json')
    actions=lambda p:[clean(json.loads(s)) for s in (p/'action_batches.jsonl').read_text().splitlines()]
    result={'physical_per_tick_equal':digest(a/'state_fingerprints.jsonl')==digest(b/'state_fingerprints.jsonl'),
            'submitted_controls_equal':actions(a)==actions(b),
            'score_equal':ra['strategy_scorecard']['defender_score']==rb['strategy_scorecard']['defender_score'],
            'terminal_equal':ra['terminal_result']==rb['terminal_result'],'ticks_equal':ra['ticks_run']==rb['ticks_run']}
    result['eligible']=all(result.values());write(folder/'observer_audit.json',result)
    if not result['eligible']:raise ValueError('Observer affected native rollout')
    return result


def source_job(repo,base_code,out,scene,seed):
    folder=out/'sources'/scene/f'seed-{seed}'
    if folder.exists():raise ValueError('Existing pilot attempt retained')
    for mode in ['observed','shadow']:
        target=folder/mode;target.mkdir(parents=True)
        cmd=[sys.executable,'-B',str(Path(__file__).with_name('hf_collect.py')),'--repo',str(repo),'--base-code',str(base_code),
             '--scenario',scene,'--seed',str(seed),'--output',str(target)]
        if mode=='observed':cmd.append('--observe')
        with (target/'stdout.log').open('w') as log:
            code=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=7200).returncode
        write(target/'completion.json',{'exit_code':code})
        if code:raise RuntimeError(f'Pilot source failed: {target}')
    return {'scene':scene,'seed':seed,**compare(folder)}


def local_features(frame,candidate):
    # No target IDs, tags, hidden armament or true velocity. Full recorded own public
    # state and snapshot contact geometry remain available; no post-hoc weakening.
    p=candidate['estimated_position_m'];own=sorted(frame['own_public'],key=lambda x:x['entity_id']);v=[]
    for o in own:
        v.extend([*(float(x)/10000 for x in o['position_m']),*(float(x)/50 for x in o['velocity_mps']),
                  float(o['heading_deg'])/360,float(o['health']),float(o['energy'])])
    if len(own)>16:raise ValueError('Declared own-state padding insufficient')
    v+= [0.]*(16*9-len(v))
    v+= [1. if i<len(own) else 0. for i in range(16)]
    qs=[q['public']['estimated_position_m'] for q in frame['contacts']]
    distances=[float(np.linalg.norm(np.array(p)-np.array(o['position_m']))) for o in own]
    v+=[*(float(x)/10000 for x in p),float(candidate['confidence']),float(candidate['quality']),
         float(candidate['age_ticks'])/10,min(distances,default=0)/10000,len(qs)/20,
         min((x[0] for x in qs),default=0)/10000,max((x[0] for x in qs),default=0)/10000,
         min((x[1] for x in qs),default=0)/10000,max((x[1] for x in qs),default=0)/10000]
    return v


def events(out):
    rows=[];leak=[];available={};raw_scope=[]
    for p in sorted((out/'sources').glob('*/seed-*/observed/public_frames.json')):
        meta=read(p);hist={}
        for f in meta['frames']:
            dedup={}
            for q in f['contacts']:
                pub=q['public'];cid=pub['contact_id'];gold=q['offline_gold_real']
                leaky=any(x in cid.lower() for x in ['decoy','feint','diversion'])
                leak.append({'scene':meta['scenario'],'seed':meta['seed'],'tick':f['tick'],'gold_real':gold,'id_predict_real':not leaky,'role_word_in_id':leaky})
                # Primary pilot restricts both classes to the same observed air domain.
                if float(pub['estimated_position_m'][2])<=10:continue
                target=q['offline_target'];prev=dedup.get(target)
                if prev is None or (-pub['confidence'],pub['contact_id'])<(-prev['public']['confidence'],prev['public']['contact_id']):dedup[target]=q
            for target,q in dedup.items():hist.setdefault(target,[]).append((f,q))
        for target,track in hist.items():
            for i in range(0,len(track)-7,8):
                w=track[i:i+8];frame,q=w[-1];pub=q['public']
                if w[-1][0]['tick']-w[0][0]['tick']>40:continue
                if len({a['public']['observed_tick'] for _,a in w})<4:continue
                anon='c_'+hashlib.sha256(f"anonymous:{meta['seed']}:{target}".encode()).hexdigest()[:12]
                current={k:v for k,v in pub.items() if k not in ['contact_id','observer_entity_id']}
                own=[{k:v for k,v in o.items() if k!='entity_id'} for o in frame['own_public']]
                public={'candidate':anon,'current':current,'own_snapshot':own,
                    'protected_facilities_m':[[-1200,-200,0],[700,-400,0]],
                    'other_current_contacts':[{k:v for k,v in z['public'].items() if k not in ['contact_id','observer_entity_id']} for z in frame['contacts']],
                    'contact_history':[{'tick':f['tick'],'observed_tick':a['public']['observed_tick'],'estimated_position_m':a['public']['estimated_position_m'],'confidence':a['public']['confidence'],'age_ticks':a['public']['age_ticks']} for f,a in w]}
                prompt=json.dumps(public,separators=(',',':'))
                for bad in ['intruder.','decoy-','target.facility','offline_gold','spawn_tick','loadout','ammunition']:
                    if bad in prompt:raise ValueError('Hidden identity/role/weapon appeared in anonymous view')
                eid=hashlib.sha256(f"{meta['scenario']}:{meta['seed']}:{target}:{[f['tick'] for f,_ in w]}".encode()).hexdigest()[:24]
                rows.append({'id':eid,'scene':meta['scenario'],'seed':meta['seed'],'offline_target':target,
                    'gold_real':q['offline_gold_real'],'features':local_features(frame,pub),'prompt':prompt,
                    'ticks':[f['tick'] for f,_ in w],'current_snapshot_sha':hashlib.sha256(json.dumps(current,sort_keys=True).encode()).hexdigest()})
        raw_scope.append({'scene':meta['scenario'],'seed':meta['seed'],'recorded_frames':len(meta['frames'])})
    write(out/'native_identity_audit.json',{'n_contact_records':len(leak),'id_word_rule_accuracy':sum(r['id_predict_real']==r['gold_real'] for r in leak)/len(leak) if leak else None,
        'decoy_records':sum(not r['gold_real'] for r in leak),'decoy_records_with_role_word':sum(not r['gold_real'] and r['role_word_in_id'] for r in leak),
        'records':leak,'boundary':'native contact IDs, not supplied to anonymous offline LLM; not a legitimate anonymous discriminator'})
    write(out/'candidate_events.json',rows);return rows


def oof(rows,c,group_key):
    # Leave-seed-out and leave-underlying-target-out are both reported. IDs only
    # define offline validation groups and never enter features or prompts.
    y=np.array([r['gold_real'] for r in rows]);p=np.zeros(len(rows))
    groups=sorted({r[group_key] for r in rows})
    for group in groups:
        tr=[i for i,r in enumerate(rows) if r[group_key]!=group];te=[i for i,r in enumerate(rows) if r[group_key]==group]
        if len(set(y[tr]))<2:return {'state':'training-class-insufficient','grouping':group_key}
        m=c.fit([rows[i]['features'] for i in tr],y[tr],.1,True)
        p[te]=c.predict(m,[rows[i]['features'] for i in te])
    return {'state':'pilot-OOF','grouping':group_key,'groups':len(groups),**accuracy(y,p),'probabilities':p.tolist()}


def classify(rows,out):
    def call(item):
        i,r=item;base=f'http://127.0.0.1:{8101+i%2}/v1'
        payload={'model':'Qwen3.8-27B','temperature':0,'max_tokens':128,'chat_template_kwargs':{'enable_thinking':False},
                 'response_format':SCHEMA,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':r['prompt']}]}
        d={'id':r['id'],'seed':r['seed'],'scene':r['scene'],'gold_real':r['gold_real'],'endpoint':base,'request':payload,'p_real':None};t=time.time()
        try:
            response=requests.post(base+'/chat/completions',json=payload,timeout=120);d['status']=response.status_code;d['raw_text']=response.text;response.raise_for_status();raw=response.json();d['raw_response']=raw
            if raw['model']!='Qwen3.8-27B':raise ValueError('Model mismatch')
            v=json.loads(raw['choices'][0]['message']['content']);p=float(v['p_real'])
            if not np.isfinite(p) or not 0<=p<=1 or v['label'] not in ['real','feint'] or (p>.5)!=(v['label']=='real'):raise ValueError('Invalid classification')
            d['p_real']=p
        except Exception as e:d['error']=repr(e)
        d['seconds']=time.time()-t;write(out/'responses'/f"{r['id']}.json",d);return d
    with ThreadPoolExecutor(max_workers=4) as pool:return list(pool.map(call,enumerate(rows)))


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--base-code',type=Path,required=True);p.add_argument('--channel-code',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output
    if out.exists():raise ValueError('Previous pilot retained')
    out.mkdir(parents=True)
    frozen={'kind':'development-pilot-not-independent-confirmation','scenes':SCENES,'seeds':SEEDS,'native_engine_unchanged':True,
       'source_policy':'native Rule+GOAI plan10 decision5','source_controls':'observer/shadow paired complete native episodes',
       'history':'8 samples at 5-tick spacing, span<=40, >=4 distinct sensor observation ticks; air-only same observed domain; no changes based on results',
       'budget':'up to20feint+20real per scene, select by fixed random20261004; reduced pilot explicitly allowed, never formal400',
       'baseline':'complete public numerical current features, fixed L2 quadratic .1; leave-seed-out and leave-target-out',
       'LLM':{'model':'Qwen3.8-27B','thinking':False,'temperature':0,'max_tokens':128,'JSON_schema':True,'workers':4,'prompt':SYSTEM},
       'native_ID_audit':'record roles leaked via decoy/feint/diversion in actual contact IDs; anonymous diagnostic cannot certify native input',
       'formal_confirmation_release':'NOT automatic. Requires no truth-bearing native input, adequate both-class source coverage, pilot D1 signal, frozen independent protocol.'}
    write(out/'protocol.json',frozen)
    jobs=[(s,k) for s in SCENES for k in SEEDS];done=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures=[pool.submit(source_job,a.repo,a.base_code,out,s,k) for s,k in jobs]
        from concurrent.futures import as_completed
        for f in as_completed(futures):
            done.append(f.result());write(out/'progress.json',{'phase':'source-and-shadow','done':len(done),'total':len(jobs)})
    write(out/'source_audits.json',done);rows=events(out);selected=[];rng=random.Random(20261004)
    for scene in SCENES:
        groups=[[r for r in rows if r['scene']==scene and r['gold_real']==v] for v in [False,True]];n=min(20,*map(len,groups))
        for g in groups:rng.shuffle(g);selected+=g[:n]
    write(out/'pilot_dataset.json',selected);numeric={};c=load_channel(a.channel_code)
    for scene in SCENES:
        rs=[r for r in rows if r['scene']==scene]
        if len(rs)>=20 and len({r['gold_real'] for r in rs})==2:
            numeric[scene]={key:oof(rs,c,key) for key in ['seed','offline_target']}
        else:numeric[scene]={'state':'insufficient-air-event-coverage','counts':{str(v):sum(r['gold_real']==v for r in rs) for v in [False,True]}}
    write(out/'numeric_diagnostics.json',numeric)
    responses=classify(selected,out) if selected else [];write(out/'LLM_results.json',responses)
    llm={}
    for scene in SCENES:
        rs=[r for r in responses if r['scene']==scene]
        if rs:
            correct=[r['p_real'] is not None and (r['p_real']>.5)==r['gold_real'] for r in rs]
            llm[scene]={'n':len(rs),'accuracy':sum(correct)/len(rs),'errors':sum(r['p_real'] is None for r in rs),'n_seed_clusters':len({r['seed'] for r in rs})}
    leak=read(out/'native_identity_audit.json')
    result={'state':'pilot-complete','numeric':numeric,'LLM':llm,'native_ID_accuracy':leak['id_word_rule_accuracy'],
        'native_decoy_records_with_role_word':leak['decoy_records_with_role_word'],'formal_confirmation_started':False,
        'readiness':'not-certified-native-ID-boundary' if leak['decoy_records_with_role_word'] else 'requires-independent-protocol-review',
        'scope':'anonymous offline pilot diagnostic; cannot certify native high-fidelity D1 or actual online recognition'}
    write(out/'status.json',result);report(out,result)
    print(json.dumps({k:v for k,v in result.items() if k!='numeric'}),flush=True)


def report(out,result):
    lines=['# 高保真IE06/IE11 D1开发pilot','', '5 seeds/场景，原生Rule+GOAI完整局和未插桩影子局配对；不改引擎、场景、装备、计分。',
       f"实际接触ID词规则正确率：{result['native_ID_accuracy']}；诱饵ID暴露记录：{result['native_decoy_records_with_role_word']}。", '',
       '匿名离线LLM输入去掉真实ID、角色、武器、未来timeline；它是独立受控诊断视图，不是证明原生LLM提示已消除泄露。', '',
       '|场景|数值leave-seed-out平衡准确率|数值leave-target-out平衡准确率|匿名LLM准确率|LLM样本数|','|---|---:|---:|---:|---:|']
    for scene in SCENES:
        n=result['numeric'][scene];l=result['LLM'].get(scene,{})
        def fmt(key):return f"{n[key]['balanced_accuracy']:.2%}" if key in n and 'balanced_accuracy' in n[key] else '覆盖不足'
        lines.append(f"|{scene}|{fmt('seed')}|{fmt('offline_target')}|{l.get('accuracy','未调用')}|{l.get('n',0)}|")
    lines+=['','角色契约用无武器decoy与武装设施攻击者；主判别两类都限定公开空中高度>10m，避免只靠空/水域差异。'
            '数值特征完整保留当前位置、公开置信/质量/年龄、自身状态、其它当前接触几何；假想历史来自8次每5tick采集，不能冒称原生产LLM已收到这个窗口。',
            '以上都是开发pilot，不是400事件确认，不以多tick伪造独立seed置信度。留目标外验证防止同一固定目标几何跨seed重复带来的虚高。', '',
            f"正式确认未启动；就绪状态：{result['readiness']}。"
            '若原生角色词ID暴露，必须先明确匿名接触接口修复范围、所有栈对等映射及回执兼容；不得把匿名诊断通过当成原生D1通过。'
            '若数值仍高于60%或LLM低于85%，也不把pilot包装为通过；需合法受控场景设计或理论适用边界调整。']
    (out/'高保真_D1_pilot报告.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':main()
