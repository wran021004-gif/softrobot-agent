"""Bounded native fixtures and real Store opt-in; no Provider requests."""
from copy import deepcopy
import json
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pydantic import ValidationError
from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.state_io import digest
from tools.research.contracts import MechanismStudy,PhysicalReplayRequest
from extensions.tendon_family.passive_execution import execute_pair,baseline_arm
from extensions.reference.passive_evaluation_v2 import inspect,metrics,diagnostic_metrics
from tests.research.test_passive_program_v2 import configuration_v2,prepared_host_v2
from tests.research.test_p3_study_readiness import fixture_directory,small_task,fixture


def question(**extra):
    return MechanismStudy(operation='inspect',target=dict(quantity='finite_time_task_violation',goal='decrease'),
        point_semantics='frozen_task_initial_state',effect_semantics='finite_time_task_response',
        max_evaluations=1,passive_ablation=['tendon_0'],**extra)


class SparseNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=configuration_v2();cls.cfg['task']['goal']['data']['route_check']='every_physics_step'
        cls.inp=SessionInput.model_validate(cls.cfg);cls.elapsed={};cls.raw={}
        for level in ('full','screening'):
            with fixture_directory() as directory:
                start=time.perf_counter()
                cls.raw[level]=execute_pair(cls.inp,directory,['tendon_0'],execution_checks=level).data.data
                cls.elapsed[level]=time.perf_counter()-start

    def test_sparse_routes_preserve_all_physics_and_dense_qualification(self):
        full=self.raw['full'];screen=self.raw['screening']
        self.assertEqual(full['status'],'completed',full.get('reason'))
        self.assertEqual(screen['status'],'completed',screen.get('reason'))
        self.assertEqual(full['cost']['physics_steps'],screen['cost']['physics_steps'])
        self.assertEqual(full['physical_binding'],screen['physical_binding'])
        self.assertEqual([r['sha256'] for r in full['trace_files']],[r['sha256'] for r in screen['trace_files']])
        for a,b in ((baseline_arm(full),baseline_arm(screen)),
                (full['paired_ablation']['ablation'],screen['paired_ablation']['ablation'])):
            for original,sampled in zip(a['episodes'],b['episodes']):
                f=deepcopy(original);s=deepcopy(sampled)
                fr=f.pop('route_geometry');sr=s.pop('route_geometry')
                self.assertEqual(f,s)
                self.assertEqual(fr['checked_poses'],1+round(self.inp.task.timing.duration_s/self.inp.task.timing.timestep_s))
                self.assertEqual(sr['checked_poses'],1+round(self.inp.task.timing.duration_s/self.inp.task.timing.sample_period_s))
                self.assertEqual(sr['sampling'],'score_grid')
        self.assertNotIn('execution_checks',full)
        policy=deepcopy(screen['execution_checks']);identity=policy.pop('identity')
        self.assertEqual(digest(policy),identity)
        self.assertEqual(diagnostic_metrics(self.inp.task,full),diagnostic_metrics(self.inp.task,screen))
        print(json.dumps(dict(scope='Bounded fixture, not P3 scientific evidence',elapsed_s=self.elapsed,
            full_route_checks=full['cost']['route_segment_body_checks'],screening_route_checks=screen['cost']['route_segment_body_checks'])))

    def test_screening_cannot_pass_original_evaluator_even_with_forged_passing_label(self):
        task=small_task();raw=fixture(task)
        self.assertEqual(inspect(task,raw),('valid',None))
        raw['execution_checks']=dict(version='sparse_route_screening_v1',level='screening')
        self.assertEqual(inspect(task,raw),('incomplete','SCREENING_REQUIRES_ORIGINAL_FULL_VALIDATION'))
        self.assertIsNone(metrics(task,raw)['task_success'])
        raw.pop('execution_checks')
        raw['episodes'][0]['route_geometry'].update(sampling='score_grid',checked_poses=21)
        self.assertEqual(inspect(task,raw),('incomplete','ROUTE_POSE_COVERAGE_MISSING'))
        with self.assertRaises(ValidationError):
            PhysicalReplayRequest(candidate=dict(artifact_id='f'*64),execution_checks='screening')

    def test_research_kernel_returns_screening_diagnostics_without_formal_objective(self):
        from tools.research.structure_research import calculate
        q=SimpleNamespace(mechanism_study=question(execution_checks='screening'),candidate=dict(artifact_id='a'*64),
            operating_point='standardized_initial_pretension',protocol=SimpleNamespace(model_dump=lambda **kw:{}))
        # A native saved fixture supplies execution only; the actual research
        # kernel owns observation extraction, qualification and result scopes.
        context=dict(selected_parameters=[],space={},parameters={},evaluations=1,comparisons=[],
            execution_checks=dict(level='screening',version='sparse_route_screening_v1'))
        with patch('extensions.tendon_family.passive_execution.execute_pair',return_value=SimpleNamespace(data=SimpleNamespace(data=deepcopy(self.raw['screening'])))):
            result=calculate(self.cfg,{},q,dict(actual_time_s=0.),context)
        self.assertEqual(result['status'],'computed',result.get('reason'))
        r=result['structure_research'];observation=r['records'][0]['observation']
        self.assertEqual(r['execution_checks']['level'],'screening')
        self.assertIsNone(observation['value'])
        self.assertFalse(observation['task_gap']['valid_complete'])
        self.assertIsNone(r['best_valid_record_index'])
        self.assertEqual(observation['diagnostic_task_gap']['status'],'complete')
        from tools.research.analysis import scoped_result
        from tools.research.task_constraints import describe_analysis_requirements
        requirements=describe_analysis_requirements(self.cfg,dict(candidate=q.candidate))
        applicability=dict(status='diagnostic',model_assessment=dict(model_id='fixture',model_version='1',
            representation_id='fixture',relevant_assumptions=[]),horizon={},constraint_coverage=[])
        scoped=scoped_result(result,requirements,applicability,q)
        self.assertEqual(scoped['scoped_claim']['verification_status'],'sparse_route_screening_diagnostic')
        self.assertEqual(scoped['scoped_claim']['conclusion'],'diagnostic')
        self.assertFalse(scoped['analysis_applicability']['full_task_supported'])
        self.assertIn('full physics-step route coverage',scoped['diagnostic_layers']['dynamic_validation']['missing_checks'])


