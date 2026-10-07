"""Focused recovery risks, using saved history and offline ledger probes."""
from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from uuid import uuid4
import shutil
import gc
import json
import subprocess
import sys

from tools.context_assembly import (EvidenceArchive, create_working_state, update_working_state,
    assert_experiment_eligible, persist_working_state, restore_working_state, assemble_working_context)
from tools.platform_store import Store
from tools.state_io import read, digest
from examples.check_research_recovery import ROOT, M4, SCOPE, prepare_sequence, child_restore


class ResearchRecoveryTests(TestCase):
    def setUp(self):
        # Normal inherited Windows ACLs; tempfile's private mode is inaccessible
        # under this workspace sandbox.
        self.directory = ROOT / 'runs' / ('research-recovery-test-' + uuid4().hex)
        self.directory.mkdir()
        def cleanup():
            target = self.directory.resolve()
            if not target.is_relative_to((ROOT / 'runs').resolve()) or not target.name.startswith('research-recovery-test-'):
                raise ValueError('TEST_CLEANUP_OUTSIDE_EXPECTED_DIRECTORY')
            gc.collect()  # Release read-only sqlite handles from the existing Store.
            shutil.rmtree(target)
        self.addCleanup(cleanup)
        self.archive = EvidenceArchive(self.directory / 'context', scope={'role':'Offline contract probes'})
        self.authority = dict(roles={}, legal_actions={'simulate':True},
            remaining_budget={'backend_solves':3}, stop={'status':'active', 'sealed_cases':[]})
        self.state = create_working_state({'bound_facts':{}}, authority=self.authority, archive=self.archive)

    def test_ledger_unknown_work_and_deliberate_repetition(self):
        rows = [dict(experiment_id=name, status=status) for name,status in
            [('pending','pending'), ('failed','failed'), ('incomplete','incomplete'), ('complete','completed')]]
        state = update_working_state(self.state, archive=self.archive, experiment_updates=rows)
        for row in rows:
            with self.assertRaisesRegex(ValueError,'WORK_ALREADY_RECORDED'):
                assert_experiment_eligible(state, row)
        repeat = dict(experiment_id='repeat-1', replication_of='complete', status='pending',
            action='simulate', cost={'backend_solves':1}, cache_hit=False)
        self.assertTrue(assert_experiment_eligible(state, repeat))
        state = update_working_state(state, archive=self.archive, experiment_updates=[repeat])
        repeat['status'] = 'completed'
        state = update_working_state(state, archive=self.archive, experiment_updates=[repeat])
        self.assertEqual(len(state['experiments']['repeat-1']), 2)
        repeat['cache_hit'] = True
        repeat['experiment_id'] = 'cached-repeat'
        with self.assertRaisesRegex(ValueError,'CACHE_IS_NOT_REPETITION'):
            assert_experiment_eligible(state, repeat)
        with self.assertRaisesRegex(ValueError,'COMPLETED_WORK_IMMUTABLE'):
            update_working_state(state, archive=self.archive,
                experiment_updates=[dict(experiment_id='incomplete',status='completed')])

    def test_claim_sources_candidate_invalidation_and_budget_stop(self):
        ref = self.archive.snapshot({'counterexample':{'value':False,'unit':'1'}})
        selector = dict(reference=ref,pointer='/counterexample')
        claim = dict(claim_id='hypothesis',statement='A tentative interpretation',
            supporting_evidence=[selector],counterexamples=[])
        state = create_working_state({'bound_facts':{}}, authority=self.authority,
            archive=self.archive, claims=[claim], candidate_configuration={'physics':'a','task':'t'},
            candidate_artifacts=[dict(kind='linearization',reference=ref,
                dependencies={'physics':'a'},reusable=True),
                dict(kind='task_reference',reference=ref,dependencies={'task':'t'},reusable=True)])
        revised = deepcopy(claim);revised.update(statement='Counterexample leaves the cause unresolved',counterexamples=[selector])
        state = update_working_state(state, archive=self.archive,claim_revisions=[revised],
            candidate_configuration={'physics':'b','task':'t'})
        self.assertEqual(state['claims']['hypothesis'][0]['claim'],claim)
        self.assertEqual(state['claims']['hypothesis'][1]['claim'],revised)
        self.assertFalse(state['candidate_artifacts'][0]['reusable'])
        self.assertTrue(state['candidate_artifacts'][1]['reusable'])
        with self.assertRaisesRegex(ValueError,'BUDGET_CANNOT_RESET'):
            update_working_state(state,archive=self.archive,authority=dict(self.authority,remaining_budget={'backend_solves':4}))
        stop = dict(self.authority,stop={'status':'stopped','sealed_cases':[{'case_id':'sealed'}]})
        state = update_working_state(state,archive=self.archive,authority=stop)
        with self.assertRaisesRegex(ValueError,'CANNOT_REOPEN'):
            update_working_state(state,archive=self.archive,authority=self.authority)
        with self.assertRaisesRegex(ValueError,'CANNOT_RESUME'):
            assert_experiment_eligible(state,{'experiment_id':'new'})
        store = Store(self.directory / 'store')
        reference = persist_working_state(state,store=store,archive=self.archive)
        restored,archive = restore_working_state(reference,store=store,scope=self.archive.scope)
        self.assertEqual({k:v for k,v in restored.items() if k!='current_execution'},state)
        self.assertTrue(restored['current_execution']['sealed'])
        self.assertEqual(archive.retrieve(ref,pointer='/counterexample')['page']['content'],{'value':False,'unit':'1'})
        with self.assertRaisesRegex(ValueError,'WORKING_STATE_SCOPE'):
            restore_working_state(reference,store=store,scope={'role':'different'})
        with self.assertRaisesRegex(ValueError,'ARCHIVE_STORE_REQUIRED'):
            Store(M4).create_context_archive()

    def test_saved_multiround_restore_into_new_process_and_shared_facts(self):
        prepare_sequence(self.directory)
        result = subprocess.run([sys.executable,'examples/check_research_recovery.py','--restore',str(self.directory)],
            cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        restored = read(self.directory / 'restored.json')
        self.assertTrue(restored['new_process'])
        self.assertTrue(restored['same_factual_entry_point'])
        self.assertEqual(restored['budget']['backend_solves'],0)
        self.assertEqual(restored['stop']['status'],'model_stopped')
        self.assertEqual(len(restored['claims']['holding_response']),3)
        self.assertNotEqual(restored['roles']['selected_incumbent'],restored['roles']['latest_attempt'])
        self.assertEqual(restored['purposes']['research_decision']['fact_identity'],
            restored['purposes']['final_report']['fact_identity'])
        self.assertGreater(restored['purposes']['research_decision']['facts'],200)
        self.assertIn('CANNOT_RESUME',restored['resume_rejection'])
