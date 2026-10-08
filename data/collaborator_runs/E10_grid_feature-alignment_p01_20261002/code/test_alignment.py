import unittest
import numpy as np
from grid_alignment import plane, balanced, bootstrap_metrics


class Tests(unittest.TestCase):
    def test_plane_whitelist(self):
        row={"local_features":list(range(84))}
        self.assertEqual(plane([row]).tolist(), [list(range(64))])
        row['local_features'][64:]=[999]*20
        self.assertEqual(plane([row]).tolist(), [list(range(64))])

    def test_balanced(self):
        self.assertEqual(balanced([False, True], [.1, .9]), 1)

    def test_auc_ties_and_paired_clusters(self):
        rows=[{'seed':i//2,'gold_real':bool(i%2),'p':.5} for i in range(8)]
        clusters=np.array([i//2 for i in range(8)])
        weights=np.random.default_rng(1).multinomial(4,[.25]*4,size=100)
        m, b, valid=bootstrap_metrics(rows,'p',weights,clusters)
        self.assertEqual(m['auc'],.5)
        self.assertEqual(m['balanced_accuracy'],.5)
        self.assertTrue(np.all(b==.5))
        self.assertEqual(m['auc_ci95'],[.5,.5])
        for row in rows:row['p']=.9 if row['gold_real'] else .1
        m,_,_=bootstrap_metrics(rows,'p',weights,clusters)
        self.assertEqual(m['auc'],1)
        self.assertEqual(m['accuracy'],1)
        self.assertEqual(m['auc_ci95'],[1.,1.])


if __name__=='__main__':unittest.main()
