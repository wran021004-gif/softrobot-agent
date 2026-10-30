"""Four bounded offline wire/state checks. Synthetic results are not science."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from tools.research import agent, core
from tools.research.config import ROOT
from tools.research.contracts import AnalysisRequest
from tools.research.design import generate_candidate
from tools.research.nonlinear_capability import T1, T2
from tools.research.research_context import agent_decision_brief
from tools.research.state import state, update, save, readable_results
from tools.research.task_constraints import mathematical_method_view
from tools.state_io import atomic_json, read, digest
from tests.research.test_p63a_math_interface import fixture_host, generate
from tests.research.test_information_flow import packet, generation
from tests.research.test_recent_round_tools import run_fixture


EXAMPLES={}


def provision():
    h=fixture_host();s=state(h)
    scope=dict(study_id=h.run_id,resolved_identity=s['spec']['resolved_identity'],
        execution_scopes=['registered mathematics'])
    save(h,dict(user_approval='OFFLINE FIXTURE ONLY',scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    return h


def example(name, value):
    EXAMPLES[name]=value
    atomic_json(ROOT/'runs/p63b3_mock_examples.json',dict(
        scope='Synthetic Mock HTTP fixtures only; real Provider/math/physical workers = 0',examples=EXAMPLES))


def feedback(h, tool_id):
    rows=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id)
        if e['kind']=='model_original_tool_feedback']
    value=next(r['result'] for r in reversed(rows) if r['tool_use']['toolUseId']==tool_id)
    assert value['status']=='success',value
    return json.loads(value['content'][0]['text'])


class ActionInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.worker=patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_SCIENCE_WORKER'))
        self.worker.start();self.addCleanup(self.worker.stop)

    def test_g_m_protected_stop_query_matches_same_wire_without_permission_change(self):
        audit=read(ROOT/'docs/research/p63b2_gm_sol_audit.json')
        shapes=audit['confirmed_interface_gaps']['protected_stop_query_schema_mismatch']
        for name in ('G','M'):
            observed=next(r for r in shapes if r['test']==name)
            self.assertNotIn(observed['advertised_query']['reference']['artifact_id'],observed['allowed_reference_enum'])
            h=provision()
            if name=='G':
                with patch.object(core,'guard'):core.dispatch(h,generation(h),'offline-g-generation')
                candidate=list(state(h)['candidates'].values())[-1]
                spec=deepcopy(state(h)['spec']);spec.update(capabilities=[],allowed_plan_actions=['generate','stop'])
                spec['budgets']['mathematical_evaluations']=0;update(h,spec=spec)
            else:candidate=generate(h)
            refs=[]
            if name=='M':
                for i in range(2):
                    refs.append(save(h,dict(status='computed',operation='native_dynamics_v1',candidate=candidate,
                        protocol=state(h)['spec']['analysis_protocol'],implementation=state(h)['freeze'],
                        fixture='Synthetic result and source list; no calculation',sources=[candidate],index=i)))
                update(h,analysis_results=refs)
            update(h,count_closeout=True)
            before=deepcopy(state(h));allowed=readable_results(before,h)
            self.assertNotIn(candidate,allowed)
            query=agent_decision_brief(h)['stop_result_index']['query']
            wires=run_fixture(h,[('evidence_read',query),None])
            l0=packet(wires[0]);schema=next(t['function']['parameters'] for t in wires[0]['tools'] if t['function']['name']=='evidence_read')
            self.assertEqual(query,l0['evidence_access']['stop_index']['query'])
            self.assertEqual(query['reference'],before['family_space_reference'])
            Draft202012Validator(schema).validate(query)
            self.assertEqual(set(schema['$defs']['EvidenceRef']['properties']['artifact_id']['enum']),{r['artifact_id'] for r in allowed})
            self.assertEqual(feedback(h,'offline-use-0')['results'],refs)
            self.assertIn('not a complete scientific result body',feedback(h,'offline-use-0')['notice'])
            self.assertEqual(core.read_evidence(h,query,record_read=False),refs)
            with self.assertRaisesRegex(ValueError,'PROTECTED_EVIDENCE_READ'):
                core.read_evidence(h,dict(reference=candidate,view='full'),record_read=False)
            self.assertEqual(state(h)['spec']['budgets'],before['spec']['budgets'])
            self.assertEqual(state(h)['mathematical_evaluations'],0)
            self.assertEqual(packet(wires[0])['current_research_state']['object']['task_acceptance'],'unmeasured')
            example(name+'_closeout',dict(l0=l0['current_research_state'],query=query,
                allowed_reference_enum=schema['$defs']['EvidenceRef']['properties']['artifact_id']['enum'],fresh_results=refs))

    def test_single_method_action_survives_actual_mock_provider_delivery(self):
        h=provision();candidate=generate(h)
        query=dict(reference=candidate,view='mathematical_capabilities',pointer='/methods/fixed_input_structure_v1')
        original=core.read_evidence(h,query,record_read=False)
        wires=run_fixture(h,[('evidence_read',query),None])
        action=feedback(h,'offline-use-0')
        self.assertNotIn('policy',action)
        for key in ('scientific_purpose','applicability','planning_status','missing','required_parameters',
                'required_sources','already_bound','estimated_evaluations','request_template_query','next_submission'):
            self.assertIn(key,action)
        self.assertEqual(core.read_evidence(h,action['request_template_query'],record_read=False),original['request_template'])
        restored={}
        for q in action['full_detail_queries']:
            restored.update(core.read_tool_evidence(h,q,record_read=False))
        self.assertEqual(restored,original)
        delivered=packet(wires[-1])['tool_continuation']['pending_feedback']['items'][0]
        selected=delivered.get('facts',{}).get('selected_value',{})
        if delivered['delivery']=='exact_feedback':selected=json.loads(delivered['result']['content'][0]['text'])
        for key in ('scientific_purpose','missing','request_template_query','next_submission'):
            self.assertEqual(selected[key],action[key])
        directory=core.read_tool_evidence(h,dict(reference=candidate,view='mathematical_capabilities',pointer='/methods'))
        self.assertEqual(directory['policy'],'main_evidence_navigation_v1')
        row=core.read_evidence(h,dict(reference=state(h)['family_space_reference'],view='working_set',pointer='/candidate_index/0'),record_read=False)
        for key,field in (('parameters_query','parameters'),('provenance_query','provenance')):
            self.assertEqual(core.read_evidence(h,row[key],record_read=False),h.store.artifact(candidate)[field])
        from tools.research.experience import retrieve
        search=retrieve(h,dict(operation='search',limit=1))
        self.assertIn('read_query',search['read_guidance'])
        self.assertEqual(search['results'][0]['read_query']['entry_id'],search['results'][0]['entry_id'])
        example('single_method_provider_delivery',dict(query=query,tool_response=action,next_provider_feedback=delivered))

    def test_method_prerequisites_and_original_t1_t2_budget_states(self):
        h=provision();candidate=generate(h);before=deepcopy(state(h))
        methods=mathematical_method_view(h,candidate)['methods']
        fixed=methods['fixed_input_structure_v1']
        self.assertEqual(fixed['planning_status'],'requires_parameters')
        self.assertIn('structure_response.variable',json.dumps(fixed['missing']))
        self.assertIn('structure_response.candidates',json.dumps(fixed['missing']))
        self.assertIn('same-task',json.dumps(fixed['required_sources']))
        self.assertEqual(methods[T1]['planning_status'],'requires_parameters')
        self.assertEqual(methods[T2]['planning_status'],'requires_comparable_t1_results')
        self.assertEqual(methods['native_dynamics_v1']['planning_status'],'ready')
        self.assertEqual(state(h),before)
        update(h,count_closeout=True)
        self.assertEqual(mathematical_method_view(h,candidate)['methods'][T1]['planning_status'],'blocked')
        update(h,count_closeout=False)
        spec=deepcopy(before['spec']);spec['budgets']['mathematical_evaluations']=0;update(h,spec=spec)
        self.assertEqual(mathematical_method_view(h,candidate)['methods'][T1]['planning_status'],'insufficient_budget')
        self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_operator_state_route_diagnose_and_bound_analysis_wire(self):
        h=provision();spec=state(h)['spec']
        candidate=generate_candidate(h,dict(version='serial_family_generation_v2',
            family_space_identity=spec['family_space_identity'],segment_count=2,tendon_count=4),
            dict(decision_owner='Operator',origin='operator_provided_unmeasured_baseline'))['candidate']
        plan=dict(action='diagnose',hypothesis='Synthetic Main question about fixed-input mechanisms',
            expected_observation='Candidate-bound legal mathematical request',weakening_observation='Incompatible state or source',
            fixed_conditions='Frozen task, protocol and physical inputs',stopping_condition='No scientific worker',
            interpretation='Interface fixture only',supporting_evidence=[],
            decision=dict(hypothesis_id='b3-fixture',research_intent='DIAGNOSE',
                selected_candidate=candidate,selected_method='native_dynamics_v1',requested_budget=0))
        query=dict(reference=candidate,view='mathematical_capabilities',pointer='/methods/fixed_input_structure_v1')
        wires=run_fixture(h,[('evidence_read',query),('research_route',dict(tool='research_plan',action='diagnose')),
            ('research_plan',plan),None])
        initial=packet(wires[0])['current_research_state']
        self.assertEqual(initial['object']['origin'],'Operator')
        self.assertTrue(initial['object']['compiled']);self.assertFalse(initial['object']['control_initialized'])
        self.assertFalse(initial['object']['mathematical_result']);self.assertEqual(initial['object']['task_acceptance'],'unmeasured')
        routed=packet(wires[2]);direct=routed['tool_continuation']['direct_plan']
        self.assertEqual(direct['action'],'diagnose');self.assertEqual(direct['status'],'tool_selected_not_submitted')
        self.assertIn('no research_route call is needed',direct['instruction'])
        self.assertEqual(routed['current_research_state']['last_effective_action']['status'],'tool_selected_not_submitted')
        self.assertIn('fixed_input_structure_v1',routed['current_research_state']['methods_read'])
        final=packet(wires[-1]);handoff=final['tool_continuation']['analysis_handoff']
        schema=next(t['function']['parameters'] for t in wires[-1]['tools'] if t['function']['name']=='research_analysis')
        self.assertTrue(handoff['loaded']);self.assertEqual(handoff['method'],'native_dynamics_v1')
        self.assertEqual(handoff['remaining_scientific_fields'],schema['required'])
        self.assertEqual(set(schema['properties']['operating_point']['enum']),{'saved_state','standardized_initial_pretension'})
        payload=dict(operating_point='standardized_initial_pretension')
        Draft202012Validator(schema).validate(payload)
        full=agent.bind_selected_analysis_request(h,payload,tool_use_id='offline-b3-binding')
        self.assertEqual(full['candidate'],candidate);self.assertEqual(full['protocol'],spec['analysis_protocol'])
        self.assertEqual(full['model_source'],'mujoco');AnalysisRequest.model_validate(full)
        self.assertIn('diagnose_plan_completed',final['current_research_state']['completed'])
        self.assertFalse(final['current_research_state']['object']['mathematical_result'])
        self.assertEqual(state(h)['mathematical_evaluations'],0)
        self.assertEqual(h.store.remaining()['used']['worker_calls'],0)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        example('diagnose_analysis_handoff',dict(initial=initial,routed=routed['current_research_state'],
            direct_plan=direct,after_diagnose=final['current_research_state'],analysis_handoff=handoff,
            actual_provider_schema=schema,main_input=payload,full_bound_request=full))


if __name__=='__main__':unittest.main()
