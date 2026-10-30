"""G1 failure regressions, actual SDK/Mock wire, and one isolated Native Worker.

Only RealNativeSearchTest performs real numerical work; no real Provider here.
"""
from copy import deepcopy
import json, unittest
from pathlib import Path
from unittest.mock import patch
from jsonschema import Draft202012Validator
import numpy as np
from tools.platform_store import plain
from tools.research import agent,core
from tools.research.config import ROOT
from tools.research.contracts import Plan,FamilyMixedSearch
from tools.research.structure_intent import compile_search,StructureChoiceError
from tools.research.scientific_intent import control_settings,compile_question,question_schema
from tools.research.state import state,update,save
from tools.research.control_correction import corrected_tensions
from tests.research.test_p63c2_scientific_intent import question_host
from tests.research.test_p63a_math_interface import generate,t1_request,diagnose
from tests.research.test_recent_round_tools import run_fixture


def provision():
    h=question_host();spec=deepcopy(state(h)['spec'])
    g1=json.loads((ROOT/'configs/research/study_p63g1_m3_autonomous_sol.json').read_text(encoding='utf-8'))
    spec['research_decisions'].update(structure_search_interface='scientific_structure_search_v1',analysis_interface='scientific_question_v2')
    spec['family_search']=g1['family_search'];spec['fidelity_policy']=g1['fidelity_policy']
    spec['native_control_limits']=g1['native_control_limits']
    spec['budgets']['mathematical_evaluations']=1000000
    spec['capabilities']=list(set(spec['capabilities'])|{'search','control_correction'})
    spec['allowed_plan_actions']=list(set(spec['allowed_plan_actions'])|{'search'})
    update(h,spec=spec)
    return h


def search_plan(**changes):
    query=dict(version='scientific_structure_search_v1',research_goal='structure_control_codesign',
        design_variable_groups=['lengths','materials','routing'],evaluation_model='native_mujoco',
        control_treatment='reoptimized',structure_search_effort=dict(max_proposals=2,max_evaluations=2),
        control_search_effort=dict(method='pattern',knot_count=4,iterations=80,evaluation_requests=120))
    query.update(changes)
    return dict(action='search',search=query,hypothesis='OFFLINE fixture: geometry-control adaptation may reduce the full-task gap',
        expected_observation='A finite best-found improvement',weakening_observation='Comparable valid failures',
        fixed_conditions='Frozen task, physical model and constraints',stopping_condition='Declared finite effort',
        interpretation='No global or independent acceptance claim',decision=dict(hypothesis_id='offline-g2',claimed_inference='empirical_search'))


