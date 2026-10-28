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
            card.write_text(f'Task: synthetic M{i}\nTrace: fixture only\nSpecial: unmeasured\nKnow-how: fixture\n',encoding='utf8')
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
        search=retrieve(h,dict(operation='search'))
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
            ('experience_retrieve',dict(operation='read',entry_id='fixture-m5',revision='1')),None])
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
        self.assertFalse(state(h)['analysis_results']);self.assertFalse(state(h)['physical_replays'])
        from tools.research.agent import converse
        before=h.store.remaining()
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'):
            asyncio.run(converse(h,restore_only=True))
        self.assertEqual(h.store.remaining(),before)
