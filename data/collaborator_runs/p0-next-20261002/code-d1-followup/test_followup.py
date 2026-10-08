import unittest
import numpy as np
from hf_audit import labels_for
from hf_pilot import local_features,SCENES,SEEDS,SCHEMA,clean
from grid_diagnose import accuracy


class Tests(unittest.TestCase):
    def test_contract_requires_armed_facility_attack(self):
        es=[{'id':'d','faction_id':'coalition.intruder','tags':['decoy']},
            {'id':'t','faction_id':'coalition.intruder','tags':['target.facility.command'],'loadout_ref':'w','ammunition':{'w':1}},
            {'id':'ambiguous','faction_id':'coalition.intruder','tags':['main']}]
        labels,issues=labels_for({'entities':es,'events':[]})
        self.assertEqual(labels,{'d':False,'t':True});self.assertEqual(issues[0]['id'],'ambiguous')
    def test_armed_decoy_not_silently_non_threat(self):
        labels,issues=labels_for({'entities':[{'id':'x','faction_id':'coalition.intruder','tags':['decoy'],'loadout_ref':'w','ammunition':{'w':1}}],'events':[]})
        self.assertEqual(labels,{});self.assertTrue(issues)
    def test_feature_truth_id_invariance(self):
        q={'estimated_position_m':[10000,-500,100],'confidence':.8,'quality':.9,'age_ticks':0,'contact_id':'decoy-secret'}
        f={'own_public':[{'entity_id':'u','position_m':[0,0,0],'velocity_mps':[0,0,0],'heading_deg':0,'health':1,'energy':1}],
           'contacts':[{'public':q,'offline_gold_real':False}]}
        a=local_features(f,q);q['contact_id']='real-secret';f['contacts'][0]['offline_gold_real']=True
        self.assertEqual(a,local_features(f,q));self.assertEqual(len(a),172)
    def test_same_model_fixed_schema(self):
        self.assertTrue(SCHEMA['json_schema']['strict']);self.assertEqual(len(SEEDS),5);self.assertEqual(len(SCENES),2)
    def test_auc(self):
        m=accuracy([False,True],[.1,.9]);self.assertEqual(m['accuracy'],1);self.assertEqual(m['auc'],1)
    def test_clean_preserves_actions(self):
        self.assertEqual(clean({'action_id':'random','controls':{'speed':5}}),{'controls':{'speed':5}})


if __name__=='__main__':unittest.main()
