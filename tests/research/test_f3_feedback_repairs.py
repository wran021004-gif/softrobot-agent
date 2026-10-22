"""Synthetic protocol regressions only; no new physics, MATLAB or Provider sends."""
import gzip
import json
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
import httpx
import numpy as np
from extensions.tendon_family.sorosim_control import normalize_nmpc_rows,SorosimNMPCController
from extensions.tendon_family.control import execute_ideal_tension
from extensions.tendon_family.gvs_reporting import aligned_predictions
from tools.research.evidence_views import recorded_math_summary
from tools.research.research_context import mathematics_authorization,resolved_candidate_facts,ordered_candidates,recorded_changes
from tools.research.core import read_evidence
from tools.research.state import state,save,update
from tools.research import reporter
from tools.state_io import digest
from tests.research import test_s129_agent_reporting as reporter_fixtures
from tests.research.test_s126_checkpoint import cold_host


def solver_output():
    return dict(horizon=1,states=[[0.]*4,[1.]*4],tensions=[.4,2.6,1.5,0.],
        tip_positions=[.3,-.03,.19],tip_velocities=[.01,.02,.03],accepted=True,
        exitflag=2,constraint_violation=1e-13,selected_iteration=5,returned_constraint_violation=1e-13,
        recovery=dict(selected=False,wall_s=0),optimization_s=.2,warm_preparation_s=.1,validation_s=.1)


class FeedbackRepairTests(unittest.TestCase):
    def test_single_interval_preserves_channels_and_vector_predictions_in_actual_command(self):
        c=SorosimNMPCController.__new__(SorosimNMPCController)
        c.parameters=SimpleNamespace(substeps=1,max_unusable_updates=3,integration_method='implicit_euler',model_dump=lambda **kw:{})
        c.session=SimpleNamespace(evaluate=Mock(return_value=solver_output()),timings=dict(calls=[{}]))
        c.request=Mock(return_value={'fixture':'synthetic'})
        c.plan=dict(identity='controller-fixture',task={},specification=dict(identity='model-fixture',tendon_order=['a','b','c','d']),solver={})
        c.physics=dict(identity='physics-fixture',tendons=[dict(force_limit_n=8)]*4)
        c.previous=np.array([1.]*4);c.limits=np.array([8.]*4);c.period_s=.01;c.observations=[]
        c.coordinate_order=['q0','q1'];c.construction=dict(construction_s=.1)
        with patch('extensions.tendon_family.sorosim_control.ScopedMathematicalClaim'):
            command=c.command(.34,dict(tip=np.array([0.,0.,0.]),gvs_projection=dict(projection_residual_max_rad_m=0)),[0.,0.],[0.,0.])
        self.assertEqual(command.tolist(),[.4,2.6,1.5,0.])
        self.assertEqual(c.last['one_step_prediction']['tip_position_m'],[.3,-.03,.19])
        self.assertEqual(c.last['one_step_prediction']['tip_velocity_m_s'],[.01,.02,.03])
        self.assertEqual(c.last['applied_input_selection']['branch'],'accepted_selected_plan')
        self.assertFalse(c.last['failure_response_used'])
        self.assertFalse(c.observations[-1]['solver_request_record']['exact_solver_replay_supported'])

    def test_wrong_shape_and_nonfinite_outputs_rejected_without_broadcast(self):
        original=solver_output()
        for key,bad in [('tensions',.4),('tip_positions',.3),('tip_velocities',[0.,float('nan'),0.]),('states',[0.]*8)]:
            with self.subTest(key=key):
                value=deepcopy(original);value[key]=bad
                with self.assertRaisesRegex(ValueError,'OUTPUT_SHAPE_INVALID'):
                    normalize_nmpc_rows(value,state_size=4,input_size=4,substeps=1)
        for bad in (.4,[.4],[1,2,3,float('nan')]):
            with self.assertRaisesRegex(ValueError,'FINITE_TENDON_VECTOR'):
                execute_ideal_tension(dict(tendons=[dict(force_limit_n=8)]*4),bad)
        self.assertEqual(original,solver_output())

    def test_scalar_prediction_is_unavailable_instead_of_vector_broadcast(self):
        observations=[dict(time_s=.34,actual_tension_n=[1.]*4,one_step_prediction=dict(time_s=.35,
            tip_position_m=.3,tip_velocity_m_s=.02,applied_tension_n=[1.]*4))]
        comparisons,missing=aligned_predictions([dict(time_s=.35,tip_m=[.3,0,0])],observations)
        self.assertEqual(comparisons,[]);self.assertIn('shape invalid',missing[0]['reason'])

    def test_tiny_recorded_strict_violation_does_not_become_pass_or_infeasibility(self):
        value=dict(mathematical_facts=dict(status='computed',objective=0.,converged=True,exitflag=1,
            original_feasible=False,relaxed_feasible=True,task=dict(constraint_ids=['speed'],times_s=[.35],
                signed_margin=[-1.59e-14],actual_norm=[.0200000000000159],original_sampled_requirements_satisfied=False)),
            trajectory=dict(slacks=dict(position=0,speed=0)),task_requirements=dict(constraints=[dict(
                constraint_id='speed',signal=dict(units='m/s'),radius=.02)]),physical_validation='not_run',
            task_acceptance='unmeasured',verified_conclusions=[dict(conclusion='inconclusive')])
        original=deepcopy(value);summary=recorded_math_summary(value,dict(artifact_id='a'*64))
        row=summary['original_predicate_diagnostics']['recomputed']['maxima_by_constraint'][0]
        self.assertEqual((row['positive_violation'],row['unit']),(1.59e-14,'m/s'))
        self.assertTrue(summary['zero_slack_with_positive_recorded_violation'])
        self.assertFalse(summary['original_feasible']);self.assertEqual(summary['conclusion'],['inconclusive'])
        self.assertFalse(summary['independent_physical_acceptance_established']);self.assertEqual(value,original)

    def test_formal_math_authorization_does_not_claim_t2_inputs_exist(self):
        h=Mock();h.run_id='fixture';methods={'sampled-affine-conic-minimax-v1':'Proposed SOCP, blocked until Study approval',
            'controlled-capability-sensitivity-v1':'Proposed T2, blocked until Study approval'}
        s=dict(spec=dict(resolved_identity='resolved-fixture',mathematical_methods=methods))
        scope=dict(study_id=h.run_id,resolved_identity='resolved-fixture',execution_scopes=['registered mathematics'])
        a=dict(scope=scope,scope_identity=digest(scope),user_approval=True)
        ref=dict(artifact_id='a'*64);h.store.events.return_value=[dict(kind='formal_study_authorization',outputs=[ref])]
        h.store.artifact.return_value=a
        display=mathematics_authorization(h,s)
        self.assertTrue(display['registered_study_scope_authorized'])
        self.assertTrue(all(r['frozen_method_grant'] for r in display['methods']))
        self.assertFalse(display['proposal_text_is_current_execution_gate']);self.assertEqual(s['spec']['mathematical_methods'],methods)
        h.store.events.return_value=[]
        self.assertIsNone(mathematics_authorization(h,s)['registered_study_scope_authorized'])

    def test_gzip_original_reads_and_failed_pointer_offer_real_navigation(self):
        h=cold_host();before=h.store.remaining();value=[dict(time_s=.34,position=[1,2,3])]
        with h.store.transaction() as db:
            ref=h.store.put(db,gzip.compress(json.dumps(value).encode()),'application/gzip')
        self.assertEqual(read_evidence(h,dict(reference=ref,view='range',count=1),record_read=False)['items'],value)
        with self.assertRaises(KeyError) as raised:
            read_evidence(h,dict(reference=ref,pointer='/0/velocity'),record_read=False)
        nav=raised.exception.evidence_navigation
        self.assertEqual(nav['available_fields'],['time_s','position'])
        self.assertEqual(read_evidence(h,nav['data_access']['queries'][0],record_read=False)['items'],value)
        self.assertEqual(h.store.remaining(),before)

    def test_candidates_are_ordered_by_events_and_diffs_record_all_factors(self):
        h=Mock();h.run_id='fixture';a={'artifact_id':'a'*64};b={'artifact_id':'b'*64}
        h.store.events.return_value=[dict(kind='candidate_constructed',outputs=[b]),dict(kind='candidate_constructed',outputs=[a])]
        self.assertEqual(ordered_candidates(h,dict(candidates={'a':a,'b':b})),[b,a])
        rows=recorded_changes(dict(length=.1,physics=dict(density=1100,viscosity=.0005)),dict(length=.2,physics=dict(density=500,viscosity=.02)))
        self.assertEqual({r['pointer'] for r in rows},{'/length','/physics/density','/physics/viscosity'})


