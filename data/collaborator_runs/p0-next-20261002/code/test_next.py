import copy
from pathlib import Path
import unittest
import yaml
from pressure_variants import transform,inventory
from count_campaign import d3
from channel_experiment import current_features,fit,predict,visible_local
import numpy as np


class Tests(unittest.TestCase):
    def scene(self):
        return {'scenario':{'entities':[{'id':'u1','faction_id':'coalition.intruder','platform_ref':'u','tags':['uav'],
                 'initial_state':{'position_m':[10000,1000,150],'health':1},'component_refs':['radar']}],
                 'events':[],'world':{'dt':1},'scoring':{'a':1}}}
    def test_native_exact(self):
        s=self.scene();self.assertEqual(transform(s,1),s)
    def test_clone_equipment_originals_preserved(self):
        s=self.scene();before=copy.deepcopy(s);new=transform(s,3)
        self.assertEqual(s,before);self.assertEqual(inventory(new)[0],inventory(s)[0])
        for e in inventory(new)[1:]:self.assertEqual(e['component_refs'],['radar']);self.assertEqual(e['initial_state']['health'],1)
    def test_d3_positive_not_merely_high_variance(self):
        self.assertTrue(d3([.4]*10)['pass']);self.assertFalse(d3([-.4,.5]*5)['pass'])
    def test_d3_no_clipping(self):self.assertFalse(d3([-.2]*10)['pass'])
    def test_native_wave_times_preserved(self):
        s=self.scene();base=copy.deepcopy(s['scenario']['entities'][0]);base['id']='spawned'
        s['scenario']['events']=[{'id':'spawn1','event_type':'spawn','trigger':{'tick':250},'payload':{'entity':base}}]
        new=transform(s,4);self.assertEqual(s['scenario']['events'][0],new['scenario']['events'][0])
        self.assertTrue(all(e['trigger']['tick']==250 for e in new['scenario']['events']))
    def test_local_features_no_truth_id_goal_history(self):
        grid=np.zeros((5,5),int);grid[3,2]=4
        f={'position':[11,10],'gold_real':True,'contact':'feint-secret','heading':[1,2],
           'local_observations':{'u':{'grid':grid.tolist(),'own_state':[.5,.5,1,1,1],'kind':'usv','subgoal':{'role':'real'}}}}
        base=current_features(f);self.assertIsNotNone(base)
        f['gold_real']=False;f['contact']='another';f['heading']=[-1,-2];f['local_observations']['u']['subgoal']={'role':'feint'}
        self.assertEqual(base,current_features(f));self.assertEqual(visible_local(f)[3:],(3,2))
    def test_candidate_must_be_locally_visible(self):
        f={'position':[19,19],'local_observations':{'u':{'grid':np.zeros((5,5)).tolist(),'own_state':[.5,.5,1,1,1]}}}
        self.assertIsNone(current_features(f))
    def test_numeric_model_can_learn_separable_signal(self):
        x=[[-1]*81]*20+[[1]*81]*20;y=[False]*20+[True]*20
        m=fit(x,y,.01,False);p=predict(m,[[-1]*81,[1]*81])
        self.assertLess(p[0],.1);self.assertGreater(p[1],.9)


if __name__=='__main__':unittest.main()
