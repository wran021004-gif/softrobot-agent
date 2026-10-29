"""Two directed offline checks; no real Provider or scientific Worker."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from uuid import uuid4

from jsonschema import Draft202012Validator
from tools.research import agent,core
from tools.research.config import ROOT
from tools.research.contracts import AnalysisRequest
from tools.research.state import state,update,require_authorization
from tools.research.research_context import agent_decision_brief
from tools.research.task_constraints import mathematical_method_view
from tools.state_io import atomic_json,read
from tests.research.p63b4_prepare import prepare_study,SPECS
from tests.research.test_p63b3_action_interface import provision
from tests.research.test_p63a_math_interface import generate
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_information_flow import packet


class B4PreparationTests(unittest.TestCase):
    def setUp(self):
        for target in ('tools.service_execution._run_contained','extensions.tendon_family.mujoco_analysis.NativeModel'):
            stop=patch(target,side_effect=AssertionError('NO_NATIVE_MODEL_OR_WORKER'))
            stop.start();self.addCleanup(stop.stop)

    def test_protected_provenance_and_conditional_state_sources_on_wire(self):
        h=provision();candidate=generate(h);update(h,count_closeout=True)
        before=deepcopy(state(h));brief=agent_decision_brief(h)
        self.assertIsNone(brief['current_research_state']['object']['provenance_query'])
        self.assertNotIn('provenance_query',brief['current_candidate'])
        with self.assertRaisesRegex(ValueError,'PROTECTED_EVIDENCE_READ'):
            core.read_evidence(h,dict(reference=candidate,view='full',pointer='/provenance'))
        self.assertEqual(state(h),before)
        update(h,count_closeout=False)
        query=agent_decision_brief(h)['current_research_state']['object']['provenance_query']
        self.assertEqual(core.read_evidence(h,query),h.store.artifact(candidate)['provenance'])
        plan=dict(action='diagnose',hypothesis='OFFLINE B4 source condition',expected_observation='Exact inputs shown',
            weakening_observation='Source guidance contradicts Schema',fixed_conditions='Frozen fixture',
            stopping_condition='No computation',interpretation='Synthetic only',supporting_evidence=[],
            decision=dict(hypothesis_id='offline-b4',research_intent='DIAGNOSE',selected_candidate=candidate,
                selected_method='native_dynamics_v1',requested_budget=0))
        wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='diagnose')),('research_plan',plan),None])
        handoff=packet(wires[-1])['tool_continuation']['analysis_handoff']
        schema=next(t['function']['parameters'] for t in wires[-1]['tools'] if t['function']['name']=='research_analysis')
        self.assertEqual(handoff['remaining_scientific_fields'],schema['required'])
        self.assertIn('Top-level',handoff['remaining_scientific_fields_scope'])
        self.assertEqual(handoff['conditional_scientific_inputs'][0]['exactly_one_of'],[['saved_state'],['execution','update_id']])
        points={p['operating_point']:p for p in handoff['operating_point_sources']['operating_points']}
        self.assertEqual(points['saved_state']['readiness'],'missing_exact_state_source')
        self.assertEqual(points['standardized_initial_pretension']['readiness'],'frozen_initialization_available')
        self.assertEqual(handoff['operating_point_sources']['available_source_references'],[])
        Draft202012Validator(schema).validate(dict(operating_point='standardized_initial_pretension'))
        self.assertFalse(Draft202012Validator(schema).is_valid(dict(operating_point='saved_state')))
        atomic_json(ROOT/'runs/p63b4_handoff_check.json',dict(handoff=handoff,schema=schema,
            real_provider_requests=0,workers=0,protected_provenance_query=None))

    def test_prepared_m_and_m0_contract_alignment_budgets_and_no_authorization(self):
        for kind in SPECS:
            cfg=read(ROOT/'configs/research'/SPECS[kind]);cfg['study_id']='p63b4-offline-'+kind.lower()+'-'+uuid4().hex[:8]
            path=ROOT/'configs/research'/('._'+cfg['study_id']+'.json');atomic_json(path,cfg)
            try:h,prepared=prepare_study(kind,path)
            finally:path.unlink()
            s=state(h)
            with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL'):
                require_authorization(h)
            self.assertEqual(s['analysis_results'],[]);self.assertFalse(s.get('control_initializations',[]))
            self.assertFalse(s['results']);self.assertEqual(s['mathematical_evaluations'],0)
            self.assertEqual(h.store.remaining()['used']['model_calls'],0)
            self.assertFalse(any(e['kind']=='formal_study_authorization' for e in h.store.events(h.run_id)))
            self.assertEqual(h.store.artifact(prepared['baseline'])['provenance']['decision_owner'],'Operator')
            if kind=='M':
                self.assertEqual(len(prepared['success_cases']),9)
                self.assertEqual(s['spec']['budgets']['provider_requests'],12)
                self.assertEqual(s['spec']['budgets']['mathematical_evaluations'],4)
            else:
                q=AnalysisRequest.model_validate(prepared['request'])
                Draft202012Validator(AnalysisRequest.model_json_schema()).validate(prepared['request'])
                self.assertEqual(s['spec']['mode'],'engineering_numerical')
                self.assertEqual(s['spec']['budgets']['provider_requests'],0)
                self.assertEqual(prepared['expected_mathematical_evaluations'],3)
                self.assertAlmostEqual(prepared['plus_value']-prepared['base_value'],prepared['h'])
                self.assertAlmostEqual(prepared['base_value']-prepared['minus_value'],prepared['h'])
                self.assertEqual(len(s['candidates']),3)
                self.assertEqual(len({str(r['dimensions']) for r in prepared['alignment']}),1)
                self.assertEqual(prepared['applicability']['status'],'applicable')
                detail=mathematical_method_view(h,prepared['baseline'])['methods'][q.operation]
                self.assertEqual(detail['planning_status'],'unauthorized')
                schema=agent.selected_analysis_schema(q.operation,detail,bound=True)
                variables={k:v for k,v in prepared['request'].items() if k not in ('candidate','operation','model_source','protocol')}
                Draft202012Validator(schema).validate(variables)
                self.assertEqual(len(prepared['result_fields']),5)
            self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
            self.assertEqual(h.store.remaining()['used']['worker_calls'],0)


if __name__=='__main__':unittest.main()
