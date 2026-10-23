"""Small evidence/selection regression: no model builds or solver calls."""
import unittest
from tests.research.s140_structure_effect_screen import replayed_score, select_targets


class ScreenTests(unittest.TestCase):
    def test_fixed_and_conic_score_use_verified_replay(self):
        replay = dict(numerically_valid=True, records=[dict(signed_violation=.2), dict(signed_violation=-.3)])
        self.assertEqual(replayed_score(dict(replay=replay, quantities={'replayed_violation': {'value': .2}})), .2)
        self.assertEqual(replayed_score(dict(replay=replay, replayed_violation=.2)), .2)
        self.assertIsNone(replayed_score(dict(replay=dict(replay, numerically_valid=False))))

    def test_sub_tolerance_noise_cannot_choose_a_different_pair(self):
        rows = [dict(id=name, direction=direction, B=dict(signed_violation=-.2+noise,
            optimality_status='numerically_checked', locality=dict(geometry_screen_pass=True)))
            for name, direction, noise in [('a',[0,1,0],0.), ('b',[0,0,1],1e-11), ('c',[0,-1,0],-1e-11)]]
        self.assertEqual(select_targets(rows), (['a','b'], True))
        for row in rows:
            row['B']['locality']['geometry_screen_pass'] = False
        self.assertEqual(select_targets(rows), (['yz_plus','minus_y_plus_z'], False))


if __name__ == '__main__':
    unittest.main()
