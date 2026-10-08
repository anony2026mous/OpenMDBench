"""Package precisely the frozen inputs consumed by an analysis; no source edits."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
inputs=json.loads(a.manifest.read_text(encoding='utf-8'))['files']
if a.output.exists():raise FileExistsError(a.output)
mapping={};written=set()
with zipfile.ZipFile(a.output,'x',zipfile.ZIP_DEFLATED) as z:
    for source,digest in inputs.items():
        path=Path(source)
        if any(x in path.parts for x in ('.ssh','.aws','.git')):raise ValueError('Out-of-scope input')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Source drift '+source)
        member='files/'+digest+path.suffix
        if member not in written:z.write(path,member);written.add(member)
        mapping[source]={'member':member,'sha256':digest,'bytes':path.stat().st_size}
    z.writestr('source_index.json',json.dumps({'original_manifest':str(a.manifest),'indexed_sources':len(inputs),'unique_files':len(written),'sources':mapping},ensure_ascii=False,indent=2))
    z.writestr('original_input_manifest.json',a.manifest.read_bytes())
print(json.dumps({'zip':str(a.output),'sha256':hashlib.sha256(a.output.read_bytes()).hexdigest(),'bytes':a.output.stat().st_size,'sources':len(inputs),'unique_files':len(written)},ensure_ascii=False))
