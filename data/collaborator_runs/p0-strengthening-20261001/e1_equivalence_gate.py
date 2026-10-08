"""Await native-time full trajectories, verify every recorded tick, then launch."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
from common import read, write, digest


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--regression',type=Path,required=True)
    p.add_argument('--workers',type=int,default=32)
    a=p.parse_args()
    families=['IE-05-MULTI-AXIS','IE-09-STAGGERED-WAVES']
    start=time.time()
    paths=[a.regression/f/k/'report.json' for f in families for k in ['native','clone']]
    while not all(p.exists() for p in paths):
        if time.time()-start>7200:
            raise TimeoutError('Equivalence regression did not complete')
        time.sleep(20)
    proofs=[]
    for family in families:
        native,clone=[a.regression/family/k for k in ['native','clone']]
        n,c=[read(d/'report.json') for d in [native,clone]]
        if n.get('aborted') or c.get('aborted'):
            raise ValueError('Equivalence regression engineering failure retained')
        if (native/'state_fingerprints.jsonl').read_bytes()!=(clone/'state_fingerprints.jsonl').read_bytes():
            raise ValueError('Tick-state fingerprints differ')
        if n['strategy_scorecard']!=c['strategy_scorecard']:
            raise ValueError('Scorecards differ')
        for key in ['ticks_run','total_fires','total_fires_defender','total_fires_intruder',
                    'engagements_by_target','fire_rejections','terminal_result']:
            if n.get(key)!=c.get(key):
                raise ValueError(f'Episode field differs: {key}')
        proofs.append({'family':family,'seed':1101,'all_recorded_tick_states_equal':True,
                       'n_ticks':sum(1 for _ in (native/'state_fingerprints.jsonl').open()),
                       'scorecard_equal':True,'native_report_sha256':digest(native/'report.json'),
                       'clone_report_sha256':digest(clone/'report.json'),
                       'fingerprints_sha256':digest(native/'state_fingerprints.jsonl')})
    write(a.output/'equivalence_gate.json',{'passed':True,'proofs':proofs,
          'scope':'Recorded entity-state full trajectories and scorecards; source and compiled equivalence additionally frozen'})
    return subprocess.call([sys.executable,'-B',str(Path(__file__).with_name('e1_full_campaign.py')),
             '--repo',str(a.repo),'--output',str(a.output),'--workers',str(a.workers)])


if __name__=='__main__':
    raise SystemExit(main())
