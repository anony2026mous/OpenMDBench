"""Static role-contract and public-channel audit of the actual remote release."""
import argparse
import hashlib
import json
from pathlib import Path
import yaml


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def inventory(s):
    return list(s['entities'])+[e['payload']['entity'] for e in s.get('events',[]) if e['event_type']=='spawn']


def labels_for(s):
    labels={};problems=[]
    for e in inventory(s):
        if e['faction_id']!='coalition.intruder':continue
        tags=set(e.get('tags',[]));is_decoy=bool(tags&{'decoy','feint','diversion'})
        armed=bool(e.get('loadout_ref') and sum((e.get('ammunition') or {}).values())>0)
        if is_decoy and not armed:labels[e['id']]=False
        elif not is_decoy and armed and any(t.startswith('target.facility.') for t in tags):labels[e['id']]=True
        else:problems.append({'id':e['id'],'reason':'role/weapon/target contract ambiguous'})
    return labels,problems


def audit(repo,out):
    if out.exists():raise ValueError('Audit attempt retained')
    engine=repo/'openmd/source-code/source_codes';formal=engine/'scenarios/formal';rows=[]
    for slug in ['ie_06_decoy_mixed','ie_11_decoy_screen','md_ad_004_deception']:
        s=yaml.safe_load((formal/slug/'scenario.yaml').read_text())['scenario'];p=yaml.safe_load((formal/slug/'agents.yaml').read_text())
        labels,issues=labels_for(s);intr=[e for e in inventory(s) if e['faction_id']=='coalition.intruder']
        rows.append({'package':slug,'scene_sha':digest(formal/slug/'scenario.yaml'),'profile_sha':digest(formal/slug/'agents.yaml'),
          'intruder_count':len(intr),'feint':sum(not v for v in labels.values()),'genuine':sum(labels.values()),
          'offline_roles':labels,'ambiguous':issues,'decoy_routes':[r for r in p['attack'].get('routes',[]) if r.get('match_tag') in ['decoy','diversion-south','diversion-center','diversion-north']],
          'attack_timeline_offline_only':p['attack'].get('timeline',[]),
          'geometry':[{k:e.get(k) for k in ['id','tags','loadout_ref','ammunition','initial_state']} for e in intr],
          'boundary':'labels only offline; roles stable for IE06/11 as declared unarmed decoys, not inferred from filenames; MD-AD-004 needs distinct breach-intent contract'})
    source_files=[engine/'openmdbench/world/factory_v2.py',repo/'openmd/code/eval/v2_agent.py',repo/'openmd/code/eval/llm_planner.py',repo/'openmd/code/eval/run_episode.py']
    evidence=[]
    for f in source_files:
        lines=f.read_text().splitlines()
        for i,line in enumerate(lines):
            if any(k in line for k in ['evidence_id = f"sensor.contact.', '"contact_id": evidence_id', 'observer_faction_id=self.faction_id', 'c[\'contact_id\']', 'format_for_prompt', 'briefing_declared']):
                evidence.append({'file':str(f),'line':i+1,'text':line.strip()})
    frozen={str(p.relative_to(engine)):digest(p) for p in engine.rglob('*') if p.is_file() and p.suffix in ['.py','.yaml','.json']}
    result={'scope':'static audit, native runtime exposure awaits pilot','repo':str(repo),'scenes':rows,'source_hashes':frozen,'evidence':evidence,
       'candidate_scenes':['IE-06-DECOY-MIXED','IE-11-DECOY-SCREEN'],
       'identity_risk':'contact evidence includes semantic underlying target ID and is projected as contact_id. Requires runtime check and explicit anonymized experiment interface before no-label claim.',
       'native_D1_certified':False,'no_engine_changes':True,'pilot':'5 independent seeds per scene; observer/shadow equivalence; anonymous offline diagnostic vs native raw-ID leakage check'}
    write(out/'audit.json',result)
    lines=['# 高保真D1诱饵场景静态审计','', '|场景包|突防实体|诱饵|真正目标|未明确角色|','|---|---:|---:|---:|---:|']
    for r in rows:lines.append(f"|{r['package']}|{r['intruder_count']}|{r['feint']}|{r['genuine']}|{len(r['ambiguous'])}|")
    lines+=['','IE06/IE11具有明确无武器decoy标签、脱离路线及真实设施攻击装订，可建立离线真值契约。'
            '这补充并纠正“高保真所有场景均无真假契约”的笼统说法；E1载体IE05/IE09仍是另一范围。',
            'MD-AD-004 diversion/main均无武器，不能用IE的武器契约直接标注；本pilot不纳入。', '',
            '接触内部证据ID包含target_entity_id，公开投影使用evidence_id；v2_agent读取该观测，LLM提示包含contact_id。'
            '静态链提示诱饵ID暴露风险，必须通过真实pilot确认，不仅凭源码字符串下结论。',
            '角色契约不等于当前数值观测不可分；位置、方位、出现时序均须实测。原生场景、引擎和E1完全不改。']
    (out/'高保真_D1_场景审计.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'scenes':[{k:r[k] for k in ['package','intruder_count','feint','genuine']} for r in rows],'identity_risk':result['identity_risk']}),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();audit(a.repo,a.output)
