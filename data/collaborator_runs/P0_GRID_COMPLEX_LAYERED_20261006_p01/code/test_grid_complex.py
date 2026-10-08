"""Algebra, scoring identity and passive-instrumentation regression checks."""
import argparse
import json
from pathlib import Path
import sys
import unittest
import grid_complex_campaign as g


ROOT=None


class StatisticsTests(unittest.TestCase):
    def test_negative_effect(self):
        d=g.boot([-.2,-.1,-.3,-.4,-.25]);self.assertLess(d['ci95'][1],0)
    def test_positive_effect(self):
        self.assertGreater(g.boot([.1,.2,.1,.3,.4])['ci95'][0],0)
    def test_zero_effect(self):
        self.assertEqual(g.boot([0]*5)['ci95'],[0,0])
    def test_missing_not_zero(self):
        self.assertIsNone(g.boot([]))
    def test_reproducible_bootstrap(self):
        self.assertEqual(g.boot([1,2,3,4,5]),g.boot([1,2,3,4,5]))
    def test_reject_nan(self):
        with self.assertRaises(ValueError):g.boot([float('nan')])
    def test_small_sample_variance(self):
        self.assertIsNone(g.boot([.2])['SD'])
    def test_protocol_identity(self):
        p=g.verify(ROOT)
        self.assertEqual(p['checkpoint_sha256'],g.EXPECTED_CHECKPOINT)
        self.assertEqual(len(p['seeds'])*len(p['arms']),20)
        self.assertNotIn(p['smoke_seed'],p['seeds'])


class NativeEquivalence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=g.verify(ROOT);cls.comp=g.imports(cls.p)
    def vanilla(self,arm):
        Grid,_,_,_,_,_=self.comp
        seed=self.p['smoke_seed'];env=Grid(difficulty='complex',seed=seed,task_mode='continuous')
        agent,_=g.make_agent(self.p,arm,seed,ROOT/'smoke','unused',self.comp)
        rows=[]
        while not env.done and env.step_count<150:
            obs=env._get_observation('blue');actions=agent.act(obs,env=env)
            env.step(actions,None);env.compute_reward('blue')
            rows.append({'actions':actions,'after':g.state(env)})
        case=ROOT/'smoke'/g.case_id(arm,seed)
        selected=g.read(case/'selected.json');out=Path(selected['attempt_dir'])
        logged=[json.loads(l) for l in (out/'events.jsonl').read_text().splitlines()]
        self.assertEqual(g.canonical(rows),g.canonical([{'actions':r['actions'],'after':r['after']} for r in logged]))
        result=g.read(out/'episode.json')
        self.assertEqual(g.canonical(env.get_episode_metrics()),g.canonical(result['native_metrics']))
        self.assertEqual(result['V'],env.get_episode_metrics()['blue_score'])
        m=result['native_metrics']
        recomputed=.6*float(m['mission_success'])+.2*(1-m['red_combatants_alive']/max(m['red_combatants_total'],1))+.2*m['blue_alive']/max(m['blue_total'],1)
        self.assertAlmostEqual(result['V'],recomputed)
    def test_rule_passive_equivalence(self):self.vanilla('rule')
    def test_mappo_passive_equivalence(self):self.vanilla('pure-mappo')


def main():
    global ROOT
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--native',action='store_true')
    a=p.parse_args();ROOT=a.root
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(StatisticsTests)
    if a.native:suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(NativeEquivalence))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    g.write(ROOT/('smoke/passive_equivalence.json' if a.native else 'protocol/unit_tests.json'),
            {'pass':result.wasSuccessful(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'at':g.now(),'test_code_sha256':g.sha(Path(__file__))})
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
