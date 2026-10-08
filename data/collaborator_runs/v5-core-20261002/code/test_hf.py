import unittest
from hf_campaign import restricted, select, SCENES


class Tests(unittest.TestCase):
    def test_feature_whitelist(self):
        p={'estimated_position_m':[1,2,3],'confidence':.9,'quality':.8,'age_ticks':2}
        expected=restricted(p)
        p.update(offline_gold=True,contact_id='decoy',history=[99],weapons=[1])
        self.assertEqual(restricted(p),expected)
        self.assertEqual(len(expected),6)

    def test_fixed_balanced_selection(self):
        rows=[{'scene':scene,'seed':seed,'gold_real':gold,'id':f'{scene}:{seed}:{gold}:{i}'}
              for scene in SCENES for seed in [1,2] for gold in [False,True] for i in range(25)]
        selected=select(rows,[1,2])
        self.assertEqual(len(selected),160)
        self.assertEqual(select(list(reversed(rows)),[1,2]),selected)
        self.assertEqual(sum(r['gold_real'] for r in selected),80)

    def test_coverage_shortage_stops(self):
        with self.assertRaises(ValueError):select([], [1])


if __name__=='__main__':unittest.main()
