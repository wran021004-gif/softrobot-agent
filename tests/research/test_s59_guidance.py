"""Offline fixtures only: no provider, MATLAB solve or physics stepping."""
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import numpy as np
from extensions.math_analysis.kernels import instantaneous_braking
from tools.research import core, analysis
from tools.research.budget import backend_capacity, require_guidance
from tools.research.config import ROOT, resolve
from tools.research.contracts import AnalysisRequest
from tools.research.holding_diagnostic import diagnose, snapshot_audit
from tools.research.state import state, update, save
from tools.state_io import read
from tests.research import test_agent_feedback as feedback_fixtures
from tests.research import test_task_analysis_contract as task_fixtures


class BrakingKernelTests(unittest.TestCase):
    def model(self):
        # Fixture: y=q^2, v=2*q*w, wdot=-3*w+2*u, q=2,w=3,u=1.
        # Cv=[2*w,2*q] so its first term contributes the essential 2*w^2.
        return NS(time_domain='continuous',u0=[1.],drift=[3.,-7.],B=[[0.],[2.]],
            binding=dict(tension_limits_n=[8.]),
            input_definition=[NS(name='tendon_tension',units='N',frame='tendon_path')],
            endpoint_outputs=[NS(name='tip_velocity',frame='world',units='m/s',
                value0=[12.,0.,0.],C=[[6.,4.],[0.,0.],[0.,0.]],D=[[0.],[0.],[0.]])])

    def test_absolute_input_intercept_keeps_passive_and_jdot(self):
        r=instantaneous_braking(self.model())
        self.assertEqual(r['current_acceleration_m_s2'],[-10.,0.,0.])
        self.assertEqual(r['passive_acceleration_m_s2'],[-18.,0.,0.])
        self.assertEqual(r['optimal_tension_n'],[0.])
        self.assertEqual(r['minimum_v_dot_a_m2_s3'],-216.)
        self.assertTrue(r['locally_decelerating_direction'])
        # Independent derivative of 2*q*w along the nonlinear flow.
        h=1e-6;q=2.;w=3.;wdot=-7.
        fd=(2*(q+h*w)*(w+h*wdot)-2*(q-h*w)*(w-h*wdot))/(2*h)
        self.assertAlmostEqual(fd,r['current_acceleration_m_s2'][0],places=7)
        self.assertNotEqual(fd,4*wdot)  # Omitting Jdot fails this fixture.

    def test_componentwise_box_minimum_and_sign(self):
        model=self.model();model.endpoint_outputs[0].value0=[-12.,0.,0.]
        r=instantaneous_braking(model)
        self.assertEqual(r['optimal_tension_n'],[8.])
        self.assertLessEqual(r['minimum_v_dot_a_m2_s3'],r['current_v_dot_a_m2_s3'])

    def test_near_zero_has_no_first_order_discrimination(self):
        m=self.model();m.endpoint_outputs[0].value0=[0.,0.,0.]
        r=instantaneous_braking(m)
        self.assertIsNone(r['locally_decelerating_direction'])
        self.assertTrue(r['near_zero_velocity'])
        self.assertIsNone(r['regional_error_bound'])

    def test_units_frame_and_bounds_rejected(self):
        for field,value in [('frame','local'),('units','mm/s')]:
            m=self.model();setattr(m.endpoint_outputs[0],field,value)
            with self.assertRaises(ValueError):instantaneous_braking(m)
        m=self.model();m.u0=[8.01]
        with self.assertRaises(ValueError):instantaneous_braking(m)

    def test_instantaneous_is_separate_from_finite_horizon_contract(self):
        p=resolve(ROOT/'configs/research/study_sorosim_s59_agent.json')['analysis_protocol']
        ref=dict(artifact_id='a'*64)
        with self.assertRaises(ValueError):AnalysisRequest(candidate=ref,operation='instantaneous_braking_v1',protocol=p)
        q=AnalysisRequest(candidate=ref,operation='instantaneous_braking_v1',protocol=p,operating_point='saved_state',saved_state=ref)
        self.assertEqual(q.operation,'instantaneous_braking_v1')
        self.assertEqual(AnalysisRequest(candidate=ref,operation='braking',protocol=p).operation,'braking')


