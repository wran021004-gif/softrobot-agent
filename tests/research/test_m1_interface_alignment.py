"""Offline alignment regressions; synthetic evidence never establishes science."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator
from tools.research import core
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
from tools.research.scientific_intent import (compile_question,selected_question_schema,
    conic_entry,method_alignment)
from tools.research.object_choices import main_tool_schema,expand_references,reference_choices
from tools.research.provider import provider_schema
from tools.research.state import state,update,save
from tools.research.physical_replay import seed_control
from tools.research.contracts import ControlSeedRequest
from tools.research.rl import import_mathematical_reference
from tools.research.config import ROOT
from tests.research import test_m1_native_search_scope as fixtures
from tests.research.test_p63a_math_interface import generate
from tests.research.test_p63g3_action_handoff import diagnosis
from tests.research.test_research_authorization_preflight import approve

SPEC=ROOT/'configs/research/study_m1_low_tendon_speed004_v1.json'


class AlignmentTests(unittest.TestCase):
    def setUp(self):
        self.patch=patch.object(fixtures,'SPEC',SPEC);self.patch.start();self.addCleanup(self.patch.stop)
        self.cm=fixtures.scoped_fixture();self.h=self.cm.__enter__()
        self.addCleanup(self.cm.__exit__,None,None,None)
        approve(self.h,[REGISTERED_MATHEMATICS_SCOPE]);self.c=generate(self.h)
        with patch.object(core,'guard'):
            core.dispatch(self.h,diagnosis(self.c,'mechanism_research'),'alignment-diagnose')

    def question(self):
        return dict(version='scientific_question_v4',domain='structure',structure=dict(
            operation='inspect',effect_semantics='mechanism_effect',
            target=dict(quantity='joint_damping',reduction='norm'),
            operating_point='frozen_task_initial_state',requested_budget=1))

    def test_domain_handoff_loads_actual_diagnose_schema_before_plan(self):
        from tools.research import agent
        directory=[dict(tool='research_plan',actions=['initialize_control','diagnose'])]
        update(self.h,pilot={**state(self.h)['pilot'],'tool_directory':directory})
        for current,domain,chosen in (('mechanism_research','control','control_feasibility'),
                                     ('control_feasibility','structure','mechanism_research')):
            with self.subTest(domain=domain):
                with patch.object(core,'guard'):
                    core.dispatch(self.h,diagnosis(self.c,current),'fixture-choice-'+domain)
                agent.select_tool_route(self.h,dict(tool='research_plan',action='initialize_control'),'fixture-init-'+domain)
                registry={k:SimpleNamespace(tool_spec={}) for k in ('research_route','research_plan')}
                loaded=agent.load_selected_tool_schema(self.h,registry,directory)
                self.assertEqual(loaded['plan_action'],'initialize_control')
                ledger=self.h.store.remaining()
                before=deepcopy(state(self.h))
                out=compile_question(self.h,dict(version='scientific_question_v4',domain=domain,
                    **{domain:{}}),tool_use_id='fixture-mismatch-'+domain)
                self.assertEqual(out['reason'],'DIAGNOSE_DOMAIN_MISMATCH')
                self.assertFalse(out['scientific_execution_started'])
                self.assertEqual(state(self.h),before)
                self.assertEqual(out['next']['tool'],'research_route')
                agent.select_tool_route(self.h,out['next']['input'],'fixture-load-diagnose-'+domain)
                loaded=agent.load_selected_tool_schema(self.h,registry,directory)
                self.assertEqual(loaded['plan_action'],'diagnose')
                self.assertEqual(out['then']['next_research_action'],chosen)
                schema=registry['research_plan'].tool_spec['inputSchema']['json']
                self.assertIn('next_research_action',schema['properties'])
                Draft202012Validator(schema).validate(diagnosis(self.c,chosen))
                self.assertEqual(self.h.store.remaining(),ledger)
        self.assertEqual(state(self.h)['analysis_results'],[])

    def test_loaded_plan_action_error_exposes_explicit_route_without_execution(self):
        from tools.research import agent
        update(self.h,pilot={**state(self.h)['pilot'],'tool_directory':[
            dict(tool='research_plan',actions=['initialize_control','diagnose'])]})
        schema=agent.plan_schema(['initialize_control'],decision_required=True)
        request=dict(action='diagnose')
        error=next(e for e in Draft202012Validator(schema).iter_errors(request)
            if e.validator=='enum' and list(e.absolute_path)==['action'])
        before=deepcopy(state(self.h));ledger=self.h.store.remaining()
        feedback=agent.error_feedback(self.h,dict(name='research_plan',input=request),error,before)
        self.assertEqual(feedback['error_code'],'TOOL_SCHEMA_ENUM')
        self.assertEqual(feedback['field'],'action')
        self.assertIn('research_route',feedback['expected'])
        self.assertIn('"action": "diagnose"',feedback['expected'])
        self.assertFalse(feedback['scientific_execution_started'])
        self.assertEqual(state(self.h),before)
        self.assertEqual(self.h.store.remaining(),ledger)

    def test_delivered_schema_discriminates_targets_and_exclusive_sources(self):
        q=self.question();schema=selected_question_schema(self.h)
        Draft202012Validator(schema).validate(q)
        q['structure'].update(effect_semantics='reoptimized_task_capability',target='best_found_J')
        Draft202012Validator(schema).validate(q)
        q['structure']['target']=dict(quantity='optimal_task_violation',goal='decrease')
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(q)))
        q=self.question();q['structure'].update(operating_point='saved_native_state',
            saved_state=self.c,execution=self.c,update_id=0)
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(q)))
        q['structure'].pop('execution');q['structure'].pop('update_id')
        choices=reference_choices(self.h)
        wire=provider_schema(main_tool_schema(schema,choices))
        alias=next(k for k,v in choices.items() if v==self.c)
        q['structure']['saved_state']=alias
        Draft202012Validator(wire).validate(q)
        self.assertEqual(expand_references(q,main_tool_schema(schema,choices))['structure']['saved_state'],self.c)

    def test_conic_explicit_empty_parameters_do_not_inherit_plan_variables(self):
        q=conic_entry()['then']['input']
        Draft202012Validator(selected_question_schema(self.h)).validate(q)
        out=compile_question(self.h,q,tool_use_id='conic-inspect')
        self.assertEqual(out['status'],'ready',out)
        self.assertEqual(out['request']['operation'],'task_capability')
        self.assertEqual(out['request']['capability_method'],'sampled-affine-conic-minimax-v1')
        self.assertEqual(out['request']['model_source'],'gvs')
        self.assertNotIn('control_optimization',out['request'])
        self.assertEqual(state(self.h)['mathematical_evaluations'],0)

    def test_t1_value_is_never_converted_to_conic_value(self):
        q=self.question();q['structure'].update(operation='differentiate',
            effect_semantics='reoptimized_task_capability',target='optimal_task_violation',
            operating_point='frozen_task_initial_state',parameter_paths=['segments.0.length_m'],
            source_selection=dict(t1_results=[self.c]))
        out=compile_question(self.h,q,tool_use_id='value-mismatch')
        self.assertEqual(out['reason'],'NAMED_VALUE_AND_MODEL_SEMANTICS_DISAGREE')
        self.assertIn('next_choice',out)
        self.assertEqual(q['structure']['target'],'optimal_task_violation')

    def test_method_alignment_requires_registered_structured_identity(self):
        intent=dict(agent_hypothesis=dict(decision=dict(selected_method='Conic/SOCP around a Native schedule')))
        payload=dict(control=dict(numerical_method='mujoco-nonlinear-task-capability-v1'))
        out=method_alignment(intent,payload,'mujoco-nonlinear-task-capability-v1',dict(operation='mujoco_nonlinear_task_capability_v1'))
        self.assertEqual(out['original_hypothesis_status'],'requires_main_review')
        self.assertEqual(out['structured_request_status'],'pending_worker')
        out=method_alignment(intent,{},'mujoco_direct_control_v1',dict(operation='mujoco_direct_control_v1'))
        self.assertEqual(out['original_hypothesis_status'],'requires_main_review')
        intent['agent_hypothesis']['decision']['selected_method']='sampled-affine-conic-minimax-v1'
        out=method_alignment(intent,{},'mujoco_direct_control_v1',dict(operation='mujoco_direct_control_v1'))
        self.assertEqual(out['original_hypothesis_status'],'not_tested')

    def test_native_result_seed_rejection_guides_exact_schedule_without_acceptance(self):
        from tools.research.agent import error_feedback
        source=seed_control(self.h,ControlSeedRequest(candidate=self.c))['source']
        native=save(self.h,dict(status='computed',candidate=self.c,
            operation='mujoco_direct_control_v1',control_schedule_reference=source,
            fixture='Synthetic reference distinction; no Worker'), 'synthetic_native_result')
        request=ControlSeedRequest(candidate=self.c,parent=self.c,source=native)
        before=deepcopy(state(self.h));ledger=self.h.store.remaining()
        with self.assertRaisesRegex(ValueError,'CONTROL_INITIALIZATION_REQUIRES_EXECUTABLE_SOURCE') as caught:
            seed_control(self.h,request)
        feedback=error_feedback(self.h,dict(name='research_plan',input=dict(
            action='initialize_control',control_seed=request.model_dump(mode='json'))),caught.exception,before)
        self.assertEqual(feedback['field'],'control_seed.source')
        self.assertIn('/control_schedule_reference',feedback['expected'])
        self.assertFalse(feedback['worker_started'])
        self.assertEqual(state(self.h)['control_initializations'],before['control_initializations'])
        corrected=self.h.store.artifact(native)['control_schedule_reference']
        copied=seed_control(self.h,ControlSeedRequest(candidate=self.c,parent=self.c,source=corrected))
        actual=self.h.store.artifact(copied['source'])
        self.assertEqual(actual['trajectory'],self.h.store.artifact(source)['trajectory'])
        self.assertEqual(actual['task_acceptance'],'unmeasured')
        self.assertFalse(actual['provenance']['inherited_acceptance'])
        self.assertEqual(self.h.store.remaining(),ledger)

    def test_source_without_schedule_or_measured_execution_is_actionably_rejected(self):
        source=save(self.h,dict(fixture='No executable sequence'),'synthetic_missing_schedule')
        with self.assertRaisesRegex(ValueError,'CONTROL_INITIALIZATION_REQUIRES_EXECUTABLE_SOURCE'):
            seed_control(self.h,ControlSeedRequest(candidate=self.c,parent=self.c,source=source))

    def test_native_residual_import_requires_owned_computed_exact_source(self):
        source=seed_control(self.h,ControlSeedRequest(candidate=self.c))['source']
        with self.assertRaisesRegex(ValueError,'VERIFIED_MATHEMATICAL_TRAJECTORY_REQUIRED'):
            import_mathematical_reference(self.h,self.c,source)
        raw=dict(status='computed',candidate=self.c,operation='mujoco_direct_control_v1',
            control_schedule_reference=source,native_dynamics=dict(optimized_schedule=self.h.store.artifact(source)),
            fixture='Synthetic binding only; no Worker or scientific evidence')
        ref=save(self.h,raw,'synthetic_native_result');update(self.h,analysis_results=[ref])
        relation=import_mathematical_reference(self.h,self.c,source)
        self.assertEqual(relation['native_analysis'],ref)
        raw['status']='incomplete';bad=save(self.h,raw,'synthetic_incomplete')
        update(self.h,analysis_results=[bad])
        with self.assertRaisesRegex(ValueError,'VERIFIED_MATHEMATICAL_TRAJECTORY_REQUIRED'):
            import_mathematical_reference(self.h,self.c,source)


class SignedBrakingSemanticsTests(unittest.TestCase):
    def test_signed_range_extrema_are_preserved_without_braking_sign_conversion(self):
        from extensions.math_analysis.mechanism_registry import observe
        mechanics=dict(coordinates=dict(dof_order=['q'],tendon_order=['t']),
            function_metrics=dict(instantaneous_speed_derivative_range_m_s2=[-3.,5.]),
            time_s=.4,qpos_rad=[0.],qvel_rad_s=[1.],actual_tensions_n=[1.],input_bounds_n=[[0.,8.]])
        maximum=observe(mechanics,dict(quantity='instantaneous_braking',reduction='maximum',goal='increase'))
        minimum=observe(mechanics,dict(quantity='instantaneous_braking',reduction='minimum',goal='decrease'))
        self.assertEqual(maximum['value'],5.)
        self.assertEqual(minimum['value'],-3.)
        self.assertEqual(maximum['target']['goal'],'increase')
        self.assertEqual(minimum['target']['goal'],'decrease')


if __name__=='__main__':unittest.main()