class ReporterSourceRepairTests(unittest.TestCase):
    setUpClass=classmethod(lambda cls:reporter_fixtures.AgentReportingTests.setUpClass())
    setUp=reporter_fixtures.AgentReportingTests.setUp
    put=reporter_fixtures.AgentReportingTests.put
    physical=reporter_fixtures.AgentReportingTests.physical

    def test_catalog_critical_sample_is_accepted_and_unknown_id_has_structured_rejection(self):
        reference=self.physical();base=reporter.investigate(self.h,dict(question='Synthetic source mapping check',references=[reference]))['report_reference']
        saved=self.h.store.artifact(base);wire=reporter._wire(self.h,base,saved);payload=json.loads(wire['messages'][-1]['content'])
        card=saved['report']['results'][0];location=card['critical_observations'][0]['source']
        selected=next(k for k,v in payload['source_catalog'].items() if v==location)
        for key,expected in ((selected,'available'),('S999999','unavailable')):
            body=dict(choices=[dict(finish_reason='stop',message=dict(content=json.dumps(dict(interpretations=[dict(
                kind='new_information',text='Synthetic source validation only',source_ids=[key])]))))])
            result=reporter._finish(self.h,SimpleNamespace(last_request='offline-fixture'),wire,httpx.Response(200,json=body))
            final=self.h.store.artifact(result);self.assertEqual(final['interpretation_status'],expected)
            if expected=='unavailable':
                self.assertEqual(final['rejection_details']['invalid_source_ids'],['S999999'])
                self.assertEqual(final['rejection_details']['catalog'],payload['source_catalog'])
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],0)


if __name__=='__main__':unittest.main()
