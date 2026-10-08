import unittest
from e11_experiment import aggregate, stability, score_from_layers

class TestE11(unittest.TestCase):
    def test_aggregate_keeps_original_episode_mean(self):
        a=aggregate([{'seed':1,'score':1.},{'seed':1,'score':1.},{'seed':2,'score':0.}])
        self.assertAlmostEqual(a['mean'],2/3)
        self.assertEqual(a['n_seeds'],2)

    def test_stability_not_just_positive_mean(self):
        h=aggregate([{'seed':i,'score':v} for i,v in enumerate([.9,.9,.1,.9,.9])])
        b=aggregate([{'seed':i,'score':.5} for i in range(3)])
        s=stability(h,b)
        self.assertTrue(s['mean_win'])
        self.assertFalse(s['every_seed_win'])

    def test_score_normalized_once(self):
        d={'strategy_scorecard':{'layers':{'a':.8,'b':1},'layer_weights':{'a':.6,'b':.4},'layer_applicability':{'a':True,'b':False},'defender_score':.8}}
        self.assertEqual(score_from_layers(d),.8)

    def test_bad_score_rejected(self):
        d={'strategy_scorecard':{'layers':{'a':.8},'layer_weights':{'a':.6},'layer_applicability':{},'defender_score':1.}}
        with self.assertRaises(ValueError):score_from_layers(d)

if __name__=='__main__':unittest.main()
