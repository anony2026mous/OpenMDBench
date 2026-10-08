"""Remote-only preflight and supervised parallel P0 launch. No repository writes."""
import argparse
import concurrent.futures as cf
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import requests
from common import read,write,digest
from pressure_variants import prepare

REPO=Path('/root/openmd/releases/gitlab-ccabad00154e/repo')
ENV=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',TI_CPU_MAX_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg')


def preflight(out):
    folder=out/'preflight';attempt=1
    while folder.exists():
        attempt+=1;folder=out/f'preflight-{attempt:02d}'
    folder.mkdir(parents=True,exist_ok=False)
    subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('test_next.py'))],env=ENV,check=True)
    def request(i):
        base=f'http://127.0.0.1:{8101+i%2}/v1';models=requests.get(base+'/models',timeout=20);models.raise_for_status()
        if 'Qwen3.8-27B' not in [r['id'] for r in models.json()['data']]:raise ValueError('Model mismatch')
        payload={'model':'Qwen3.8-27B','temperature':0,'max_tokens':128,'chat_template_kwargs':{'enable_thinking':False},
            'messages':[{'role':'user','content':'Connection audit, not experimental data. Return only JSON {"ok":true}.'}]}
        start=time.time();r=requests.post(base+'/chat/completions',json=payload,timeout=120);r.raise_for_status();data=r.json()
        text=data['choices'][0]['message'].get('content') or ''
        if data.get('model')!='Qwen3.8-27B' or json.loads(text.strip()).get('ok') is not True:raise ValueError('Preflight response mismatch')
        item={'endpoint':base,'request':payload,'response':data,'seconds':time.time()-start}
        write(folder/'llm-loadtest'/f'call-{i}.json',item);return {'endpoint':base,'seconds':item['seconds']}
    with cf.ThreadPoolExecutor(max_workers=8) as pool:health=list(pool.map(request,range(8)))
    print(json.dumps({'stage':'loadtest-ok','calls':len(health),'max_seconds':max(r['seconds'] for r in health)}),flush=True)
    variants=prepare(REPO,out/'E1-count');engine=Path(variants['engine']);print('32 count variants compiled',flush=True)
    cmd=[sys.executable,'-B',str(Path(__file__).with_name('channel_experiment.py')),'collect','--source',str(REPO/'openmd'),'--output',str(folder/'grid-smoke'),'--seed','5001']
    with (folder/'grid-smoke.log').open('w') as log:subprocess.run(cmd,env=ENV,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    print('Grid real rollout and exact uninstrumented shadow passed',flush=True)
    native=REPO/'openmd/source-code/source_codes';jobs=[]
    for row in variants['variants']:
        if row['count']==row['base_count']:
            for cloned in [False,True]:jobs.append((row,cloned))
    def regression(job):
        row,cloned=job;target=folder/'native-regression'/row['family']/('cloned' if cloned else 'original')
        target.mkdir(parents=True)
        script='episode_adapter.py' if cloned else 'e1_trial.py'
        cmd=[sys.executable,'-B',str(Path(__file__).with_name(script)),'--repo',str(REPO),'--engine',str(engine if cloned else native),
             '--scenario',row['public_id'] if cloned else row['family'],'--seed','4001','--arm','rule','--output',str(target),'--trace-state']
        with (target/'stdout.log').open('w') as f:subprocess.run(cmd,env=ENV,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=7200)
        print(json.dumps({'regression_done':row['family'],'cloned':cloned}),flush=True)
    with cf.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(regression,jobs))
    audits=[]
    for row in variants['variants']:
        if row['count']!=row['base_count']:continue
        root=folder/'native-regression'/row['family'];a=root/'original';b=root/'cloned'
        ar,br=read(a/'report.json'),read(b/'report.json')
        same=(digest(a/'state_fingerprints.jsonl')==digest(b/'state_fingerprints.jsonl') and ar['strategy_scorecard']['defender_score']==br['strategy_scorecard']['defender_score']
              and ar['strategy_scorecard']['terminal']==br['strategy_scorecard']['terminal'])
        audits.append({'family':row['family'],'exact_per_tick_physical_equivalence':same})
        if not same:write(folder/'regression_failures.json',audits);raise ValueError('Native physical equivalence failed')
    manifest={'passed':True,'time':time.time(),'repo':str(REPO),'unit_tests':8,'LLM_loadtest':health,'native_regressions':audits,
       'grid_shadow_passed':read(folder/'grid-smoke/audit.json')['eligible'],
       'code_hashes':{str(p.relative_to(Path(__file__).parent)):digest(p) for p in Path(__file__).parent.rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']}}
    write(folder/'preflight.json',manifest)
    write(out/'preflight_pointer.json',{'folder':str(folder),'manifest_sha':digest(folder/'preflight.json')})


def threadcheck(out):
    pointer=read(out/'preflight_pointer.json');oldpath=Path(pointer['folder'])/'preflight.json'
    if digest(oldpath)!=pointer['manifest_sha']:raise ValueError('Preflight changed')
    previous=read(oldpath)
    if previous.get('thread_config_verified'):raise ValueError('Thread qualification already retained')
    original_folder=Path(pointer['folder']);folder=out/'thread-preflight';attempt=1
    while folder.exists():attempt+=1;folder=out/f'thread-preflight-{attempt:02d}'
    folder.mkdir();m=prepare(REPO,out/'E1-count');jobs=[r for r in m['variants'] if r['count']==r['base_count']]
    def run(row):
        target=folder/row['family'];target.mkdir()
        cmd=[sys.executable,'-B',str(Path(__file__).with_name('episode_adapter.py')),'--repo',str(REPO),'--engine',m['engine'],
            '--scenario',row['public_id'],'--seed','4001','--arm','rule','--output',str(target),'--trace-state']
        with (target/'stdout.log').open('w') as f:subprocess.run(cmd,env=ENV,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=7200)
        old=original_folder/'native-regression'/row['family']/'original'
        a,b=read(old/'report.json'),read(target/'report.json')
        same=digest(old/'state_fingerprints.jsonl')==digest(target/'state_fingerprints.jsonl') and a['strategy_scorecard']['terminal']==b['strategy_scorecard']['terminal'] and a['strategy_scorecard']['defender_score']==b['strategy_scorecard']['defender_score']
        result={'family':row['family'],'exact_physical_and_score_equivalence':same,'reference_seconds':a['elapsed_seconds'],'limited_seconds':b['elapsed_seconds'],
                'speedup':a['elapsed_seconds']/b['elapsed_seconds']}
        write(target/'qualification.json',result)
        if not same:raise ValueError('Thread change failed physical equivalence')
        return result
    with cf.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,jobs))
    sealed={**previous,'thread_config_verified':True,'TI_CPU_MAX_NUM_THREADS':1,'thread_qualification':results,
       'previous_manifest_sha':digest(oldpath),'sealed_at':time.time(),
       'code_hashes':{str(p.relative_to(Path(__file__).parent)):digest(p) for p in Path(__file__).parent.rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']}}
    write(folder/'preflight.json',sealed);write(out/'preflight_pointer.json',{'folder':str(folder),'manifest_sha':digest(folder/'preflight.json')})
    print(json.dumps({'thread_qualification':results}),flush=True)


def supervise(out):
    pointer=read(out/'preflight_pointer.json');path=Path(pointer['folder'])/'preflight.json'
    if digest(path)!=pointer['manifest_sha']:raise ValueError('Preflight manifest changed')
    manifest=read(path)
    if not manifest['passed']:raise ValueError('Preflight not passed')
    if not manifest.get('thread_config_verified') or manifest['TI_CPU_MAX_NUM_THREADS']!=1:raise ValueError('Runtime thread configuration not qualified')
    for name,h in manifest['code_hashes'].items():
        if digest(Path(__file__).parent/name)!=h:raise ValueError('Code changed after preflight')
    import fcntl
    lock=(out/'supervisor.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    jobs=[('E1',[sys.executable,'-B',str(Path(__file__).with_name('count_campaign.py')),'--repo',str(REPO),'--output',str(out/'E1-count'),'--workers','24']),
          ('E3',[sys.executable,'-B',str(Path(__file__).with_name('channel_experiment.py')),'campaign','--source',str(REPO/'openmd'),'--output',str(out/'E3-channel'),'--workers','12'])]
    logs=[];children=[];started=time.time();budget=read(Path(__file__).with_name('gate_protocol.json'))['task_package']['campaign_time_budget_seconds']
    for name,cmd in jobs:
        log=(out/f'{name}-campaign.log').open('a');logs.append(log)
        p=subprocess.Popen(cmd,env=ENV,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        children.append((name,p,cmd))
    write(out/'launch.json',{'supervisor_pid':os.getpid(),'started_at':started,'deadline':started+budget,
         'children':[{'name':n,'pid':p.pid,'command':cmd} for n,p,cmd in children]})
    try:
        while any(p.poll() is None for _,p,_ in children):
            if time.time()-started>budget:
                for _,p,_ in children:
                    if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
                write(out/'budget_stop.json',{'at':time.time(),'reason':'predeclared 48h budget'})
                break
            time.sleep(5)
    finally:
        for _,p,_ in children:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=20)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
        for f in logs:f.close()
        write(out/'completion.json',{'finished_at':time.time(),'children':[{'name':n,'pid':p.pid,'exit_code':p.poll()} for n,p,_ in children]})
        subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('analyze_next.py')),'--campaign',str(out)],env=ENV,check=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['preflight','threadcheck','launch','supervise','status']);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
    if a.command=='preflight':preflight(out)
    elif a.command=='threadcheck':threadcheck(out)
    elif a.command=='launch':
        if (out/'launch.json').exists():raise ValueError('Existing launch retained; inspect supervisor/children first')
        log=(out/'supervisor.log').open('a')
        proc=subprocess.Popen([sys.executable,'-B',str(Path(__file__)),'supervise','--output',str(out)],env=ENV,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        log.close();print(json.dumps({'supervisor_pid':proc.pid,'output':str(out)}))
    elif a.command=='supervise':supervise(out)
    else:
        for name in ['launch.json','completion.json','E1-count/status.json','E1-count/progress.json','E3-channel/status.json','E3-channel/progress.json']:
            path=out/name
            if path.exists():print(json.dumps({'file':name,'data':read(path)},ensure_ascii=False))


if __name__=='__main__':main()
