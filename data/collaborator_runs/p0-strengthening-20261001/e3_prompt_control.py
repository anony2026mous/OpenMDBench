"""Secondary matched-event prompt control, not an extra tuned classifier."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
from common import read,write,digest
from e3_classify import SYSTEM


def main():
    p=argparse.ArgumentParser(); p.add_argument('--campaign',type=Path,required=True); a=p.parse_args()
    src=a.campaign/'classification'; dest=a.campaign/'original-prompt-control'
    dest.mkdir(parents=True,exist_ok=False)
    events=read(src/'dataset.json'); audit=read(src/'dataset_audit.json')
    write(dest/'dataset.json',events)
    if digest(dest/'dataset.json')!=digest(src/'dataset.json'):
        raise ValueError('Control input events changed')
    audit['classifier_protocol']=SYSTEM
    audit['secondary_control']='Same held-out v2 event set; original frozen prompt; added before reading v2 aggregate results, secondary not original primary endpoint'
    audit['control_frozen_at']=time.time()
    write(dest/'dataset_audit.json',audit)
    write(dest/'control_manifest.json',{'source_dataset_sha256':digest(src/'dataset.json'),
          'old_events_pooled':False,'same_events_as_v2':True,'system':SYSTEM,
          'frozen_at':time.time(),'n_calls':400,'threshold':.5,
          'scope':'Secondary matched prompt diagnostic; original and refined prompt see identical events, not cross-batch score subtraction'})
    return subprocess.call([sys.executable,'-B',str(Path(__file__).with_name('e3_classify.py')),
      '--frames',str(a.campaign/'frames'),'--output',str(dest),'--endpoints',
      'http://127.0.0.1:8101/v1','http://127.0.0.1:8102/v1','--workers','16','--per-class','200'])


if __name__=='__main__': raise SystemExit(main())
