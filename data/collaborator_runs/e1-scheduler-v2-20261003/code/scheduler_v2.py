"""E1 scheduler-only hot handoff: CPU24 + two endpoint-specific LLM2 lanes."""
import argparse
import concurrent.futures as cf
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time


REAL_EXECUTOR = cf.ThreadPoolExecutor
CPU_ARMS = {'rule', 'rl', 'rule-rl'}


def lane(job):
    seed, arm = job[1], job[2]
    return 'cpu' if arm in CPU_ARMS else f'llm-{seed % 2}'


class RoutedExecutor:
    """Never let a waiting LLM job occupy a CPU slot or the other endpoint."""
    def __init__(self, max_workers=None, **kwargs):
        self.pools = {k: REAL_EXECUTOR(max_workers=n) for k,n in [('cpu',24),('llm-0',2),('llm-1',2)]}

    def submit(self, fn, job):
        return self.pools[lane(job)].submit(fn, job)

    def __enter__(self): return self

    def __exit__(self, *args):
        for p in self.pools.values(): p.shutdown(wait=True)


def process(pid):
    try:
        text=Path(f'/proc/{pid}/stat').read_text()
        tail=text[text.rfind(')')+2:].split()
        return {'state':tail[0], 'ppid':int(tail[1]), 'exit_status':int(tail[49])}
    except FileNotFoundError: return None


def command(pid):
    try: return Path(f'/proc/{pid}/cmdline').read_bytes().decode().strip('\0').split('\0')
    except FileNotFoundError:return []


def children(parent):
    answer=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        pid=int(p.name);state=process(pid)
        if state and state['ppid']==parent:
            cmd=command(pid)
            if any(x.endswith('/episode_adapter.py') for x in cmd):answer.append((pid,cmd))
    return answer


