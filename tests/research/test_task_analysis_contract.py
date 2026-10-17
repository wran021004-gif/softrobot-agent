"""Offline M1 boundaries. Synthetic linear systems are fixtures, not robot evidence."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from schemas.platform import SessionInput
from schemas.platform_analysis import (AnalysisProtocol, AnalysisResult, EndpointLinearizedModel,
    TaskAnalysisRequirement, TaskAnalysisProtocol)
from tools.platform_store import plain
from tools.state_io import digest
from tools.research.config import ROOT, resolve
from tools.research.contracts import AnalysisRequest
from tools.research import analysis
from tools.research.task_constraints import (describe_analysis_requirements, model_assessment,
    check_analysis_applicability)
from tools.research_tasks import assemble_acceptance


class TaskAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT/'runs').mkdir(exist_ok=True)
        cls.spec = resolve(ROOT/'configs/research/study.json')

    def setUp(self):
        self.cfg = deepcopy(self.spec['configuration'])
        self.ref = dict(artifact_id='a'*64)
        tendons = self.cfg['robot']['structure']['data']['tendons']
        self.binding = dict(candidate_id='synthetic-unit-test', candidate=self.ref, configuration=self.ref,
            task_identity=digest(self.cfg['task']), effective_configuration_identity=digest(self.cfg),
            evaluation_profile_identity='fixture-profile', source_identity='fixture-source',
            tension_limits_n=[t['force_limit_n'] for t in tendons], tendon_order=[t['id'] for t in tendons])
        self.req = describe_analysis_requirements(SessionInput.model_validate(self.cfg), self.binding)
        self.q = AnalysisRequest(candidate=self.ref, operation='endpoint', operating_point='controller_start_input',
            protocol=self.spec['analysis_protocol'])
        self.assessment = model_assessment(SessionInput.model_validate(self.cfg), self.req, self.q.operation)

    def applicability(self, req=None, query=None, model=None):
        return check_analysis_applicability(req or self.req, query or self.q, self.assessment, model=model)

    def fixture_model(self, offset=0.):
        """Two stable states, six bounded inputs; deliberately not a GVS robot."""
        nu = len(self.binding['tendon_order'])
        position = list(self.cfg['task']['goal']['data']['target_m']); position[0] += offset
        C, D = [[1.,0.],[0.,0.],[0.,0.]], [[0.]*nu for _ in range(3)]
        output = dict(name='tip_position', entity='tip', dimension=3, units='m', frame='world', phase='instantaneous')
        return EndpointLinearizedModel(state_definition=[dict(name='fixture_state',entity='fixture',dimension=2,
                units='m',frame='world',phase='instantaneous')],
            input_definition=[dict(name='tendon_tension',entity='fixture',dimension=nu,units='N',frame='tendon_path',phase='instantaneous')],
            output_definition=[output], x0=[0.,0.], u0=[0.]*nu, A=[[-1.,0.],[0.,-2.]],
            B=[[1.]+[0.]*(nu-1), [0.]*nu], time_domain='continuous', drift=[0.,0.], y0=position, C=C, D=D,
            binding=self.binding, operating_point=dict(name='synthetic_fixture',remaining_task_s=.35,actual_time_s=0.,
                phase='fixture_only',construction=dict(static_equilibrium=False)),
            state_scales=[1.,1.],input_scales=[1.]*nu,output_scales=[.01]*3,
            normalization_derivation='Synthetic unit-test fixture only',protocol_identity=digest(plain(self.q.protocol)),
            evidence=[self.ref],endpoint_outputs=[
                dict(name='tip_position',units='m',value0=position,C=C,D=D,scales=[.01]*3),
                dict(name='tip_velocity',units='m/s',value0=[0.]*3,C=[[0.,0.]]*3,D=D,scales=[.02]*3)])

    def compute_fixture(self, query=None, offset=0.):
        model = self.fixture_model(offset)
        envelope = dict(records=[{},dict(model=plain(model),point=model.operating_point,construction={})])
        with patch('extensions.tendon_family.math_analysis.calculate_candidate_configuration',return_value=envelope):
            return analysis.calculate(self.cfg,self.binding,query or self.q)

    def test_frozen_translation_and_distinct_holding(self):
        with patch('tools.research.config.resolve',side_effect=AssertionError('mutable source read')):
            repeat = describe_analysis_requirements(SessionInput.model_validate(self.cfg),self.binding)
        self.assertEqual(plain(repeat),plain(self.req))
        terminal, position, speed = self.req.constraints
        self.assertEqual(terminal.indices,[35]); self.assertEqual(position.indices,list(range(30,36)))
        self.assertEqual(speed.indices,position.indices)
        self.assertEqual([terminal.radius,position.radius,speed.radius],[.01,.01,.02])
        self.assertEqual(self.req.physical_inputs['lower'],[0.]*6)
        self.assertEqual(self.req.physical_inputs['upper'],self.binding['tension_limits_n'])
        changed = deepcopy(self.cfg)
        changed['policy']['controller']['parameters']['data']['settling']['position_limit_m'] = .007
        requirements = describe_analysis_requirements(SessionInput.model_validate(changed),self.binding)
        self.assertEqual(requirements.constraints[1].radius,.007)
        self.assertEqual(requirements.constraints[0].radius,.01)

    def test_time_varying_reference_and_intervals_are_descriptions_only(self):
        payload = plain(self.req); c = payload['constraints'][0]
        c.update(indices=[1,2,3],reference=[[.1,0.,0.],[.2,.1,0.],[.3,0.,.1]])
        payload['constraints'] = [c]
        varying = TaskAnalysisRequirement.model_validate(payload)
        self.assertNotEqual(varying.constraints[0].reference[0],varying.constraints[0].reference[-1])
        self.assertEqual(self.applicability(varying)['status'],'not_applicable')
        c.update(kind='component_interval',radius=None,lower=[-.01]*3,upper=[.01]*3)
        interval = TaskAnalysisRequirement.model_validate(payload)
        self.assertTrue(self.applicability(interval)['constraint_coverage'][0]['expressible'])
        self.assertEqual(self.applicability(interval)['status'],'not_applicable')

    def test_invalid_indices_grids_and_bounds(self):
        for indices in ([36],[-1],[35,35],[True],[1.5]):
            payload = plain(self.req); payload['constraints'][0]['indices'] = indices
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                TaskAnalysisRequirement.model_validate(payload)
        payload = plain(self.req); payload['time_grid_s'][30] += .001
        with self.assertRaises(ValueError): TaskAnalysisRequirement.model_validate(payload)
        payload = plain(self.req); payload['constraints'][0]['reference'][0][0] = float('nan')
        with self.assertRaises(ValueError): TaskAnalysisRequirement.model_validate(payload)
        changed = deepcopy(self.cfg); changed['task']['timing']['sample_period_s'] = .03
        with self.assertRaises(ValueError): describe_analysis_requirements(SessionInput.model_validate(changed),self.binding)

    def test_signal_semantics_and_unsupported_requirements(self):
        for key,value in [('name','contact_force'),('units','mm'),('frame','robot_base'),('phase','pre_step')]:
            payload = plain(self.req); payload['constraints'] = payload['constraints'][:1]
            payload['constraints'][0]['signal'][key] = value
            self.assertEqual(self.applicability(TaskAnalysisRequirement.model_validate(payload))['status'],'not_applicable')
        payload = plain(self.req); payload['constraints'] = payload['constraints'][:1]
        payload['constraints'][0].update(kind='unsupported',radius=None,unsupported_requirement=dict(
            kind='nonconvex_obstacle_avoidance',obstacle='synthetic_fixture'))
        req = TaskAnalysisRequirement.model_validate(payload)
        self.assertEqual(self.applicability(req)['status'],'not_applicable')
        self.assertEqual(req.constraints[0].unsupported_requirement['obstacle'],'synthetic_fixture')

    def test_model_physics_prevents_computation(self):
        changed = deepcopy(self.cfg)
        changed['task']['environment']['data']['external_forces'] = [dict(entity='tip',force_n=[1.,0.,0.],start_s=0.,end_s=.35)]
        with patch('extensions.tendon_family.math_analysis.calculate_candidate_configuration') as calculate:
            out = analysis.calculate(changed,self.binding,self.q)
            calculate.assert_not_called()
        self.assertEqual(out['scoped_claim']['conclusion'],'not_applicable')
        self.assertIn('external',str(out['analysis_applicability']['reasons']))
        req = self.req.model_copy(update=dict(required_physics=['contact_response']))
        assessed = model_assessment(SessionInput.model_validate(self.cfg),req,self.q.operation)
        self.assertEqual(check_analysis_applicability(req,self.q,assessed)['status'],'not_applicable')
        req = self.req.model_copy(update=dict(required_physics=['unknown_disturbance_physics']))
        assessed = model_assessment(SessionInput.model_validate(self.cfg),req,self.q.operation)
        self.assertEqual(check_analysis_applicability(req,self.q,assessed)['status'],'not_applicable')

    def test_actual_outputs_inputs_and_saved_horizon(self):
        model = self.fixture_model()
        bad = model.model_copy(update=dict(binding={**model.binding,'tendon_order':list(reversed(model.binding['tendon_order']))}))
        self.assertEqual(self.applicability(model=bad)['status'],'not_applicable')
        bad = model.model_copy(update=dict(operating_point={**model.operating_point,'remaining_task_s':.015}))
        self.assertEqual(self.applicability(model=bad)['status'],'not_applicable')
        bad = model.model_copy(update=dict(endpoint_outputs=[o.model_copy(update=dict(frame='robot_base')) for o in model.endpoint_outputs]))
        self.assertEqual(self.applicability(model=bad)['status'],'not_applicable')
        saved = model.model_copy(update=dict(operating_point={**model.operating_point,'actual_time_s':.3,'remaining_task_s':.05}))
        self.assertEqual(self.applicability(model=saved)['horizon']['analysis_horizon_s'],.05)

    def test_actual_kernel_witness_certificate_and_gramian_strength(self):
        feasible = self.compute_fixture()
        self.assertEqual(feasible['scoped_claim']['conclusion'],'feasible_witness')
        self.assertTrue(all(feasible['endpoint']['checks'].values()))
        impossible = self.compute_fixture(offset=100.)
        self.assertEqual(impossible['scoped_claim']['conclusion'],'model_infeasibility_certificate')
        self.assertGreater(impossible['endpoint']['infeasibility_certificate']['separating_direction']['margin_over_limit'],0.)
        q = self.q.model_copy(update=dict(operation='controllability',scoring_window_s=.35))
        diagnostic = self.compute_fixture(q)
        self.assertEqual(diagnostic['scoped_claim']['conclusion'],'diagnostic')
        self.assertEqual(diagnostic['task_acceptance'],'unmeasured')
        claim = feasible['scoped_claim']
        self.assertEqual(claim['model_identity'],digest(feasible['model']))
        self.assertEqual(claim['protocol_identity'],digest(plain(self.q.protocol)))
        for key in ('candidate','configuration','evaluation_profile_identity','source_identity','task_identity'):
            self.assertEqual(claim['binding'][key],self.req.binding[key])
        self.assertFalse(feasible['analysis_applicability']['full_task_supported'])
        braking = self.compute_fixture(self.q.model_copy(update=dict(operation='braking')))
        self.assertEqual(braking['scoped_claim']['constraint_coverage'][2]['analyzed_indices'],[35])

    def test_failed_missing_and_unverified_results_stay_inconclusive(self):
        for result in (dict(status='execution_incomplete'),dict(status='unavailable'),
                dict(status='computed',endpoint=dict(status='undetermined',solver=dict(success=False))),
                dict(status='computed',endpoint=dict(status='infeasible_in_local_model',infeasibility_certificate=dict(certified_infeasible=True)))):
            out = analysis.scoped_result(result,self.req,self.applicability(),self.q)
            self.assertEqual(out['scoped_claim']['conclusion'],'inconclusive')
        raw = dict(records=[{},dict(name='target_equilibrium',reason='Fixture failed construction',construction={})])
        with patch('extensions.tendon_family.math_analysis.calculate_candidate_configuration',return_value=raw):
            out = analysis.calculate(self.cfg,self.binding,self.q)
        self.assertEqual(out['scoped_claim']['conclusion'],'inconclusive')

    def test_real_gvs_initial_linearization_is_diagnostic(self):
        from extensions.tendon_family.gvs_basis import resolve_basis
        basis = self.cfg['policy']['controller']['parameters']['data']['recipe']['basis']
        binding = {**self.binding,'basis':basis,'coordinate_order':list(resolve_basis(
            self.cfg['robot']['structure']['data'],basis).coordinate_order)}
        q = self.q.model_copy(update=dict(operation='controllability',scoring_window_s=.35))
        out = analysis.calculate(self.cfg,binding,q)
        self.assertEqual(out['scoped_claim']['conclusion'],'diagnostic')
        self.assertEqual(out['model']['binding']['tendon_order'],self.req.physical_inputs['tendon_order'])
        self.assertEqual(out['task_acceptance'],'unmeasured')

    def test_new_worker_failure_is_scoped_and_charged_once(self):
        from test_mainline import MainlineTests
        from types import SimpleNamespace
        from tools.research.state import update, state
        case = MainlineTests(); case.setUp(); self.addCleanup(case.tearDown)
        update(case.host,freeze='synthetic-fixture',mathematical_evaluations=0)
        query = AnalysisRequest.model_validate({**plain(self.q),'candidate':case.candidate})
        with patch('tools.service_execution._run_contained',return_value=SimpleNamespace(returncode=1)) as worker:
            first = analysis.dispatch(case.host,query,'m1-failed-fixture',guard=lambda *args:None)
            reused = analysis.dispatch(case.host,query,'m1-failed-fixture',guard=lambda *args:None)
        self.assertEqual(worker.call_count,1)
        self.assertEqual(first['reference'],reused['reference'])
        self.assertEqual(first['scoped_claim']['conclusion'],'inconclusive')
        self.assertEqual(first['scoped_claim']['binding']['evaluation_profile_identity'],'fixture')
        self.assertEqual(state(case.host)['mathematical_evaluations'],1)
        self.assertEqual(state(case.host)['numerical_reserved_s'],0.)

    def test_old_contracts_and_acceptance_unchanged(self):
        old = dict(kind='fixture',protocol=self.ref,bindings=[],records=[],evidence=[],limitations=[])
        self.assertEqual(AnalysisResult.model_validate(old).analysis_version,'1.0.0')
        v2 = TaskAnalysisProtocol.model_validate(self.spec['analysis_protocol'])
        v1 = {k:v for k,v in plain(v2).items() if k in AnalysisProtocol.model_fields}; v1['protocol_id']='reach-local-v1'
        self.assertEqual(AnalysisProtocol.model_validate(v1).protocol_id,'reach-local-v1')
        ev = dict(validity='valid',task_success=True,metrics=[dict(name='position_error',value=.005,units='m')],
            constraints=[dict(name='task_bound',satisfied=True,observed=.005,limit=.01,units='m')],source=self.ref,
            evaluator='evaluate.reach',comparison_identity='fixture')
        settling = self.cfg['policy']['controller']['parameters']['data']['settling']
        profile = dict(complete=True,solver_error_count=0,force_bound_violation_n=0.,sampled_settling=dict(
            **settling,available=True,max_error_m=.005,max_speed_m_s=.01,passed=True))
        accepted = assemble_acceptance(self.cfg,ev,profile)
        self.assertTrue(accepted['accepted'])
        profile['sampled_settling'].update(max_speed_m_s=.03,passed=False)
        self.assertFalse(assemble_acceptance(self.cfg,ev,profile)['accepted'])


class KKTQualification(unittest.TestCase):
    def test_recovery_replay_cannot_validate_another_raw_iterates_multipliers(self):
        from tools.research.analysis import kkt_reliability
        raw=dict(primal_inf=0.,stationarity_inf=0.,dual_violation=0.,complementarity_inf=0.,same_as_selected_trajectory=False)
        q=kkt_reliability(raw,dict(activity_diagnostics=[dict(numerical_LICQ=True)],
            second_order_sufficiency='independently_verified'),dict(passed=True))
        self.assertFalse(q['regular_local_branch_verified'])
        self.assertIn('replay_iterate_correspondence',q['obstructions'])

    def test_missing_regularity_cannot_become_an_envelope_gradient(self):
        from tools.research.analysis import kkt_reliability,complete_lagrangian_sensitivity
        residuals=dict(primal_inf=0.,stationarity_inf=.01,dual_violation=0.,complementarity_inf=0.)
        q=kkt_reliability(residuals,dict(activity_diagnostics=[dict(numerical_LICQ=True)]),dict(passed=True))
        self.assertEqual(q['reliability'],'solver_unresolved')
        self.assertFalse(q['envelope_gradient_available'])
        with self.assertRaisesRegex(ValueError,'WITHOUT_REGULAR_BASE'):
            complete_lagrangian_sensitivity({}, {}, .001,variable='segments.0.length_m',qualification=q)

    def test_complete_lagrangian_includes_initial_dynamics_and_bounds(self):
        from tools.research.analysis import complete_lagrangian_sensitivity
        # Algebra fixture only. In a real call each value comes from a rebuilt model.
        terms=dict(objective=1.,initial_state=2.,complete_dynamics=3.,task=4.,lower_bounds=5.,upper_bounds=6.)
        minus=dict(lagrangian_terms={k:0. for k in terms});plus=dict(lagrangian_terms=terms)
        result=complete_lagrangian_sensitivity(minus,plus,.5,variable='segments.0.length_m',
            qualification=dict(regular_local_branch_verified=True))
        self.assertEqual(result['derivative_per_m'],21.)
        self.assertEqual(result['descent_certificate'],'unavailable')


if __name__ == '__main__': unittest.main()
