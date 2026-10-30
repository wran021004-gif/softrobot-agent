"""Offline C2 contract/compiler/wire checks. All numerical outputs are fabricated."""
from copy import deepcopy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from jsonschema import Draft202012Validator
from tools.platform_store import plain
from tools.research import agent, analysis, core
from tools.research.contracts import AnalysisRequest, ScientificQuestion
from tools.research.config import ROOT, resolve
from tools.research.control_correction import corrected_tensions
from tools.research.nonlinear_capability import T1, T2, T1_OPERATION, T2_OPERATION
from tools.research.scientific_intent import compile_question
from tools.research.state import state, update, save
from tools.research.task_constraints import mathematical_method_view
from tools.state_io import read, atomic_json
from tests.research.test_p63a_math_interface import generate, t1_request, diagnose, offline_dispatch, synthetic_t1
from tests.research.test_p63b3_action_interface import provision
from tests.research.test_recent_round_tools import run_fixture


def question_host():
    h=provision();spec=deepcopy(state(h)['spec'])
    spec['research_decisions']['analysis_interface']='scientific_question_v1'
    update(h,spec=spec)
    return h


def control_question(**changes):
    return dict(question_type='control_feasibility',control_scope=dict(mode='full_task'),
        search_strategy='response',requested_budget=4,**changes)


def structural_question(semantics, **changes):
    return dict(question_type='structure_parameter_effect',effect_semantics=semantics,
        parameter_paths=['segments.0.length_m'],**changes)