class SparseContractTests(unittest.TestCase):
    def test_legacy_default_and_unsupported_method(self):
        self.assertNotIn('execution_checks',plain(question()))
        value=plain(question(execution_checks='screening'));self.assertEqual(value['execution_checks'],'screening')
        value['operation']='interact';value['parameter_paths']=['a','b']
        with self.assertRaisesRegex(ValidationError,'SCREENING_CHECKS_REQUIRE'):MechanismStudy.model_validate(value)

    def test_exact_opt_in_preserves_full_task_and_all_costs_and_is_idempotent(self):
        from tools.research.state import state
        from tools.research.budget import authorize_sparse_research_checks
        h,_=prepared_host_v2();before=h.store.remaining();old=deepcopy(state(h)['spec'])
        scope=dict(study_id=h.run_id,resolved_identity=old['resolved_identity'],execution_policy=dict(version='sparse_route_screening_v1'))
        approval=dict(version='sparse_research_checks_approval_v1',approved=True,source='Explicit offline fixture only',scope=scope,scope_identity=digest(scope))
        bad=deepcopy(approval);bad['scope']['resolved_identity']='wrong';bad['scope_identity']=digest(bad['scope'])
        with self.assertRaisesRegex(ValueError,'EXACT_USER_APPROVED'):authorize_sparse_research_checks(h,bad)
        self.assertEqual(h.store.remaining(),before)
        result=authorize_sparse_research_checks(h,approval);new=state(h)['spec']
        self.assertEqual(new['canonical_task'],old['canonical_task'])
        self.assertEqual(new['configuration'],old['configuration'])
        self.assertEqual(new['budgets'],old['budgets'])
        self.assertEqual(h.store.remaining(),before)
        self.assertTrue(state(h)['validation_extension_pending_binding'])
        self.assertEqual(result['provider_requests_sent'],0)
        self.assertTrue(authorize_sparse_research_checks(h,approval)['already_applied'])

    def test_schema_admission_and_scientific_compiler_retain_explicit_level(self):
        from tools.research.state import state,update
        from tools.research.scientific_intent import question_schema,compile_dynamic
        from tools.research.structure_research import prepare_context
        from tools.research.design import verify_candidate
        cfg=configuration_v2();cfg['task']['goal']['data']['route_check']='every_physics_step'
        with patch('tests.research.test_passive_program_v2.configuration_v2',return_value=cfg):h,ref=prepared_host_v2()
        s=state(h);c=verify_candidate(h,ref);spec=deepcopy(s['spec']);spec['research_decisions']['analysis_interface']='scientific_question_v4'
        schema=question_schema(spec,c)
        self.assertNotIn('execution_checks',schema['$defs']['ScientificStructureV4']['properties'])
        with self.assertRaisesRegex(ValueError,'FROZEN_SPARSE'):prepare_context(spec,c,question(execution_checks='screening'),[])
        spec['research_execution_checks']=dict(version='sparse_route_screening_v1');update(h,spec=spec)
        self.assertIn('execution_checks',question_schema(spec,c)['$defs']['ScientificStructureV4']['properties'])
        context=prepare_context(spec,c,question(execution_checks='screening'),[])
        self.assertEqual(context['execution_checks']['level'],'screening')
        from tools.research.contracts import ScientificStructureV4
        q=ScientificStructureV4(operation='inspect',effect_semantics='finite_time_task_response',
            target='finite_time_task_violation',operating_point='frozen_task_initial_state',
            control_treatment='no_active_control',physical_problem='passive_unilateral_equilibrium',
            passive_ablation=['tendon_0'],execution_checks='screening')
        intent=dict(candidate=ref,agent_hypothesis=dict(decision={}))
        with patch('tools.research.task_constraints.mathematical_method_view',return_value=dict(methods={'mechanism_structure_v1':dict(planning_status='admissible')})),patch(
                'tools.research.agent.bind_selected_analysis_request',side_effect=lambda host,payload,**kw:payload):
            compiled=compile_dynamic(h,q,{},intent,tool_use_id='offline-sparse-compile')
        self.assertEqual(compiled['status'],'ready',compiled)
        self.assertEqual(compiled['request']['mechanism_study']['execution_checks'],'screening')


if __name__=='__main__':unittest.main()
