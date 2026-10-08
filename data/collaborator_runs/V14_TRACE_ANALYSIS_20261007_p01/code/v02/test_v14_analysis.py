import unittest
import v14_analysis as v

class Tests(unittest.TestCase):
    def command(self, task, unit, goal='hold'):
        return {'task_id':task,'parameters':{'unit_id':unit},'goal_type':goal}
    def test_unique_domains(self):
        r=v.coupling([self.command('a','u'),self.command('b','u'),self.command('c','s')],['a','b','c'],{'u':'air','s':'surface'})
        self.assertEqual(r['count'],2);self.assertEqual(r['engagement_goal_count'],0)
    def test_unknown_is_not_zero(self):
        self.assertIsNone(v.coupling([],['patrol_uav_001'],{})['count'])
    def test_no_accepted_zero(self):
        self.assertEqual(v.coupling([],[],{})['count'],0)
    def test_duplicate_task_ambiguous(self):
        self.assertIsNone(v.coupling([self.command('a','u'),self.command('a','s')],['a'],{'u':'air','s':'surface'})['count'])
    def test_missing_decision_no_complete_mean(self):
        r=v.case_stats([{'count':2,'engagement_goal_count':1},{'count':None}])
        self.assertIsNone(r['effective_mean']);self.assertEqual(r['resolved_only_mean'],2)
    def test_single_seed_no_ci(self):
        self.assertIsNone(v.seed_summary([{'seed':31,'effective_mean':2}])['CI95'])
    def test_parsing(self):
        self.assertEqual(v.parse_response('```json\n{"goal_commands":[]}\n```'),[])
        self.assertIsNone(v.parse_response('not a plan'))
    def test_target_domain_not_used(self):
        self.assertIsNone(v.coupling([self.command('a','unknown')],['a'],{})['count'])

if __name__=='__main__':unittest.main()
