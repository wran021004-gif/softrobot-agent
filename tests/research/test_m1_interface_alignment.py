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


if __name__=='__main__':unittest.main()
