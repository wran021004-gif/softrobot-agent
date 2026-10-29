"""Curated history and frozen access: offline Store/SDK fixtures, no science."""
from copy import deepcopy
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
from uuid import uuid4
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from tools.platform_store import plain
from tools.research import experience, reporter
from tools.research.config import ROOT, resolve
from tools.research.contracts import ExperienceQuery, KnowledgePolicy
from tools.research.evidence_policy import registered_references
from tools.research.provider import provider_schema
from tools.research.state import state, update
from tests.research import test_research_knowledge as legacy
from tests.research import test_research_reporting as reporting


def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def key(row):return row['entry_id']+'@'+row['revision']
def sha(body):return hashlib.sha256(body).hexdigest()


class KnowledgeConsolidationTests(unittest.TestCase):
    def setUp(self):
        fixture=legacy.KnowledgeTests();fixture.setUp()
        self.addCleanup(fixture.doCleanups);self.h=fixture.h

    def freeze(self, **policy):
        spec=deepcopy(state(self.h)['spec']);spec['study_id']=self.h.run_id
        policy=KnowledgePolicy.model_validate(policy)
        spec['knowledge']=plain(policy)
        spec['knowledge_manifest']=experience.freeze_knowledge(policy)
        update(self.h,spec=spec)
        return spec

    def test_exact_union_preserves_all_original_content_and_p3_trace(self):
        rows=experience._index_rows();by_key={key(r):r for r in rows}
        self.assertEqual(len(rows),33);self.assertEqual(len(by_key),33)
        refs=[('4de5d5d475755578653e9cca8febe395adeb8764',8),
            ('9d2ca3e288b41cfe425e34eac2555f3465d9f0d0',15),
            ('6b982c7b45a334ef2dcabb491aa5d41e8afa3039',10)]
        union=set()
        for commit,count in refs:
            original=json.loads(subprocess.check_output(['git','show',commit+':memory/diagnostic_index.json'],cwd=ROOT))['entries']
            self.assertEqual(len(original),count)
            for entry in original:
                union.add(key(entry));self.assertIn(key(entry),by_key)
                body=subprocess.check_output(['git','show',commit+':'+entry['path']],cwd=ROOT)
                # Git's text conversion is distinct from source-audit raw hashes.
                self.assertEqual((ROOT/by_key[key(entry)]['path']).read_text(encoding='utf8'),body.decode('utf8').replace('\r\n','\n'))
        self.assertEqual(len(union),17)
        audit=read(ROOT/'docs/research/p62k_source_audit.json')
        self.assertEqual(audit['conflicts'],[])
        self.assertTrue(all(r['content_equal'] for r in audit['duplicate_keys']))
        self.assertFalse(audit['p3_remote_branch_present_at_start'])

    def test_nine_cases_have_scoped_identity_and_authentic_limitations(self):
        self.freeze(allow_benchmark_answers=True)
        rows=[r for r in experience.entries(self.h) if r['kind']=='success_case']
        self.assertEqual(len(rows),9)
        for row in rows:
            actual=experience.retrieve(self.h,dict(operation='read',entry_id=row['entry_id'],revision=row['revision']))
            self.assertEqual(actual['results'][0]['content']['schema'],'project_research_success_case_v1')
            self.assertEqual(actual['results'][0]['content_sha256'],sha((ROOT/row['path']).read_bytes()))
            self.assertEqual(actual['results'][0]['content_role'],'research_trace')
            self.assertFalse(actual['scientific_evidence'])
            self.assertTrue(6<=len(actual['results'][0]['content']['trace'])<=12)
            self.assertTrue(row.get('decision_ownership') or actual['results'][0]['content'].get('decision_ownership'))
        m3=read(ROOT/'memory/cases/m3_research_v1/success_trace.json')
        self.assertEqual(m3['final_result']['status'],'draft_protocol_accepted')
        self.assertFalse(m3['task_scope']['formal_benchmark_approved'])
        phs=read(ROOT/'memory/cases/phs2d_passive_research_v1/success_trace.json')
        self.assertFalse(phs['final_result']['formal_select'])
        self.assertIn('development',phs['final_result']['task_scope'])
        p3=read(ROOT/'memory/cases/p3_passive_progressive_stiffness_v1/success_trace.json')
        self.assertTrue(p3['status']['original_task_passed'])
        self.assertTrue(p3['status']['two_cells_per_segment_passed'])
        self.assertEqual(p3['status']['four_cells_per_segment'],'INVALID')
        self.assertEqual(registered_references(self.h),[])

    def test_new_methods_have_versioned_portable_source_chains(self):
        methods=[r for r in experience._index_rows() if r.get('introduced_in')=='p62k' and r['kind']=='procedure']
        self.assertEqual(len(methods),8)
        for row in methods:
            content=read(ROOT/row['path'])
            self.assertTrue(experience.english_source_ready(row))
            self.assertEqual(content['revision'],row['revision'])
            self.assertTrue(content['source_case_ids']);self.assertTrue(content['procedure'])
            self.assertEqual(content['status']['generalization'],'unverified')
            self.assertFalse(content['status']['current_scientific_evidence'])
            for source in content['evidence']:
                self.assertEqual(source['hash_convention'],'UTF-8 with LF line endings')
                self.assertEqual(sha((ROOT/source['path']).read_text(encoding='utf8').encode()),source['sha256'])

    def test_default_discovery_is_short_english_and_never_reads_bodies(self):
        spec=self.freeze();spec['research_decisions']=dict(language_policy=dict(version='english_sources_v1',authored_language='en'))
        update(self.h,spec=spec);before=deepcopy(state(self.h))
        with patch.object(experience,'_index_rows',side_effect=AssertionError('FROZEN_METADATA_ONLY')):
            hint=experience.retrieval_hint(self.h)
        self.assertTrue(0<len(hint['hints'])<=2)
        self.assertLess(len(json.dumps(hint).encode()),3000)
        self.assertEqual(state(self.h),before)
        self.assertNotIn('content',hint);self.assertEqual(before['retrievals'],[])
        actual=experience.retrieve(self.h,hint['hints'][0]['read_query'])
        self.assertTrue(actual['results'][0]['content']['procedure'])
        self.assertFalse(actual['scientific_evidence'])
        found=experience.retrieve(self.h,dict(operation='search',kind='procedure'))
        self.assertGreater(len(found['results']),1)
        self.assertGreater(found['matched_count'],1)
        self.assertTrue(all('content' not in r for r in found['results']))
        self.assertEqual(len(experience.retrieve(self.h,dict(operation='search',limit=1))['results']),1)
        self.assertFalse(any(r['kind']=='success_case' for r in experience.entries(self.h)))
        with self.assertRaisesRegex(ValueError,'EXACT_EXPERIENCE_READ'):
            experience.retrieve(self.h,dict(operation='read',entry_id='owner-m1-research-trace',revision='1'))

    def test_off_exclude_kind_and_include_filter_before_content_access(self):
        with patch.object(experience,'_index_rows',side_effect=AssertionError('OFF_MUST_NOT_READ_INDEX')):
            self.freeze(mode='off')
            self.assertIsNone(experience.retrieval_hint(self.h))
            with self.assertRaisesRegex(ValueError,'KNOWLEDGE_DISABLED'):
                experience.retrieve(self.h,dict(operation='read',entry_id='owner-m1-research-trace',revision='1'))
        spec=self.freeze(allow_benchmark_answers=True,exclude_entry_ids=['owner-m1-research-trace'],allowed_kinds=['procedure'],include_entry_ids=['research-strict-near-tolerance','owner-m1-research-trace'])
        self.assertTrue(spec['knowledge_manifest']['entries'])
        self.assertEqual({r['entry_id'] for r in experience.entries(self.h)},{'research-strict-near-tolerance'})
        with patch.object(Path,'read_bytes',side_effect=AssertionError('DENIED_BEFORE_BODY_ACCESS')):
            with self.assertRaisesRegex(ValueError,'EXACT_EXPERIENCE_READ'):
                experience.retrieve(self.h,dict(operation='read',entry_id='owner-m1-research-trace',revision='1'))
        self.assertEqual(state(self.h)['retrievals'],[])

    def test_frozen_access_catalog_survives_index_change_and_reads_current_file(self):
        row=deepcopy(next(r for r in experience._index_rows() if r['entry_id']=='model-physics-comparison'))
        root=ROOT/'runs'/('p62k-catalog-'+uuid4().hex[:8]);root.mkdir()
        self.addCleanup(lambda:shutil.rmtree(root))
        with patch.object(experience,'ROOT',root):
            (root/'memory').mkdir();(root/'body.json').write_text('{"fixture":1}',encoding='utf8')
            row['path']='body.json';(root/'memory/diagnostic_index.json').write_text(json.dumps(dict(entries=[row])),encoding='utf8')
            with patch.object(Path,'read_bytes',side_effect=AssertionError('NO_BODY_READ_AT_FREEZE')):
                self.freeze()
            (root/'memory/diagnostic_index.json').write_text('{"entries":[]}',encoding='utf8')
            actual=experience.retrieve(self.h,dict(operation='read',entry_id=row['entry_id'],revision=row['revision']))
            self.assertEqual(actual['results'][0]['content'],{'fixture':1})
            (root/'body.json').write_text('{"fixture":2}',encoding='utf8')
            actual=experience.retrieve(self.h,dict(operation='read',entry_id=row['entry_id'],revision=row['revision']))
            self.assertEqual(actual['results'][0]['content'],{'fixture':2})
            with patch.object(Path,'read_bytes',side_effect=AssertionError('SEARCH_METADATA_ONLY')):
                self.assertEqual(experience.retrieve(self.h,dict(operation='search'))['matched_count'],1)

    def test_old_study_does_not_gain_new_answers_or_method_versions(self):
        before=deepcopy(state(self.h)['spec'])
        rows=experience.entries(self.h)
        self.assertTrue(rows)
        self.assertTrue(all(not r.get('introduced_in') for r in rows))
        self.assertEqual(state(self.h)['spec'],before)
        self.assertNotIn('knowledge_manifest',before)

    def test_new_resolve_owns_default_access_catalog(self):
        spec=resolve(ROOT/'configs/research/study_bf6_public.json')
        self.assertEqual(spec['knowledge']['mode'],'enabled')
        self.assertTrue(spec['knowledge_manifest']['entries'])
        self.assertFalse(any('content_sha256' in r for r in spec['knowledge_manifest']['entries']))
        self.assertFalse(any(r.get('benchmark_sensitive') for r in spec['knowledge_manifest']['entries']))
        source=ROOT/'configs/research/study_bf6_public.json'
        original=read(source);original['knowledge_manifest']={'entries':[]}
        with patch('tools.research.config.read',side_effect=lambda path:deepcopy(original) if Path(path)==source else read(path)):
            self.assertEqual(resolve(source)['knowledge_manifest'],spec['knowledge_manifest'])

    def test_query_schema_keeps_old_calls_and_bounds_optional_extensions(self):
        for query in ({'key':'legacy'}, {'operation':'read','entry_id':'x','revision':'1'},
                {'operation':'search','task':'tracking','kind':'procedure','limit':20}):
            ExperienceQuery.model_validate(query)
        schema=provider_schema(ExperienceQuery.model_json_schema())
        Draft202012Validator.check_schema(schema)
        self.assertFalse({'allOf','anyOf','oneOf','not'} & schema.keys())
        self.assertLess(len(json.dumps(schema)),3500)
        self.assertIsNone(ExperienceQuery().limit)
        self.assertEqual(ExperienceQuery(limit=100).limit,100)
        self.assertIn('full',__import__('tools.research.contracts',fromlist=['EvidenceQuery']).EvidenceQuery.model_json_schema()['properties']['view']['enum'])

    def test_scientific_admission_and_execution_contracts_are_unchanged(self):
        baseline='9d2ca3e288b41cfe425e34eac2555f3465d9f0d0'
        for path,names in [('tools/research/evidence_policy.py',{'admit_decision'}),
                ('tools/research/contracts.py',{'Plan','AnalysisRequest','EvidenceQuery'})]:
            old=ast.parse(subprocess.check_output(['git','show',baseline+':'+path],cwd=ROOT).decode())
            current=ast.parse((ROOT/path).read_text(encoding='utf8'))
            def contracts(tree):return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if getattr(n,'name',None) in names}
            self.assertEqual(contracts(old),contracts(current))

    def test_new_reporter_method_read_remains_outside_scientific_catalog(self):
        from types import SimpleNamespace
        from tools.research.state import save
        self.freeze()
        ref=save(self.h,dict(fixture='Saved data only; no science'))
        query=dict(operation='read',entry_id='research-contact-causality',revision='2')
        with patch.object(reporter,'assemble',return_value=SimpleNamespace(results=[])),\
                patch.object(reporter,'applicable_corrections',return_value=[]),patch.object(reporter,'_save',return_value=ref) as saved:
            reporter.investigate(self.h,dict(question='Explain saved fixture with authorized context',references=[ref],experience_queries=[query]))
        receipt_ref=saved.call_args.kwargs['request']['experience_receipts'][0]
        receipt=self.h.store.artifact(receipt_ref)
        self.assertEqual(receipt['reader'],'reporter');self.assertFalse(receipt['scientific_evidence'])
        self.assertIsNone(experience.read_progress(self.h))
        update(self.h,pilot=dict(provider=dict(adapter='deepseek',model='fixture',thinking='disabled',reasoning_effort='high',max_tokens=None)))
        with patch.object(reporter.ScientificReport,'model_validate',return_value=SimpleNamespace(results=[],relations=[],mode='investigation',question='Fixture')),\
                patch.object(reporter,'reporter_handoff_summary',return_value=dict(findings=[],comparisons=[],scope=[],limitations=[])):
            wire=reporter._wire(self.h,ref,dict(report={},request=dict(experience_receipts=[receipt_ref])))
        packet=json.loads(wire['messages'][-1]['content'])
        self.assertEqual(packet['source_catalog'],{})
        self.assertIn(query['entry_id'],json.dumps(packet['procedural_guidance'][0]))
        self.assertEqual(registered_references(self.h),[])


