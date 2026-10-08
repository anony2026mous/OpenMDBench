"""Passive HF observer around the frozen runner; identical policy controls."""
import argparse
import json
import os
from pathlib import Path
import sys
from hf_audit import labels_for
import yaml


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--base-code',type=Path,required=True)
    p.add_argument('--scenario',required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--observe',action='store_true');a=p.parse_args()
    engine=a.repo/'openmd/source-code/source_codes';os.environ['OPENMDBENCH_ROOT']=str(engine)
    sys.path[:0]=[str(engine),str(a.repo/'openmd/code/eval'),str(a.base_code)]
    import run_episode
    import e1_trial
    if not Path(run_episode.__file__).resolve().is_relative_to(a.repo):raise ValueError('Wrong runner')
    registry=yaml.safe_load((engine/'scenarios/formal/registry.yaml').read_text());slug=next(r['package'] for r in registry['scenarios'] if r['public_id']==a.scenario)
    scene=yaml.safe_load((engine/'scenarios/formal'/slug/'scenario.yaml').read_text())['scenario'];labels,issues=labels_for(scene)
    if issues or set(labels.values())!={False,True}:raise ValueError('Offline roles incomplete')
    original=run_episode._build_defender;frames=[]
    class Passive:
        def __init__(self,agent):self.agent=agent;self.faction_id=agent.faction_id
        def get_stats(self):return self.agent.get_stats()
        def __call__(self,session):
            tick=session.world_view.tick
            if tick%5==0:
                obs=session.world_view.observation(observer_faction_id=self.faction_id)
                # Whitelist public payload; no credentials/claims/session auth stored.
                own=e1_trial.plain(obs.own_entities);contacts=e1_trial.plain(obs.contacts_by_faction.get(self.faction_id,()))
                known=tuple(labels)
                contact_rows=[]
                for contact in contacts:
                    target=run_episode._contact_suffix(contact.get('contact_id'),known)
                    if target in labels:
                        contact_rows.append({'public':contact,'offline_target':target,'offline_gold_real':labels[target]})
                frames.append({'tick':tick,'own_public':own,'contacts':contact_rows})
            return self.agent(session)
    if a.observe:
        def build(profile,args):return Passive(original(profile,args))
        run_episode._build_defender=build
    sys.argv=['e1_trial.py','--repo',str(a.repo),'--engine',str(engine),'--scenario',a.scenario,'--seed',str(a.seed),'--arm','rule','--output',str(a.output),'--trace-state']
    try:e1_trial.main()
    finally:run_episode._build_defender=original
    if a.observe:
        (a.output/'public_frames.json').write_text(json.dumps({'scenario':a.scenario,'seed':a.seed,'role_contract':labels,'frames':frames},ensure_ascii=False)+'\n',encoding='utf-8')


if __name__=='__main__':main()
