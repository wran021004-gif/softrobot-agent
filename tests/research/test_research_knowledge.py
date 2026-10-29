"""Diagnostic retrieval boundaries; synthetic sessions, no science or Provider."""
import json
from copy import deepcopy
from pathlib import Path
import shutil
import gc
from types import SimpleNamespace
from uuid import uuid4
import unittest
from unittest.mock import patch

from schemas.platform import ProjectConfig
from tools.platform_store import Store, plain
from tools.research.state import save, state, update
from tools.research.experience import retrieve, disposition_bindings, retrieval_hint, PUBLIC_STATUS
from tools.research.evidence_policy import registered_references
from tools.research.config import ROOT, resolve
from tools.research_tasks import task_adapter


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        folder=ROOT/'runs'/('knowledge-'+uuid4().hex[:8]);folder.mkdir()
        self.addCleanup(lambda: (gc.collect(),shutil.rmtree(folder)))
        self.h=SimpleNamespace(store=Store(folder),run_id=folder.name)
        project=ProjectConfig(project_id=self.h.run_id,grant_id=self.h.run_id,
            authorization_source='Synthetic offline diagnostic test only',
            budget=dict(model_calls=0,tool_calls=0,worker_calls=0,backend_solves=0,wall_s=None))
        self.h.store.create(project)
        self.h.store.create_session(dict(input=dict(run_id=self.h.run_id,policy=dict(budget=plain(project.budget))),purpose='Offline fixture; no Study'))
        update(self.h,spec=dict(mode='engineering_numerical',capabilities=['analysis'],canonical_task=dict(family='task.oriented_tracking')),retrievals=[],research_status='ready')

    def test_search_read_and_disposition_preserve_evidence_boundary(self):
        ledger=self.h.store.remaining()
        found=retrieve(self.h,dict(operation='search',task='oriented_tracking'))
        self.assertTrue(found['results'])
        self.assertTrue(all(r['status']==PUBLIC_STATUS and 'content' not in r and not r['original_evidence_references'] for r in found['results']))
        with self.assertRaisesRegex(ValueError,'EXACT_ACTUAL_READ'):
            disposition_bindings(self.h,{found['results'][0]['exact_key']:'adopted'})
        row=found['results'][0]
        actual=retrieve(self.h,dict(operation='read',entry_id=row['entry_id'],revision=row['revision']))
        binding=disposition_bindings(self.h,{row['exact_key']:'context_only'})[0]
        self.assertEqual(binding['content_sha256'],row['content_sha256'])
        self.assertEqual(binding['read_receipt'],actual['reference'])
        self.assertFalse(actual['scientific_evidence'])
        self.assertEqual(registered_references(self.h),[])
        self.assertEqual(ledger,self.h.store.remaining())
        with self.assertRaisesRegex(ValueError,'EXACT_EXPERIENCE_READ'):
            retrieve(self.h,dict(operation='read',entry_id='nmpc-feasibility-case'))

    def test_l0_hint_has_no_case_content_or_read_credit(self):
        before=state(self.h);hint=retrieval_hint(self.h)
        self.assertEqual(hint['query'],dict(operation='search',task='oriented_tracking'))
        self.assertNotIn('procedure',json.dumps(hint))
        self.assertEqual(state(self.h),before)
        update(self.h,spec={**before['spec'],'rl_evaluation_source':{'fixture':True}})
        self.assertIsNone(retrieval_hint(self.h))
        update(self.h,spec={**before['spec'],'mode':'autonomous','budgets':dict(protected_provider_requests=0)})
        self.assertIsNone(retrieval_hint(self.h))

    def test_cross_task_guidance_is_labeled_and_not_scientific_evidence(self):
        s=state(self.h);update(self.h,spec={**s['spec'],'canonical_task':{'family':'task.reach'}})
        hint=retrieval_hint(self.h)
        self.assertEqual(hint['query'],{'operation':'search'})
        result=retrieve(self.h,dict(operation='read',entry_id='research-contact-causality',revision='1'))
        row=result['results'][0]
        self.assertEqual(row['current_task_type'],'task.reach')
        self.assertEqual(row['historical_task_type'],'oriented_tracking')
        self.assertIn('unverified',row['applicability'])
        self.assertIn('not current Study scientific evidence',result['scope'])
        self.assertFalse(result['scientific_evidence'])
        self.assertEqual(registered_references(self.h),[])

    def test_reporter_records_reads_without_scientific_registration(self):
        from tools.research import reporter
        ref=save(self.h,dict(fixture='Existing evidence, no scientific claim'))
        request=dict(question='Diagnose saved evidence using procedural guidance',references=[ref],
            experience_queries=[dict(operation='read',entry_id='research-contact-causality',revision='1')])
        with patch.object(reporter,'assemble',return_value=SimpleNamespace(results=[])),patch.object(reporter,'applicable_corrections',return_value=[]),patch.object(reporter,'_save',return_value=ref) as saved:
            reporter.investigate(self.h,request)
        receipt=self.h.store.artifact(saved.call_args.kwargs['request']['experience_receipts'][0])
        self.assertEqual(receipt['reader'],'reporter')
        self.assertFalse(receipt['scientific_evidence'])
        self.assertEqual(registered_references(self.h),[])

    def test_reporter_wire_keeps_guidance_outside_scientific_sources(self):
        from tools.research import reporter
        receipt=retrieve(self.h,dict(operation='read',entry_id='research-contact-causality',revision='1'),reader='reporter')
        update(self.h,pilot=dict(provider=dict(adapter='deepseek',model='fixture',thinking='disabled',reasoning_effort='high',max_tokens=None)))
        saved=dict(report={'fixture':'No scientific result'},request=dict(experience_receipts=[receipt['reference']]))
        # Only the wire's advisory boundary is exercised; no report is registered.
        with patch.object(reporter.ScientificReport,'model_validate',return_value=SimpleNamespace(results=[],relations=[],mode='investigation',question='Fixture')),\
                patch.object(reporter,'reporter_handoff_summary',return_value=dict(findings=[],comparisons=[],scope=[],limitations=[])):
            wire=reporter._wire(self.h,receipt['reference'],saved)
        packet=json.loads(wire['messages'][-1]['content'])
        self.assertNotIn('max_tokens',wire)
        self.assertEqual(packet['source_catalog'],{})
        self.assertEqual(len(packet['procedural_guidance']),1)
        self.assertFalse(packet['procedural_guidance'][0]['scientific_evidence'])

    def test_mock_http_probe_uses_retrieval_and_records_plan_without_science(self):
        import asyncio
        import httpx
        from tests.research.flash_pro_decision_probe import run_case
        from tests.research.test_cross_task_integration import plan
        spec=resolve(ROOT/'configs/research/study_bf6_public.json')
        frozen=dict(protocol=dict(requests_per_case_model=4,max_tokens=None,thinking='enabled',reasoning_effort='high',authorization='Synthetic mock-HTTP fixture; client output cap omitted'),
            provider=spec['runtime']['provider'],instructions='Fixture only',cases=dict(on=dict(evidence={'fixture':True})))
        seen=[]
        def reply(request):
            self.assertNotIn('max_tokens',json.loads(request.content))
            seen.append(request)
            n=len(seen)
            calls=[('experience_retrieve',dict(operation='search',task='oriented_tracking')),
                ('experience_retrieve',dict(operation='read',entry_id='research-contact-causality',revision='1')),
                ('research_plan',plan('diagnose',experience_disposition={'research-contact-causality@1':'context_only'}))]
            message=dict(role='assistant',content='Synthetic fixture only')
            if n<=3:
                name,value=calls[n-1]
                message.update(content='',tool_calls=[dict(id='fixture-'+str(n),type='function',function=dict(name=name,arguments=json.dumps(value)))])
            return httpx.Response(200,json=dict(id='fixture',object='chat.completion',created=1,model='deepseek-v4-pro',
                choices=[dict(index=0,finish_reason='tool_calls' if n<=3 else 'stop',message=message)],
                usage=dict(prompt_tokens=10,completion_tokens=2,total_tokens=12)))
        folder=self.h.store.root/('p'+uuid4().hex[:5])
        with patch('tools.research.core.dispatch',side_effect=AssertionError('NO_SCIENTIFIC_DISPATCH')),patch('tools.research.analysis.dispatch',side_effect=AssertionError('NO_SCIENTIFIC_DISPATCH')):
            result=asyncio.run(run_case(folder,frozen,'on','deepseek-v4-pro',httpx.MockTransport(reply),experience_enabled=True))
        self.assertEqual(result['actual_requests'],4,result.get('harness_error'))
        self.assertEqual(result['accepted_decisions'],1)
        self.assertEqual(result['scientific_workers'],0)
        self.assertEqual([r['contract'] for r in result['tool_checks']],['valid']*3)

    def test_ppo_rejects_all_three_bf_tasks_before_scene_or_xml(self):
        from tools.research import rl
        for leaf in ('study_tracking_public.json','study_bf5_public.json','study_bf6_public.json'):
            cfg=resolve(ROOT/'configs/research'/leaf)['configuration']
            adapter=task_adapter(cfg)
            self.assertFalse(adapter.ppo_applicability()['supported'])
            self.assertIn('ppo',adapter.execution_requirements()['unsupported_control_methods'])
            with patch.object(rl,'verify_candidate',return_value=dict(configuration=cfg)),patch('extensions.tendon_family.backends.physics_for',side_effect=AssertionError('NO_SCIENCE')):
                with self.assertRaisesRegex(ValueError,'RL_TASK_UNSUPPORTED'):
                    rl.prepare_input(self.h,SimpleNamespace(candidate={}))
        geometric=json.loads((ROOT/'tasks/tracking_linear_development.json').read_text(encoding='utf8'))
        self.assertTrue(task_adapter(geometric).ppo_applicability()['supported'])

    def test_native_t1_t2_catalog_does_not_inherit_direct_control_task_support(self):
        from tests.research.test_c1_method_context import C1Archive
        from tools.research.task_constraints import mathematical_method_view
        from tools.research.nonlinear_capability import T1,T2
        archive=C1Archive();self.addCleanup(archive.archive.close)
        host,s=archive.host();ref=s['reference_candidate']
        candidate=deepcopy(archive.artifact(ref))
        # Synthetic task substitution isolates catalog projection, not admission.
        host.store.artifact.side_effect=lambda r:candidate if plain(r)==ref else archive.artifact(r)
        s['analysis_results']=[]
        s['spec']['mathematical_methods']={T1:{'fixture':True},T2:{'fixture':True}}
        for leaf in ('study_tracking_public.json','study_bf5_public.json','study_bf6_public.json'):
            spec=resolve(ROOT/'configs/research'/leaf)
            candidate['configuration']=spec['configuration']
            s['spec']['analysis_protocol']=spec['analysis_protocol']
            with patch('tools.research.design.verify_candidate',return_value=candidate),patch('tools.research.optimal_capability.candidate_methods',return_value={}),patch('tools.research.research_context.history_index',return_value=[]):
                methods=mathematical_method_view(host,ref)['methods']
            for method in (T1,T2):
                self.assertEqual(methods[method]['planning_status'],'unsupported')
                self.assertFalse(methods[method]['kernel_supported'])
                self.assertFalse(methods[method]['executable'])
                self.assertEqual(methods[method]['supported_task_families'],['task.reach'])


if __name__=='__main__':unittest.main()
