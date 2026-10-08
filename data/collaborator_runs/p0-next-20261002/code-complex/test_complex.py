import inspect
import json
from pathlib import Path
import unittest
import numpy as np
import channel_experiment as c
import e3_classify as e


class Tests(unittest.TestCase):
    def test_native_complex_selected(self):
        source=inspect.getsource(c.collect)
        self.assertIn("difficulty='complex'",source)
        self.assertNotIn("difficulty='medium'",source)

    def test_unchanged_strong_features(self):
        previous=Path(__file__).parent.parent/'p0_channel_v3_20261002/channel_experiment.py'
        if previous.exists():
            source=previous.read_text(encoding='utf-8')
            for func in [c.visible_local,c.current_features,c.train,c.rule if hasattr(c,'rule') else c.predict]:
                self.assertIn(inspect.getsource(func).strip(),source)

    def test_schema(self):
        f=e.RESPONSE_FORMAT
        self.assertEqual(f['type'],'json_schema')
        self.assertTrue(f['json_schema']['strict'])
        self.assertEqual(set(f['json_schema']['schema']['required']),{'label','p_real'})
        self.assertIn('"response_format": RESPONSE_FORMAT',inspect.getsource(e.main))

    def test_seed_disjointness_and_fixed_protocol(self):
        p=json.loads(Path(__file__).with_name('complex_protocol.json').read_text())
        self.assertEqual(p['D1'],{'numeric_accuracy_max':.6,'LLM_accuracy_min':.85})
        self.assertEqual(p['history_contacts'],8)
        ranges=[set(range(a,b+1)) for a,b in [p['development_seeds'],p['initial_confirmation_source_seeds'],p['conditional_extension_seeds']]]
        self.assertFalse(ranges[0]&ranges[1] or ranges[0]&ranges[2] or ranges[1]&ranges[2])
        self.assertGreater(min(ranges[0]),10400)

    def test_numeric_learner(self):
        rows=[{'seed':s,'gold_real':bool(y),'local_features':[float(y)]*12} for s in range(40) for y in [0,1]]
        m=c.train(rows)
        p=c.predict(m['model'],[r['local_features'] for r in rows])
        self.assertGreater(np.mean([(v>.5)==r['gold_real'] for v,r in zip(p,rows)]),.95)

    def test_no_changed_cutoff(self):
        self.assertIn('probability > .5',inspect.getsource(e.main))
        self.assertIn('errors/len(pred)<=.05',inspect.getsource(c.campaign))


if __name__=='__main__':unittest.main()
