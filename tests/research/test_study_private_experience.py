"""Scoped private guidance and Main wire checks; synthetic cards/MockTransport only."""
from copy import deepcopy
import asyncio
import gc
import json
import os
import shutil
import unittest
from uuid import uuid4
from unittest.mock import patch

from tools.research.config import ROOT, resolve
from tools.research.core import prepare
from tools.research.experience import freeze_study_entries, retrieve, disposition_bindings, PRIVATE_STATUS
from tools.research.state import state, update, save
from tools.state_io import digest
from tests.research.test_recent_round_tools import run_fixture


class StudyPrivateExperienceTests(unittest.TestCase):
    def setUp(self):
        self.study_id='offline-m5-'+uuid4().hex[:8]
        self.folder=ROOT/'runs/research'/self.study_id/'experience'
        self.folder.mkdir(parents=True)
        self.leaf=ROOT/'configs/research'/('._'+self.study_id+'.json')
        self.addCleanup(lambda: self.leaf.unlink(missing_ok=True))
        self.addCleanup(lambda: (gc.collect(),shutil.rmtree(self.folder.parent)))
        self.rows=[]
        for i in range(1,7):
            card=self.folder/f'M{i}.md'
            text=f'Task: synthetic M{i}\nTrace: fixture only\nSpecial: unmeasured\nKnow-how: fixture\n'
            if i==5:text+='离线合成经验：完整读取仍不授予科学证据。'*12
            card.write_text(text,encoding='utf8')
            self.rows.append(dict(entry_id=f'fixture-m{i}',revision='1',kind='case',
                path=card.relative_to(ROOT).as_posix(),task=f'fixture_task_{i}',structure='fixture',
                failure_type='fixture',version='1',status=PRIVATE_STATUS,study_id=self.study_id))
        self.index=dict(schema='study_private_experience_v1',study_id=self.study_id,entries=self.rows)
        self.index_path=self.folder/'index.json'
        self.index_path.write_text(json.dumps(self.index),encoding='utf8')
        self.value=json.loads((ROOT/'configs/research/study_m5_main_off_experience_v1.json').read_text(encoding='utf8'))
        self.value.update(study_id=self.study_id,study_experience_index=self.index_path.relative_to(ROOT).as_posix())
        self.leaf.write_text(json.dumps(self.value),encoding='utf8')
        self.spec=resolve(self.leaf)

    def host(self):
        h=prepare(self.leaf);s=state(h);spec=deepcopy(s['spec']);pilot=deepcopy(s['pilot'])
        spec['authorization']='Synthetic offline MockTransport fixture only; not a live grant'
        pilot.update(session_handoff_live_admitted=True,session_handoff_boundary='request_feedback')
        update(h,spec=spec,pilot=pilot,freeze='explicit-offline-fixture')
        return h

    def test_exact_reads_are_scoped_and_require_receipts_for_disposition(self):
        h=self.host();spec=deepcopy(state(h)['spec'])
        search=retrieve(h,dict(operation='search',kind='case',limit=20))
        private=[r for r in search['results'] if r['status']==PRIVATE_STATUS]
        self.assertEqual(len(private),6)
        self.assertTrue(all('content' not in row for row in private))
        with self.assertRaisesRegex(ValueError,'EXACT_ACTUAL_READ'):
            disposition_bindings(h,{'fixture-m1@1':'adopted'})
        for row in private:
            read=retrieve(h,dict(operation='read',entry_id=row['entry_id'],revision=row['revision']))
            self.assertEqual(read['results'][0]['content'],(ROOT/row['path']).read_bytes().decode('utf8'))
            self.assertFalse(read['scientific_evidence'])
            binding=disposition_bindings(h,{row['exact_key']:'context_only'})[0]
            self.assertEqual(binding['read_receipt'],read['reference'])
        with self.assertRaisesRegex(ValueError,'EXACT_EXPERIENCE_READ'):
            retrieve(h,dict(operation='read',entry_id='fixture-m1',revision='2'))
        spec['study_id']='another-study';update(h,spec=spec)
        self.assertFalse(any(r['status']==PRIVATE_STATUS for r in retrieve(h,dict(operation='search'))['results']))

    def test_manifest_cannot_grant_another_directory_and_mesh_is_fixed(self):
        self.assertEqual(self.spec['family_space']['serial_assembly']['cell_count_bounds'],[12,12])
        self.assertEqual(self.spec['family_space']['executable_segment_counts'],[2])
        self.assertEqual(self.spec['family_space']['executable_tendon_count_bounds'],[6,6])
        self.index['entries'][0]['path']='memory/diagnostic_index.json'
        self.index_path.write_text(json.dumps(self.index),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'OUTSIDE_OWNED_SCOPE'):
            freeze_study_entries(self.value,self.value['study_experience_index'])
        with self.assertRaisesRegex(ValueError,'OUTSIDE_OWNED_SCOPE'):
            freeze_study_entries(self.value,'memory/diagnostic_index.json')

    def test_private_cards_are_direct_reads_and_off_precedes_io(self):
        from tools.research.contracts import KnowledgePolicy
        from tools.research import experience
        with patch.object(experience,'read',side_effect=AssertionError('OFF_BEFORE_INDEX_IO')):
            self.assertEqual(freeze_study_entries(self.value,'unavailable',KnowledgePolicy(mode='off')),[])
        h=self.host()
        (self.folder/'M1.md').write_text('Changed offline fixture body',encoding='utf8')
        actual=retrieve(h,dict(operation='read',entry_id='fixture-m1',revision='1'))
        self.assertEqual(actual['results'][0]['content'],'Changed offline fixture body')

    def test_main_wire_discovers_six_cards_without_startup_body_injection(self):
        h=self.host()
        # Analysis is exposed only after its existing candidate/diagnose/approval
        # prerequisites. All identities and decisions here are synthetic.
        scope=dict(study_id=h.run_id,resolved_identity=self.spec['resolved_identity'],capabilities=['analysis'])
        save(h,dict(scope=scope,scope_identity=digest(scope),user_approval='Offline MockTransport fixture only'),
            'formal_study_authorization')
        from tools.research.design import generate_candidate
        from tools.research import core
        candidate=generate_candidate(h,dict(version='serial_family_generation_v2',
            family_space_identity=self.spec['family_space_identity'],segment_count=2,tendon_count=6),
            dict(origin='Synthetic directory check; no scientific claim'))['candidate']
        diagnose=dict(action='diagnose',hypothesis='Synthetic method selection.',
            expected_observation='Unmeasured.',weakening_observation='Unmeasured.',fixed_conditions='Fixture.',
            stopping_condition='No computation.',interpretation='Unmeasured.',
            decision=dict(hypothesis_id='fixture',research_intent='DIAGNOSE',
                selected_method='mujoco_direct_control_v1',selected_candidate=candidate))
        with patch('tools.research.core.guard'):
            core.dispatch(h,diagnose,'offline-method-directory')
        wires=run_fixture(h,[('research_route',dict(tool='experience_retrieve')),
            ('experience_retrieve',dict(operation='search')),
            ('experience_retrieve',dict(operation='read',entry_id='fixture-m5',revision='1')),
            ('research_route',dict(tool='research_plan',action='generate')),None])
        research=json.loads(wires[0]['messages'][-1]['content'].split('\n',1)[1])['research']
        self.assertEqual(len(research['experience_guidance']['study_private_entries']),6)
        self.assertNotIn('Task: synthetic',json.dumps(wires[0]))
        directory={r['tool']:r for r in research['tool_directory']}
        self.assertIn('experience_retrieve',directory)
        self.assertIn('research_analysis',directory)
        self.assertTrue({'generate','initialize_control','physical_replay','select','stop'}<=set(directory['research_plan']['actions']))
        receipts=[h.store.artifact(r) for r in state(h)['retrievals']]
        self.assertEqual([r['query']['operation'] for r in receipts],['search','read'])
        self.assertEqual(receipts[-1]['results'][0]['entry_id'],'fixture-m5')
        packet=lambda wire:json.loads(wire['messages'][-1]['content'].split('\n',1)[1])['research']
        delivered=packet(wires[3])['research_state']['pending_feedback']['items'][0]
        self.assertEqual(delivered['delivery'],'exact_feedback')
        result=delivered['result']
        self.assertGreater(len(json.dumps(result,separators=(',',':')).encode()),2000)
        parsed=json.loads(''.join(b.get('text','') for b in result['content']))
        self.assertEqual(parsed['results'][0]['content'],receipts[-1]['results'][0]['content'])
        self.assertFalse(packet(wires[3])['experience_read_progress']['reads'][0]['body_delivered'])
        progress=packet(wires[4])['experience_read_progress']['reads']
        self.assertEqual(len(progress),1);self.assertEqual(progress[0]['entry_id'],'fixture-m5')
        self.assertTrue(progress[0]['tool_read_completed']);self.assertTrue(progress[0]['body_delivered'])
        self.assertNotIn('离线合成经验',json.dumps(wires[4],ensure_ascii=False))
        self.assertEqual({k:packet(wires[4])['loaded_tool'][k] for k in ('tool','action')},dict(tool='research_plan',action='generate'))
        self.assertFalse(state(h)['analysis_results']);self.assertFalse(state(h)['physical_replays'])
        from tools.research.agent import converse
        before=h.store.remaining()
        with patch('tools.research.provider.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.tool_readiness.execution_environment',return_value=dict(status='ready')),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'):
            asyncio.run(converse(h,restore_only=True))
        self.assertEqual(h.store.remaining(),before)
        resumed=run_fixture(h,[None])
        self.assertEqual({k:packet(resumed[0])['loaded_tool'][k] for k in ('tool','action')},dict(tool='research_plan',action='generate'))
        self.assertTrue(packet(resumed[0])['experience_read_progress']['reads'][0]['body_delivered'])
        schema=next(t['function']['parameters'] for t in resumed[0]['tools'] if t['function']['name']=='research_plan')
        self.assertEqual(schema['properties']['action']['enum'],['generate'])

    def test_large_card_keeps_bounded_delivery_and_no_false_body_credit_on_wire(self):
        (self.folder/'M5.md').write_text('Large synthetic guidance. '*500,encoding='utf8')
        h=self.host()
        wires=run_fixture(h,[('research_route',dict(tool='experience_retrieve')),
            ('experience_retrieve',dict(operation='read',entry_id='fixture-m5',revision='1')),None])
        research=json.loads(wires[-1]['messages'][-1]['content'].split('\n',1)[1])['research']
        self.assertEqual(research['research_state']['pending_feedback']['items'][0]['delivery'],'summary_only')
        self.assertFalse(research['experience_read_progress']['reads'][0]['body_delivered'])
        self.assertNotIn('Large synthetic guidance. '*500,json.dumps(wires[-1]))

    def test_route_fields_and_view_corrections_survive_in_actual_wire(self):
        h=self.host();ref=state(h)['family_space_reference']
        wires=run_fixture(h,[('research_route',dict(tool='research_plan')),
            ('research_route',dict(tool='evidence_read')),
            ('evidence_read',dict(reference=ref,view='fields')),
            ('evidence_read',dict(reference=ref,view='fields',fields=['candidate_index'])),
            ('evidence_read',dict(reference=ref,view='working_set',pointer='/candidate_index')),None])
        def error(index):
            research=json.loads(wires[index]['messages'][-1]['content'].split('\n',1)[1])['research']
            row=research['research_state']['pending_feedback']['items'][0]
            return (json.loads(row['result']['content'][0]['text']) if row['delivery']=='exact_feedback' else row['facts'])
        self.assertEqual(error(1)['field'],'action');self.assertIn('generate',error(1)['expected'])
        self.assertEqual(error(3)['field'],'fields');self.assertEqual(error(3)['error_code'],'TOOL_SCHEMA_REQUIRED')
        self.assertEqual(error(4)['error_code'],'EVIDENCE_VIEW_MISMATCH')
        self.assertIn('working_set',error(4)['expected']);self.assertIn('/candidate_index',error(4)['expected'])
        last=json.loads(wires[-1]['messages'][-1]['content'].split('\n',1)[1])['research']
        self.assertEqual(last['research_state']['pending_feedback']['items'][0]['status'],'success')