class GuidanceIntegrationTests(unittest.TestCase):
    setUp=feedback_fixtures.AgentFeedbackTests.setUp
    cleanup=feedback_fixtures.AgentFeedbackTests.cleanup
    plan=feedback_fixtures.AgentFeedbackTests.plan
    generate=feedback_fixtures.AgentFeedbackTests.generate
    result=feedback_fixtures.AgentFeedbackTests.result

    def test_history_and_math_must_be_actually_read(self):
        s=state(self.host);s['spec']['require_task_guidance']=True
        h=save(self.host,dict(history='fixture'));m=save(self.host,dict(math='fixture'))
        update(self.host,spec=s['spec'],holding_diagnostic_reference=h,task_math_references=[m])
        with self.assertRaisesRegex(ValueError,'FIRST_EXPERIMENT'):require_guidance(self.host,'falsifiable fixture')
        core.read_evidence(self.host,dict(reference=h))
        core.read_evidence(self.host,dict(reference=m))
        require_guidance(self.host,'falsifiable fixture')
        with self.assertRaisesRegex(ValueError,'FIRST_EXPERIMENT'):require_guidance(self.host,' ')

    def test_shared_backend_capacity_protects_evaluation(self):
        remaining=self.host.store.remaining()['remaining']['backend_solves']
        update(self.host,rl_runs={'fixture':dict(evaluation_reserved=True)})
        self.assertEqual(backend_capacity(self.host),remaining-1)
        self.assertEqual(backend_capacity(self.host,evaluation_run='fixture'),remaining)

    def test_failed_atomic_reservation_does_not_consume_stage(self):
        from tools.platform_store import zero
        before=self.host.store.remaining()['used']
        def charge(db):
            s=self.host.store.session(self.host.run_id,db)['state'];s['fixture_charge']=True
            self.host.store.update_state(db,self.host.run_id,s)
            raise ValueError('fixture evaluation capacity unavailable')
        with self.assertRaises(ValueError):
            self.host.store.reserve(self.host.run_id,'fixture-atomic','x',self.host.actor,{**zero(),'backend_solves':1},guard=charge)
        self.assertNotIn('fixture_charge',state(self.host))
        self.assertEqual(before,self.host.store.remaining()['used'])

    def test_evaluation_slot_transfer_and_episode_ceiling(self):
        from tools.research.budget import reserve_evaluation
        s=state(self.host);s['spec']['reserve_rl_evaluation']=True
        s['spec']['rl_limits']['evaluation_episodes']=1
        update(self.host,spec=s['spec'],rl_runs={'fixture':dict(evaluations=0,evaluation_reserved=True)})
        with self.host.store.transaction() as db:
            current=self.host.store.session(self.host.run_id,db)['state']
            with patch('tools.research.budget.backend_capacity',return_value=2), self.assertRaisesRegex(ValueError,'EVALUATION_CAPACITY'):
                reserve_evaluation(self.host,current,db,training=True)
            reserve_evaluation(self.host,current,db,evaluation_run='fixture')
            self.assertFalse(current['rl_runs']['fixture']['evaluation_reserved'])

    def test_exact_saved_state_cannot_move_between_candidates(self):
        candidate=self.generate();other=self.generate(dict(version='serial_family_generation_v2',
            family_space_identity=self.spec['family_space_identity'],segment_count=2,tendon_count=4,
            control_weights=dict(holding_tip_speed_weight=.3)))
        q=dict(candidate=other,operation='instantaneous_braking_v1',operating_point='saved_state',protocol=self.spec['analysis_protocol'],
            saved_state=save(self.host,dict(candidate=candidate,configuration_identity='wrong')))
        with patch.object(analysis,'guard',create=True):
            with self.assertRaisesRegex(ValueError,'EXACT_SAVED_STATE_CANDIDATE_MISMATCH'):
                analysis.dispatch(self.host,q,'fixture-candidate-mismatch',guard=lambda *a:None)
        self.assertEqual(state(self.host)['mathematical_evaluations'],0)

    def test_frozen_s59_limits_and_original_acceptance(self):
        spec=resolve(ROOT/'configs/research/study_sorosim_s59_agent.json')
        self.assertEqual(spec['budgets']['provider_requests'],48)
        self.assertEqual(spec['budgets']['protected_provider_requests'],6)
        self.assertEqual(spec['budgets']['public_operations'],120)
        self.assertEqual(spec['budgets']['physical_launches'],8)
        self.assertEqual(spec['nmpc_limits']['executions'],8)
        self.assertTrue(spec['reserve_rl_evaluation'])
        self.assertEqual(spec['rl_limits']['training_actions'],131072)
        self.assertEqual(spec['confirmation']['fresh_independent_repetitions'],0)
        self.assertEqual(spec['configuration']['task']['timing']['timestep_s'],.0005)

    def test_engineering_analysis_public_call_charged_once_even_on_worker_failure(self):
        candidate=self.generate()
        before=self.host.store.remaining()['used']['tool_calls']
        q=dict(candidate=candidate,operation='endpoint',operating_point='controller_start_input',protocol=self.spec['analysis_protocol'])
        with patch('tools.service_execution._run_contained',return_value=NS(returncode=1)) as worker:
            first=analysis.dispatch(self.host,q,'fixture-engineering-public',guard=lambda *a:None,origin='engineering_preflight')
            second=analysis.dispatch(self.host,q,'fixture-engineering-public',guard=lambda *a:None,origin='engineering_preflight')
        self.assertEqual(worker.call_count,1)
        self.assertEqual(first['reference'],second['reference'])
        self.assertEqual(self.host.store.remaining()['used']['tool_calls']-before,1)
        self.assertEqual(state(self.host)['mathematical_evaluations'],1)


