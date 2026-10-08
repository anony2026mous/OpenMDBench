import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

import remote_seed_campaign as campaign

class FakeSession:
    def __init__(self):
        self.world_view=self;self.tick=0
    def entities_stable(self):
        return [NS(id='unit.one',definition=NS(faction_id='team'),state=NS(lifecycle='active',
            position_m=(self.tick,2.,3.),velocity_mps=(1.,0.,0.),heading_deg=90.,health=1.,energy=None,ammunition={}))]
    def step(self):
        self.tick+=1;return self.tick

def fake_evaluation(count):
    session=FakeSession()
    for _ in range(count):
        receipt=session.step()
        observed=receipt
    return {'ticks_run':observed,'value':session.tick}

class CampaignTests(unittest.TestCase):
    def test_trajectory_records_every_tick_without_changing_result(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);r=campaign.TrajectoryRecorder(root/'trace.jsonl',root/'progress.json','case')
            try:result=r.run(fake_evaluation,4)
            finally:r.close()
            rows=[json.loads(x) for x in (root/'trace.jsonl').read_text().splitlines()]
            self.assertEqual(result,fake_evaluation(4));self.assertEqual([x['tick'] for x in rows],list(range(5)))
            self.assertEqual([x['entities'][0]['position_m'][0] for x in rows],list(range(5)))

    def test_missing_tick_fails(self):
        with tempfile.TemporaryDirectory() as name:
            r=campaign.TrajectoryRecorder(Path(name)/'trace',Path(name)/'progress','case');s=FakeSession()
            try:
                r.capture(s);s.tick=2
                with self.assertRaises(RuntimeError):r.capture(s)
            finally:r.close()

    def test_seed_barrier_blocks_later_seed(self):
        cases=[{'id':'a','phase':'gap','seed':17},{'id':'b','phase':'gap','seed':17},
               {'id':'c','phase':'gap','seed':19},{'id':'d','phase':'extra','seed':31}]
        self.assertEqual([x['id'] for x in campaign.seed_batch(cases,{'a'})],['b'])
        self.assertEqual([x['id'] for x in campaign.seed_batch(cases,{'a','b'})],['c'])
        self.assertEqual(campaign.seed_batch(cases,{'a','b','c','d'}),[])

    def test_zero_score_natural_loss_is_complete_not_cherry_picked(self):
        r={'terminal_result':{'outcome':'attacker_success'},'ticks_run':10,'aborted':None,'error':None,
           'strategy_scorecard':{'defender_score':0.,'scored_weight':1.}}
        self.assertTrue(campaign.eligible(r))
        for key,value in [('aborted','watchdog'),('error','exception'),('terminal_result',None)]:
            changed=copy.deepcopy(r);changed[key]=value;self.assertFalse(campaign.eligible(changed))
        r['strategy_scorecard']['scored_weight']=None;self.assertFalse(campaign.eligible(r))

    def test_source_pin_rejects_changed_files(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);p=root/'source.py';p.write_text('original');expected={'source.py':campaign.sha(p)}
            campaign.verify_files(root,expected);p.write_text('changed')
            with self.assertRaises(RuntimeError):campaign.verify_files(root,expected)

    def test_only_hybrid_gets_strong_goal_override(self):
        plan={'parameters':{'max_ticks':1800},'endpoints':['http://127.0.0.1:8001/v1','http://127.0.0.1:8002/v1'],
              'model':'Qwen3.8-27B','weight_paths':{'rl':'rl.npz','llm-rl':'hybrid.npz'}}
        for planner in ['llm-rl','llm','rl','pure-llm']:
            args=campaign.episode_arguments(plan,{'planner':planner,'scenario':'IE-01','seed':17,'slot':1},Path('output'))
            self.assertEqual('--goal-granularity' in args,planner=='llm-rl')
            self.assertEqual(args[args.index('--llm-max-tokens')+1],'1024')
            self.assertEqual(args[args.index('--max-ticks')+1],'1800')

if __name__=='__main__':unittest.main()
