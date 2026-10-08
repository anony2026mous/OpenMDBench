"""Independent complex E3 supervisor; never restarts or modifies E1/medium."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from common import read,write,digest


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['launch','supervise']);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if a.command=='launch':
        if (out/'launch.json').exists():raise ValueError('Existing launch retained')
        with (out/'supervisor.log').open('a') as log:
            child=subprocess.Popen([sys.executable,'-B',str(Path(__file__)),'supervise','--output',str(out)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        print(json.dumps({'supervisor_pid':child.pid,'output':str(out)}));return
    import fcntl
    lock=(out/'supervisor.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    code=Path(__file__).parent;frozen={str(p.relative_to(code)):digest(p) for p in code.rglob('*') if p.is_file()}
    write(out/'code_freeze.json',frozen)
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg')
    cmd=[sys.executable,'-B',str(code/'channel_experiment.py'),'campaign','--source','/root/openmd/releases/gitlab-ccabad00154e/repo/openmd','--output',str(out),'--workers','12']
    started=time.time()
    with (out/'campaign.log').open('a') as log:
        child=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        write(out/'launch.json',{'supervisor_pid':os.getpid(),'pid':child.pid,'command':cmd,'started_at':started,'code_frozen':True})
        try:status=child.wait(timeout=172800)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=20)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
            status=child.returncode;write(out/'budget_stop.json',{'reason':'48h budget','time':time.time()})
    unchanged=all(digest(code/n)==h for n,h in frozen.items())
    write(out/'completion.json',{'exit_code':status,'elapsed_seconds':time.time()-started,'code_unchanged':unchanged})
    if not unchanged or status:raise RuntimeError('complex engineering failure retained')
    subprocess.run([sys.executable,'-B',str(code/'report_complex.py'),'--campaign',str(out)],env=env,check=True)


if __name__=='__main__':main()