class KnowledgeWireTests(unittest.TestCase):
    def test_formal_discovery_exact_body_and_handoff_progress(self):
        from tests.research.test_information_flow import flow_host, packet
        from tests.research.test_recent_round_tools import run_fixture
        from tools.platform_host import Host
        h=flow_host();spec=deepcopy(state(h)['spec']);policy=KnowledgePolicy()
        spec.update(knowledge=plain(policy),knowledge_manifest=experience.freeze_knowledge(policy))
        update(h,spec=spec)
        query=dict(operation='read',entry_id='research-strict-near-tolerance',revision='3')
        wires=run_fixture(h,[('experience_retrieve',query),('research_recall',dict(trace='actions')),None])
        first=packet(wires[0]);hint=first['knowledge']['access']
        self.assertTrue(hint['hints']);self.assertLess(len(json.dumps(hint)),3000)
        self.assertNotIn('procedure',json.dumps(first['knowledge'].get('read_progress')))
        self.assertTrue({'experience_retrieve','research_investigate','evidence_read','research_recall'} <= {t['function']['name'] for t in wires[0]['tools']})
        self.assertFalse(any(r['action']=='research_analysis' and r['status']=='available' for group in first['capabilities'] for r in group['actions']))
        progress=experience.read_progress(h);self.assertTrue(progress['reads'][0]['body_delivered'])
        self.assertEqual(experience.read_progress(Host(h.store.root,h.run_id)),progress)
        self.assertEqual(packet(wires[-1])['knowledge']['read_progress'],progress)
        self.assertEqual(registered_references(h),[])
        self.assertEqual(h.store.remaining()['used']['worker_calls'],0)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_off_policy_removes_tool_and_discovery_but_retains_investigation(self):
        from tests.research.test_information_flow import flow_host, packet
        from tests.research.test_recent_round_tools import run_fixture
        h=flow_host();spec=deepcopy(state(h)['spec']);spec['knowledge']=plain(KnowledgePolicy(mode='off'))
        spec['knowledge_manifest']={'entries':[]};update(h,spec=spec)
        wires=run_fixture(h,[None]);names={t['function']['name'] for t in wires[0]['tools']}
        self.assertNotIn('experience_retrieve',names)
        self.assertTrue({'research_investigate','evidence_read','research_recall'}<=names)
        self.assertIsNone(packet(wires[0])['knowledge']['access'])


class ResourceArithmeticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):reporting.ReportingTests.setUpClass()

    def test_recorded_resource_decrease_is_separate_from_preference_and_scope(self):
        fixture=reporting.ReportingTests();fixture.setUp()
        left=fixture.physical_result();right=deepcopy(left)
        left.update(numerical_s=3210.0,cpu_time_s=2.0,boundary=dict(elapsed_s=2.0))
        right.update(numerical_s=3316.0,cpu_time_s=3.0,boundary=dict(elapsed_s=1.0))
        refs=[fixture.put(left),fixture.put(right)]
        h,_=reporting.offline_host(fixture.values,physical_replays=refs)
        report=reporter.assemble(h,refs,question='Offline recorded resource comparison')
        comparisons=report.results[0].deterministic_summary['comparisons'][0]
        resources={r['resource']:r for r in comparisons['resources']}
        self.assertEqual((resources['numerical_s']['delta'],resources['numerical_s']['numeric_change']),(-106.0,'decrease'))
        self.assertEqual(resources['elapsed_s']['numeric_change'],'increase')
        self.assertEqual((resources['cpu_time_s']['numeric_change'],resources['cpu_time_s']['time_basis']),('decrease','cpu'))
        for resource in resources.values():
            self.assertEqual(resource['preference'],'unknown');self.assertEqual(resource['direction'],'unknown')
            self.assertEqual(reporter.read_evidence(h,resource['source'],record_read=False),resource['value'])
            self.assertEqual(reporter.read_evidence(h,resource['baseline_source'],record_read=False),resource['baseline'])
        self.assertTrue(all('numeric_change' in row for row in comparisons['metrics']))

    def test_report_summary_keeps_all_constraints_and_full_read(self):
        fixture=reporting.ReportingTests();fixture.setUp()
        physical=fixture.put(fixture.physical_result())
        h,s=reporting.offline_host(fixture.values,physical_replays=[physical])
        h.store.events.return_value=[]
        report=reporter.assemble(h,[physical],question='Fixture exact report summary')
        saved=dict(report=plain(report),interpretation_status='unavailable',error=None,request={})
        reference=fixture.put(saved);before=deepcopy(s)
        summary=reporter.read_evidence(h,dict(reference=reference,view='summary'),record_read=False)
        self.assertEqual(len(summary['findings'][0]['metrics']),len(report.results[0].metrics))
        for metric in report.results[0].metrics:
            actual=next(m for m in summary['findings'][0]['metrics'] if m['name']==metric.name)
            self.assertEqual(actual['value'],metric.value);self.assertEqual(actual['source'],plain(metric.source))
            self.assertEqual(actual['passed'],metric.passed)
        self.assertIn('Non-authoritative',summary['interpretation_scope'])
        self.assertEqual(reporter.read_evidence(h,summary['full_report_query'],record_read=False),saved)
        self.assertEqual(s,before)

    def test_bound_analysis_menu_separates_read_only_and_candidate_budget(self):
        from tools.research.research_context import research_decision_brief_v3
        brief=dict(task={},actions=['diagnose'],capabilities=['analysis'],
            analysis_interface='bound_scientific_variables_v2',budget=dict(science_budget=dict(remaining_mathematical=0)))
        menu=research_decision_brief_v3(brief)['action_menu']
        diagnosis=next(r for r in menu if r['action']=='diagnose')
        self.assertEqual(diagnosis['read_only_investigation']['tool'],'research_investigate')
        self.assertEqual(diagnosis['analysis_selection']['status'],'requires_owned_candidate')
        self.assertEqual(next(r for r in menu if r['action']=='research_analysis')['status'],'blocked')
        reference=dict(artifact_id='a'*64,media_type='application/json')
        brief['current_candidate']=dict(candidate=reference,details_query=dict(reference=reference,pointer='/parameters'))
        diagnosis=next(r for r in research_decision_brief_v3(brief)['action_menu'] if r['action']=='diagnose')
        self.assertEqual(diagnosis['analysis_selection']['status'],'insufficient_mathematical_budget')
        self.assertEqual(diagnosis['analysis_selection']['candidate_query'],brief['current_candidate']['details_query'])
        self.assertEqual(diagnosis['analysis_selection']['methods_query']['reference'],reference)
        # Original read-only diagnose remains available; no additional admission gate.
        self.assertEqual(diagnosis['status'],'available')


if __name__=='__main__':unittest.main()
