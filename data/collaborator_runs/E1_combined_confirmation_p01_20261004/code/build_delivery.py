"""Versioned final report/code delivery with every member hashed; sources immutable."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    a = parser.parse_args()
    target = a.root/'delivery-v1'
    target.mkdir(exist_ok=False)
    for name in ['analysis', 'code']:
        shutil.copytree(a.root/name, target/name)
    for name in ['protocol', 'analysis', 'reports']:
        shutil.copytree(a.bundle/name, target/'provenance'/name)
    shutil.copytree(a.bundle/'frozen/code', target/'code/frozen-experiment')
    shutil.copy2(a.bundle/'code/e1_split.py', target/'code/e1_split.py')
    shutil.copy2(a.root/'imports/REMOTE_IMPORT_VERIFICATION.json', target/'provenance/REMOTE_IMPORT_VERIFICATION.json')
    files = {p.relative_to(target).as_posix(): {'bytes':p.stat().st_size,'sha256':digest(p)}
             for p in sorted(target.rglob('*')) if p.is_file()}
    manifest = {'schema':'E1-final-analysis-delivery@1','cases':120,'files':files,
                'full_raw_data':'Separate complete device-a and device-b confirmation ZIPs; no raw case omitted',
                'source_handoff_archive_sha256':'76b53bd767f4d616c3633b8ba9a39ccac8f042b14b47f838e4fe4295e995b037',
                'raw_device_a_archive_sha256':'716904d85a1398b96841b6a19429ec351e0c14c9200838b1b02982e1e38e0dba',
                'raw_device_b_archive_sha256':'6aea3600257615b129f911c255d1e5147532f5886de3343eb9ce018d76bc4435'}
    (target/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    archive = a.root/'E1_combined_confirmation_final_analysis_v1.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for p in sorted(target.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(target).as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('CRC failed')
        for name,record in files.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=record['sha256']:raise ValueError('Archive member mismatch')
    result={'archive_sha256':digest(archive),'archive_bytes':archive.stat().st_size,
            'data_members':len(files),'all_member_sha256_and_crc_verified':True,'archive':str(archive)}
    (a.root/'FINAL_DELIVERY_VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
