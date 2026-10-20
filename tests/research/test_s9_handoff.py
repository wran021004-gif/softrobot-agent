"""Candidate/model/task/point/channel handoff regressions; no MATLAB or physics."""
from copy import deepcopy
import unittest
from unittest.mock import Mock, patch
from tools.research.physical_replay import verified_input_response, guided_seed
from tools.research.contracts import ControlSeedRequest
from tools.research.control_seed import directed_inputs
from tools.research.numerics import archived
from tools.research.config import ROOT
from tools.state_io import read


class HandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref=read(ROOT/'evidence/s8_engineering/study/disposition.json')['evidence']['analyses'][0]
        cls.analysis=archived('evidence/s8_engineering/study',cls.ref)
        cls.candidate=cls.analysis['candidate']
        cls.cfg=archived('evidence/s8_engineering/study',cls.candidate)['configuration']

    def check(self,value=None,registered=True):
        host=Mock();host.store.artifact.return_value=value or self.analysis
        bound=self.analysis['model']['binding']
        spec=dict(identity=bound['model_identity'],tendon_order=bound['tendon_order'],coordinate_order=bound['coordinate_order'])
        with patch('tools.research.physical_replay.state',return_value=dict(analysis_results=[self.ref] if registered else [],spec=dict(analysis_protocol=self.analysis['protocol']))),patch('tools.research.physical_replay.verify_candidate',return_value=dict(configuration=self.cfg)),patch('tools.research.physical_replay.model_context',return_value=(None,None,None,spec)):
            return verified_input_response(host,self.candidate,self.ref)

    def test_real_s8_verified_artifact_accepted_without_mutation(self):
        self.assertEqual(self.check(),self.analysis)

    def test_identity_and_verification_rejections(self):
        mutations=[('candidate',None),('binding.task_identity','wrong'),('model.binding.model_identity','wrong'),
            ('model.operating_point.name','wrong'),('model.binding.tendon_order',['wrong']),
            ('sensitivity.verification.passed',False),('model.protocol_identity','wrong')]
        for path,value in mutations:
            a=deepcopy(self.analysis);target=a;parts=path.split('.')
            for part in parts[:-1]:target=target[part]
            target[parts[-1]]=value
            with self.subTest(path=path),self.assertRaisesRegex(ValueError,'VERIFIED_CANDIDATE'):
                self.check(a)
        with self.assertRaisesRegex(ValueError,'REGISTERED_CURRENT'):self.check(registered=False)

    def test_failed_preflight_cannot_save_baseline(self):
        q=ControlSeedRequest(candidate=self.candidate,method='mathematical_response',response_evidence=self.ref)
        with patch('tools.research.physical_replay.verify_candidate',return_value=dict(configuration=self.cfg)),patch('tools.research.physical_replay.model_context',return_value=(None,None,None,dict(tendon_order=self.analysis['binding']['tendon_order']))),patch('tools.research.physical_replay.verified_input_response',side_effect=ValueError('fixture invalid')),patch('tools.research.physical_replay._seed_control') as baseline:
            with self.assertRaisesRegex(ValueError,'fixture invalid'):guided_seed(Mock(),q,'fixture',None)
            baseline.assert_not_called()

    def test_no_input_room_is_explicit(self):
        r=directed_inputs([[0.],[8.]],[[1.],[0.],[0.]],[1.,0.,0.],[8.],1.,1e-6)
        self.assertEqual(r['status'],'no_input_room');self.assertNotIn('inputs',r)

    def test_physical_budget_rejection_precedes_baseline(self):
        q=ControlSeedRequest(candidate=self.candidate,method='physical_response',evaluation_requests=1)
        with patch('tools.research.physical_replay.verify_candidate',return_value=dict(configuration=self.cfg)),patch('tools.research.physical_replay.model_context',return_value=(None,None,None,dict(tendon_order=self.analysis['binding']['tendon_order']))),patch('tools.research.budget.backend_capacity',return_value=0),patch('tools.research.physical_replay._seed_control') as baseline:
            with self.assertRaisesRegex(ValueError,'INSUFFICIENT_SHARED_BUDGET'):guided_seed(Mock(),q,'fixture',None)
            baseline.assert_not_called()

    def test_non_endpoint_task_rejected_before_persistence(self):
        cfg=deepcopy(self.cfg);cfg['task']['family']='fixture.unsupported'
        q=ControlSeedRequest(candidate=self.candidate,method='mathematical_response',response_evidence=self.ref)
        with patch('tools.research.physical_replay.verify_candidate',return_value=dict(configuration=cfg)),patch('tools.research.physical_replay._seed_control') as baseline:
            with self.assertRaisesRegex(ValueError,'NOT_APPLICABLE'):guided_seed(Mock(),q,'fixture',None)
            baseline.assert_not_called()


if __name__=='__main__':unittest.main()
