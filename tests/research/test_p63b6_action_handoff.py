"""Four bounded offline interface checks. Mock wire facts are not research evidence."""
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from tools.research import agent,analysis
from tools.research.config import ROOT
from tools.research.contracts import AnalysisRequest,ControlSeedRequest
from tools.research.nonlinear_capability import T1
from tools.research.physical_replay import seed_control
from tools.research.research_context import agent_decision_brief,read_coverage
from tools.research.state import state,update,guard,core_hashes
from tools.research.task_constraints import mathematical_method_view
from tools.state_io import atomic_json
from tests.research.test_p63a_math_interface import generate,t1_request,diagnose
from tests.research.test_p63b3_action_interface import provision
from tests.research.test_p63b5_native_entry import plan
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_information_flow import packet


class ActionHandoffTests(unittest.TestCase):
    def setUp(self):
        for target in ('tools.service_execution._run_contained','extensions.tendon_family.mujoco_analysis.NativeModel'):
            sentinel=patch(target,side_effect=AssertionError('NO_PROVIDER_OR_SCIENCE_WORKER'))
            sentinel.start();self.addCleanup(sentinel.stop)

    def test_default_actions_explicit_routes_completed_diagnose_and_protection(self):
        h=provision()
        def load(actions=None):
            actions=actions or ['generate','initialize_control','diagnose','stop']
            registry={k:SimpleNamespace(tool_spec={}) for k in ('research_route','evidence_read')}
            registry['research_plan']=SimpleNamespace(tool_spec=dict(inputSchema={'json':agent.plan_schema(actions)}))
            if agent.selected_analysis(h,None):registry['research_analysis']=SimpleNamespace(tool_spec={})
            directory=[dict(tool='research_plan',actions=actions),dict(tool='evidence_read')]
            if 'research_analysis' in registry:directory.append(dict(tool='research_analysis'))
            update(h,pilot={**state(h)['pilot'],'tool_directory':directory})
            return agent.load_selected_tool_schema(h,registry,directory)
        self.assertEqual(load()['plan_action'],'generate')
        c=generate(h);self.assertEqual(load()['plan_action'],'diagnose')
        spec=deepcopy(state(h)['spec']);spec['budgets']['mathematical_evaluations']=0;update(h,spec=spec)
        self.assertEqual(load()['plan_action'],'generate')
        spec['budgets']['mathematical_evaluations']=12;update(h,spec=spec)
        agent.select_tool_route(h,dict(tool='research_plan',action='generate'),'fixture-generate')
        self.assertEqual(load()['plan_action'],'generate')
        agent.select_tool_route(h,dict(tool='research_plan',action='initialize_control'),'fixture-initialize')
        self.assertEqual(load()['plan_action'],'initialize_control')
        pilot=deepcopy(state(h)['pilot']);pilot.pop('tool_route');update(h,pilot=pilot)
        # Remove only fixture route events from selection by using a fresh host.
        h=provision();c=generate(h);diagnose(h,c,T1)
        self.assertEqual(load()['tool'],'research_analysis')
        update(h,count_closeout=True)
        self.assertEqual(load(['stop','select'])['plan_action'],'stop')
        self.assertIsNone(load(['stop','select'])['tool'])

    def test_first_method_read_survives_next_actual_mock_provider_wire(self):
        h=provision();c=generate(h);q=t1_request(h,c)
        query=mathematical_method_view(h,c)['methods'][T1]['detail_query']
        wires=run_fixture(h,[('evidence_read',query),None])
        self.assertEqual(packet(wires[0])['tool_continuation']['direct_plan']['action'],'diagnose')
        delivered=packet(wires[1])['tool_continuation']['pending_feedback']['items'][0]
        facts=(json.loads(delivered['result']['content'][0]['text']) if delivered['delivery']=='exact_feedback'
            else delivered['facts']['selected_value'])
        for key in ('method','scientific_purpose','planning_status','missing','request_template_query',
                'next_submission','scientific_inputs','required_parameters','estimated_evaluations','limitations'):
            self.assertIn(key,facts)
        self.assertEqual(facts['next_submission']['action'],'diagnose')
        inputs=facts['scientific_inputs']
        self.assertEqual(inputs['control_source']['references'],[q['control_optimization']['source']])
        self.assertIn('not structure',inputs['control_source']['role'])
        self.assertEqual(inputs['correction_window_s']['required_interval_s'],[0.,.6])
        self.assertIn('not a duration scalar',inputs['correction_window_s']['form'])
        self.assertIn('Later knots do not shorten',inputs['knots_s'])
        self.assertIn('scoring window are distinct',inputs['knots_s'])
        self.assertIn('pattern requires safety_margin_fraction=0',inputs['method_margin'])
        if delivered['delivery']=='summary_only':self.assertLessEqual(len(json.dumps(delivered['facts']).encode()),3000)
        atomic_json(ROOT/'runs/p63b6_mock_first_method_wire.json',dict(scope='Mock HTTP only; no real Provider or Worker',
            actual_next_request_research=packet(wires[1]),confirmed_delivery=delivered))

    def test_confirmed_method_progress_survives_recent_history_and_tracks_content(self):
        h=provision();c=generate(h);t1_request(h,c)
        query=mathematical_method_view(h,c)['methods'][T1]['detail_query']
        template={**query,'pointer':query['pointer']+'/request_template'}
        parameters=dict(reference=c,view='full',pointer='/parameters')
        run_fixture(h,[('evidence_read',query),('evidence_read',template),('evidence_read',query),
            *[('evidence_read',parameters) for _ in range(4)],None])
        before=agent_decision_brief(h)['current_research_state']
        self.assertEqual(before['methods_read'],[T1]);self.assertEqual(len(before['mathematical_read_progress']),1)
        progress=before['mathematical_read_progress'][0]
        self.assertEqual(progress['action_view'],'delivered')
        self.assertEqual(progress['control_source_prerequisites'],'delivered')
        self.assertEqual(progress['request_template'],'delivered')
        self.assertEqual(progress['diagnose'],'not_submitted')
        self.assertEqual(progress['mathematical_request'],'not_submitted')
        self.assertEqual(progress['relevant_content'],'delivered_fields_unchanged')
        reads=[r for r in read_coverage(h) if r['query']['pointer']==query['pointer']]
        self.assertEqual(reads[-1]['classification'],'exact_repeat')
        self.assertFalse(reads[-1]['complete_data'])
        seed_control(h,ControlSeedRequest(candidate=c,tensions_n=[[.3]*4]),'fixture-new-unmeasured-source')
        after=agent_decision_brief(h)['current_research_state']['mathematical_read_progress'][0]
        self.assertIn('scientific_inputs',after['changed_fields'])
        self.assertEqual(state(h)['analysis_results'],[])

    def test_direct_main_diagnose_loads_schema_and_original_source_admission(self):
        h=provision();c=generate(h);original=t1_request(h,c)
        wires=run_fixture(h,[('research_plan',plan(c)),None])
        final=packet(wires[-1]);handoff=final['tool_continuation']['analysis_handoff']
        self.assertEqual(handoff['diagnose_status'],'completed');self.assertEqual(handoff['selected_method'],T1)
        self.assertTrue(handoff['loaded']);self.assertEqual(final['tool_continuation']['direct_plan']['status'],'completed')
        schema=next(t['function']['parameters'] for t in wires[-1]['tools'] if t['function']['name']=='research_analysis')
        variables=dict(control_optimization=original['control_optimization']);Draft202012Validator(schema).validate(variables)
        full=agent.bind_selected_analysis_request(h,variables,tool_use_id='offline-b6-bound')
        AnalysisRequest.model_validate(full);update(h,core_hashes=core_hashes())
        class BeforeReservation(Exception):pass
        with patch.object(h.store,'reserve',side_effect=BeforeReservation) as reserve:
            with self.assertRaises(BeforeReservation):analysis.dispatch(h,full,'offline-b6-legal',guard=guard)
            reserve.assert_called_once()
        self.assertEqual(state(h)['mathematical_evaluations'],0);self.assertIsNone(state(h)['pending'])


if __name__=='__main__':unittest.main()