class StructureIntentTests(unittest.TestCase):
    def setUp(self):
        worker=patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER_IN_OFFLINE_CONTRACT_TEST'))
        worker.start();self.addCleanup(worker.stop)

    def test_compile_original_plan_grants_settings_and_version_gates(self):
        h=provision();before=state(h)['mathematical_evaluations']
        result=compile_search(h,search_plan(),'offline-compile');Plan.model_validate(result)
        q=FamilyMixedSearch.model_validate(result['search'])
        self.assertEqual(q.family_space_identity,state(h)['spec']['family_space_identity'])
        self.assertEqual(q.segment_counts,[2]);self.assertEqual(q.tendon_counts,[6])
        self.assertNotIn('control',q.variable_groups);self.assertEqual(q.evaluation_mode,'mujoco_control')
        self.assertEqual(q.operating_point,'standardized_initial_pretension')
        self.assertEqual(result['decision']['research_intent'],'MATHEMATICAL_ANALYSIS')
        self.assertEqual(q.control_settings.iterations,80);self.assertEqual(q.control_settings.evaluation_requests,120)
        self.assertEqual(len(q.control_settings.knots_s),4)
        self.assertEqual(q.control_settings.knots_s[-1],state(h)['spec']['analysis_protocol']['duration_s'])
        self.assertEqual(state(h)['mathematical_evaluations'],before)
        with self.assertRaises(StructureChoiceError):compile_search(h,search_plan(segment_counts=[3]),'bad-topology')
        with self.assertRaises(StructureChoiceError):compile_search(h,search_plan(evaluation_model='mathematical_proxy'),'no-model-substitution')
        spec=deepcopy(state(h)['spec']);spec['research_decisions'].pop('structure_search_interface');update(h,spec=spec)
        with self.assertRaisesRegex(ValueError,'VERSIONED'):compile_search(h,search_plan(),'old-study')

    def test_effort_defaults_limits_local_zero_and_c2_shared_mapping(self):
        h=provision();spec=state(h)['spec']
        effort=dict(method='response',knot_count=4,evaluation_requests=120)
        self.assertEqual(control_settings(spec,effort).iterations,100)
        with self.assertRaises(ValueError):control_settings(spec,{**effort,'knot_count':5})
        with self.assertRaises(ValueError):control_settings(spec,{**effort,'iterations':101})
        with self.assertRaises(ValueError):control_settings(spec,{**effort,'evaluation_requests':1001})
        local=control_settings(spec,effort,window=(.2,.4),channels=2)
        coeff=np.zeros((4,2));coeff.reshape(-1)[local.active_coefficients]=.5
        times=np.array([0.,.1,.2,.25,.35,.4,.5,.6]);base=np.ones((len(times),2))
        adjusted=corrected_tensions(base,times,local.knots_s,coeff.reshape(-1),[8.,8.],local.correction_window_s)
        np.testing.assert_allclose(adjusted[[0,1,2,5,6,7]],base[[0,1,2,5,6,7]])
        c=generate(h);t1_request(h,c);diagnose(h,c,'scientific_question')
        q=dict(version='scientific_question_v2',question_type='control_feasibility',control_scope=dict(mode='full_task'),
            control_search_effort={**effort,'iterations':80})
        result=compile_question(h,q,tool_use_id='offline-c2-v2')
        self.assertEqual(result['status'],'ready',result)
        settings=result['request']['control_optimization']['settings']
        self.assertEqual(settings['iterations'],80);self.assertEqual(settings['evaluation_requests'],120)
        self.assertEqual(len(settings['knots_s']),4)
        self.assertNotIn('requested_budget',question_schema(spec)['properties'])
        wires=run_fixture(h,[None])
        schema=next(t['function']['parameters'] for t in wires[0]['tools'] if t['function']['name']=='research_analysis')
        self.assertIn('control_search_effort',schema['properties'])
        self.assertNotIn('search_strategy',schema['properties'])

    def test_proxy_stays_proxy_and_knowledge_filters_reach_actual_wire(self):
        h=provision()
        plan=search_plan(research_goal='structural_capability_screening',evaluation_model='mathematical_proxy',
            control_treatment='not_optimized',proxy_objective='held_position_min_eigenvalue',control_search_effort=None)
        compiled=compile_search(h,plan,'offline-proxy')
        self.assertEqual(FamilyMixedSearch.model_validate(compiled['search']).evaluation_mode,'mathematical_proxy')
        self.assertNotIn('control_settings',compiled['search'])
        wires=run_fixture(h,[('experience_retrieve',dict(operation='search',kind='control')),
            ('experience_retrieve',dict(operation='read',entry_id='research-bounded-continuation',revision='2')),
            ('experience_retrieve',dict(operation='read',entry_id='research-bounded-continuation',revision='2')),None])
        feedback=[json.loads(h.store.artifact(e['outputs'][0])['result']['content'][0]['text'])
            for e in h.store.events(h.run_id) if e['kind']=='model_original_tool_feedback']
        self.assertIn('procedure',feedback[0]['filter_values']['kind'])
        self.assertEqual(feedback[0]['matched_count'],0)
        self.assertTrue(feedback[-1]['prior_read_progress']['reads'][0]['body_delivered'])
        self.assertIn('prior_read_progress',json.dumps(wires[-1]))

    def test_saved_g1_failures_report_selected_branch_without_execution(self):
        h=provision();audit=json.loads((ROOT/'docs/research/p63g1_live_audit.json').read_text(encoding='utf-8'))
        fixture=json.loads((Path(__file__).parent/'fixtures/p63g2_g1_failed_inputs.json').read_text(encoding='utf-8'))
        self.assertEqual([r['provider_request'] for r in fixture['requests']],[20,21,29,46,59,62,65,67])
        source=Path(audit['store'],'platform.sqlite');stamp=source.stat().st_mtime_ns if source.exists() else None
        for row in fixture['requests']:
            n=row['provider_request'];original=row['tool_use']
            self.assertEqual(row['input_reference'],audit['requests'][n-1]['tools'][0]['input_reference'])
            with self.subTest(request=n):
                try:Plan.model_validate(original['input'])
                except ValueError as exc:
                    out=agent.error_feedback(h,original,exc,deepcopy(state(h)))
                    self.assertEqual(out['contract'],'FamilyMixedSearch')
                    self.assertNotIn('Search].variables',out['reason'])
                    self.assertFalse(out['scientific_execution_started']);self.assertTrue(out['issues'])
                    if n==59:self.assertTrue(any('knots_s' in i['field'] for i in out['issues']))
                else:self.fail('Saved failure unexpectedly valid')
        self.assertEqual(state(h)['mathematical_evaluations'],0)
        if stamp is not None:self.assertEqual(source.stat().st_mtime_ns,stamp)

    def test_actual_route_schema_compile_original_admission_and_compact_error_wire(self):
        h=provision()
        intent=search_plan();intent['search'].pop('version')
        with patch('tools.research.core.run_search',return_value=dict(status='OFFLINE_ADMISSION_FIXTURE_ONLY')) as worker:
            wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='search')),('research_plan',intent),None])
        worker.assert_called_once()
        schema=next(t['function']['parameters'] for t in wires[1]['tools'] if t['function']['name']=='research_plan')
        Draft202012Validator(schema).validate(search_plan())
        self.assertIn('ScientificStructureSearch',schema['$defs']);self.assertNotIn('FamilyMixedSearch',schema['$defs'])
        decision=schema['$defs']['ResearchDecision']
        for k in ('research_intent','selected_method','requested_budget'):self.assertNotIn(k,decision['properties'])
        binding=next(e for e in h.store.events(h.run_id) if e['kind']=='structure_search_intent_binding')
        raw=h.store.artifact(binding['outputs'][0]);self.assertEqual(raw['compiled_plan']['decision']['research_intent'],'MATHEMATICAL_ANALYSIS')
        self.assertEqual(len(raw['compiled_plan']['search']['control_settings']['knots_s']),4)
        saved=next(e for e in h.store.events(h.run_id) if e['kind']=='original_research_plan')
        self.assertEqual(h.store.artifact(saved['outputs'][0])['admission']['admitted'],2)
        self.assertEqual(state(h)['mathematical_evaluations'],0)
        h=provision();bad=search_plan();bad['search']['control_search_effort']['knot_count']=5
        wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='search')),('research_plan',bad),None])
        feedback=[h.store.artifact(e['outputs'][0])['result'] for e in h.store.events(h.run_id) if e['kind']=='model_original_tool_feedback'][-1]
        self.assertEqual(feedback['status'],'error');self.assertIn('knot_count',feedback['content'][0]['text'])
        self.assertIn('knot_count',json.dumps(wires[-1]));self.assertEqual(state(h)['mathematical_evaluations'],0)


class RealNativeSearchTest(unittest.TestCase):
    def test_original_search_worker_real_small_native_integration(self):
        h=provision();plan=search_plan(structure_search_effort=dict(max_proposals=1,max_evaluations=1),
            control_search_effort=dict(method='pattern',knot_count=2,iterations=2,evaluation_requests=2))
        with patch.object(core,'guard'):
            out=core.dispatch(h,plan,'g2-real-isolated-worker',origin='operator')
        self.assertEqual(state(h)['mathematical_evaluations'],1,out)
        raw=h.store.artifact(state(h)['analysis_results'][0]);cost=raw['native_dynamics']['cost']
        self.assertGreater(cost['model_builds'],0);self.assertGreater(cost['physics_steps'],0)
        self.assertTrue(raw['boundary']['worker_started']);self.assertTrue(raw['boundary']['termination_confirmed'])
        self.assertTrue(state(h)['search_results'])
        (ROOT/'runs/g2_real_worker_test.json').write_text(json.dumps(dict(study=h.run_id,result=state(h)['analysis_results'][0],
            boundary=raw['boundary'],cost=cost),indent=2),encoding='utf-8')
