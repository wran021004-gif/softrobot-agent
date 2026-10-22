"""Saved SOCP fixture, actual independent replay/compiler; no physics or solve."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from tools.platform_store import plain
from tools.state_io import digest
from tools.research import physical_replay as replay
from tools.research.contracts import ControlSeedRequest
from tools.research.state import state,update,save
from tests.research import test_s130_mainline as fixture


class ControlHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixture.MainlineTests.setUpClass()

    def setUp(self):
        self.f=fixture.MainlineTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.h=self.f.h;self.raw=self.f.conic()
        c=self.h.store.artifact(self.raw['candidate'])
        # Explicitly synthetic import, with all owned Store bindings retained.
        update(self.h,candidates={c['identity']:self.raw['candidate']},imported_candidates=[self.raw['candidate']],
            imported_candidate_profile={'identity':c['profile_identity']})
        self.raw['implementation']=state(self.h)['freeze']
        self.raw['requested_operation']['capability_method']=fixture.opt.CONIC
        spec=deepcopy(state(self.h)['spec']);spec['analysis_protocol']=self.raw['protocol'];update(self.h,spec=spec)
        self.ref=self.register(self.raw)

    def register(self,raw):
        ref=save(self.h,raw,'explicit_saved_SOCP_fixture')
        update(self.h,analysis_results=[*state(self.h).get('analysis_results',[]),ref])
        return ref

    def seed(self,ref=None):
        return replay.seed_control(self.h,ControlSeedRequest(candidate=self.raw['candidate'],
            method='capability_sequence',response_evidence=ref or self.ref),'fixture-seed')

    def test_complete_sequence_uses_separate_execution_identity(self):
        before=self.h.store.remaining()
        with patch('tools.service_execution._run_contained',side_effect=AssertionError('no worker')):
            result=self.seed()
        source=self.h.store.artifact(result['source']);c=self.h.store.artifact(self.raw['candidate'])
        replay.binding(c['configuration'],source['trajectory'])
        self.assertEqual(source['trajectory']['tensions_n'],self.raw['trajectory']['applied_input_n'])
        self.assertEqual(source['task_acceptance'],'unmeasured');self.assertFalse(source['inherited_acceptance'])
        self.assertNotEqual(source['trajectory']['model_identity'],self.raw['model']['binding']['model_identity'])
        self.assertEqual(before,self.h.store.remaining())

    def test_bad_channel_time_bounds_task_and_provenance_rejected(self):
        mutations=[lambda r:r.update(implementation='foreign'),
            lambda r:r['binding'].update(task_identity='foreign'),
            lambda r:r['binding'].update(tendon_order=list(reversed(r['binding']['tendon_order']))),
            lambda r:r['trajectory']['applied_input_n'][0].__setitem__(0,100.),
            lambda r:r['trajectory']['applied_input_n'].pop(),
            lambda r:r['trajectory']['horizon'].update(start_time_s=.01),
            lambda r:r['trajectory']['replay'].update(numerically_valid=False),
            lambda r:r['trajectory']['provenance'].update(model_identity='foreign')]
        mutations.append(lambda r:r['trajectory']['applied_input_n'][0].__setitem__(0,float('nan')))
        for mutation in mutations:
            raw=deepcopy(self.raw);mutation(raw)
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):self.seed(self.register(raw))
        update(self.h,analysis_results=[])
        with self.assertRaisesRegex(ValueError,'REGISTERED'):self.seed()

    def test_failing_mathematical_task_remains_diagnostic(self):
        # A different, bounded explicit input is not the saved optimum. Recompute
        # independent replay only, then label the resulting artifact as a fixture.
        import numpy as np
        from schemas.platform_analysis import EndpointLinearizedModel,TaskAnalysisRequirement,TaskAnalysisProtocol
        from extensions.math_analysis.trajectory import prepare_trajectory,verify_witness
        raw=deepcopy(self.raw);m=EndpointLinearizedModel.model_validate(raw['model'])
        p=TaskAnalysisProtocol.model_validate(raw['protocol']);req=TaskAnalysisRequirement.model_validate(raw['task_analysis'])
        scope,dynamics,initial,rows,*_=prepare_trajectory(m,req,p,dict(coverage=[]))
        delta=np.zeros((scope['step_count'],len(m.u0)))
        check=verify_witness(m,dynamics,initial,delta,rows,scope,p.endpoint_check_atol)
        self.assertFalse(check['passed'])
        check['numerically_valid']=True
        raw['trajectory'].update(delta_input_n=delta.tolist(),applied_input_n=(delta+m.u0).tolist(),replay=check)
        result=self.seed(self.register(raw));source=self.h.store.artifact(result['source'])
        self.assertTrue(source['provenance']['diagnostic_only'])
        self.assertFalse(source['provenance']['numerical_task_passed'])
        self.assertEqual(source['task_acceptance'],'unmeasured')


if __name__=='__main__':unittest.main()
