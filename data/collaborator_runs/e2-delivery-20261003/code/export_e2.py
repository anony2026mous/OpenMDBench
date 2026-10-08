"""Export the complete current E2 analysis and its five released source batches."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import zipfile


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
    if a.archive.exists():raise ValueError('Existing export retained')
    result=Path('/root/openmd/runs/E2_Grid_dose-shape_reanalysis_p01_20261002')
    source=Path('/root/openmd/runs/p0-strengthening-20261001')
    status=json.loads((result/'status.json').read_text())
    if status['state']!='completed':raise ValueError('E2 is not complete')
    mapping={}
    for f in result.rglob('*'):
        if f.is_file():mapping['results/'+f.relative_to(result).as_posix()]=f
    names=['P1__six_arm__s501-510__main__v1']+[f'P2__goal_dose__s512-521__{m}__v1' for m in ['hold','mask2','mask1','strong']]
    for name in names:
        folder=source/'inputs'/name
        if not folder.is_dir():raise ValueError(f'Missing source batch: {folder}')
        for f in folder.rglob('*'):
            if f.is_file():mapping['raw/'+name+'/'+f.relative_to(folder).as_posix()]=f
    for name in ['e2_dose.py','common.py']:
        mapping['code/'+name]=source/name
    mapping['code/e2_reuse.py']=Path('/root/openmd/runs/v5-core-20261002/code/e2_reuse.py')
    mapping['code/export_e2.py']=Path(__file__)
    if (source/'runtime_versions.json').exists():mapping['provenance/runtime_versions.json']=source/'runtime_versions.json'
    # Validate analysed episodes/trace/request hashes before copying source bytes.
    analysis=json.loads((result/'analysis/a01/analysis.json').read_text())
    used=analysis['provenance']['P1']+[x for rows in analysis['provenance']['P2'].values() for x in rows]
    if len(used)!=140:raise ValueError('Expected60 P1+80 P2 source episodes')
    for row in used:
        episode=Path(row['path'])
        if sha(episode)!=row['sha256']:raise ValueError('Analysed episode changed')
        data=json.loads(episode.read_text())
        for filename,key in [('events.jsonl','events_sha256'),('requests.jsonl','requests_sha256')]:
            if data.get(key) and sha(episode.with_name(filename))!=data[key]:raise ValueError('Source trace changed')
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    entries=[{'local_relative_path':name,'remote_source':str(f),'bytes':f.stat().st_size,'sha256':sha(f)} for name,f in sorted(mapping.items())]
    manifest={'schema':'E2-local-delivery@1','exported_beijing':now,'authoritative_result_batch':str(result),
              'P1_seeds':list(range(501,511)),'P2_seeds':list(range(512,522)),'analysed_episodes':140,
              'P1_and_P2_not_pooled':True,'entries':entries,
              'scope':'complete current E2 output and all files in five source batch folders; no E1/E10, no new episodes',
              'limitations':'source protocols refer to remote/legacy paths; paths preserved for provenance, raw bytes not rewritten; original trained checkpoint weights/engine not bundled, not needed to recompute statistics'}
    a.archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,f in sorted(mapping.items()):z.write(f,name)
        z.writestr('delivery_manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    for row in entries:
        if sha(row['remote_source'])!=row['sha256']:raise ValueError('Source changed during export')
    checksum=sha(a.archive)
    print(json.dumps({'archive':str(a.archive),'sha256':checksum,'bytes':a.archive.stat().st_size,
                      'source_files':len(entries),'source_bytes':sum(x['bytes'] for x in entries),'exported_beijing':now}))


if __name__=='__main__':main()
