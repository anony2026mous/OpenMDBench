"""One real native episode and shadow before launching the multi-seed pilot."""
import argparse
from pathlib import Path
import json
from hf_pilot import source_job


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--base-code',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=source_job(a.repo,a.base_code,a.output,'IE-06-DECOY-MIXED',16999)
    print(json.dumps(result),flush=True)
