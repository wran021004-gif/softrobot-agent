"""Synthetic history only; no scientific result or alternate cost ledger."""
import unittest
from tests.research.p63h_evidence_report import history_curve


class CostHistoryTests(unittest.TestCase):
    def test_best_found_uses_saved_callbacks_and_confirmed_physics_work(self):
        rows=[dict(measure=dict(signed_maximum_excess=j)) for j in [4.,2.,3.,1.]]
        curve=history_curve(rows,steps_per_rollout=1000)
        self.assertEqual([r['best_found_J'] for r in curve],[4.,2.,2.,1.])
        self.assertEqual([r['physics_steps'] for r in curve],[1000,2000,3000,4000])
        self.assertEqual(history_curve([],steps_per_rollout=1000),[])
        self.assertTrue(all('wall_s' not in row for row in curve))


if __name__=='__main__':unittest.main()
