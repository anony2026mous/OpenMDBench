import json
import tempfile
import unittest
from pathlib import Path

from toolkit_night_campaign import estimated_seconds, make_queue
from p0_6_summarize import run_table

class NightCampaignTests(unittest.TestCase):
    def test_complete_unique_frozen_matrix(self):
        config = {'scenarios': ['IE-10', 'IE-11', 'IE-04'], 'seeds': [601, 602, 603]}
        queue = make_queue(config)
        self.assertEqual(len(queue), 54)
        self.assertEqual(len(set(queue)), 54)

    def test_first_priority_is_complete_paired_seed(self):
        queue = make_queue({'scenarios': ['IE-10', 'IE-11'], 'seeds': [601, 602]})
        self.assertTrue(all((s, n) == ('IE-10', 601) for s, n, a in queue[:6]))
        self.assertEqual([a for s,n,a in queue[:6]], ['rule','rule-rl','rl','llm','llm-rl','pure-llm'])

    def test_estimate_respects_observed_tail(self):
        self.assertAlmostEqual(estimated_seconds('IE-10', 'llm', {('IE-10','llm'):[100,200]}), 260)
        self.assertEqual(estimated_seconds('none', 'rule', {}), 420)
        self.assertEqual(estimated_seconds('none', 'llm', {}), 3900)

    def test_p0_ignores_full_episode_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out/'ie_example_manifest.json').write_text(json.dumps({'run_id':'ie_example','status':'running'}), encoding='utf-8')
            self.assertEqual(run_table(out, {}), [])

if __name__ == '__main__':
    unittest.main()
