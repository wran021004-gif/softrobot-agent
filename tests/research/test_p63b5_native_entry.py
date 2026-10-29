"""Three offline entry checks; no real Provider, Native model or Worker."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from uuid import uuid4

from jsonschema import Draft202012Validator
from tools.research import agent,analysis,core
from tools.research.config import ROOT
from tools.research.contracts import AnalysisRequest,LocalControlSearchSettings
from tools.research.nonlinear_capability import T1
from tools.research.physical_replay import binding,explicit_control_source
from tools.research.state import state,update,guard,core_hashes,require_authorization
from tools.research.task_constraints import mathematical_method_view
from tools.state_io import atomic_json,read
from tests.research.p63b5_prepare import prepare_study,SPEC
from tests.research.test_p63a_math_interface import generate,t1_request
from tests.research.test_p63b3_action_interface import provision,feedback
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_information_flow import packet


def plan(candidate,action='diagnose'):
    value=dict(action=action,hypothesis='OFFLINE entry fixture',expected_observation='Explicit bound source',
        weakening_observation='Admission rejects source',fixed_conditions='Frozen fixture task',
        stopping_condition='No computation',interpretation='Engineering fixture only',supporting_evidence=[],
        decision=dict(hypothesis_id='offline-b5',research_intent='DIAGNOSE' if action=='diagnose' else 'CONTROL_SEARCH',
            selected_candidate=candidate,selected_method=T1 if action=='diagnose' else 'baseline',requested_budget=0))
    if action=='initialize_control':value['control_seed']=dict(candidate=candidate,method='baseline')
    return value


class NativeEntryTests(unittest.TestCase):
    def setUp(self):
        for target in ('tools.service_execution._run_contained','extensions.tendon_family.mujoco_analysis.NativeModel'):
            stop=patch(target,side_effect=AssertionError('NO_REAL_PROVIDER_MODEL_OR_WORKER'))
            stop.start();self.addCleanup(stop.stop)

    def test_original_source_admission_and_binding_stop_before_reservation(self):
        h=provision();candidate=generate(h);query=t1_request(h,candidate)
        # Fixture-only authorization and implementation snapshot; use the real guard.
        update(h,core_hashes=core_hashes())
        source=h.store.artifact(query['control_optimization']['source'])
        cfg=h.store.artifact(candidate)['configuration'];tr=source['trajectory']
        self.assertTrue(explicit_control_source(source));binding(cfg,tr)
        self.assertEqual(state(h)['control_initializations'][-1]['candidate'],candidate)
        self.assertNotEqual(query['control_optimization']['source'],candidate)
        self.assertEqual(tr['tendon_order'],[t['id'] for t in cfg['robot']['structure']['data']['tendons']])
        self.assertEqual(tr['times_s'],[i*cfg['task']['timing']['control_period_s'] for i in range(31)])
        self.assertEqual(source['task_acceptance'],'unmeasured')
        before=deepcopy(state(h));bad=deepcopy(query);bad['control_optimization']['source']=candidate
        AnalysisRequest.model_validate(bad)  # Reference shape alone is insufficient.
        with self.assertRaisesRegex(ValueError,'BOUND_EXECUTABLE_CONTROL_SOURCE_REQUIRED'):
            analysis.dispatch(h,bad,'offline-b5-bad-source',guard=guard)
        class BeforeReservation(Exception):pass
        with patch.object(h.store,'reserve',side_effect=BeforeReservation) as reserve:
            with self.assertRaises(BeforeReservation):
                analysis.dispatch(h,AnalysisRequest.model_validate(query),'offline-b5-legal',guard=guard)
            reserve.assert_called_once()
        self.assertEqual(state(h),before)
        self.assertEqual(state(h)['mathematical_evaluations'],0)
        self.assertIsNone(state(h)['pending'])

    def test_method_margin_guidance_schema_and_diagnose_initialize_diagnose_wire(self):
        h=provision();candidate=generate(h)
        detail=mathematical_method_view(h,candidate)['methods'][T1]
        action=core.read_tool_evidence(h,detail['detail_query'],record_read=False)
        self.assertIn('control_input_guidance',action)
        self.assertEqual(action['control_input_guidance']['recorded_sources'],[])
        base=dict(version='local_control_search_v2',correction_window_s=[0.,.6],knots_s=[0.,.6])
        for method,margin in (('pattern',0.),('response',0.),('response',.05)):
            LocalControlSearchSettings.model_validate(dict(base,method=method,safety_margin_fraction=margin))
        with self.assertRaisesRegex(ValueError,'SAFETY_MARGIN_REQUIRES_RESPONSE_METHOD'):
            LocalControlSearchSettings.model_validate(dict(base,method='pattern',safety_margin_fraction=.05))
        with self.assertRaisesRegex(ValueError,'SAFETY_MARGIN_REQUIRES_V2_SEARCH'):
            LocalControlSearchSettings(method='response',safety_margin_fraction=.05)
        wires=run_fixture(h,[('research_route',dict(tool='evidence_read')),('evidence_read',detail['detail_query']),
            ('research_route',dict(tool='research_plan',action='diagnose')),
            ('research_plan',plan(candidate)),('research_route',dict(tool='research_plan',action='initialize_control')),
            ('research_plan',plan(candidate,'initialize_control')),
            ('research_route',dict(tool='research_plan',action='diagnose')),('research_plan',plan(candidate)),None])
        self.assertEqual(feedback(h,'offline-use-1')['control_input_guidance'],action['control_input_guidance'])
        initialized=feedback(h,'offline-use-5')['new_facts']['value']
        self.assertEqual(initialized['source'],state(h)['control_initializations'][-1]['source'])
        after=packet(wires[6])['tool_continuation']['control_initialization_handoff']
        self.assertIn('new diagnose',after['next'])
        self.assertNotIn('research_analysis',{t['function']['name'] for t in wires[6]['tools']})
        schema=next(t['function']['parameters'] for t in wires[-1]['tools'] if t['function']['name']=='research_analysis')
        settings=schema['$defs']['LocalControlSearchSettings']['properties']
        self.assertIn('pattern requires',settings['method']['description'])
        self.assertIn('Positive margin requires',settings['safety_margin_fraction']['description'])
        self.assertIn('not the Reach/Hold',settings['correction_window_s']['description'])
        self.assertIn('never the structure candidate',schema['$defs']['NativeControlOptimization']['properties']['source']['description'])
        variables=dict(control_optimization=dict(source=initialized['source'],settings=dict(base,method='pattern')))
        Draft202012Validator(schema).validate(variables)
        full=agent.bind_selected_analysis_request(h,variables,tool_use_id='offline-b5-bound')
        self.assertEqual(full['candidate'],candidate);AnalysisRequest.model_validate(full)
        self.assertEqual(packet(wires[-1])['tool_continuation']['analysis_handoff']['control_input_guidance'],
            mathematical_method_view(h,candidate)['methods'][T1]['control_input_guidance'])
        self.assertEqual(state(h)['analysis_results'],[])

    def test_independent_preparation_operator_inputs_no_authorization_or_science(self):
        cfg=read(ROOT/'configs/research'/SPEC);cfg['study_id']='p63b5-offline-'+uuid4().hex[:8]
        path=ROOT/'configs/research'/('._'+cfg['study_id']+'.json');atomic_json(path,cfg)
        try:h,prepared=prepare_study(path)
        finally:path.unlink()
        s=state(h)
        with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL'):require_authorization(h)
        self.assertEqual(len(s['candidates']),1);self.assertEqual(len(s['control_initializations']),1)
        self.assertEqual(h.store.artifact(prepared['baseline'])['provenance']['decision_owner'],'Operator')
        self.assertEqual(h.store.artifact(prepared['control_operator_provenance'])['decision_owner'],'Operator')
        binding(h.store.artifact(prepared['baseline'])['configuration'],
            h.store.artifact(prepared['control_initialization']['source'])['trajectory'])
        self.assertEqual(s['plans'],[]);self.assertEqual(s['analysis_results'],[]);self.assertEqual(s['results'],[])
        self.assertEqual(s['mathematical_evaluations'],0);self.assertIsNone(s['pending'])
        self.assertEqual(h.store.remaining()['used']['model_calls'],0)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        self.assertEqual(h.store.remaining()['used']['worker_calls'],0)
        self.assertEqual(s['spec']['budgets']['provider_requests'],12)
        self.assertEqual(s['spec']['budgets']['mathematical_evaluations'],4)
        self.assertEqual(prepared['provider'],dict(model='gpt-5.6-sol',reasoning='none'))
        self.assertEqual(s['spec']['research_decisions']['mathematics'],[])
        self.assertFalse(any(e['kind'] in ('formal_study_authorization','live_handoff_admission') for e in h.store.events(h.run_id)))


if __name__=='__main__':unittest.main()
