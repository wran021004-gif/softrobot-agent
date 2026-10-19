"""Numerical seed fixtures; no real physics, MATLAB or provider requests."""
import unittest
import numpy as np
from tools.research.control_seed import directed_inputs
from tools.research.contracts import ControlSeedRequest

REF={'artifact_id':'a'*64,'media_type':'application/json'}


class ControlSeedTests(unittest.TestCase):
    def test_targets_channels_and_grids(self):
        for channels,count in ((1,7),(3,12),(6,20)):
            response=np.eye(3,channels)
            if channels==6:response[:,3:]=np.eye(3)*.5
            u=np.ones((count,channels))
            positive=directed_inputs(u,response,[.1,.2,.3],[8]*channels,.5,1e-6)
            negative=directed_inputs(u,response,[-.1,-.2,-.3],[8]*channels,.5,1e-6)
            self.assertEqual(np.shape(positive['inputs']),(count,channels))
            self.assertGreater(positive['delta_n'][0],0);self.assertLess(negative['delta_n'][0],0)
            self.assertEqual(positive['task_acceptance'],'unmeasured')

    def test_bounds_at_every_interval(self):
        u=np.array([[0.,7.99,1.],[.01,7.,1.]])
        fit=directed_inputs(u,np.eye(3),[-1,1,.2],[8]*3,2.,1e-6)
        self.assertAlmostEqual(fit['delta_n'][0],0,places=12)
        self.assertLessEqual(fit['delta_n'][1],.01+1e-12)
        self.assertTrue(np.all(np.asarray(fit['inputs'])<=8))

    def test_rank_deficiency_has_no_forced_input(self):
        for response in (np.zeros((3,4)),np.diag([1.,1.,1e-12])):
            fit=directed_inputs(np.ones((4,response.shape[1])),response,[1,1,1],[8]*response.shape[1],1.,1e-6)
            self.assertEqual(fit['status'],'unreliable_response');self.assertNotIn('inputs',fit)

    def test_illegal_or_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError,'FINITE'):
            directed_inputs([[1]*3],np.eye(3),[float('nan'),0,0],[8]*3,1.,1e-6)

    def test_math_requires_reference_and_baseline_serialization(self):
        with self.assertRaisesRegex(ValueError,'REGISTERED_RESPONSE'):ControlSeedRequest(candidate=REF,method='mathematical_response')
        self.assertNotIn('method',ControlSeedRequest(candidate=REF).model_dump())
        q=ControlSeedRequest(candidate=REF,method='mathematical_response',response_evidence=REF)
        self.assertEqual(q.method,'mathematical_response')


if __name__=='__main__':unittest.main()
