"""P6.1 synthetic protocol fixtures only; no real Provider or scientific worker."""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import httpx
from jsonschema import Draft202012Validator
from tools.platform_store import plain
from tools.research import agent, reporter
from tools.research.config import ROOT, information_flow_v1, validate_conversation_policy
from tools.research.contracts import Plan, EvidenceQuery, ExperienceQuery, ResearchRecallQuery
from tools.research.evidence_policy import admit_decision, citation_role, citation_inventory, registered_references
from tools.research.experience import retrieve, read_progress
from tools.research.provider import provider_schema
from tools.research.research_context import (research_action_trace, milestone_trace, research_recall,
    agent_decision_brief, research_decision_brief_v3, information_flow_brief)
from tools.research.state import state, update, save
from tests.research.test_recent_round_tools import provision, run_fixture
from tests.research import test_s129_agent_reporting as reporting_tests


def flow_host():
    h=provision();spec=deepcopy(state(h)['spec'])
    spec['research_decisions'].update(tool_schema_policy=dict(version='research_information_flow_v1'),
        language_policy=dict(version='english_sources_v1',authored_language='en'))
    update(h,spec=spec)
    return h


def generation(h):
    return dict(action='generate',generation=dict(version='serial_family_generation_v2',
        family_space_identity=state(h)['spec']['family_space_identity'],segment_count=2,tendon_count=4),
        hypothesis='Synthetic offline candidate hypothesis.',expected_observation='Legal candidate.',
        weakening_observation='Generation fails frozen constraints.',fixed_conditions='Frozen fixture domain.',
        stopping_condition='No scientific computation.',interpretation='Task acceptance unmeasured.',supporting_evidence=[],
        decision=dict(hypothesis_id='offline-p61',research_intent='DESIGN_MODIFICATION',selected_method='generate'))


def packet(wire):
    return json.loads(wire['messages'][-1]['content'].split('\n',1)[1])['research']


