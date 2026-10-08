"""Authorized COUNT-only scenario copies from the CURRENT remote release."""
import copy
import math
from pathlib import Path
import shutil
import yaml
from common import digest, read, write

FAMILIES={'IE-05-MULTI-AXIS':'ie_05_multi_axis', 'IE-09-STAGGERED-WAVES':'ie_09_staggered_waves'}


def inventory(scene):
    s=scene['scenario']
    return [*s['entities'],*(e['payload']['entity'] for e in s['events'] if e['event_type']=='spawn')]


def transform(scene,total):
    new=copy.deepcopy(scene);s=new['scenario']
    originals=[e for e in inventory(scene) if e['faction_id']=='coalition.intruder']
    if total<len(originals):raise ValueError('Authorization only increases count')
    # Alternate platform classes; preserve each source's native wave membership.
    groups={}
    for e in originals:groups.setdefault(e['platform_ref'],[]).append(e)
    ordered=[]
    for i in range(max(map(len,groups.values()))):
        for k in sorted(groups):
            if i<len(groups[k]):ordered.append(groups[k][i])
    spawned={e['payload']['entity']['id']:e for e in scene['scenario']['events'] if e['event_type']=='spawn'}
    occupied=[e['initial_state']['position_m'][:2] for e in inventory(scene)]
    for i in range(total-len(originals)):
        base=ordered[i%len(ordered)];clone=copy.deepcopy(base)
        clone['id']=base['id']+f'-p{i+1:03d}'
        x,y,z=base['initial_state']['position_m']
        target=(-1200.,-200.) if 'uav' in base.get('tags',[]) else (700.,-400.)
        radius=math.hypot(x-target[0],y-target[1]);angle=math.atan2(y-target[1],x-target[0])
        found=False
        # Deterministic arc offset; equal initial objective distance, minimum clearance.
        for k in range(1,61):
            shift=(1 if k%2 else -1)*math.ceil(k/2)*250./radius
            candidate=[target[0]+radius*math.cos(angle+shift),target[1]+radius*math.sin(angle+shift),z]
            if all(math.hypot(candidate[0]-q[0],candidate[1]-q[1])>=150 for q in occupied):
                clone['initial_state']['position_m']=candidate;occupied.append(candidate[:2]);found=True;break
        if not found:raise ValueError('Count menu violates declared placement clearance')
        if base['id'] in spawned:
            event=copy.deepcopy(spawned[base['id']]);event['id']+=f'-p{i+1:03d}';event['payload']['entity']=clone
            s['events'].append(event)
        else:s['entities'].append(clone)
    before={e['id']:e for e in inventory(scene)};after={e['id']:e for e in inventory(new)}
    if any(after[k]!=v for k,v in before.items()):raise AssertionError('Original entity changed')
    for k in s:
        if k not in ['entities','events'] and s[k]!=scene['scenario'][k]:raise AssertionError('Forbidden config change')
    if total==len(originals) and new!=scene:raise AssertionError('Native count not exactly equivalent')
    return new


def prepare(repo,out):
    native=repo/'openmd/source-code/source_codes';engine=out/'experiment-engine';mf=out/'variants.json'
    if mf.exists():
        m=read(mf)
        for name,h in m['original_hashes'].items():
            if digest(native/name)!=h:raise ValueError('Remote source changed')
            if name!='scenarios/formal/registry.yaml' and digest(engine/name)!=h:raise ValueError('Copied source changed')
        if digest(engine/'scenarios/formal/registry.yaml')!=m['registry_hash']:raise ValueError('Copied registry changed')
        for row in m['variants']:
            folder=engine/'scenarios/formal'/row['package']
            if digest(folder/'scenario.yaml')!=row['scene_hash'] or digest(folder/'agents.yaml')!=row['profile_hash']:raise ValueError('Frozen count variant changed')
        return m
    if engine.exists():raise ValueError('Interrupted copy retained; use distinct attempt')
    shutil.copytree(native,engine,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git'))
    hashes={str(p.relative_to(native)):digest(p) for p in native.rglob('*') if p.is_file() and p.suffix in ['.py','.yaml','.json']}
    formal=engine/'scenarios/formal';registry=yaml.safe_load((formal/'registry.yaml').read_text())
    rows=[]
    for family,slug in FAMILIES.items():
        scene=yaml.safe_load((formal/slug/'scenario.yaml').read_text());base_n=sum(e['faction_id']=='coalition.intruder' for e in inventory(scene))
        entry=next(e for e in registry['scenarios'] if e['public_id']==family)
        coarse=set(range(base_n,3*base_n+1,3 if base_n==9 else 2))
        for count in range(base_n,3*base_n+1):
            name=f'p0count_{slug}_n{count:03d}';folder=formal/name;folder.mkdir()
            modified=transform(scene,count)
            (folder/'scenario.yaml').write_text(yaml.safe_dump(modified,sort_keys=False,allow_unicode=True),encoding='utf8')
            shutil.copy2(formal/slug/'agents.yaml',folder/'agents.yaml')
            public=f'COUNT-{family}-N{count:03d}'
            registry['scenarios'].append({**entry,'public_id':public,'package':name})
            latest=max([0,*[e['trigger']['tick'] for e in modified['scenario']['events'] if e['event_type']=='spawn']])
            rows.append({'family':family,'count':count,'base_count':base_n,'package':name,'public_id':public,'coarse':count in coarse,'latest_spawn':latest,
                         'scene_hash':digest(folder/'scenario.yaml'),'profile_hash':digest(folder/'agents.yaml')})
    (formal/'registry.yaml').write_text(yaml.safe_dump(registry,sort_keys=False,allow_unicode=True),encoding='utf8')
    import os,sys
    os.environ['OPENMDBENCH_ROOT']=str(engine)
    sys.path[:0]=[str(engine),str(repo/'openmd/code/eval')]
    from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
    for row in rows:
        resolved,_=compile_formal_scenario_v2(row['public_id'])
        row['resolved_hash']=resolved.resolved_hash
        if row['count']==row['base_count']:
            original,_=compile_formal_scenario_v2(row['family'])
            if original.resolved_hash!=resolved.resolved_hash:raise ValueError('Native-count compile regression failed')
            row['native_compile_equivalent']=True
    if any(digest(engine/n)!=h for n,h in hashes.items() if n!='scenarios/formal/registry.yaml'):
        raise ValueError('Copied native source/config modified')
    m={'remote_repo':str(repo),'engine':str(engine),'original_hashes':hashes,'variants':rows,
       'registry_hash':digest(formal/'registry.yaml'),'count_limit':'native through 3x native; all integer counts predeclared',
       'positions':'new clones only: constant objective radius, deterministic 250m arc search, >=150m initial horizontal clearance',
       'unchanged':'all original entities, physics/catalog/weapons/scores/native wave times/horizon; profiles byte-identical'}
    write(mf,m);return m
