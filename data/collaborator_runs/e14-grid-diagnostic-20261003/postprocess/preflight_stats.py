"""Read-only source reanalysis; add a separate uncertainty artifact only."""
import argparse
import json
from pathlib import Path
import numpy as np

def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);a=p.parse_args()
    target=a.batch/'analysis/a00/medium_transfer_seed_uncertainty_v1.json'
    if target.exists():raise ValueError('Existing uncertainty version retained')
    result={}
    for tier in ['simple','medium','complex']:
        source=a.batch/f'raw/preflight/medium_transfer_{tier}.json'
        rows=json.loads(source.read_text())['rows'];x=np.array([r['success'] for r in rows],float)
        samples=x[np.random.default_rng(20261003).integers(0,len(x),size=(20000,len(x)))].mean(1)
        result[tier]={'n_environment_seeds':len(x),'n_training_checkpoints':1,'successes':int(x.sum()),
            'SR':float(x.mean()),'environment_seed_bootstrap_ci95':np.quantile(samples,[.025,.975]).tolist(),
            'checkpoint_training_seed':42,'new_complex_training':False,
            'scope':'fixed available medium checkpoint transfer precheck, not reproduction of original complex-trained paper checkpoint',
            'source':str(source)}
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