class InformationFlowTests(unittest.TestCase):
    def test_direct_reads_preserve_generate_and_stable_prompt(self):
        h=flow_host();ref=state(h)['family_space_reference']
        wires=run_fixture(h,[('evidence_read',dict(reference=ref,view='working_set',pointer='/candidate_index')),
            ('research_plan',generation(h)),('research_recall',dict(trace='milestones')),None])
        for wire in wires:
            names={t['function']['name'] for t in wire['tools']}
            self.assertTrue({'research_plan','evidence_read','research_recall','experience_retrieve','research_investigate'}<=names)
            for tool in wire['tools']:
                schema=tool['function']['parameters'];Draft202012Validator.check_schema(schema)
                self.assertFalse({'allOf','anyOf','oneOf','not'} & schema.keys())
        self.assertTrue(all(w['messages'][0]==wires[0]['messages'][0] for w in wires))
        first=packet(wires[0]);last=packet(wires[-1])
        self.assertEqual(first['version'],'research_information_flow_v1')
        self.assertEqual(len(first['capabilities']),5)
        self.assertEqual(first['evidence_access']['citation_eligibility']['scientific_result_count'],0)
        self.assertIsNone(first['research_focus']['candidate'])
        self.assertEqual(last['research_focus']['formal_hypothesis']['hypothesis_id'],'offline-p61')
        self.assertTrue(last['research_focus']['candidate'])
        self.assertEqual(last['tool_continuation']['loaded']['plan_action'],'generate')
        for field in ('current_intent','history_trace','research_state','recent_round'):
            self.assertNotIn(field,last)
        self.assertEqual(len(state(h)['plans']),1)
        self.assertEqual(h.store.remaining()['used']['worker_calls'],0)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        trace=research_action_trace(h,limit=None);milestones=milestone_trace(trace)
        self.assertTrue(milestones['recent']);self.assertTrue(all(r in trace['recent'] for r in milestones['recent']))
        before=deepcopy(state(h))
        page=research_recall(h,dict(trace='milestones',limit=1))
        self.assertEqual(page['items'][0]['source'],milestones['recent'][0]['source'])
        detail=research_recall(h,dict(step=page['items'][0]['step'],view='details'))
        self.assertFalse(detail['formal_read_credit']);self.assertEqual(state(h),before)

    def test_protected_closeout_keeps_reads_stop_and_no_science(self):
        h=flow_host();update(h,count_closeout=True)
        wire=run_fixture(h,[None])[0];value=packet(wire)
        names={t['function']['name'] for t in wire['tools']}
        self.assertTrue({'research_plan','evidence_read'}<=names)
        self.assertFalse({'research_investigate','research_analysis','experience_retrieve'} & names)
        self.assertEqual(value['tool_continuation']['loaded']['plan_action'],'stop')
        self.assertTrue(value['budget']['closeout'])
        self.assertEqual(state(h)['plans'],[])

    def test_domain_role_empty_exploration_and_unchanged_formal_gates(self):
        h=flow_host();ref=state(h)['family_space_reference'];raw=generation(h)
        self.assertEqual(citation_role(h,ref),'domain_reference')
        self.assertEqual(citation_inventory(h),[])
        self.assertIsNotNone(admit_decision(h,Plan.model_validate(raw)))
        minimal=dict(artifact_id=ref['artifact_id'])
        self.assertEqual(citation_role(h,minimal),'domain_reference')
        raw['supporting_evidence']=[minimal]
        with self.assertRaisesRegex(ValueError,'UNREGISTERED_RESEARCH_EVIDENCE') as failed:
            admit_decision(h,Plan.model_validate(raw))
        feedback=agent.error_feedback(h,dict(name='research_plan',input=raw,toolUseId='bad-domain'),failed.exception,state(h))
        self.assertEqual(feedback['citation_errors'][0]['role'],'domain_reference')
        self.assertIn('supporting_evidence=[]',feedback['citation_errors'][0]['correction'])
        raw=generation(h);raw.pop('generation');raw.update(action='stop')
        raw['decision'].update(research_intent='STOP',claimed_inference='observed_task_pass')
        with self.assertRaisesRegex(ValueError,'INFERENCE_NOT_SUPPORTED'):
            admit_decision(h,Plan.model_validate(raw))

    def test_english_knowledge_actual_read_and_persistent_progress(self):
        h=flow_host();before=registered_references(h)
        found=retrieve(h,dict(operation='search'))
        self.assertTrue(found['results'])
        self.assertTrue(all(r['authored_language']=='en' for r in found['results']))
        row=next(r for r in found['results'] if r['entry_id']=='research-strict-near-tolerance')
        self.assertEqual(row['revision'],'2')
        actual=retrieve(h,dict(operation='read',entry_id=row['entry_id'],revision=row['revision']))
        self.assertFalse(actual['scientific_evidence'])
        content=actual['results'][0]['content']
        self.assertNotIn('reviewed_by',content['language_origin'])
        for source in content['evidence']:
            blob=subprocess.check_output(['git','show',source['source_commit']+':'+source['path']],cwd=ROOT)
            self.assertEqual(hashlib.sha256(blob).hexdigest(),source['sha256'])
        for fact in content['historical_facts']:
            source=content['evidence'][fact['evidence_index']];value=json.loads(subprocess.check_output(['git','show',source['source_commit']+':'+source['path']],cwd=ROOT))
            for token in fact['pointer'].strip('/').split('/'):value=value[token]
            self.assertEqual(fact['value'],value)
        progress=read_progress(h);self.assertTrue(progress['reads'][0]['tool_read_completed'])
        self.assertFalse(progress['reads'][0]['body_delivered'])
        from tools.platform_host import Host
        restored=Host(h.store.root,run_id=h.run_id)
        self.assertEqual(read_progress(restored),progress)
        self.assertEqual(registered_references(h),before)
        with self.assertRaisesRegex(ValueError,'EXPERIENCE_REQUIRES_REVIEWED_ENGLISH_SOURCE'):
            retrieve(h,dict(operation='read',entry_id=row['entry_id'],revision='1'))

    def test_version_and_all_focused_action_schemas(self):
        h=flow_host();spec=state(h)['spec'];validate_conversation_policy(spec['research_decisions'])
        for action in ('generate','initialize_control','diagnose','select','stop'):
            canonical=agent.plan_schema([action],decision_required=True,focused=True,study=spec,
                family_version=spec['family_space']['version'],diagnose_candidate_required=True)
            projected=provider_schema(canonical)
            Draft202012Validator.check_schema(projected)
            self.assertFalse({'allOf','anyOf','oneOf','not'} & projected.keys())
            self.assertEqual(provider_schema(projected),projected)
            payload=generation(h)
            self.assertEqual(Draft202012Validator(canonical).is_valid(payload),Draft202012Validator(projected).is_valid(payload))
            if action in ('stop','select'):
                self.assertIn('No new design hypothesis',canonical['properties']['hypothesis']['description'])
        for contract in (EvidenceQuery,ExperienceQuery,ResearchRecallQuery,reporter.InvestigationRequest):
            Draft202012Validator.check_schema(provider_schema(contract.model_json_schema()))
        query=dict(reference=state(h)['family_space_reference'],view='fields')
        self.assertFalse(Draft202012Validator(provider_schema(EvidenceQuery.model_json_schema())).is_valid(query))
        query['fields']=['version']
        self.assertTrue(Draft202012Validator(provider_schema(EvidenceQuery.model_json_schema())).is_valid(query))
        self.assertFalse(information_flow_v1({'research_decisions':{'tool_schema_policy':{'version':'on_demand_tools_v3'}}}))

    def test_new_packet_confirms_exact_reads_and_knowledge_delivery(self):
        from tools.research.research_context import read_coverage
        from tools.research.session_handoff import pending_feedback_delivery
        h=flow_host();ref=save(h,dict(fixture='Exact read, not scientific evidence',values=list(range(1200))))
        wires=run_fixture(h,[('evidence_read',dict(reference=ref,view='full')),
            ('experience_retrieve',dict(operation='read',entry_id='research-strict-near-tolerance',revision='2')),None])
        reads=[r for r in read_coverage(h) if r.get('tool_call_id')=='offline-use-0']
        self.assertTrue(reads[0]['successfully_provided']);self.assertTrue(reads[0]['full_artifact'])
        self.assertIsNone(pending_feedback_delivery(h))
        self.assertTrue(read_progress(h)['reads'][0]['body_delivered'])
        self.assertIn('pending_feedback',packet(wires[1])['tool_continuation'])

    def test_pending_native_submission_is_in_trace_without_execution_claim(self):
        h=flow_host()
        agent.record(h,'model_original_tool_request',dict(tool_use=dict(name='research_analysis',toolUseId='pending-math',
            input=dict(operation='native_dynamics_v1'))))
        trace=research_action_trace(h,limit=None)
        self.assertEqual(trace['total'],1)
        self.assertEqual(trace['recent'][0]['execution_status'],'pending')
        self.assertEqual(trace['recent'][0]['result_references'],[])
        self.assertEqual(milestone_trace(trace)['total'],1)

    def test_selected_analysis_saved_state_exclusivity_survives_projection(self):
        detail=dict(operation='native_dynamics_v1',request_template={'model_source':'mujoco'},required_parameters=[])
        canonical=agent.selected_analysis_schema('fixture-native',detail,bound=True)
        wire=provider_schema(canonical);Draft202012Validator.check_schema(wire)
        self.assertNotIn('allOf',wire)
        from typing import get_args
        from tools.research.contracts import AnalysisRequest
        for operation in get_args(AnalysisRequest.model_fields['operation'].annotation):
            for bound in (False,True):
                schema=agent.selected_analysis_schema(operation,dict(operation=operation,request_template={},required_parameters=[]),bound=bound)
                projected=provider_schema(schema);Draft202012Validator.check_schema(projected)
                self.assertFalse({'allOf','anyOf','oneOf','not'} & projected.keys(),operation)
        ref={'artifact_id':'a'*64}
        cases=[(dict(operating_point='standardized_initial_pretension'),True),
            (dict(operating_point='saved_state',saved_state=ref),True),
            (dict(operating_point='saved_state',execution=ref,update_id=0),True),
            (dict(operating_point='saved_state'),False),
            (dict(operating_point='saved_state',execution=ref,update_id=0,saved_state=ref),False),
            (dict(operating_point='standardized_initial_pretension',saved_state=ref),False)]
        for value,valid in cases:
            self.assertEqual(Draft202012Validator(canonical).is_valid(value),valid,value)
            self.assertEqual(Draft202012Validator(wire).is_valid(value),valid,value)

    def test_real_sdk_projects_selected_analysis_and_preserves_canonical_schema(self):
        from types import SimpleNamespace
        from tools.research.provider import build_model,live_model_class
        h=flow_host();schema=agent.selected_analysis_schema('fixture-native',
            dict(operation='native_dynamics_v1',request_template={'model_source':'mujoco'},required_parameters=[]),bound=True)
        canonical=deepcopy(schema)
        model=build_model(state(h)['pilot']['provider'],api_key='offline',
            transport=httpx.MockTransport(lambda r:self.fail('Formatting must not send')),
            model_class=live_model_class(SimpleNamespace(host=h)))
        spec=dict(name='research_analysis',description='Offline schema fixture',inputSchema={'json':schema})
        wire=model.format_request([dict(role='user',content=[dict(text='Offline')])],[spec],'Fixed instructions')
        self.assertEqual(schema,canonical)
        projected=wire['tools'][0]['function']['parameters']
        self.assertNotIn('allOf',projected)
        self.assertFalse(Draft202012Validator(projected).is_valid(dict(operating_point='saved_state')))
        asyncio.run(model._custom_client.close())

    def test_milestone_pagination_retains_failures_and_terminal_events(self):
        h=flow_host();run_fixture(h,[('research_plan',{'action':'stop'}),('research_plan',generation(h)),None])
        trace=research_action_trace(h,limit=None)
        self.assertEqual([r['execution_status'] for r in trace['recent']],['rejected','completed'])
        first=research_recall(h,dict(limit=1));second=research_recall(h,dict(offset=first['next_offset'],limit=1))
        self.assertNotEqual(first['items'][0]['step'],second['items'][0]['step'])
        self.assertIsNone(second['next_offset'])
        self.assertEqual(milestone_trace(trace)['total'],2)


class DelegatedReadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):reporting_tests.AgentReportingTests.setUpClass()

    def setUp(self):
        self.fixture=reporting_tests.AgentReportingTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.h=self.fixture.h

    def test_optional_reads_exact_values_deltas_sources_and_no_credit(self):
        ref=self.fixture.physical();raw=self.h.store.artifact(ref);other=deepcopy(raw)
        other['acceptance']['components']['holding_speed']['value']=.05
        second=self.fixture.put(other);update(self.h,physical_replays=[ref,second])
        before=deepcopy(state(self.h));known=registered_references(self.h)
        result=reporter.investigate(self.h,dict(question='Extract speed values and the comparable difference.',references=[second,ref]))
        saved=self.h.store.artifact(result['report_reference'])
        self.assertTrue(saved['request']['selected_reads'])
        summary=reporter.reporter_handoff_summary(self.h,result['report_reference'],saved)
        delta=next(r for r in summary['findings'][0]['comparisons'][0]['metrics'] if r['metric']=='holding_speed')
        self.assertAlmostEqual(delta['delta'],.01);self.assertEqual(delta['unit'],'m/s')
        self.assertTrue(delta['comparable'])
        self.assertEqual(reporter.read_evidence(self.h,delta['source'],record_read=False),.05)
        wire=reporter._wire(self.h,result['report_reference'],saved)
        self.assertEqual(len(wire['messages']),2);self.assertNotIn('tools',wire)
        payload=json.loads(wire['messages'][-1]['content']);self.assertTrue(payload['source_catalog'])
        self.assertEqual(registered_references(self.h),known);self.assertEqual(state(self.h),before)
        # An explicit repeated question retains normal Reporter priority.
        self.assertEqual(reporter.interpretation_priority(saved['report'],[saved['report']],decision_v3=True),'explicit_investigation')
        repeated=reporter.investigate(self.h,dict(question='Extract speed values and the comparable difference.',references=[second,ref]))
        self.assertNotEqual(repeated['report_reference'],result['report_reference'])
        asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(reporting_tests.reporter_response)))
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],2)
        self.assertEqual([saved['interpretation_status'] for _,saved in reporter.current_reports(self.h)],['available','available'])

    def test_exact_read_missing_path_and_budget_fallback_keep_facts(self):
        ref=self.fixture.physical()
        request=dict(question='Extract the exact speed and report any missing solver record.',references=[ref],reads=[
            dict(reference=ref,view='fields',pointer='/acceptance/components/holding_speed',fields=['value','unit','limit']),
            dict(reference=ref,view='full',pointer='/not_recorded')])
        initial=reporter.investigate(self.h,request);saved=self.h.store.artifact(initial['report_reference'])
        selected=saved['request']['selected_reads']
        self.assertEqual(selected[0]['value']['value'],.04)
        self.assertEqual(selected[1]['status'],'unavailable');self.assertTrue(selected[1]['suggested_query'])
        spec=deepcopy(state(self.h)['spec']);spec['budgets']['protected_provider_requests']=self.h.store.remaining()['remaining']['model_calls']
        update(self.h,spec=spec)
        asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(lambda r:self.fail('No Provider request allowed'))))
        latest_ref,latest=reporter.current_reports(self.h)[-1]
        self.assertEqual(latest['interpretation_status'],'unavailable')
        self.assertEqual(latest['report'],saved['report'])
        self.assertTrue(reporter.reporter_handoff_summary(self.h,latest_ref,latest)['findings'][0]['metrics'])
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],0)

    def test_incomparable_math_and_physical_remain_distinct_l0_states(self):
        physical=self.fixture.physical();math=self.fixture.put(self.fixture.f.math_result())
        update(self.h,analysis_results=[math])
        self.assertEqual(citation_role(self.h,physical),'independent_evaluation')
        self.assertEqual(citation_role(self.h,math),'scientific_result')
        report=reporter.assemble(self.h,[math,physical],question='Compare mathematical and physical scope.')
        self.assertIsNot(report.relations[0].comparable,True)
        for ref in (math,physical):
            delivery=reporter.scientific_feedback(self.h,dict(reference=ref))
            saved=self.h.store.artifact(delivery['report_reference'])
            summary=reporter.reporter_handoff_summary(self.h,delivery['report_reference'],saved)
            brief=dict(latest_reports=[summary],actions=[],task={},budget={},current_candidate={},
                additional_mathematical_evidence=[])
            l0=information_flow_brief(brief,research_decision_brief_v3(brief))
            self.assertTrue(l0['verified_facts'])
            self.assertEqual(l0['reporter_findings'][0]['result_references'],[ref])
            self.assertFalse(l0['research_focus']['open_questions'])
            self.assertIsNone(l0['research_focus']['task_accepted'])


if __name__=='__main__':unittest.main()
