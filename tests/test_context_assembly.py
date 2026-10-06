"""Focused real saved-corpus regression; no grants, providers or numerical work."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
import hashlib
import json

from tools.context_assembly import EvidenceArchive, assemble_context, assemble_request, retrieve_fact, request_facts, measure_input
from tools.state_io import read
from tools.platform_store import Store
from tools.bound_reporting import render, render_text
from examples.check_context_assembly import ROOT,M4ROOT,saved_research_fixture,actual_research_builder


class ContextAssemblyTests(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(dir=ROOT/'runs',prefix='context-offline-')
        def cleanup():
            target=Path(self.temp.name).resolve()
            if not target.is_relative_to((ROOT/'runs').resolve()) or not target.name.startswith('context-offline-'):
                raise ValueError('TEST_CLEANUP_OUTSIDE_EXPECTED_DIRECTORY')
            self.temp.cleanup()
        self.addCleanup(cleanup)
        self.store,self.state,self.packet,self.authority,self.payload=saved_research_fixture()
        self.archive=EvidenceArchive(Path(self.temp.name),scope={'role':'Saved corpus offline test'},stores=(self.store,))
        self.config=read(M4ROOT/'freeze.json')['provider_configuration']
        self.ledger=read(ROOT/'runs/milestone4_bound_20261006/ledger.json')

    def test_geometry_repeat_counterexamples_and_reordering(self):
        a=assemble_context('research_decision',self.packet,archive=self.archive,authority=self.authority)
        p=deepcopy(self.packet);p['history']['rows'].reverse()
        b=assemble_context('research_decision',p,archive=self.archive,authority=self.authority)
        self.assertEqual(a['canonical_facts'],b['canonical_facts'])
        va,vb=a['view'],b['view']
        self.assertEqual(va['history'],vb['history'])
        self.assertEqual(va['working_context']['roles'],vb['working_context']['roles'])
        pair=va['bound_evidence']['replications'][0]
        self.assertNotEqual(pair['original_execution_id'],pair['repeated_execution_id'])
        self.assertTrue(pair['measured_differences']);self.assertIn('broad variability',va['working_context']['repeatability_scope'])
        rows={r['execution_id']:r for r in va['bound_evidence']['executions']}
        original=rows['a8382f8a4c6e4ebe921fb72f821b2188'];other=rows['91c3ba1b01d6499fb26df8f95409401b']
        self.assertEqual(original['weights'],other['weights']);self.assertNotEqual(original['structure_identity'],other['structure_identity'])
        self.assertEqual(set(rows),{r['candidate']['execution_id'] for r in self.packet['history']['rows'] if r['metrics']})
        self.assertTrue(any(f['metric']=='joint_reach_holding_passed' and not f['value'] for f in a['canonical_facts'].values()))
        self.assertTrue(va['working_context']['unresolved_questions'])
        self.assertIn('frozen_pre_experiment_background',va['case']['question_status'])

    def test_exact_metric_retrieval_source_and_swap_rejection(self):
        a=assemble_context('final_report',self.ledger,archive=self.archive)
        f=next((k,v) for k,v in a['canonical_facts'].items() if v['execution_id']=='a8382f8a4c6e4ebe921fb72f821b2188' and v['metric']=='terminal_error_m')
        key,fact=f
        result=retrieve_fact(a,key,archive=self.archive,expected={'execution_id':fact['execution_id'],'metric':fact['metric'],'structure_identity':fact['structure_identity']})
        self.assertEqual(result['page']['content'],fact);self.assertEqual(result['units'],'m');self.assertFalse(result['truncated'])
        original=self.archive.retrieve(fact['source_artifact'],pointer='/metrics/0/value',binding=fact)
        self.assertEqual(original['page']['content'],0.008117263030117125)
        reopened=EvidenceArchive.from_manifest(ROOT/a['audit']['source_manifest'],scope=self.archive.scope,stores=(self.store,))
        self.assertEqual(reopened.retrieve(fact['source_artifact'],pointer='/metrics/0/value')['page']['content'],fact['value'])
        with self.assertRaisesRegex(ValueError,'OUT_OF_SCOPE'):
            EvidenceArchive.from_manifest(ROOT/a['audit']['source_manifest'],scope={'role':'Unrelated role'},stores=(self.store,))
        with self.assertRaisesRegex(ValueError,'CROSS_EXECUTION'):retrieve_fact(a,key,archive=self.archive,expected={'execution_id':'91c3ba1b01d6499fb26df8f95409401b'})
        report=read(ROOT/'runs/milestone4_bound_20261006/interpretation2.json')['interpretation']
        self.assertIn('0.008117263030117125',render(report,self.ledger)['rendered'])
        bad=deepcopy(report);bad['claims'][0]['execution_id']='another execution'
        with self.assertRaisesRegex(ValueError,'CROSS_EXECUTION'):render(bad,self.ledger)

    def test_bounded_original_pointer_paging_and_host_compatibility(self):
        from tools.platform_tools import read_evidence
        from schemas.platform_operations import ReadEvidence
        doc={'detail':{'a/b~c':[[i]*30 for i in range(500)],'large':'x'*20000},'signed_error_m':[-.05,.007,.043]}
        ref=self.archive.snapshot(doc)
        root=self.archive.retrieve(ref)
        self.assertEqual(root['page']['kind'],'overview');self.assertTrue(root['truncated'])
        detail=self.archive.retrieve(ref,pointer='/detail')
        self.assertEqual(detail['child_pointers'][0]['pointer'],'/detail/a~1b~0c')
        first=self.archive.retrieve(ref,pointer='/detail/a~1b~0c',limit=100,byte_limit=512)
        self.assertIsNotNone(first['continuation'])
        second=self.archive.retrieve(**first['continuation'])
        self.assertEqual(second['page']['content'][0],doc['detail']['a/b~c'][first['continuation']['offset']])
        self.assertEqual(self.archive.retrieve(ref,pointer='/signed_error_m')['page']['content'],doc['signed_error_m'])
        fake=MagicMock();fake.session.return_value={'state':{}}
        ctx=SimpleNamespace(artifact=lambda _:doc,store=fake,run_id='offline')
        page=read_evidence(ctx,ReadEvidence(reference=ref,pointer='/signed_error_m'))
        self.assertEqual(page.content,doc['signed_error_m']);self.assertEqual(fake.update_state.call_count,1)
        with self.assertRaisesRegex(ValueError,'OUT_OF_SCOPE'):self.archive.retrieve({'artifact_id':'0'*64,'media_type':'application/json'})
        with self.assertRaisesRegex(ValueError,'POINTER_NOT_FOUND'):self.archive.retrieve(ref,pointer='/missing')

    def test_actual_research_and_reporting_builders(self):
        from examples.milestone_bound_successor import build_reporting_request4,provider4
        from examples.milestone5_control_reporting import build_interpretation_request,packet,request
        path=self.store.db;before=hashlib.sha256(path.read_bytes()).hexdigest()
        payload,audit=actual_research_builder(Path(self.temp.name)/'actual')
        view=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        self.assertEqual(view['working_context']['purpose'],'research_decision')
        schema=payload['tools'][0]['function']['parameters']['anyOf'][0]
        self.assertEqual(set(schema['properties']['action']['enum']),set(view['capabilities']['legal']))
        p4,a4=build_reporting_request4(self.config,self.ledger,'Offline preserved instructions.',archive=self.archive)
        self.assertEqual(json.loads(p4['messages'][1]['content'])['working_context']['purpose'],'final_report')
        m5=Store(ROOT/'runs/milestone5_control_20261006')
        archive5=EvidenceArchive(Path(self.temp.name)/'m5',scope={'role':'Saved M5 offline'},stores=(m5,self.store))
        p5,a5=build_interpretation_request(self.config,packet(),'Offline preserved instructions.',archive=archive5)
        record=dict(payload=p5,context_assembly_audit=a5)
        self.assertEqual(json.loads(p5['messages'][1]['content'])['working_context']['purpose'],'research_decision')
        facts=request_facts(record);key='measure8_original075_cached_complete_update_s'
        report=dict(report='Complete update {{'+key+'}}.',recommendation='Stop.',unresolved=[])
        rendered=render_text(report,facts)
        self.assertEqual(rendered['provenance'][0]['binding']['metric'],'complete_update_s')
        self.assertEqual(rendered['provenance'][0]['binding']['unit'],'s')
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
        self.assertTrue(audit['measurement']['passed']);self.assertTrue(a4['measurement']['passed'])
        with self.assertRaisesRegex(ValueError,'SEALED'):provider4(0,prepare_only=True)
        with self.assertRaisesRegex(ValueError,'SEALED'):request(0,prepare_only=True)

    def test_required_overflow_archive_failure_and_whole_payload_measurement(self):
        before=measure_input(self.payload,self.config,'research_decision')
        bigger=deepcopy(self.payload);bigger['tools'][0]['function']['description']+='x'*10000
        self.assertGreater(measure_input(bigger,self.config,'research_decision')['estimated_input_tokens'],before['estimated_input_tokens'])
        config=deepcopy(self.config);config['context_bytes']=100
        with self.assertRaisesRegex(ValueError,'REQUIRED_MATERIAL_EXCEEDS_BUDGET'):
            assemble_request(self.payload,config,'research_decision',self.packet,archive=self.archive,authority=self.authority,context_slot='research_packet')
        bad=deepcopy(self.ledger);next(iter(bad['facts'].values()))['source_artifact']['artifact_id']='0'*64
        with self.assertRaisesRegex(ValueError,'SOURCE_NOT_RETRIEVABLE'):assemble_context('final_report',bad,archive=self.archive)
        self.assertTrue(list(Path(self.temp.name).glob('audits/*.json')))
        with self.assertRaisesRegex(ValueError,'SECRET'):self.archive.snapshot({'api_key':'must never archive'})
