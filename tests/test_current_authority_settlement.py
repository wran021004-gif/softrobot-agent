"""Offline copies of the existing v3 ledger; no provider or backend reruns."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import gc
from contextlib import closing
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
from examples import research_model_v1 as pilot
from tools.platform_store import Store,zero
from tools.current_research_authority import accounting_binding,verify_accounting_transition
from tools.context_assembly import EvidenceArchive,ROOT,update_working_state
from tools.state_io import read,digest
from tools.batch_budget import downstream_available
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter

SOURCE=ROOT/'runs/research_native_development_v3_20261007'


class SettlementTests(TestCase):
    def setUp(self):
        self.root=ROOT/'runs'/('settlement-test-'+uuid4().hex);self.root.mkdir()
        with closing(Store(SOURCE).connect(True)) as src,closing(Store(self.root).connect()) as dst:src.backup(dst)
        # Isolated unit ledger writes only. The real grant index is untouched;
        # copied projects remain forbidden by production check_root. Paid host
        # invocation is explicitly disabled for the whole fixture.
        original=Store.check_root
        def fixture_root(store,db):
            if store.root==self.root:return
            return original(store,db)
        self.guard=patch.object(Store,'check_root',fixture_root);self.guard.start()
        from tools.platform_host import Host
        self.paid=patch.object(Host,'invoke',side_effect=AssertionError('OFFLINE_FIXTURE_NO_EXECUTION'));self.paid.start()
        shutil.copyfile(SOURCE/'live_clock.json',self.root/'live_clock.json')
        self.store=Store(self.root);self.run='research_native_development_v3_20261007-research'
        self.state=read(SOURCE/'working_state.json')['state']
        self.archive=SimpleNamespace(stores=(self.store,))

    def tearDown(self):
        self.guard.stop();self.paid.stop();gc.collect()
        assert self.root.resolve().is_relative_to((ROOT/'runs').resolve());shutil.rmtree(self.root)

    def authority(self):
        binding=accounting_binding(self.store,self.run);value=self.store.artifact(binding['reference'])
        return dict(remaining_budget=value['research_capacity'],budget_accounting=value['accounting'],
            campaign_clock=value['clock'],accounting_binding=binding)

    def settle(self,row,elapsed=336.64255690574646,status='completed'):
        return self.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],
            caller='engineering',tool_id='engineering.offline_replay',tool_version='3.2.0',
            execution_status=status,charged=zero()),{'offline':True},elapsed)

    def baseline(self):
        authority=self.authority();self.assertTrue(verify_accounting_transition(self.state,authority,self.archive))
        state=deepcopy(self.state);state['authority'].update(authority);state['budget_accounting']=authority['budget_accounting'];state['budget']=authority['remaining_budget']
        return state

    def cloned_working(self):
        w=pilot.restore(SOURCE);w.store=self.store
        from tools.platform_host import Host
        w.host=Host(self.root,self.run)
        saved=read(SOURCE/'working_state.json')
        shutil.copytree(SOURCE/'context_assembly',self.root/'context_assembly')
        manifest=read(ROOT/saved['source_manifest'])
        archive=EvidenceArchive(self.root/'context_assembly',scope=w.working['archive_scope'],stores=(self.store,))
        for source in manifest['sources']:
            source=deepcopy(source)
            if 'store_root' in source:source['store_root']=self.root.relative_to(ROOT).as_posix()
            if 'path' in source:
                suffix=Path(source['path']).relative_to(SOURCE.relative_to(ROOT))
                source['path']=(self.root.relative_to(ROOT)/suffix).as_posix()
            archive.sources[source['reference']['artifact_id']]=source
        w.context_archive=archive
        return w

    def test_same_session_dependency_migration_and_request(self):
        from examples.research_campaign_v3 import migrate_research_dependency,seal
        from tools.current_research_authority import verify_dependency_migration
        before_state=self.baseline();w=self.cloned_working()
        before=deepcopy(self.store.session(self.run));used=self.store.remaining()['used']
        self.assertEqual(w.host.compatibility()['changed'],['research.decide@1.0.0'])
        w.freeze['implementation']=seal();boundary=migrate_research_dependency(w)
        after=self.store.session(self.run)
        self.assertEqual(after['snapshot']['input'],before['snapshot']['input'])
        self.assertEqual(after['state']['turn'],before['state']['turn'])
        self.assertEqual(after['state'].get('protocol_corrections_used'),before['state'].get('protocol_corrections_used'))
        self.assertEqual(self.store.remaining()['used'],used)
        self.assertTrue(w.host.compatibility()['compatible'])
        self.assertTrue(verify_accounting_transition(before_state,self.authority(),self.archive))
        pilot.configure(w);payload=payload_for(w.host,EvidenceDrivenAdapter())
        self.assertIn('research_decide',[t['function']['name'] for t in payload['tools']])
        # Even a migration artifact/event cannot authorize changing the input.
        from tools.platform_store import plain
        forged=deepcopy(after['snapshot']);forged['input']['policy']['budget']['model_calls']+=1
        with self.store.transaction() as db:
            boundary['after_snapshot']=plain(self.store.put(db,forged));ref=plain(self.store.put(db,boundary))
            self.store.event(db,self.run,'authorized_dependency_migration','completed',outputs=[ref],version='3.3.0')
            db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(boundary['after_snapshot']['artifact_id'],self.run))
            state=self.store.session(self.run,db)['state'];state['authorized_dependency_migration']=ref
            self.store.update_state(db,self.run,state)
        with self.assertRaisesRegex(ValueError,'MIGRATION_CHANGED_AUTHORIZATION'):
            verify_dependency_migration(self.store,self.run,digest(before['snapshot']),digest(forged))

    def test_recorded_release_and_actual_outgoing_request(self):
        events=self.store.events(self.run)
        reserved=next(e for e in events if e['request_id']=='observed-live-boundary-repairs' and e['status']=='reserved')
        settled=next(e for e in events if e['request_id']=='observed-live-boundary-repairs' and e['status']=='completed')
        self.assertEqual(reserved['cost']['wall_s'],1800.)
        self.assertAlmostEqual(settled['cost']['wall_s'],336.64255690574646)
        self.baseline()
        # Full configure -> shared fit -> current snapshot check, using the saved
        # physical outcomes and explicitly permitted historical source archive.
        w=self.cloned_working()
        pilot.configure(w);payload=payload_for(w.host,EvidenceDrivenAdapter())
        packet=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        self.assertEqual(packet['capabilities']['remaining'],downstream_available(self.store,self.run))
        self.assertEqual(packet['capabilities']['remaining']['backend_solves'],6)
        self.assertEqual(self.store.remaining()['remaining']['backend_solves'],26)
        self.assertEqual(self.store.remaining()['used']['backend_solves'],2)

    def test_restored_outstanding_then_failed_partial_settlement_and_repeat(self):
        old=self.baseline();row,_=self.store.reserve(self.run,'offline-reservation',digest('test'),'engineering',{**zero(),'tool_calls':1,'wall_s':1800.})
        during=self.authority();self.assertTrue(verify_accounting_transition(old,during,self.archive))
        old['authority'].update(during);old['budget_accounting']=during['budget_accounting'];old['budget']=during['remaining_budget']
        restored=Store(self.root);self.assertIsNone(restored.lookup(self.run,'offline-reservation')['receipt'])
        self.store=restored;self.archive.stores=(restored,)
        receipt=self.settle(row,elapsed=123.5,status='failed');after=self.authority()
        self.assertTrue(verify_accounting_transition(old,after,self.archive))
        self.assertAlmostEqual(after['remaining_budget']['wall_s']-during['remaining_budget']['wall_s'],1676.5)
        charged=deepcopy(self.store.remaining()['used'])
        self.assertEqual(self.settle(row,elapsed=0),receipt);self.assertEqual(self.store.remaining()['used'],charged)
        old['authority'].update(after);old['budget_accounting']=after['budget_accounting'];old['budget']=after['remaining_budget']
        self.assertTrue(verify_accounting_transition(old,self.authority(),self.archive))

    def test_unknown_reservation_stays_charged_until_explicit_settlement(self):
        old=self.baseline();row,_=self.store.reserve(self.run,'offline-unknown',digest('unknown'),'engineering',{**zero(),'tool_calls':1,'wall_s':1800.})
        self.store.mark_unknown(self.run,row['request_id']);authority=self.authority()
        self.assertTrue(verify_accounting_transition(old,authority,self.archive))
        self.assertIsNone(self.store.lookup(self.run,row['request_id'])['receipt'])
        self.assertAlmostEqual(authority['budget_accounting']['used']['wall_s']-old['budget_accounting']['used']['wall_s'],1800.)

    def test_unauthorized_grant_increase_stale_session_and_lost_charge_rejected(self):
        old=self.baseline();authority=self.authority()
        stale=deepcopy(old);stale['authority']['current_authority']['session_id']='old-session'
        with self.assertRaisesRegex(ValueError,'STALE_SESSION'):verify_accounting_transition(stale,authority,self.archive)
        wrong=deepcopy(authority);wrong['remaining_budget']=self.store.remaining()['remaining']
        with self.assertRaisesRegex(ValueError,'WRONG_PHASE_CAPACITY'):verify_accounting_transition(old,wrong,self.archive)
        with self.store.transaction() as db:
            config=self.store.config(db);config['budget']['wall_s']+=1
            db.execute('UPDATE meta SET value=? WHERE key=?',(json.dumps(config),'config'))
        with self.assertRaises(ValueError):verify_accounting_transition(old,self.authority(),self.archive)

    def test_discarded_spending_or_settled_history_rejected(self):
        old=self.baseline()
        with self.store.transaction() as db:db.execute('DELETE FROM calls WHERE request_id=?',('model-0',))
        with self.assertRaisesRegex(ValueError,'DISCARDED_OR_UNRECORDED'):self.authority()

    def test_original_deadline_and_frozen_phase_policy_cannot_expand(self):
        old=self.baseline();clock=read(self.root/'live_clock.json');clock['deadline_unix']+=1
        (self.root/'live_clock.json').write_text(json.dumps(clock),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'CLOCK_CHANGED'):verify_accounting_transition(old,self.authority(),self.archive)
        clock['deadline_unix']-=1;(self.root/'live_clock.json').write_text(json.dumps(clock),encoding='utf8')
        with self.store.transaction() as db:
            state=self.store.session(self.run,db)['state'];state['role_context']['campaign_permissions']['reserved_verification_backends']=0
            self.store.update_state(db,self.run,state)
        with self.assertRaisesRegex(ValueError,'PHASE_POLICY_CHANGED'):verify_accounting_transition(old,self.authority(),self.archive)
