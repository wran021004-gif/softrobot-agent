"""Deterministic rejections precede workers and scientific reservations."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from tools.research import analysis
from tools.research.contracts import AnalysisRequest
from tools.research.design import generate_candidate
from tools.research.state import state, update, save
from tools.state_io import digest
from tests.research.test_s125_contract import cold_host


def candidate_fixture():
    h=cold_host();s=state(h);update(h,freeze='s127-isolated-fixture')
    ref=generate_candidate(h,dict(version='serial_family_generation_v2',family_space_identity=s['spec']['family_space_identity'],
        segment_count=2,tendon_count=4),dict(origin='s127_test_fixture_not_scientific_evidence'))['candidate']
    return h,ref


class MathAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.h,cls.ref=candidate_fixture()

    def query(self,**kw):
        return dict(candidate=self.ref,operation='equilibrium',operating_point='target_equilibrium',
            protocol=state(self.h)['spec']['analysis_protocol'],**kw)

    def assert_rejected_before_science(self,q,error):
        h=self.h;before=deepcopy(state(h));ledger=h.store.remaining()
        with patch('tools.service_execution._run_contained') as worker,patch.object(analysis,'admission',wraps=analysis.admission) as fit:
            with self.assertRaisesRegex(ValueError,error):analysis.dispatch(h,q,'fixture-'+digest(q),guard=lambda *a:None)
            worker.assert_not_called()
            # Type/point errors are rejected before even computing scientific capacity.
            if error in ('EQUILIBRIUM_REQUIRES_TARGET_POINT','STATIC_SENSITIVITY','SCORING_WINDOW','EXPLICIT_SCORE','PAIRED','INSTANTANEOUS'):
                fit.assert_not_called()
        self.assertEqual(state(h),before);self.assertEqual(h.store.remaining(),ledger)

    def test_invalid_operation_point_window_matrix(self):
        base=self.query()
        cases=[({'operating_point':'standardized_initial_pretension'},'EQUILIBRIUM_REQUIRES_TARGET_POINT'),
            ({'operation':'input_sensitivity','operating_point':'target_equilibrium'},'STATIC_SENSITIVITY'),
            ({'operation':'linearization','scoring_window_s':None},'EXPLICIT_SCORE'),
            ({'operation':'linearization','scoring_window_s':.123456},'SCORING_WINDOW'),
            ({'operation':'design_sensitivity','operating_point':'fixed_input_equilibrium'},'PAIRED'),
            ({'operation':'instantaneous_braking_v1'},'INSTANTANEOUS')]
        for changes,error in cases:
            with self.subTest(changes=changes):self.assert_rejected_before_science(dict(base,**changes),error)

    def test_saved_state_identity_dimensions_phase_and_remaining_time(self):
        h=self.h;c=h.store.artifact(self.ref);cfg=c['configuration']
        from extensions.tendon_family.gvs_basis import resolve_basis
        design=cfg['robot']['structure']['data'];basis=cfg['policy']['controller']['parameters']['data']['recipe']['basis']
        order=list(resolve_basis(design,basis).coordinate_order);tendons=[t['id'] for t in design['tendons']]
        point=dict(candidate=self.ref,configuration_identity=digest(cfg),x=[0.]*(2*len(order)),u=[.2]*len(tendons),
            coordinate_order=order,tendon_order=tendons,phase='interval_start_previous_applied_input',input_units='N',actual_time_s=.34)
        variants=[(dict(candidate={'artifact_id':'a'*64}),'CANDIDATE_MISMATCH'),(dict(x=[0.]),'ORDER_AND_PHASE'),
            (dict(phase='optimizer_prediction'),'ORDER_AND_PHASE'),(dict(actual_time_s=.36),'ACTUAL_TIME_REQUIRED')]
        with patch('tools.research.tool_readiness.require'):
            for changes,error in variants:
                ref=save(h,dict(point,**changes),'test_fixture')
                q=dict(self.query(),operation='instantaneous_braking_v1',operating_point='saved_state',saved_state=ref)
                self.assert_rejected_before_science(q,error)
            ref=save(h,point,'test_fixture');q=dict(self.query(),operation='linearization',operating_point='saved_state',saved_state=ref,
                scoring_window_s=state(h)['spec']['analysis_protocol']['windows_s'][-1])
            self.assert_rejected_before_science(q,'REMAINING_TASK_TIME')

    def test_legal_points_remain_requests_not_claims_of_numerical_success(self):
        target=AnalysisRequest.model_validate(self.query())
        sensitivity=AnalysisRequest.model_validate(dict(self.query(),operation='input_sensitivity',operating_point='fixed_input_equilibrium'))
        self.assertIsNone(target.saved_state);self.assertIsNone(sensitivity.saved_state)
        self.assertFalse(hasattr(target,'accepted'))


if __name__=='__main__':unittest.main()
