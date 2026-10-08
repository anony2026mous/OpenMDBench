"""Harness-only public goal interventions; no engine or released eval edits."""
import argparse
import dataclasses
import json
import os
from pathlib import Path
import sys
from common import write


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--repo',type=Path,required=True);p.add_argument('--engine',type=Path,required=True)
    p.add_argument('--dose',choices=['strong','hold'],default='strong');p.add_argument('--greedy',action='store_true')
    a,remaining=p.parse_known_args()
    os.environ['OPENMDBENCH_ROOT']=str(a.engine.resolve());sys.path[:0]=[str(a.engine),str(a.repo/'openmd/code/eval')]
    import run_episode
    from goai_protocol import GoalCommand
    original=run_episode._build_defender;records=[]
    class Wrapped:
        wants_meta=True
        def __init__(self,base):self.base=base
        def get_stats(self):return self.base.get_stats()
        def plan(self,observation,tick,reports,unit_roles,meta=None):
            goals=self.base.plan(observation,tick,reports,unit_roles,meta=meta)
            native=[dataclasses.asdict(g) for g in goals]
            if a.greedy:
                contacts=[c for c in observation.contacts_by_faction.get(observation.observer_faction_id,())
                          if c.get('confidence',0)>=self.base.config.confidence_min and c.get('age_ticks',0)<=self.base.config.contact_max_age_ticks]
                own={str(v['entity_id']):v for v in observation.own_entities};used=set();new=[]
                # Keep original non-attack support goals. Change only assignment decision rule.
                for g in sorted(goals,key=lambda v:v.unit_id or ''):
                    if g.goal_type!='intercept':new.append(g);continue
                    candidates=[c for c in contacts if c['contact_id'] not in used and self.base._contact_allowed(c,self.base._target_domains(meta,g.unit_id))]
                    if not candidates:new.append(dataclasses.replace(g,goal_type='hold',parameters={'unit_id':g.unit_id,'duration':30}));continue
                    c=min(candidates,key=lambda v:(self.base._dist_xy(own[g.unit_id]['position_m'],v['estimated_position_m']),v['contact_id']))
                    used.add(c['contact_id']);params=dict(g.parameters);params['target_id']=c['contact_id'];new.append(dataclasses.replace(g,parameters=params))
                goals=new
            before=[dataclasses.asdict(g) for g in goals]
            if a.dose=='hold':
                goals=[dataclasses.replace(g,goal_type='hold',parameters={'unit_id':g.unit_id,'duration':30},constraints=[])
                       if g.goal_type!='hold' else g for g in goals]
            records.append({'tick':tick,'native':native,'before':before,'after':[dataclasses.asdict(g) for g in goals]})
            return goals
    def build(profile,args):
        agent=original(profile,args)
        if args.planner in ['rule','rule-rl']:
            if not hasattr(agent,'planner') or args.planner not in ['rule','rule-rl']:raise ValueError('Intervention requires deterministic rule planner')
            agent.planner=Wrapped(agent.planner)
        elif a.dose=='hold' or a.greedy:raise ValueError('Intervention requires deterministic rule planner')
        return agent
    run_episode._build_defender=build
    import e1_trial
    sys.argv=[sys.argv[0],'--repo',str(a.repo),'--engine',str(a.engine),*remaining]
    try:e1_trial.main()
    finally:run_episode._build_defender=original
    output=Path(remaining[remaining.index('--output')+1])
    write(output/'goal_interventions.json',{'dose':a.dose,'greedy':a.greedy,'records':records})


if __name__=='__main__':main()
