"""Offline scientific discovery and actual SDK wire; no numerical execution."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from tools.research import agent,core
from tools.research.contracts import EvidenceIntentQuery, EvidenceReadQuery
from tools.research.state import state,update
from tools.research.object_choices import main_projection
from tests.research.test_p63c2_scientific_intent import question_host
from tests.research.test_p63a_math_interface import generate
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_information_flow import packet


def all_pages(h,q):
    pages=[]
    while q:
        page=core.read_tool_evidence(h,q);pages.append(page)
        q=page.get('next_query')
        if len(pages)>100:raise AssertionError('Pagination made no progress')
    return pages


def capture_schemas(wires,label):
    from tools.research.config import ROOT
    directory=ROOT/'runs/semantic-evidence-wire-captures';directory.mkdir(exist_ok=True)
    schemas={t['function']['name']:t['function']['parameters'] for t in wires[0]['tools']
        if t['function']['name'] in ('evidence_read','research_investigate')}
    (directory/(label+'.json')).write_text(json.dumps(dict(scope='Actual SDK Mock HTTP Schema; no real Provider.',schemas=schemas),indent=2),encoding='utf-8')


class SemanticEvidenceTests(unittest.TestCase):
    def setUp(self):
        for name in ('tools.service_execution._run_contained','mujoco.mj_step',
                'extensions.tendon_family.mujoco_analysis.NativeModel'):
            p=patch(name,side_effect=AssertionError('NO_WORKER_OR_PHYSICS_ALLOWED'));p.start();self.addCleanup(p.stop)

    def host(self):
        h=question_host();c=generate(h);return h,c

    def test_active_structure_parameters_methods_and_raw_compatibility(self):
        h,c=self.host();before=deepcopy(state(h));used=h.store.remaining()
        for topic in ('structure','structure_parameters','task','mechanism_capabilities','mathematical_methods','mathematical_results'):
            pages=all_pages(h,dict(subject='current_candidate',topic=topic))
            self.assertTrue(all(not p['formal_read_credit'] for p in pages))
            self.assertTrue(all(p['subject']==c for p in pages))
            for page in pages:
                for source in page['sources']:core.read_evidence(h,source,record_read=False)
        rows=[r for p in all_pages(h,dict(subject=c,topic='structure_parameters')) for r in p['facts']]
        group=rows[0]['parameter_group']
        chosen=core.read_tool_evidence(h,dict(subject=c,topic='structure_parameters',group=group))
        self.assertTrue(all(r['parameter_group']==group for r in chosen['facts']))
        exact=core.read_tool_evidence(h,dict(reference=c,view='fields',pointer='/parameters',fields=['segment_count']),record_read=False)
        self.assertEqual(exact['segment_count'],2)
        self.assertEqual(state(h),before);self.assertEqual(h.store.remaining(),used)

    def test_unknown_ambiguous_foreign_and_mixed_queries(self):
        h,c=self.host()
        with self.assertRaises(ValueError):core.read_tool_evidence(h,dict(subject=c,topic='invented'))
        groups=core.read_tool_evidence(h,dict(subject=c,topic='structure_parameters',group='material'))
        self.assertEqual(groups['status'],'selection_required')
        self.assertTrue(groups['choices'])
        with self.assertRaisesRegex(ValueError,'NOT_REGISTERED_IN_STUDY'):
            core.read_tool_evidence(h,dict(subject=dict(artifact_id='f'*64),topic='structure'))
        with self.assertRaises(ValueError):EvidenceReadQuery.model_validate(dict(subject=c,topic='structure',pointer='/parameters'))
        for q in (dict(subject=c,topic='structure'),dict(reference=c,view='full')):
            EvidenceReadQuery.model_validate(q);Draft202012Validator(agent.evidence_query_schema(state(h)['spec'])).validate(q)

    def test_page_handle_pins_subject_scope_content_and_projection(self):
        h,c=self.host();q=dict(subject=c,topic='structure_parameters')
        first=core.read_tool_evidence(h,q);nxt=first['next_query']
        self.assertEqual(main_projection(h,nxt)['continuation'],nxt['continuation'])
        self.assertEqual(core.read_tool_evidence(h,nxt)['status'],'available')
        bad=deepcopy(nxt);bad['topic']='mathematical_methods'
        with self.assertRaisesRegex(ValueError,'SCOPE_MISMATCH'):core.read_tool_evidence(h,bad)
        bad=deepcopy(nxt);bad['continuation']['content_identity']='stale'
        with self.assertRaisesRegex(ValueError,'STALE_EVIDENCE'):core.read_tool_evidence(h,bad)
        bad=deepcopy(nxt);bad['continuation']['study_id']='other'
        with self.assertRaisesRegex(ValueError,'SCOPE_MISMATCH'):core.read_tool_evidence(h,bad)

    def test_actual_main_schema_feedback_and_sdk_resume(self):
        h,c=self.host()
        q=dict(subject=c,topic='structure_parameters')
        nxt=core.read_tool_evidence(h,q)['next_query']
        wires=run_fixture(h,[('evidence_read',q),('evidence_read',nxt),('evidence_read',dict(subject=c,topic='mathematical_methods')),None])
        capture_schemas(wires,'active')
        schema=next(t['function']['parameters'] for t in wires[0]['tools'] if t['function']['name']=='evidence_read')
        self.assertIn('EvidenceIntentQuery',schema['$defs'])
        for wire in wires:
            self.assertIn('scientific_queries',packet(wire)['evidence_access'])
        self.assertIn('evidence_continuation_v1',json.dumps(wires[1]))
        self.assertIn('semantic_evidence_v1',json.dumps(wires[1]))
        self.assertNotIn('SCOPE_MISMATCH',json.dumps(wires))
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_passive_v2_registered_mechanisms_and_v4_preparation(self):
        from tests.research.test_passive_program_v2 import prepared_host_v2
        from tools.research.scientific_intent import question_schema
        h,c=prepared_host_v2(mathematical_budget=5)
        structure=all_pages(h,dict(subject=c,topic='structure'))
        facts={k:v for p in structure for k,v in p['facts'].items()}
        self.assertEqual(len(facts['fixed_payout_lengths_m']),1)
        mechanisms=all_pages(h,dict(subject=c,topic='mechanism_capabilities'))
        facts={k:v for p in mechanisms for k,v in p['facts'].items()}
        self.assertIn('finite_time_response',facts)
        self.assertEqual(facts['finite_time_response']['effect_semantics'],'finite_time_task_response')
        primitives=all_pages(h,dict(subject=c,topic='mechanism_capabilities',group='primitives'))
        self.assertIn('constraint_length_residual',{k for p in primitives for k in p['facts']})
        params=[r for p in all_pages(h,dict(subject=c,topic='structure_parameters')) for r in p['facts']]
        self.assertTrue(any(r['selectable'] for r in params))
        self.assertEqual(state(h)['spec']['research_decisions']['analysis_interface'],'scientific_question_v4')
        schema=question_schema(state(h)['spec'],h.store.artifact(c))
        self.assertIn('structure',schema['properties'])
        wires=run_fixture(h,[('research_route',dict(tool='evidence_read')),
            ('evidence_read',dict(subject=c,topic='mechanism_capabilities')),None])
        capture_schemas(wires[1:],'passive')
        self.assertIn('finite_time_task_response',json.dumps(wires[-1]))
        self.assertEqual(packet(wires[-1])['research_focus']['control']['status'],'not_applicable')
        used=h.store.remaining()['used'];self.assertEqual(used['backend_solves'],0)
        self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_m5_constraints_methods_and_sdk_discovery(self):
        from tests.research.test_p63a_math_interface import fixture_host
        from tests.research.test_research_authorization_preflight import approve
        from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
        from tools.research.config import ROOT
        from tools.state_io import read
        execution=read(ROOT/'configs/research/study_p4_m5_autonomy.json')['family_execution']
        h=fixture_host(task='bf5_position_tool_axis_v1.json',family_execution=execution,control='control_bf5_tool_axis.json');c=generate(h)
        approve(h,[REGISTERED_MATHEMATICS_SCOPE])
        task={k:v for p in all_pages(h,dict(subject=c,topic='task')) for k,v in p['facts'].items()}
        self.assertIn('tool_axis',json.dumps(task))
        self.assertEqual(task['frozen_task']['family'],'task.position_tool_axis')
        methods=[r for p in all_pages(h,dict(subject=c,topic='mathematical_methods')) for r in p['facts']]
        by_id={r['id']:r for r in methods}
        self.assertEqual(by_id['task_capability']['planning_status'],'unsupported')
        self.assertIn('mujoco_direct_control_v1',by_id)
        wires=run_fixture(h,[('evidence_read',dict(subject=c,topic='task')),('evidence_read',dict(subject=c,topic='mathematical_methods')),None])
        self.assertIn('tool_axis',json.dumps(wires[-1]))
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_reporter_semantic_sources_and_next_main_explanation(self):
        import asyncio,httpx
        from tools.research import reporter
        from tools.research.state import save
        from tests.research.test_s129_agent_reporting import reporter_response
        h,c=self.host()
        before=deepcopy(state(h).get('evaluation_reads',[]))
        outcome=reporter.investigate(h,dict(question='Explain the registered structural and material mechanisms.',
            subject=c,focus=['effective continuous parameters','registered mechanism prerequisites']))
        saved=h.store.artifact(outcome['report_reference'])
        self.assertTrue(saved['request']['selected_reads'])
        self.assertTrue(all('topic' in q for q in saved['request']['reads']))
        wire=reporter._wire(h,outcome['report_reference'],saved)
        payload=json.loads(wire['messages'][-1]['content'])
        for source in payload['source_catalog'].values():core.read_evidence(h,source,record_read=False)
        self.assertTrue(any('/configuration' in loc['pointer'] for loc in payload['source_catalog'].values()))
        self.assertTrue(any('facts' in (r.get('value') or {}) for r in payload['selected_reads']))
        with patch('tools.research.provider.credential',return_value='offline'):
            asyncio.run(reporter.complete_reports(h,httpx.MockTransport(reporter_response)))
        current=reporter.current_reports(h)[-1]
        self.assertEqual(current[1]['interpretation_status'],'available',current[1].get('error'))
        wires=run_fixture(h,[None])
        findings=packet(wires[0])['reporter_findings']
        self.assertTrue(findings[-1]['interpretations'])
        self.assertEqual(state(h).get('evaluation_reads',[]),before)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_semantic_compaction_keeps_cursor_and_no_formal_credit(self):
        from tools.research.session_handoff import selected_evidence_facts
        h,c=self.host();query=dict(subject=c,topic='structure_parameters')
        value=core.read_tool_evidence(h,query)
        compact=selected_evidence_facts(value,query,1700)
        self.assertEqual(compact['next_query'],value['next_query'])
        self.assertFalse(compact['formal_read_credit'])
        self.assertFalse(compact['scientific_result_created'])
        self.assertEqual(core.read_tool_evidence(h,compact['next_query'])['status'],'available')

    def test_changed_projection_rejects_old_cursor_and_pins_old_candidate(self):
        from tools.research.scientific_intent import parameter_catalog
        h,c=self.host();q=dict(subject='current_candidate',topic='structure_parameters')
        first=core.read_tool_evidence(h,q);nxt=first['next_query']
        generate(h,lengths=(.17,.11))
        self.assertEqual(core.read_tool_evidence(h,nxt)['subject'],c)
        rows=parameter_catalog(state(h)['spec'],h.store.artifact(c));changed=deepcopy(rows)
        changed[0]['current_value']='changed registered projection fixture'
        with patch('tools.research.scientific_intent.parameter_catalog',return_value=changed):
            with self.assertRaisesRegex(ValueError,'STALE_EVIDENCE_CONTINUATION'):core.read_tool_evidence(h,nxt)

    def test_semantic_physical_read_never_grants_select_and_raw_guard_remains(self):
        from tests.research.test_p63g_bounded_evidence import bounded_host,BoundedEvidenceTests
        from tools.research.feedback import eligibility
        from tools.research.state import save
        h=bounded_host();c,ref=BoundedEvidenceTests().physical(h)
        before=deepcopy(state(h).get('evaluation_reads',[]))
        pages=all_pages(h,dict(subject=ref,topic='physical_results'))
        self.assertTrue(all(not p['formal_read_credit'] for p in pages))
        self.assertEqual(state(h).get('evaluation_reads',[]),before)
        self.assertFalse(eligibility(h,ref,selection=True)['eligible'])
        forbidden=save(h,dict(fixture='Unregistered raw object'),'unregistered_fixture')
        with patch('tools.research.core.protected',return_value=True):
            with self.assertRaisesRegex(ValueError,'PROTECTED_EVIDENCE_READ'):
                core.read_tool_evidence(h,dict(reference=forbidden,view='full'))
        with self.assertRaisesRegex(ValueError,'EVIDENCE_SUBJECT_NOT_REGISTERED'):
            core.read_tool_evidence(h,dict(subject=forbidden,topic='physical_results'))

    def test_main_delegates_saved_result_without_pointer_on_actual_sdk(self):
        import httpx
        from tools.research import reporter
        from tests.research.test_p63a_math_interface import t1_request,offline_dispatch
        from tests.research.test_s129_agent_reporting import reporter_response
        h,c=self.host();ref=offline_dispatch(h,t1_request(h,c),'semantic-synthetic-saved-math')['reference']
        complete=reporter.complete_reports
        async def mock_reports(host,transport,**kwargs):
            return await complete(host,httpx.MockTransport(reporter_response),**kwargs)
        with patch.object(reporter,'complete_reports',side_effect=mock_reports):
            wires=run_fixture(h,[('research_investigate',dict(question='Explain the saved control result and its limitations.',
                subject=ref,focus=['model scope','recorded constraints'])),None])
        findings=packet(wires[-1])['reporter_findings']
        self.assertEqual(findings[-1]['status'],'available')
        self.assertTrue(findings[-1]['interpretations'])
        self.assertFalse(findings[-1]['scientific_citation_eligible'])
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        reads=reporter.current_reports(h)[-1][1]['request']['reads']
        self.assertTrue(any(q.get('topic')=='mathematical_results' for q in reads))
        comparisons=core.read_tool_evidence(h,dict(subject='registered_results',topic='comparison',selection=[ref]))
        self.assertEqual(comparisons['reason'],'SELECT_TWO_DISTINCT_REGISTERED_RESULTS')

    def test_two_saved_results_reuse_original_comparison_scope(self):
        from tests.research.test_p63a_math_interface import t1_request,offline_dispatch
        h,c=self.host();other=generate(h,lengths=(.17,.11))
        refs=[offline_dispatch(h,t1_request(h,ref),'semantic-pair-'+str(i))['reference'] for i,ref in enumerate((c,other))]
        before=deepcopy(state(h));used=h.store.remaining()
        pages=all_pages(h,dict(subject='registered_results',topic='comparison',selection=refs))
        facts={k:v for p in pages for k,v in p['facts'].items()}
        self.assertTrue(facts['relations'])
        self.assertTrue(all(p['view_kind']=='derived_research_comparison' for p in pages))
        self.assertTrue(all(not p['formal_read_credit'] and not p['scientific_result_created'] for p in pages))
        self.assertEqual(state(h),before);self.assertEqual(h.store.remaining(),used)

    def test_saved_math_detail_entry_delivers_semantic_facts_on_actual_sdk(self):
        from tools.research.research_context import agent_decision_brief
        from tests.research.test_p63a_math_interface import t1_request,offline_dispatch
        h,c=self.host();ref=offline_dispatch(h,t1_request(h,c),'semantic-detail-fixture')['reference']
        query=agent_decision_brief(h)['mathematical_research']['latest_result']['detail_query']
        self.assertEqual(query,dict(subject=ref,topic='mathematical_results'))
        reads=deepcopy(state(h).get('evaluation_reads',[]))
        pages=all_pages(h,query)
        self.assertTrue(all(p['version']=='semantic_evidence_v1' for p in pages))
        self.assertTrue(any(item['facts'] for p in pages for item in p['facts']))
        for page in pages:
            for source in page['sources']:core.read_evidence(h,source,record_read=False)
        self.assertEqual(state(h).get('evaluation_reads',[]),reads)
        wires=run_fixture(h,[('evidence_read',query),None])
        advertised=packet(wires[0])['mathematical_research']['latest_result']['detail_query']
        self.assertEqual(advertised['topic'],'mathematical_results')
        self.assertNotIn('pointer',advertised)
        feedback=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id)
            if e['kind']=='model_original_tool_feedback'][-1]
        value=json.loads(feedback['result']['content'][0]['text'])
        self.assertEqual(value['version'],'semantic_evidence_v1')
        self.assertFalse(value['formal_read_credit'])
        # Exact old derived-view reads remain available for deliberate review.
        raw=core.read_evidence(h,dict(reference=ref,view='working_set',pointer='/mathematical_decision_view'),record_read=False)
        self.assertTrue(raw);self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_frozen_task_is_queryable_before_any_candidate_exists(self):
        h=question_host();self.assertFalse(state(h)['candidates'])
        pages=all_pages(h,dict(subject='current_task',topic='task'))
        facts={k:v for p in pages for k,v in p['facts'].items()}
        self.assertEqual(facts['frozen_task'],h.store.session(h.run_id)['snapshot']['input']['task'])
        for page in pages:
            for source in page['sources']:core.read_evidence(h,source,record_read=False)
        wires=run_fixture(h,[('evidence_read',dict(subject='current_task',topic='task')),None])
        self.assertIn('semantic_evidence_v1',json.dumps(wires[-1]))
        self.assertFalse(state(h)['candidates'])

    def test_reporter_cold_task_returns_direct_read_without_report_or_science(self):
        from tools.research import reporter
        h=question_host();before=deepcopy(state(h));ledger=h.store.remaining()
        events=h.store.events(h.run_id)
        with patch.object(reporter,'assemble',side_effect=AssertionError('TASK_IS_NOT_A_RESULT_CARD')):
            result=reporter.investigate(h,dict(question='Explain the frozen task.',subject='current_task'))
        self.assertEqual(result['status'],'unsupported')
        self.assertEqual(result['alternative_tool'],'evidence_read')
        self.assertFalse(result['scientific_result_created'])
        self.assertEqual(state(h),before);self.assertEqual(h.store.remaining(),ledger)
        self.assertEqual(h.store.events(h.run_id),events)
        pages=all_pages(h,result['alternative_query'])
        snapshot=h.store.session(h.run_id)['snapshot']
        facts={k:v for p in pages for k,v in p['facts'].items()}
        self.assertEqual(facts['frozen_task'],snapshot['input']['task'])
        self.assertFalse(reporter.entries(h))
        schema=reporter.InvestigationRequest.model_json_schema()
        self.assertNotIn('current_task',schema['properties']['subject']['anyOf'][0]['enum'])
        wires=run_fixture(h,[('research_investigate',dict(question='Explain frozen task.',subject='current_task')),None])
        feedback=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id)
            if e['kind']=='model_original_tool_feedback'][-1]
        self.assertEqual(feedback['result']['status'],'error')
        self.assertIn('evidence_read(subject=current_task, topic=task)',json.dumps(wires[-1]))
        self.assertFalse(reporter.entries(h));self.assertFalse(state(h)['candidates'])
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_reporter_owned_plan_is_provenance_not_a_scientific_result(self):
        from tools.research import reporter
        from tools.platform_store import plain
        from tools.research.state import save,update
        h,c=self.host();before=deepcopy(state(h).get('evaluation_reads',[]))
        plan=save(h,dict(request_id='offline-lineage-plan',original_plan=dict(action='generate',hypothesis='Offline lineage fixture only')))
        update(h,plans=[*state(h).get('plans',[]),plan])
        query=dict(reference=plan,view='full',pointer='/original_plan')
        expected=plain(reporter.EvidenceQuery.model_validate(query))
        outcome=reporter.investigate(h,dict(question='Verify owned construction lineage.',references=[c,plan],reads=[query]))
        saved=h.store.artifact(outcome['report_reference'])
        self.assertEqual(len(saved['report']['results']),1)
        self.assertEqual(saved['report']['results'][0]['identity']['result']['reference'],c)
        self.assertEqual(saved['request']['supporting_plan_references'],[plan])
        self.assertEqual(saved['request']['reads'].count(expected),1)
        raw=next(r for r in saved['request']['selected_reads'] if r['query']==expected)
        self.assertEqual(raw['value']['action'],'generate')
        self.assertEqual(state(h).get('evaluation_reads',[]),before)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        with self.assertRaisesRegex(ValueError,'INVESTIGATION_REQUIRES_CANDIDATE_OR_SAVED_RESULT'):
            reporter.investigate(h,dict(question='Plan intent alone is not an outcome.',references=[plan]))
        foreign=save(h,dict(original_plan=dict(action='generate',hypothesis='Unregistered foreign fixture')))
        with self.assertRaisesRegex(ValueError,'INVESTIGATION_SUBJECT_NOT_REGISTERED_IN_STUDY'):
            reporter.investigate(h,dict(question='Do not admit unowned Plans.',references=[c,foreign]))
        outcome=reporter.investigate(h,dict(question='Preserve automatic candidate topics with provenance.',references=[c,plan]))
        saved=h.store.artifact(outcome['report_reference'])
        self.assertEqual([q['topic'] for q in saved['request']['automatic_reads']],['structure','task'])
        self.assertIn(expected,saved['request']['reads'])

    def test_reporter_focus_is_prose_and_explicit_reads_select_registered_topics(self):
        from tools.research import reporter
        h,c=self.host()
        reporter.investigate(h,dict(question='Explain structure.',subject=c,
            focus=['materials','tendon routes','stiffness']))
        saved=reporter.entries(h)[-1][1]
        self.assertEqual([q['topic'] for q in saved['request']['automatic_reads']],['structure','task'])
        reporter.investigate(h,dict(question='Read registered parameter choices.',subject=c,
            reads=[dict(subject=c,topic='structure_parameters')]))
        saved=reporter.entries(h)[-1][1]
        self.assertEqual(saved['request']['automatic_reads'],[])
        self.assertEqual(saved['request']['reads'][0]['topic'],'structure_parameters')
        self.assertTrue(all(row.get('status')!='unavailable' for row in saved['request']['selected_reads']))


if __name__=='__main__':unittest.main()
