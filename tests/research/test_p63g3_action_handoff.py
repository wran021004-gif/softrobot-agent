"""G2 request regressions and real SDK/Mock wire. No real Provider requests."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator
from tools.research import core
from tools.research.config import ROOT, resolve
from tools.research.scientific_intent import compile_question, parameter_catalog
from tools.research.state import state, update
from tests.research.test_p63g2_structure_intent import provision, search_plan
from tests.research.test_p63a_math_interface import generate, diagnose, t1_request, offline_dispatch
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_information_flow import packet


def g3_host():
    h=provision();spec=deepcopy(state(h)['spec'])
    spec['research_decisions']['analysis_interface']='scientific_question_v3'
    update(h,spec=spec)
    return h


def saved_input(number):
    audit=json.loads((ROOT/'docs/research/p63g2_live_audit.json').read_text(encoding='utf-8'))
    return deepcopy(audit['requests'][number-1]['tools'][0]['input'])


def diagnosis(c, choice=None):
    p=saved_input(5);p['decision']['selected_candidate']=c;p['supporting_evidence']=[]
    if choice:p['next_research_action']=choice
    return p


def schema(wire, name):
    return next(t['function']['parameters'] for t in wire['tools'] if t['function']['name']==name)


class ActionHandoffTests(unittest.TestCase):
    def setUp(self):
        p=patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_SCIENTIFIC_WORKER_IN_MOCK_TEST'))
        p.start();self.addCleanup(p.stop)

    def test_g2_diagnose_explicit_codesign_wire_original_search_admission(self):
        h=g3_host();c=generate(h)
        with patch('tools.research.core.run_search',return_value=dict(status='OFFLINE_ADMISSION_FIXTURE_ONLY')) as worker:
            wires=run_fixture(h,[('research_plan',diagnosis(c,'structure_control_codesign')),
                ('research_plan',search_plan()),None])
        worker.assert_called_once()
        self.assertIn('next_research_action',schema(wires[0],'research_plan')['properties'])
        self.assertIn('ScientificStructureSearch',schema(wires[1],'research_plan')['$defs'])
        self.assertFalse(any(t['function']['name']=='research_analysis' for t in wires[1]['tools']))
        handoff=packet(wires[1])['tool_continuation']
        self.assertEqual(handoff['loaded']['plan_action'],'search')
        self.assertEqual(handoff['direct_plan']['action'],'search')
        self.assertNotIn('analysis_handoff',handoff)
        self.assertNotIn('Submit ScientificQuestion',json.dumps(handoff))
        bindings=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id) if e['kind']=='structure_search_intent_binding']
        q=bindings[0]['compiled_plan']['search']
        self.assertEqual((len(q['control_settings']['knots_s']),q['control_settings']['iterations'],q['control_settings']['evaluation_requests']),(4,80,120))
        plans=[h.store.artifact(r) for r in state(h)['plans']]
        self.assertEqual(plans[-1]['admission']['admitted'],2)
        self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_neutral_choice_then_explicit_route_and_no_automatic_science(self):
        h=g3_host();c=generate(h)
        wires=run_fixture(h,[('research_plan',diagnosis(c)),
            ('research_route',dict(tool='research_plan',action='search')),None])
        names={t['function']['name'] for t in wires[1]['tools']}
        self.assertNotIn('research_analysis',names);self.assertNotIn('research_plan',names)
        self.assertIsNone(packet(wires[1])['tool_continuation']['scientific_action_handoff']['diagnose_choice'])
        self.assertIn('ScientificStructureSearch',schema(wires[2],'research_plan')['$defs'])
        self.assertEqual(state(h)['analysis_results'],[]);self.assertEqual(state(h)['search_results'],[])

    def test_parameter_and_control_choices_load_v3_with_matching_feedback(self):
        for choice in ('single_parameter_effect','control_feasibility'):
            with self.subTest(choice=choice):
                h=g3_host();c=generate(h)
                wires=run_fixture(h,[('research_plan',diagnosis(c,choice)),None])
                q=schema(wires[1],'research_analysis');Draft202012Validator.check_schema(q)
                self.assertEqual(q['properties']['version']['const'],'scientific_question_v3')
                self.assertIn('parameter_group',q['properties']);self.assertNotIn('parameter_paths',q['properties'])
                continuation=packet(wires[1])['tool_continuation']
                self.assertEqual(continuation['analysis_handoff']['interface'],'scientific_question_v3')
                self.assertTrue(continuation['analysis_handoff']['parameter_catalog'])
                feedback=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id) if e['kind']=='model_original_tool_feedback'][0]
                result=json.loads(feedback['result']['content'][0]['text'])
                self.assertEqual(result['execution_feedback']['execution_entry']['interface'],'scientific_question_v3')

    def test_three_exact_g2_bad_requests_prioritize_operation_over_parameter(self):
        h=provision();c=generate(h);diagnose(h,c,'scientific_question');before=deepcopy(state(h))
        for n in (6,8,10):
            q=saved_input(n)
            result=compile_question(h,q,tool_use_id='g2-replay-'+str(n))
            self.assertEqual(result['reason'],'SCIENTIFIC_OPERATION_MISMATCH')
            self.assertEqual(result['status'],'needs_choice');self.assertFalse(result['scientific_execution_started'])
            self.assertFalse(result['scientific_result_produced']);self.assertNotIn('request',result)
        self.assertEqual(state(h),before)

    def test_registry_groups_and_no_arbitrary_parameter_or_t1_creation(self):
        h=g3_host();c=generate(h);diagnose(h,c,'scientific_question')
        rows=parameter_catalog(state(h)['spec'],h.store.artifact(c))
        for r in rows:
            self.assertIn('unit',r);self.assertIn('validity',r);self.assertFalse(r['parameter_id'].startswith('/'))
        q=dict(version='scientific_question_v3',question_type='structure_parameter_effect',
            effect_semantics='reoptimized_task_capability',parameter_group='lengths')
        before=deepcopy(state(h));result=compile_question(h,q,tool_use_id='group')
        self.assertEqual(result['reason'],'REGISTERED_PHYSICAL_PARAMETER_REQUIRED')
        self.assertGreaterEqual(len([r for r in result['choices']['parameters'] if r['selectable']]),2)
        for bad in ('/parameters/geometry','/parameters/spans/0/anchor_angle_offset_rad','/spans/0/guide_angle_offset_rad','segments.0.cells','tendon_parameters.length_servo_gain_n_m'):
            result=compile_question(h,{**q,'parameter_id':bad},tool_use_id='bad-id')
            self.assertEqual(result['reason'],'REGISTERED_EFFECTIVE_CONTINUOUS_PARAMETER_REQUIRED')
        result=compile_question(h,{**q,'parameter_id':'segments.0.length_m'},tool_use_id='valid-id')
        self.assertEqual(result['status'],'needs_prerequisite');self.assertIn('T1',result['reason'])
        self.assertEqual(state(h),before)

    def test_group_selection_and_semantic_repair_are_delivered_in_actual_wire(self):
        h=g3_host();c=generate(h)
        query=dict(version='scientific_question_v3',question_type='structure_parameter_effect',
            effect_semantics='reoptimized_task_capability',parameter_group='lengths')
        mismatch={**query,'parameter_id':'/parameters/geometry','control_search_effort':dict(method='pattern',iterations=80,evaluation_requests=120)}
        wires=run_fixture(h,[('research_plan',diagnosis(c,'single_parameter_effect')),
            ('research_analysis',query),('research_analysis',mismatch),None])
        self.assertIn('REGISTERED_PHYSICAL_PARAMETER_REQUIRED',json.dumps(packet(wires[2])))
        self.assertIn('SCIENTIFIC_OPERATION_MISMATCH',json.dumps(packet(wires[3])))
        self.assertEqual(state(h)['analysis_results'],[])

    def test_v3_uses_comparable_saved_t1_without_creating_structures_or_search(self):
        h=g3_host();cs=[generate(h,x) for x in ((.16,.11),(.155,.11),(.165,.11))]
        refs=[offline_dispatch(h,t1_request(h,c),'g3-synthetic-t1-'+str(i))['reference'] for i,c in enumerate(cs)]
        diagnose(h,cs[0],'scientific_question');before=deepcopy(state(h))
        result=compile_question(h,dict(version='scientific_question_v3',question_type='structure_parameter_effect',
            effect_semantics='reoptimized_task_capability',parameter_group='lengths',parameter_id='segments.0.length_m'),tool_use_id='g3-saved-t2')
        self.assertEqual(result['status'],'ready')
        self.assertEqual(result['request']['nonlinear_response']['t1_results'],refs)
        self.assertEqual(state(h)['candidates'],before['candidates'])
        self.assertEqual(state(h)['mathematical_evaluations'],before['mathematical_evaluations'])
        self.assertEqual(state(h)['search_results'],before['search_results'])

    def test_legacy_study_cannot_opt_in_through_a_plan(self):
        h=provision();c=generate(h)
        with self.assertRaisesRegex(ValueError,'VERSIONED_AVAILABLE'):
            core.dispatch(h,diagnosis(c,'structure_control_codesign'),'legacy-illegal')


if __name__=='__main__':unittest.main()
