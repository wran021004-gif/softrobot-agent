"""Stable-initialization classification fixtures; no physics integration."""
import unittest
from tests.research import test_bf6_oriented_tracking as fixtures
from tests.research.bf6_r2_stability import stable_start


class StabilityGateTests(unittest.TestCase):
    def setUp(self):
        fixtures.OrientedTrackingTests.setUpClass();self.fixture=fixtures.OrientedTrackingTests();self.fixture.setUp()
        self.raw=self.fixture.raw();self.raw['physics_step_attempts']=600

    def test_stable_goal_failure_is_a_valid_start(self):
        self.raw['samples'][12]['tip_m'][1]+=.05
        _,a=self.fixture.accept(self.raw)
        self.assertFalse(a['accepted']);self.assertTrue(stable_start(a,self.raw))

    def test_contact_is_not_stable(self):
        self.raw['environment_contact']['contact_free']=False
        _,a=self.fixture.accept(self.raw)
        self.assertFalse(stable_start(a,self.raw))

    def test_incomplete_or_unresolved_sources_are_not_stable(self):
        self.raw['status']='incomplete';self.raw['physics_steps']=599
        _,a=self.fixture.accept(self.raw)
        self.assertFalse(stable_start(a,self.raw))

    def test_full_original_pass_is_distinct_from_stable_only(self):
        _,a=self.fixture.accept(self.raw)
        self.assertTrue(a['accepted']);self.assertTrue(stable_start(a,self.raw))


if __name__=='__main__':unittest.main()
