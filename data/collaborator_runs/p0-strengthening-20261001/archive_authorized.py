"""Archive all authorized trials after E1 finishes; no Git mutation."""
import argparse
import importlib.metadata
from pathlib import Path
import subprocess
import sys
import time
import tarfile
import shutil
from common import read,write,digest


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
    versions={'python':sys.version,'packages':{}}
    for name in ['numpy','scipy','torch','taichi','PyYAML','requests','pydantic','stable-baselines3']:
        try: versions['packages'][name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: versions['packages'][name]=None
    write(root/'runtime_versions.json',versions)
    # Earlier baseline manifest already locked the evaluation harness. Verify,
    # then export unchanged sources/weights, rather than claiming a late freeze.
    baseline=read(root/'results/E1-unmodified-baseline/manifest.json')
    repo=Path(read(root/'E1-authorized-20261001/variant_manifest.json')['repo'])
    original_eval={name:sha for name,sha in baseline['source_hashes'].items() if name.startswith('openmd/code/eval/')}
    intact=all(digest(repo/name)==sha for name,sha in original_eval.items())
    if not intact:raise ValueError('Evaluation harness changed since earlier baseline freeze')
    write(root/'evaluation_source_integrity.json',{'unchanged_since_earlier_baseline':intact,
          'earlier_manifest_sha256':digest(root/'results/E1-unmodified-baseline/manifest.json'),
          'source_hashes':original_eval})
    exported=root/'frozen-evaluation-source';exported.mkdir(exist_ok=True)
    for name in original_eval:
        shutil.copy2(repo/name,exported/Path(name).name)
    weights=root/'frozen-highfi-PPO';weights.mkdir(exist_ok=True)
    for name in ['theta_rl_legacy2.npz','theta_arm5_v12.npz']:
        shutil.copy2(repo/'openmd/code/eval/_w1_runs/rl'/name,weights/name)
    start=time.time();flag=root/'E1-authorized-20261001/finalization_status.json'
    while not flag.exists():
        if time.time()-start>21600:raise TimeoutError('E1 finalization unavailable')
        time.sleep(20)
    if read(flag)['state']!='reports-and-archive-complete':
        raise ValueError('Engineering review needed before final archive')
    subprocess.run([sys.executable,'-B',str(root/'summarize_authorized.py'),'--root',str(root)],check=True)
    destination=root.parent/'p0-authorized-stage-20261001.tar.gz'
    with tarfile.open(destination,'w:gz') as t:
        for folder in ['E1-authorized-20261001','E3-prospective-20261001','E3-prospective-v2-20261001',
                       'E3-prospective-pilot','results/E1-authorized-analysis','results/E2','results/E3-expanded-audit',
                       'inputs','assets','archive-source','archive-toolkit','frames','results/E3','results/E3-expanded',
                       'results/E1-unmodified-baseline','frozen-evaluation-source','frozen-highfi-PPO']:
            t.add(root/folder,arcname=folder,filter=lambda info:None
                  if any(v in Path(info.name).parts for v in ['checkpoints','__pycache__','mpl']) else info)
        for path in [*root.glob('*.py'),*root.glob('*.md'),root/'P0_authorized_status.json',root/'runtime_versions.json',
                     root/'model_service_metadata.json',root/'evaluation_source_integrity.json']:
            t.add(path,arcname=path.name)
    write(root/'P0_authorized_packaging_manifest.json',{'archive':str(destination),
          'archive_sha256':digest(destination),'size_bytes':destination.stat().st_size,
          'excluded':['large prior baseline checkpoint snapshots','MPL cache','Python bytecode'],
          'all_authorized_attempts_included':True,'both_E3_confirmation_rounds_included':True})
    print(destination,flush=True)


if __name__=='__main__':main()
