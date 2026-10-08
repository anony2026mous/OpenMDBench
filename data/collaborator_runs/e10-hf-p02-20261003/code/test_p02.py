import unittest
import numpy as np
from hf_campaign import quotas, select, SCENES, restricted
from grid_alignment import bootstrap_metrics


class Tests(unittest.TestCase):
    def test_equal_when_possible(self):
        self.assertEqual(quotas({i:30 for i in range(10)}),{i:20 for i in range(10)})

    def test_capped_distribution(self):
        c=dict(enumerate([12,236,10,12,14,11,10,12,10,129]))
        q=quotas(c)
        self.assertEqual(sum(q.values()),200)
        self.assertTrue(all(1<=q[s]<=c[s] for s in q))
        self.assertEqual(q,quotas(dict(reversed(list(c.items())))))

    def test_total_shortage_and_missing_class(self):
        with self.assertRaises(ValueError):quotas({i:10 for i in range(10)})
        with self.assertRaises(ValueError):quotas({0:0,1:300})

    def test_selection_deterministic_balanced_and_unique(self):
        c=dict(enumerate([12,236,10,12,14,11,10,12,10,129]))
        rows=[{'scene':scene,'seed':s,'gold_real':g,'id':f'{scene}:{s}:{g}:{i}'}
              for scene in SCENES for s,n in c.items() for g in [False,True] for i in range(n)]
        selected,a=select(rows,list(c))
        self.assertEqual(len(selected),800)
        self.assertEqual(len({r['id'] for r in selected}),800)
        self.assertEqual(select(list(reversed(rows)),list(c)),(selected,a))
        for scene in SCENES:
            self.assertEqual(sum(r['scene']==scene and r['gold_real'] for r in selected),200)
            for s in c:
                counts=[sum(r['scene']==scene and r['seed']==s and r['gold_real']==g for r in selected) for g in [False,True]]
                self.assertEqual(counts[0],counts[1])
                self.assertGreater(counts[0],0)
        dev,alloc=select(rows,list(c),'development')
        self.assertEqual(len(dev),524)

    def test_numeric_whitelist_unchanged(self):
        p={'estimated_position_m':[1,2,3],'confidence':.9,'quality':.8,'age_ticks':2}
        expected=restricted(p);p['contact_id']='decoy';p['gold_real']=True
        self.assertEqual(restricted(p),expected)

    def test_seed_equal_bootstrap_differs_from_event_weight(self):
        rows=[{'seed':s,'gold_real':bool(i%2),'p':(.9 if i%2 else .1) if s==0 else (.1 if i%2 else .9)}
              for s,n in [(0,2),(1,8)] for i in range(n)]
        cluster=np.array([r['seed'] for r in rows]);weights=np.ones((20,2))
        raw,_,_=bootstrap_metrics(rows,'p',weights,cluster)
        macro,b,_=bootstrap_metrics(rows,'p',weights/np.array([2,8]),cluster)
        self.assertAlmostEqual(raw['accuracy'],.2)
        self.assertTrue(np.allclose(b,.5))
        self.assertEqual(macro['accuracy_ci95'],[.5,.5])


if __name__=='__main__':unittest.main()
