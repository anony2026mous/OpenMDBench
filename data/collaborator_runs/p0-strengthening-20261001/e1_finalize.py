"""Finish reporting after terminal campaign state; archive all attempts."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
import tarfile
from common import read,write,digest


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--campaign',type=Path,required=True)
    p.add_argument('--root',type=Path,required=True)
    a=p.parse_args()
    start=time.time()
    while not (a.campaign/'status.json').exists():
        if time.time()-start>21600:
            raise TimeoutError('Campaign has no terminal state after six hours')
        time.sleep(20)
    state=read(a.campaign/'status.json')
    if state['state'] not in ['authorized-knob-infeasible','confirmation-complete']:
        write(a.campaign/'finalization_status.json',{'state':'engineering-review-needed','campaign':state})
        return 1
    r=subprocess.run([sys.executable,'-B',str(a.root/'e1_analyze.py'),
                      '--campaign',str(a.campaign),'--output',str(a.root/'results/E1-authorized-analysis')])
    if r.returncode:
        return r.returncode
    destination=a.root.parent/'p0-e1-authorized-20261001-lite.tar.gz'
    with tarfile.open(destination,'w:gz') as t:
        for sub in [a.campaign, a.root/'results/E1-authorized-analysis',a.root/'results/E3-expanded-audit']:
            if sub.exists():
                t.add(sub,arcname=str(sub.relative_to(a.root)),filter=lambda info: None
                      if any(v in Path(info.name).parts for v in ['checkpoints','__pycache__','mpl']) else info)
        for name in ['e1_variants.py','e1_trial.py','e1_equivalence_gate.py','e1_full_campaign.py',
                     'e1_analyze.py','e1_finalize.py','e3_paired_audit.py','test_e1.py','common.py']:
            t.add(a.root/name,arcname=name)
    write(a.campaign/'finalization_status.json',{'state':'reports-and-archive-complete',
            'archive':str(destination),'archive_sha256':digest(destination),
            'campaign_state':state['state']})
    return 0


if __name__=='__main__':
    raise SystemExit(main())