class HoldingHistoryTests(unittest.TestCase):
    def test_simultaneous_peak_state_and_signed_reversal(self):
        rows=[dict(time_s=t,position_m=[p,0,0],velocity_m_s=[v,0,0],actual_tension_n=[u]*4)
            for t,p,v,u in [(.25,0.,1.,1),(.30,.01,-2.,2),(.35,.005,-1.,3)]]
        result=diagnose(rows,[0.,0.,0.])
        self.assertEqual(result['holding_peak']['time_s'],.30)
        self.assertEqual(result['holding_peak']['actual_tension_n'],[2]*4)
        self.assertEqual(result['late_vector_reversal_times_s'],[.30])
        self.assertFalse(result['full_physics_step_coverage'])

    def test_partial_snapshot_stops_without_prefix_or_steps(self):
        source=read(ROOT/'evidence/sorosim_s59/historical_diagnostic.json')['results'][0]
        # Only XML compilation and dimension checks; mj_step is forbidden here.
        with patch('mujoco.mj_step',side_effect=AssertionError('no hidden stepping')):
            audit=snapshot_audit(source)
        self.assertEqual(audit['status'],'not_restorable')
        self.assertIn('qacc_warmstart',audit['missing_integration_fields'])
        self.assertTrue(audit['complete_qpos_qvel_dimensions'])
        self.assertEqual(audit['attempted_physics_steps'],0)
        self.assertEqual(audit['prefix_replay_steps'],0)


class InstantaneousApplicabilityTests(unittest.TestCase):
    setUpClass=classmethod(task_fixtures.TaskAnalysisTests.setUpClass.__func__)
    setUp=task_fixtures.TaskAnalysisTests.setUp
    applicability=task_fixtures.TaskAnalysisTests.applicability

    def test_diagnostic_never_covers_original_task_samples(self):
        q=self.q.model_copy(update=dict(operation='instantaneous_braking_v1'))
        app=self.applicability(query=q)
        self.assertEqual(app['status'],'applicable')
        self.assertFalse(app['full_task_supported'])
        self.assertTrue(all(c['status']=='diagnostic' and not c['analyzed_indices'] for c in app['constraint_coverage']))
        self.assertEqual(app['horizon']['analysis_horizon_s'],0.)


if __name__=='__main__':unittest.main()