def main():
    p=argparse.ArgumentParser()
    for key in ['repo','code','output','old-recovery','new-recovery','recovery-code']:
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--legacy-pid',type=int,required=True)
    a=p.parse_args();out=a.output.resolve();new=a.new_recovery.resolve();old=a.old_recovery.resolve()
    sys.path.insert(0,str(a.code))
    campaign=importlib.import_module('count_campaign')
    spec=importlib.util.spec_from_file_location('old_recovery_helpers',a.recovery_code)
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    protocol=base.verify(a.code,out);protocol_sha=base.digest(out/'protocol.json')
    m=campaign.prepare(a.repo,out);rows={r['public_id']:r for r in m['variants']}
    import fcntl
    new.mkdir(parents=True,exist_ok=False)
    guard=(new/'supervisor.lock').open('a');fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
    legacy_cmd=command(a.legacy_pid)
    if str(a.recovery_code) not in legacy_cmd or '--recovery' not in legacy_cmd or legacy_cmd[legacy_cmd.index('--recovery')+1]!=str(old):
        raise ValueError('Legacy process identity mismatch; do not signal')
    if read_status(base,old).get('state')!='repairing' or (old/'scheduler_handoff_v2.json').exists():raise ValueError('Legacy phase changed or already handed off; no hot handoff')
    parked=False;work_started=False;progress_lock=threading.Lock();done=[]
    active={};cycle=0
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',TI_CPU_MAX_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg',MPLCONFIGDIR=str(out/'mpl'))
    def status(state,**kw):
        with progress_lock:
            base.write(new/'status.json',{'state':state,'cycle':cycle,'pid':os.getpid(),
                'updated_at':time.time(),'scheduler':{'CPU':24,'8101':2,'8102':2},
                'completed_repairs':len(done),'active_jobs':dict(active),**kw})
    def event(data):
        with progress_lock:
            with (new/'scheduler_events.jsonl').open('a') as f:f.write(json.dumps({'time':time.time(),**data})+'\n')
    try:
        # Park only the supervisor, never its running episode children.
        os.kill(a.legacy_pid,signal.SIGSTOP);parked=True
        for _ in range(100):
            if process(a.legacy_pid)['state'] in ['T','t']:break
            time.sleep(.05)
        else:raise ValueError('Supervisor did not park')
        adopted={}
        for pid,cmd in children(a.legacy_pid):
            folder=Path(cmd[cmd.index('--output')+1]).resolve()
            if not folder.is_relative_to(old/'attempts'):raise ValueError('Unexpected child output path')
            retry=base.read(folder/'retry_manifest.json');original=Path(retry['original_folder'])
            if not original.is_relative_to(out):raise ValueError('Unexpected canonical folder')
            completion=base.read(original/'completion.json');config=completion['config']
            base.classify_completion(original,rows[config['scenario']],protocol_sha,campaign.outcome)
            if folder in [v['folder'] for v in adopted.values()]:raise ValueError('Duplicate child')
            adopted[str(original)]={'pid':pid,'folder':folder,'retry':retry,'cmd':cmd}
        if len(adopted)>2:raise ValueError('Unexpected legacy concurrency')
        shutil.copy2(old/'status.json',new/'legacy_status_at_handoff.json')
        base.write(new/'manifest.json',{'created_at':time.time(),'original_protocol_sha':protocol_sha,
            'scheduler_code_sha':base.digest(__file__),'legacy_pid':a.legacy_pid,
            'adopted_episodes':[{**v,'folder':str(v['folder'])} for v in adopted.values()],
            'resources':{'CPU_workers':24,'LLM_episode_workers_per_endpoint':2,'total_LLM_episode_workers':4},
            'endpoint_assignment':'unchanged: frozen endpoints[seed % 2]',
            'scientific_inputs_changed':False,'timeouts_changed':False,
            'handoff':'SIGSTOP old supervisor; children run unchanged. Observe true child exit status from parked-parent zombies before retiring supervisor.'})
        base.write(old/'scheduler_handoff_v2.json',{'superseded_by':str(new),'legacy_pid':a.legacy_pid,'adopted_children':[v['pid'] for v in adopted.values()],'time':time.time()})
        work_started=True
        for cycle in range(4):
            base.verify(a.code,out);campaign.prepare(a.repo,out)
            failures=[];valid=0
            for f in sorted(out.glob('*/*/*/seed-*/completion.json')):
                c=base.read(f)['config'];row=rows[c['scenario']]
                kind,_=base.classify_completion(f.parent,row,protocol_sha,campaign.outcome)
                if kind=='valid':valid+=1
                else:failures.append((f.parent,c,row))
            # Existing children enter their endpoint pools FIRST, reserving their slots.
            failures.sort(key=lambda j:(str(j[0]) not in adopted,str(j[0])))
            snap=new/'snapshots'/f'cycle-{cycle:02d}';snap.mkdir(parents=True)
            for f in [out/'status.json',out/'progress.json',*out.glob('*_jobs.json')]:
                if f.exists():shutil.copy2(f,snap/f.name)
            base.write(snap/'inventory.json',{'valid_cases':valid,'failures':[str(j[0]) for j in failures]})
            status('repairing',valid_cases_before=valid,failures=len(failures))
            def repair(job):
                folder,c,row=job;key=str(folder);relative=folder.relative_to(out);saved=base.file_inventory(folder)
                attempt_base=new/'attempts'/relative;attempt_base.mkdir(parents=True,exist_ok=True)
                inherited=adopted.get(key)
                start_attempt=inherited['retry']['attempt'] if inherited else 1
                for attempt in range(start_attempt,3):
                    if inherited:
                        trial=inherited['folder'];started=inherited['retry']['started_at'];pid=inherited['pid']
                        with progress_lock:active[key]={'lane':lane((row,c['seed'],c['arm'])),'pid':pid,'adopted':True,'output':str(trial)}
                        event({'event':'adopt-running-episode','pid':pid,'case':key})
                        status('repairing',valid_cases_before=valid,failures=len(failures))
                        while True:
                            state=process(pid)
                            if state is None:raise RuntimeError('Adopted child vanished without observed exit status')
                            if state['state']=='Z':break
                            time.sleep(2)
                        wait_status=state['exit_status']
                        code=os.waitstatus_to_exitcode(wait_status)
                        base.write(new/'adopted-exits'/f'{pid}.json',{'pid':pid,'wait_status':wait_status,'exit_code':code,'observed_at':time.time()})
                        inherited=None
                    else:
                        trial=attempt_base/f'try-{attempt:02d}'
                        if trial.exists():continue
                        trial.mkdir();cmd=[sys.executable,'-B',str(a.code/'episode_adapter.py'),'--repo',str(a.repo),'--engine',m['engine'],
                            '--scenario',c['scenario'],'--seed',str(c['seed']),'--arm',c['arm'],'--dose',c['dose'],'--output',str(trial),
                            '--endpoint',protocol['LLM']['endpoints'][c['seed']%2]]
                        if c['greedy']:cmd.append('--greedy')
                        started=time.time();base.write(trial/'retry_manifest.json',{'original_folder':key,'command':cmd,'original_file_hashes':saved,'started_at':started,'attempt':attempt})
                        with (trial/'stdout.log').open('w') as log:
                            proc=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
                            with progress_lock:active[key]={'lane':lane((row,c['seed'],c['arm'])),'pid':proc.pid,'adopted':False,'output':str(trial)}
                            event({'event':'start','pid':proc.pid,'case':key,'endpoint':protocol['LLM']['endpoints'][c['seed']%2]})
                            status('repairing',valid_cases_before=valid,failures=len(failures))
                            try:code=proc.wait(timeout=7200)
                            except subprocess.TimeoutExpired:
                                proc.kill();proc.wait();base.write(trial/'retry_failure.json',{'reason':'process_timeout','seconds':7200});continue
                    completion={'config':c,'exit_code':code,'elapsed_seconds':time.time()-started,'report_sha':base.digest(trial/'report.json') if (trial/'report.json').exists() else None}
                    base.write(trial/'completion.json',completion)
                    if code:
                        if not (trial/'report.json').exists() or not base.is_step_timeout(base.read(trial/'report.json')):raise RuntimeError('Failure needs review: '+str(trial))
                        event({'event':'engineering-timeout','case':key,'attempt':attempt});continue
                    campaign.outcome(trial/'report.json',row)
                    archive=new/'original-failures'/relative;archive.parent.mkdir(parents=True,exist_ok=True)
                    if archive.exists() or base.file_inventory(folder)!=saved:raise ValueError('Canonical original changed; cannot promote')
                    folder.rename(archive)
                    try:trial.rename(folder)
                    except BaseException:archive.rename(folder);raise
                    base.write(attempt_base/'promotion.json',{'original_archived_at':str(archive),'accepted_attempt':attempt,'accepted_folder':key,'report_sha':completion['report_sha'],'promoted_at':time.time(),'inherited_retry':key in adopted})
                    with progress_lock:done.append(key);active.pop(key,None)
                    event({'event':'promote-first-valid','case':key,'elapsed_seconds':completion['elapsed_seconds']})
                    status('repairing',valid_cases_before=valid,failures=len(failures));return
                raise RuntimeError('Engineering retry limit reached: '+key)
            with RoutedExecutor() as pool:
                # repair uses a folder/config/row tuple; routing needs seed and arm.
                def routed(j):return repair(j[3])
                futures=[pool.submit(routed,(j[2],j[1]['seed'],j[1]['arm'],j)) for j in failures]
                for f in cf.as_completed(futures):f.result()
            if parked:
                state=process(a.legacy_pid)
                if not state or state['state'] not in ['T','t'] or command(a.legacy_pid)!=legacy_cmd:raise ValueError('Legacy supervisor identity/state changed')
                # Its children have all exited and their actual statuses were captured.
                if any(process(v['pid']) and process(v['pid'])['state']!='Z' for v in adopted.values()):raise ValueError('Legacy child still running')
                os.kill(a.legacy_pid,signal.SIGTERM);os.kill(a.legacy_pid,signal.SIGCONT)
                for _ in range(100):
                    state=process(a.legacy_pid)
                    if state is None or state['state']=='Z':break
                    time.sleep(.1)
                else:raise ValueError('Old supervisor did not exit; retain lock, review')
                parked=False;event({'event':'retire-old-supervisor','pid':a.legacy_pid})
                base.write(old/'status.json',{'state':'superseded-by-scheduler-v2','active_recovery':str(new),'handoff_completed_at':time.time()})
                adopted={}
            # The original campaign regains its own flock; separate lanes route all jobs.
            cf.ThreadPoolExecutor=RoutedExecutor
            sys.argv=[str(a.code/'count_campaign.py'),'--repo',str(a.repo),'--output',str(out),'--workers','24']
            status('frozen-campaign-running',valid_cases_before=valid)
            try:campaign.main()
            except RuntimeError:
                if base.read(out/'status.json').get('state')=='engineering-review-required':continue
                raise
            finally:cf.ThreadPoolExecutor=REAL_EXECUTOR
            base.analysis(out,new,campaign)
            report=new/'reports/E1续跑阶段报告_v1.md'
            text=report.read_text(encoding='utf-8').replace('仅将 LLM 对局调度从8路降至2路；CPU-only阶段仍使用原24路。','调度优化为CPU独立24路；LLM按原seed端点映射，每端点2路，共4路。旧在途对局完整接管，不重跑；旧恢复审计链保留。')
            report.write_text(text,encoding='utf-8')
            status('finished',campaign_status=base.read(out/'status.json'));return
        raise RuntimeError('Recovery cycle limit reached')
    except BaseException as exc:
        if parked and not work_started:os.kill(a.legacy_pid,signal.SIGCONT)
        status('review-required',error=repr(exc),legacy_supervisor_parked=parked)
        raise
    finally:cf.ThreadPoolExecutor=REAL_EXECUTOR


def read_status(base,path):return base.read(path/'status.json')


if __name__=='__main__':main()
