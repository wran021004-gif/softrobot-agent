"""Scientific interface handoffs with real SDK/Mock HTTP and fabricated workers.

No real Provider, contained worker or physical integration is authorized here.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from tools.research import agent, core
from tools.research.contracts import AnalysisRequest, ScientificQuestionV4
from tools.research.scientific_intent import (compile_question, completed_question_plan,
    control_method_choices, question_schema)
from tools.research.state import state, update, save
from tools.research.task_constraints import mathematical_method_view
from tools.state_io import atomic_json, read
from tests.research.test_r3_b_stage1 import integrated_host, structure_question
from tests.research.test_p63a_math_interface import synthetic_t1, t1_request, diagnose, generate
from tests.research.test_p63g3_action_handoff import diagnosis, schema
from tests.research.test_information_flow import generation, packet
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_structure_mechanism_aplus import synthetic_worker


def control_question():
    return dict(domain='control',control=dict(control_scope=dict(mode='full_task'),
        control_search_effort=dict(method='pattern',knot_count=4,iterations=2,evaluation_requests=4)))


def initialization(h,candidate):
    plan=generation(h)
    plan.update(action='initialize_control',control_seed=dict(candidate=candidate,method='baseline'))
    plan.pop('generation')
    plan['decision'].update(research_intent='CONTROL_SEARCH',selected_candidate=candidate)
    return plan


class IntentCompilationHandoffTests(unittest.TestCase):
    def setUp(self):
        for name in ('tools.service_execution._run_contained','mujoco.mj_step'):
            p=patch(name,side_effect=AssertionError('NO_REAL_SCIENTIFIC_WORKER_OR_INTEGRATION'))
            p.start();self.addCleanup(p.stop)

    def test_control_preparation_preserves_choice_and_actual_sdk_reaches_original_t1(self):
        h,c=integrated_host();seen=[]
        def worker(command,log,timeout,**kw):
            request=read(Path(command[-1]));query=AnalysisRequest.model_validate(request['query'])
            seen.append(query)
            atomic_json(Path(command[-1]).with_name('result.json'),synthetic_t1(request))
            return SimpleNamespace(returncode=0)
        with patch('tools.service_execution._run_contained',side_effect=worker), \
                patch('tools.research.reporter._wire',side_effect=ValueError('MOCK_REPORTER_UNAVAILABLE')):
            wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='diagnose')),
                ('research_plan',diagnosis(c,'control_feasibility')),
                ('research_route',dict(tool='research_plan',action='initialize_control')),
                ('research_plan',initialization(h,c)),('research_analysis',control_question()),None])
        self.assertEqual(len(seen),1)
        self.assertEqual(seen[0].operation,'mujoco_nonlinear_task_capability_v1')
        self.assertEqual((seen[0].control_optimization.settings.iterations,
            seen[0].control_optimization.settings.evaluation_requests),(2,4))
        Draft202012Validator(schema(wires[4],'research_analysis')).validate(control_question())
        self.assertEqual(completed_question_plan(h)['candidate'],c)
        plans=[h.store.artifact(r)['original_plan'] for r in state(h)['plans']]
        self.assertEqual([p['action'] for p in plans[-2:]],['diagnose','initialize_control'])
        handoff=packet(wires[4])['tool_continuation']['analysis_handoff']
        self.assertEqual(handoff['status'],'diagnose_completed')
        self.assertNotIn('parameter_catalog',handoff)
        self.assertTrue(any(r['readiness']=='ready_for_scientific_request' for r in handoff['control_methods']))
        raw=h.store.artifact(state(h)['analysis_results'][0])
        self.assertEqual(raw['task_acceptance'],'unmeasured')
        compilations=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id)
            if e['kind']=='scientific_intent_compilation']
        self.assertEqual(compilations[-1]['raw_main_input'],control_question())
        ScientificQuestionV4.model_validate(compilations[-1]['compiled_question'])
        self.assertIn('control.question_type',compilations[-1]['deterministic_field_sources'])

    def test_structure_inspect_and_explicit_direction_use_original_worker_and_keep_scope(self):
        h,c=integrated_host()
        inspect=structure_question();inspect['structure'].update(operation='inspect',requested_budget=1)
        inspect['structure'].pop('control_treatment')
        differentiate=structure_question();differentiate['structure'].pop('control_treatment')
        differentiate['structure']['target']['goal']='decrease'
        with synthetic_worker(h,c),patch('tools.research.reporter._wire',side_effect=ValueError('MOCK_REPORTER_UNAVAILABLE')):
            wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='diagnose')),
                ('research_plan',diagnosis(c,'mechanism_research')),('research_analysis',inspect),
                ('research_analysis',differentiate),None])
        for wire,q in ((wires[2],inspect),(wires[3],differentiate)):
            Draft202012Validator(schema(wire,'research_analysis')).validate(q)
        self.assertEqual(len(state(h)['analysis_results']),2)
        self.assertEqual(len(state(h)['candidates']),1)
        raw=h.store.artifact(state(h)['analysis_results'][-1])
        self.assertEqual(raw['operation'],'mechanism_structure_v1')
        self.assertEqual(raw['requested_operation']['mechanism_study']['target']['goal'],'decrease')
        self.assertEqual(raw['task_acceptance'],'unmeasured')
        self.assertNotIn('parameter_catalog',packet(wires[-1])['tool_continuation']['analysis_handoff'])

    def test_shared_legal_source_catalog_distinguishes_missing_unique_and_ambiguous(self):
        h,c=integrated_host();diagnose(h,c,'scientific_question')
        missing=control_method_choices(mathematical_method_view(h,c))
        self.assertTrue(any(r['readiness']=='requires_control_initialization' and
            r['preparation']['control_seed']['candidate']==c for r in missing if r['selectable']))
        source=t1_request(h,c)['control_optimization']['source']
        choices=control_method_choices(mathematical_method_view(h,c))
        self.assertTrue(any(r['readiness']=='ready_for_scientific_request' for r in choices))
        raw=deepcopy(h.store.artifact(source));raw['trajectory']['tensions_n'][0][0]+=.01
        other=save(h,raw,'synthetic-distinct-source')
        update(h,control_initializations=[*state(h)['control_initializations'],dict(candidate=c,source=other)])
        result=compile_question(h,control_question(),tool_use_id='ambiguous-sources')
        self.assertEqual(result['reason'],'SCIENTIFICALLY_DISTINCT_CONTROL_SOURCES')
        self.assertEqual(len(result['choices']['control_source']),2)
        self.assertEqual(state(h)['analysis_results'],[])

    def test_projected_generation_respects_frozen_routing_without_restricting_other_grants(self):
        h,c=integrated_host();spec=state(h)['spec']
        q=generation(h);q['generation']['spans']=[dict(first_segment=1,last_segment=1,count=4)]
        projected=agent.plan_schema(['generate'],decision_required=True,
            family_version=spec['family_space']['version'],study=spec)
        self.assertTrue(list(Draft202012Validator(projected).iter_errors(q)))
        other=deepcopy(spec);other['family_space']['conditional_rules']='consecutive_spans_v1'
        broader=agent.plan_schema(['generate'],decision_required=True,
            family_version=spec['family_space']['version'],study=other)
        self.assertNotIn('const',broader['$defs']['Span']['properties']['first_segment'])
        narrowed=deepcopy(spec);narrowed['topology_scope']=dict(segment_counts=[2],tendon_counts=[6])
        constrained=agent.plan_schema(['generate'],decision_required=True,
            family_version=spec['family_space']['version'],study=narrowed)
        generation_name='GenerationRequestV2' if spec['family_space']['version']=='serial_family_space_v2' else 'GenerationRequest'
        self.assertEqual(constrained['$defs'][generation_name]['properties']['segment_count']['enum'],[2])
        self.assertEqual(constrained['$defs'][generation_name]['properties']['tendon_count']['enum'],[6])
        self.assertEqual(state(h)['analysis_results'],[])

    def test_illegal_root_semantics_direction_and_sealed_state_never_start_science(self):
        h,c=integrated_host();q=structure_question()
        for field in ('hypothesis','requested_budget','operating_point'):
            invalid={**q,field:'invalid-root'}
            self.assertEqual(compile_question(h,invalid,tool_use_id=field)['reason'],'INVALID_SCIENTIFIC_V4_INPUT')
        invalid=deepcopy(q);invalid['structure']['target']=dict(quantity='directional_acceleration_bounds',
            direction_world=[0.,0.,2.],goal='increase')
        self.assertEqual(compile_question(h,invalid,tool_use_id='direction')['reason'],'INVALID_SCIENTIFIC_V4_INPUT')
        invalid=deepcopy(q);invalid['structure']['effect_semantics']='reoptimized_task_capability'
        projected=question_schema(state(h)['spec'],h.store.artifact(c),'mechanism_research')
        self.assertTrue(list(Draft202012Validator(projected).iter_errors(invalid)))
        self.assertNotEqual(compile_question(h,invalid,tool_use_id='semantics')['status'],'ready')
        update(h,research_status='stopped')
        self.assertEqual(compile_question(h,q,tool_use_id='sealed')['reason'],'ORIGINAL_PROTECTED_CLOSEOUT_OR_STOP')
        self.assertEqual(state(h)['analysis_results'],[])
        self.assertEqual(state(h)['mathematical_evaluations'],0)
        self.assertEqual(run_fixture(h,[None]),[])
        self.assertEqual(state(h)['research_status'],'stopped')

    def test_preparation_for_another_candidate_does_not_inherit_scientific_choice(self):
        h,c=integrated_host()
        with patch.object(core,'guard'):core.dispatch(h,diagnosis(c,'control_feasibility'),'first-choice')
        other=generate(h,(.165,.11))
        with patch.object(core,'guard'):core.dispatch(h,initialization(h,other),'other-preparation')
        self.assertIsNone(completed_question_plan(h))
        self.assertEqual(state(h)['analysis_results'],[])