class ScientificIntentTests(unittest.TestCase):
    def setUp(self):
        for name in ('tools.service_execution._run_contained','extensions.tendon_family.mujoco_analysis.NativeModel',
                     'mujoco.mj_step','tools.research.provider.load_credential'):
            p=patch(name,side_effect=AssertionError('NO_REAL_PROVIDER_WORKER_OR_INTEGRATION'))
            p.start();self.addCleanup(p.stop)

    def prepare(self, *, source=False):
        h=question_host();c=generate(h)
        if source:t1_request(h,c)
        diagnose(h,c,'scientific_question')
        return h,c

    def compile(self,h,q):
        return compile_question(h,q,tool_use_id='offline-c2')

    def test_schema_scientific_explanations_and_new_plan_without_solver(self):
        schema=ScientificQuestion.model_json_schema();Draft202012Validator.check_schema(schema)
        text=schema['properties']['effect_semantics']['description']
        for name in ('mechanism_effect','fixed_input_response','reoptimized_task_capability',
                     'closed_loop_performance','re_equilibrated_passive_response'):
            self.assertIn(name,text)
        self.assertNotIn('M0',json.dumps(schema));self.assertNotIn('operation',schema['properties'])
        h,c=self.prepare();spec=state(h)['spec']
        new=agent.plan_schema(['diagnose'],decision_required=True,focused=True,study=spec)
        self.assertNotIn('selected_method',new['$defs']['ResearchDecision']['required'])
        old=agent.plan_schema(['diagnose'],decision_required=True,diagnose_candidate_required=True)
        self.assertIn('selected_method',old['$defs']['ResearchDecision']['required'])
        for version in ('bound_scientific_variables_v1','bound_scientific_variables_v2'):
            spec=deepcopy(state(h)['spec']);spec['research_decisions']['analysis_interface']=version
            self.assertTrue(agent.bound_analysis_enabled(spec))

    def test_new_interface_is_accepted_only_for_new_versioned_english_configuration(self):
        from uuid import uuid4
        cfg=read(ROOT/'configs/research/study_s125_cold.json')
        cfg['research_decisions']=deepcopy(state(question_host())['spec']['research_decisions'])
        path=ROOT/'configs/research'/('._c2-'+uuid4().hex+'.json')
        atomic_json(path,cfg)
        try:
            resolved=resolve(path)
            self.assertEqual(resolved['research_decisions']['analysis_interface'],'scientific_question_v1')
        finally:path.unlink()

    def test_t1_compiles_original_contract_and_original_charge_without_scientific_claim(self):
        h,c=self.prepare(source=True);before=deepcopy(state(h));q=control_question(focus_metric='holding_max_speed_m_s')
        result=self.compile(h,q);self.assertEqual(result['status'],'ready')
        full=result['request'];AnalysisRequest.model_validate(full)
        Draft202012Validator(AnalysisRequest.model_json_schema()).validate(full)
        self.assertEqual(full['operation'],T1_OPERATION);self.assertEqual(full['candidate'],c)
        self.assertEqual(full['protocol'],before['spec']['analysis_protocol'])
        self.assertEqual(full['control_optimization']['settings']['correction_window_s'],[0.,.6])
        self.assertEqual(state(h)['mathematical_evaluations'],before['mathematical_evaluations'])
        self.assertNotIn('J',result);self.assertIn('no global',str(result['limitations']).lower())
        executed=offline_dispatch(h,full,'c2-original-cost')
        raw=h.store.artifact(executed['reference'])
        self.assertEqual(state(h)['mathematical_evaluations'],1)
        self.assertEqual(raw['nonlinear_capability']['callbacks'],4)
        self.assertEqual(raw['nonlinear_capability']['physics_steps'],400)
        self.assertEqual(raw['task_acceptance'],'unmeasured')
        self.assertEqual(h.store.remaining()['used']['worker_calls'],0)

    def test_missing_source_choices_and_no_implicit_initialization(self):
        h,c=self.prepare();before=deepcopy(state(h));r=self.compile(h,control_question())
        self.assertEqual(r['status'],'needs_prerequisite');self.assertEqual(r['preparation']['action'],'initialize_control')
        self.assertEqual(state(h),before)
        r=self.compile(h,dict(question_type='control_feasibility'))
        self.assertEqual(r['status'],'needs_choice');self.assertIn('control_scope',r['fields'])
        self.assertNotIn('request',r)

    def test_completed_plan_reuses_its_parameter_and_budget_choices(self):
        h,c=self.prepare(source=True)
        from tests.research.test_p63b5_native_entry import plan
        selected=plan(c);selected['decision'].update(requested_budget=7,selected_variables=['segments.0.length_m'])
        with patch.object(core,'guard'):core.dispatch(h,selected,'c2-plan-choices')
        q=control_question();q.pop('requested_budget')
        r=self.compile(h,q);self.assertEqual(r['request']['control_optimization']['settings']['evaluation_requests'],7)
        generate(h,(.165,.11))
        q=structural_question('fixed_input_response',fixed_input='frozen_initial_tensions',response_horizon_s=.01)
        q.pop('parameter_paths');r=self.compile(h,q)
        self.assertEqual(r['request']['structure_response']['variable'],'segments.0.length_m')

    def test_control_source_ambiguity_requires_main_and_invalid_source_never_executes(self):
        h,c=self.prepare(source=True);s=state(h);first=s['control_initializations'][0]['source']
        raw=deepcopy(h.store.artifact(first));raw['trajectory']['tensions_n'][0][0]+=.01
        second=save(h,raw,'c2-distinct-control-source-fixture')
        update(h,control_initializations=[*s['control_initializations'],dict(candidate=c,source=second)])
        r=self.compile(h,control_question());self.assertEqual(r['status'],'needs_choice')
        self.assertEqual(len(r['choices']['control_source']),2)
        r=self.compile(h,control_question(source_selection=dict(control_source=second)))
        self.assertEqual(r['request']['control_optimization']['source'],second)
        r=self.compile(h,control_question(source_selection=dict(control_source=c)))
        self.assertEqual(r['status'],'needs_prerequisite')

    def test_local_window_actual_correction_zero_outside_and_full_task_is_preserved(self):
        h,c=self.prepare(source=True);q=control_question();q['control_scope']=dict(mode='time_window',window_s=[.25,.5])
        r=self.compile(h,q);self.assertEqual(r['status'],'ready')
        cfg=r['request']['control_optimization']['settings'];channels=4
        times=np.linspace(0,.6,601);reference=np.full((len(times),channels),1.)
        for amplitude in (-2.,-.1,.1,2.):
            coefficients=np.zeros((len(cfg['knots_s']),channels));coefficients.flat[cfg['active_coefficients']]=amplitude
            actual=corrected_tensions(reference,times,cfg['knots_s'],coefficients,[8.]*channels,cfg['correction_window_s'])
            outside=(times<.25)|(times>.5)
            np.testing.assert_array_equal(actual[outside],reference[outside])
            self.assertGreater(np.max(abs(actual[~outside]-reference[~outside])),0.)
        self.assertEqual(cfg['correction_window_s'],[0.,.6])
        self.assertEqual(r['request']['protocol'],state(h)['spec']['analysis_protocol'])
        q['control_scope']['window_s']=[.6,.7]
        self.assertEqual(self.compile(h,q)['status'],'needs_choice')

    def test_fixed_input_and_reoptimized_semantics_never_substitute(self):
        h,c=self.prepare();other=generate(h,(.165,.11))
        q=structural_question('fixed_input_response',fixed_input='frozen_initial_tensions',response_horizon_s=.01,
            source_selection=dict(comparison_candidates=[other]))
        r=self.compile(h,q);self.assertEqual(r['status'],'ready')
        self.assertEqual(r['request']['operation'],'fixed_input_structure_v1')
        self.assertEqual(r['request']['structure_response']['variable'],'segments.0.length_m')
        self.assertNotIn('nonlinear_response',r['request'])
        reoptimized=self.compile(h,structural_question('reoptimized_task_capability'))
        self.assertEqual(reoptimized['status'],'needs_prerequisite')
        self.assertIn('T1',reoptimized['reason']);self.assertNotIn('request',reoptimized)
        self.assertEqual(state(h)['mathematical_evaluations'],0)
        for semantics in ('mechanism_effect','closed_loop_performance','re_equilibrated_passive_response'):
            self.assertEqual(self.compile(h,structural_question(semantics))['status'],'unsupported')
        q=structural_question(None);self.assertEqual(self.compile(h,q)['status'],'needs_choice')

    def test_original_parameters_reject_unknown_discrete_ineffective_or_unauthorized(self):
        h,c=self.prepare()
        for path in ('segments.0.unknown','segments.0.cells','tendon_count','tendon_parameters.length_servo_gain_n_m'):
            q=structural_question('reoptimized_task_capability');q['parameter_paths']=[path]
            self.assertEqual(self.compile(h,q)['status'],'unsupported')
        q=structural_question('reoptimized_task_capability');q['parameter_paths']=['segments.0.young_pa']
        self.assertEqual(self.compile(h,q)['status'],'blocked')
        q=control_question(focus_metric='invented_metric')
        self.assertEqual(self.compile(h,q)['status'],'unsupported')

    def test_t2_unique_saved_triplet_and_multiple_stencils_preserve_evidence_cost(self):
        h=question_host();candidates=[generate(h,x) for x in ((.16,.11),(.155,.11),(.165,.11))]
        refs=[offline_dispatch(h,t1_request(h,c),'c2-fixture-t1-'+str(i))['reference'] for i,c in enumerate(candidates)]
        diagnose(h,candidates[0],'scientific_question');before=deepcopy(state(h))
        q=structural_question('reoptimized_task_capability');r=self.compile(h,q)
        self.assertEqual(r['status'],'ready');self.assertEqual(r['request']['operation'],T2_OPERATION)
        self.assertEqual(r['request']['nonlinear_response']['t1_results'],refs)
        self.assertEqual(state(h)['mathematical_evaluations'],before['mathematical_evaluations'])
        result=offline_dispatch(h,r['request'],'c2-t2-aggregate');raw=h.store.artifact(result['reference'])
        self.assertEqual(state(h)['mathematical_evaluations'],4)
        self.assertEqual(raw['nonlinear_response']['cost']['physics_steps'],0)
        self.assertEqual(raw['nonlinear_response']['cost']['reused_t1_results'],3)
        self.assertEqual(raw['nonlinear_response']['direction_status'],'unresolved')
        # Another saved baseline with different search settings is not comparable.
        altered=t1_request(h,candidates[0]);altered['control_optimization']['settings']['evaluation_requests']=5
        offline_dispatch(h,altered,'c2-altered-search')
        self.assertEqual(self.compile(h,q)['status'],'ready')
        # A second admissible symmetric step is a scientific choice, never an arbitrary first match.
        for i,length in enumerate((.15,.17)):
            c=generate(h,(length,.11));offline_dispatch(h,t1_request(h,c),'c2-second-step-'+str(i))
        r=self.compile(h,q);self.assertEqual(r['status'],'needs_choice')
        self.assertEqual(len(r['choices']['t1_results']),2)
        q['source_selection']=dict(t1_results=refs)
        self.assertEqual(self.compile(h,q)['status'],'ready')

    def test_no_candidate_budget_authorization_and_protection_start_no_science(self):
        h=question_host();self.assertEqual(self.compile(h,control_question())['status'],'needs_prerequisite')
        h,c=self.prepare(source=True)
        for mode in ('authorization','budget','protected'):
            original=deepcopy(state(h));spec=deepcopy(original['spec'])
            if mode=='authorization':spec['capabilities']=[];update(h,spec=spec)
            if mode=='budget':update(h,mathematical_evaluations=spec['budgets']['mathematical_evaluations'])
            if mode=='protected':update(h,count_closeout=True)
            before=deepcopy(state(h));r=self.compile(h,control_question())
            self.assertEqual(r['status'],'blocked',r);self.assertEqual(state(h),before)
            update(h,**original)

    def test_mock_wire_diagnose_without_method_loads_question_and_executes_original_request(self):
        h=question_host();c=generate(h);t1_request(h,c)
        plan=dict(action='diagnose',hypothesis='Offline scientific question handoff',expected_observation='Finite budget improvement',
            weakening_observation='No improvement',fixed_conditions='Frozen task and structure',stopping_condition='Fixture only',
            interpretation='Engineering fixture',decision=dict(hypothesis_id='offline-c2',research_intent='DIAGNOSE',selected_candidate=c,requested_budget=0))
        def contained(command,log,timeout,**kwargs):
            request=read(Path(command[-1]));self.assertEqual(request['query']['operation'],T1_OPERATION)
            atomic_json(Path(command[-1]).with_name('result.json'),synthetic_t1(request))
            return SimpleNamespace(returncode=0)
        # Keep this wire test at the C2 execution boundary; Reporter interpretation
        # and subsequent autonomous decisions belong to C3, not this fixture.
        with patch('tools.service_execution._run_contained',side_effect=contained), \
                patch('tools.research.reporter.scientific_feedback',return_value=None):
            wires=run_fixture(h,[('research_plan',plan),('research_analysis',control_question()),None])
        for wire in wires[1:]:
            schema=next(t['function']['parameters'] for t in wire['tools'] if t['function']['name']=='research_analysis')
            self.assertIn('question_type',schema['properties']);self.assertNotIn('operation',schema['properties'])
            self.assertNotIn('AnalysisRequest',json.dumps(schema));self.assertNotIn('LocalControlSearchSettings',json.dumps(schema))
        self.assertEqual(state(h)['mathematical_evaluations'],1)
        events=h.store.events(h.run_id)
        compiled=[h.store.artifact(e['outputs'][0]) for e in events if e['kind']=='analysis_request_binding']
        self.assertEqual(compiled[0]['full_request']['operation'],T1_OPERATION)
        self.assertEqual(compiled[0]['raw_main_input'],control_question())
        self.assertEqual(len([e for e in events if e['kind']=='original_research_plan']),1)
        self.assertEqual(h.store.remaining()['used']['worker_calls'],0)

    def test_c3_three_handoff_nodes_deliver_question_semantics_without_solver_choice(self):
        from tests.research.test_information_flow import packet
        from tests.research.test_p63b5_native_entry import plan
        h=question_host();c=generate(h)
        initialize=plan(c,'initialize_control')
        diagnose_plan=plan(c);diagnose_plan['decision'].pop('selected_method')
        wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='initialize_control')),
            ('research_plan',initialize),('research_route',dict(tool='research_plan',action='diagnose')),
            ('research_plan',diagnose_plan),None])
        before=packet(wires[0])['tool_continuation']
        self.assertEqual(before['direct_plan']['action'],'diagnose')
        self.assertNotIn('decision.selected_method',before['direct_plan']['scientific_fields'])
        self.assertIn('solver name is not required',before['direct_plan']['instruction'])
        init_schema=next(t['function']['parameters'] for t in wires[1]['tools'] if t['function']['name']=='research_plan')
        description=init_schema['$defs']['ControlSeedRequest']['properties']['method']['description']
        self.assertIn('ScientificQuestion',description);self.assertNotIn('candidate and method',description)
        after=packet(wires[2])['tool_continuation']['control_initialization_handoff']
        self.assertTrue(after['control_sources']);self.assertEqual(after['task_acceptance'],'unmeasured')
        self.assertIn('new candidate-bound diagnose',after['next']);self.assertIn('ScientificQuestion',after['next'])
        self.assertNotIn('registered method',after['next'])
        diagnose_schema=next(t['function']['parameters'] for t in wires[3]['tools'] if t['function']['name']=='research_plan')
        self.assertNotIn('selected_method',diagnose_schema['$defs']['ResearchDecision']['required'])
        final=packet(wires[4])['tool_continuation']['analysis_handoff']
        self.assertTrue(final['loaded']);self.assertEqual(final['status'],'diagnose_completed')
        final_schema=next(t['function']['parameters'] for t in wires[4]['tools'] if t['function']['name']=='research_analysis')
        self.assertIn('question_type',final_schema['properties']);self.assertNotIn('operation',final_schema['properties'])
        self.assertEqual(state(h)['mathematical_evaluations'],0);self.assertEqual(state(h)['analysis_results'],[])


if __name__=='__main__':unittest.main()
