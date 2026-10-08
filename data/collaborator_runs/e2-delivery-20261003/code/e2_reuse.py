"""Versioned E2 reanalysis using the already released P1/P2 remote inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output
    if out.exists():raise ValueError('Existing E2 batch retained')
    out.mkdir(parents=True);source=a.source;script=source/'e2_dose.py';inputs=source/'inputs'
    names=['P1__six_arm__s501-510__main__v1']+[f'P2__goal_dose__s512-521__{m}__v1' for m in ['hold','mask2','mask1','strong']]
    files=[f for name in names for f in (inputs/name).glob('*/episode.json')]
    if not files:raise ValueError('No released raw episodes')
    frozen={str(f):sha(f) for f in [*files,script,source/'common.py']}
    write(out/'manifest/protocol.json',{'kind':'reanalysis-existing-independent-P1-P2-batches',
           'raw_sources':frozen,'code_sha256':sha(Path(__file__)),
           'P1_seeds':list(range(501,511)),'P2_seeds':list(range(512,522)),
           'doses':['hold','mask2','mask1','strong'],'statistics':'20000 paired seed-bootstrap; P1 and P2 never pooled',
           'fifth_point':'not added: four released doses sufficient for requested proxy-shape plot',
           'scope':'ordinal unit availability, not bits, no analytic f fitting',
           'attempt_policy':'latest valid attempt by attempt index, not score; source hashes audited by existing analysis'})
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLBACKEND='Agg',MPLCONFIGDIR=str(out/'logs/mpl'))
    (out/'logs').mkdir(exist_ok=True)
    with (out/'logs/analysis.log').open('w') as log:
        code=subprocess.run([sys.executable,'-B',str(script),'--input',str(inputs),'--output',str(out/'analysis/a01')],env=env,stdout=log,stderr=subprocess.STDOUT).returncode
    if code:
        write(out/'status.json',{'state':'failed','exit_code':code});raise RuntimeError('E2 analysis failed; see retained log')
    if any(sha(f)!=h for f,h in frozen.items()):raise ValueError('Source changed during reanalysis')
    reports=out/'reports/r01';reports.mkdir(parents=True)
    for name in ['report.md','dose_gain.png','dose_gain.svg']:
        shutil.copy2(out/'analysis/a01'/name,reports/name)
    data=json.loads((out/'analysis/a01/analysis.json').read_text())
    write(out/'status.json',{'state':'completed','source_unchanged':True,'new_episodes':0,'P2_rows':len(data['P2_rows']),'completed_at':time.time()})
    print(json.dumps({'state':'completed','output':str(out),'new_episodes':0,'P2_rows':len(data['P2_rows'])}))


if __name__=='__main__':main()
