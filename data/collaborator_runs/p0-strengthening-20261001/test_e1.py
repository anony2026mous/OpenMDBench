import copy
import dataclasses
from pathlib import Path
import unittest
import yaml
from e1_variants import transform, CONFIG
from e1_trial import plain
from e1_full_campaign import outcomes


class Vec(tuple):
    def __new__(cls, seq):
        return tuple.__new__(cls, (float(seq[0]),float(seq[1]),float(seq[2])))


@dataclasses.dataclass
class State:
    position: Vec


class E1Tests(unittest.TestCase):
    def test_read_only_state_conversion(self):
        state=State(Vec([1,2,3]))
        self.assertEqual(plain(state), {'position':[1.,2.,3.]})
        self.assertIsInstance(state.position,Vec)

    def test_native_and_authorized_transforms(self):
        root=Path(__file__).parent/'inputs'/'scenario-test-source'
        if not root.exists():
            self.skipTest('Run with frozen scene-test fixtures installed')
        for family,(slug,times) in CONFIG.items():
            scene=yaml.safe_load((root/slug/'scenario.yaml').read_text(encoding='utf-8'))
            profile=yaml.safe_load((root/slug/'agents.yaml').read_text(encoding='utf-8'))
            old=copy.deepcopy(scene)
            for t in times:
                new,_,affected=transform(scene,profile,family,t)
                self.assertTrue(affected)
                if (family.startswith('IE-05') and t==0) or (family.startswith('IE-09') and t==250):
                    self.assertEqual(new,scene)
            self.assertEqual(scene,old)

    def test_sr_not_continuous_score(self):
        r={'strategy_scorecard':{'terminal':{'state':'defender_success'},'defender_score':.65}}
        self.assertEqual(outcomes(r),(1,.65))
        r['aborted']='error'
        with self.assertRaises(ValueError):
            outcomes(r)

    def test_unclassified_end_not_draw(self):
        with self.assertRaises(ValueError):
            outcomes({'strategy_scorecard':{'terminal':{'state':'active'},'defender_score':.8}})

    def test_attacker_success_is_defender_loss(self):
        self.assertEqual(outcomes({'strategy_scorecard':{'terminal':{'state':'attacker_success',
           'outcome':'intruder_success'},'defender_score':.4}}),(0,.4))


if __name__=='__main__':
    unittest.main()
