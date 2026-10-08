import unittest
from unittest.mock import patch
from e14_campaign import CONFIGS,SEEDS
from e14_worker import evaluate

class TestE14(unittest.TestCase):
    def test_exact_budget_and_scan(self):
        self.assertEqual(len(CONFIGS)*len(SEEDS),12)
        self.assertEqual(CONFIGS['default_extended']['total_steps'],10000000)
        self.assertEqual(CONFIGS['lr_half']['lr'],.00015)
        self.assertEqual(CONFIGS['lr_double_entropy_double']['entropy'],.02)

    def test_deterministic_eval_flag_restored(self):
        class Agent:trained=False
        a=Agent()
        def fake(*args):
            self.assertTrue(a.trained);return [1]
        with patch('e14_worker._evaluate_impl',side_effect=fake):self.assertEqual(evaluate(a,'complex',[1]),[1])
        self.assertFalse(a.trained)

    def test_eval_flag_restored_on_error(self):
        class Agent:trained=False
        a=Agent()
        with patch('e14_worker._evaluate_impl',side_effect=ValueError('error')):
            with self.assertRaises(ValueError):evaluate(a,'complex',[1])
        self.assertFalse(a.trained)

if __name__=='__main__':unittest.main()
