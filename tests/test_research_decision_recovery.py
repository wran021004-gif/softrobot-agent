"""Saved evidence only: no provider, numerical integration or backend runs."""
from copy import deepcopy
import gc
import json
import shutil
from unittest import TestCase
from uuid import uuid4
from examples import research_model_v1 as pilot
from examples import research_decision_recovery as recovery
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.study_history import scientific_match
from tools.platform_search import prepare_offline_batch,_run_batch
from tools.state_io import digest,read


class RecoveryEvidenceTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=pilot.ROOT/'runs'/('recovery-offline-test-'+uuid4().hex)
        cls.w=pilot.prepare(cls.directory,offline_fixture=True)
        cls.w.freeze.update(decision_only=True,recovery_instructions=recovery.INSTRUCTIONS,recovery_policy=recovery.POLICY,
            original_pilot_execution_ids=['68ec1d6cc55c4b9baefe6eb58b73540b','af79836372454e4184e61dee1030ec39'])
        for eid in cls.w.freeze['original_pilot_execution_ids']:
            cls.w.records.append(pilot.historical(cls.w,str(pilot.DEFAULT),eid,'original_pilot_observation'))
        original=pilot.restore(pilot.DEFAULT)
        pilot.copy_references(original.store,cls.w.store,original.rounds)
        cls.w.rounds=deepcopy(original.rounds);cls.w.working=None
        cls.w.freeze['recovery_boundary']=dict(original_status='failed',original_failure=read(pilot.DEFAULT/'failure.json'),
            old_implementation=original.freeze['implementation'],
            original_usage=original.store.remaining(),first_decision=original.previous_decision,
            original_action=original.rounds[0]['decision']['decision'])
        pilot.reusable.feedback(cls.w,dict(status='decision_only_recovery',history_evidence=[
            dict(candidate=r['facts']['candidate'],metrics=r['acceptance']['metrics'],status=r['acceptance']['status'])
            for r in cls.w.records]),'offline_saved_evidence')
        pilot.configure(cls.w);pilot.persist(cls.w)
        cls.original_seal=recovery.failed_session_seal(original.store,original.host.run_id)

    @classmethod
    def tearDownClass(cls):
        gc.collect()
        assert cls.directory.resolve().is_relative_to((pilot.ROOT/'runs').resolve())
        shutil.rmtree(cls.directory)

    def test_saved_overlaps_and_individual_metrics(self):
        report=recovery.overlap_report(self.w)
        for pair in report['pairs']:
            self.assertTrue(pair['comparison']['scientific_match'])
            self.assertFalse(pair['comparison']['reuse_eligible'])
            self.assertFalse(pair['deliberately_planned_repetition'])
            self.assertEqual(pair['scientific_differences'],[])
        self.assertFalse(report['pairs'][0]['metrics']['terminal_error_m']['equal'])
        self.assertFalse(report['pairs'][0]['metrics']['holding_max_error_m']['equal'])
        self.assertTrue(report['pairs'][0]['metrics']['holding_max_speed_m_s']['equal'])
        self.assertTrue(all(r['equal'] for r in report['pairs'][1]['metrics'].values()))

    def test_meaningful_changes_never_merge_and_unknown_reuse(self):
        effective=self.w.store.artifact(self.w.records[0]['facts']['configuration'])['effective']
        for mutate in (
            lambda c:c['robot']['structure']['data']['components'][0].update(length_m=.161),
            lambda c:c['policy']['controller']['parameters']['data']['recipe'].update(holding_tip_speed_weight=.06),
            lambda c:c['task']['goal']['data'].update(target_m=[.29,.045,.19]),
            lambda c:c['task']['initializer']['parameters']['data'].update(q=[.1]),
        ):
            changed=deepcopy(effective);mutate(changed)
            self.assertFalse(scientific_match(changed,effective)['scientific_match'])
        self.assertEqual(scientific_match(effective,effective)['implementation_mapping'],'unknown')
        self.assertFalse(scientific_match(effective,effective)['reuse_eligible'])
        implementation=dict(dependencies={'controller.test@1.0.0':'same','solver.test@1.0.0':'same'})
        self.assertTrue(scientific_match(effective,effective,implementation=implementation,historical_implementation=implementation)['reuse_eligible'])
        different=deepcopy(implementation);different['dependencies']['solver.test@1.0.0']='changed'
        self.assertFalse(scientific_match(effective,effective,implementation=implementation,historical_implementation=different)['reuse_eligible'])

    def test_actual_shared_request_contains_bound_failures_and_counterexamples(self):
        adapter=EvidenceDrivenAdapter();payload=payload_for(self.w.host,adapter)
        self.assertEqual(list(adapter.advertised.values()),['research.decide'])
        packet=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        encoded=json.dumps(packet)
        for eid in pilot.RELEVANT_HISTORY:self.assertIn(eid,encoded)
        for r in self.w.records:
            self.assertIn(str(r['acceptance']['metrics']['holding_max_speed_m_s']),encoded)
        overlap=packet['scientific_overlap']
        self.assertEqual(overlap['new_execution_count'],2)
        self.assertEqual(overlap['novel_configuration_count'],0)
        self.assertEqual(overlap['previously_evaluated_count'],2)
        self.assertEqual(overlap['deliberate_replication_count'],0)
        self.assertIn('failed',encoded);self.assertIn('IncompleteRead',encoded)
        self.assertTrue(all(c['proposal_only'] for c in packet['capabilities']['legal'].values()))
        # Actual alias selectors remain tied to their candidate and execution.
        state=self.w.store.session(self.w.host.run_id)['state']
        for alias,row in packet['current_feedback']['aliases'].items():
            ref=packet['current_feedback']['reference'];value=self.w.store.artifact(ref)
            for part in row['pointer'].strip('/').split('/'):
                value=value[int(part)] if isinstance(value,list) else value[part.replace('~1','/').replace('~0','~')]
            self.assertEqual(value,row['value'])
        self.assertEqual(self.w.store.remaining()['used']['model_calls'],0)
        self.assertEqual(self.w.store.remaining()['used']['backend_solves'],0)

    def test_restore_coverage_budget_seal_and_execution_guard(self):
        restored=pilot.restore(self.directory)
        self.assertEqual(restored.freeze['history_coverage'],self.w.freeze['history_coverage'])
        self.assertEqual(digest(restored.working),digest(self.w.working))
        self.assertEqual(restored.store.remaining(),self.w.store.remaining())
        original=pilot.restore(pilot.DEFAULT)
        self.assertEqual(recovery.failed_session_seal(original.store,original.host.run_id),self.original_seal)
        for tool in ('simulation.run','analysis.linearize_candidate','diagnosis.saved_state_check'):
            receipt=self.w.host.invoke(dict(request_id='blocked-'+uuid4().hex,tool_id=tool,tool_version='1.0.0',
                arguments={},reason='Offline decision-only dispatch guard check.',cache='new'))
            self.assertIn('DECISION_ONLY_NO_EXPERIMENT_DISPATCH',receipt['error'])
        with self.assertRaisesRegex(ValueError,'DECISION_ONLY_NO_BATCH_EXECUTION'):
            prepare_offline_batch(self.w.host,{})
        with self.assertRaisesRegex(ValueError,'DECISION_ONLY_NO_BATCH_EXECUTION'):
            _run_batch(self.w.host,lambda *args:self.fail('No stage callback may run'))

    def test_z_native_future_proposal_accepted_without_execution_allowance(self):
        from tests.test_research_model_v1 import NativePilotTests
        fixture=NativePilotTests();fixture.w=self.w
        fixture.packet=pilot.configure(self.w);fixture.alias=next(iter(fixture.packet['current_feedback']['aliases']))
        result,_=fixture.invoke_native(fixture.search())
        self.assertTrue(result['batch_plan']['decision_only'])
        self.assertFalse(result['batch_plan']['execution_authorized'])
        self.assertTrue(result['batch_plan']['requires_future_grant'])
        self.assertEqual(self.w.store.remaining()['used']['backend_solves'],0)
        self.assertNotIn('search_batch',self.w.store.session(self.w.host.run_id)['state'])

    def test_ledger_settlement_cannot_mint_budget(self):
        from tools.context_assembly import update_working_state
        state=deepcopy(self.w.working);authority=deepcopy(state['authority'])
        authority['ledger_reconciliation']=True
        authority['budget_accounting']=self.w.store.remaining()
        authority['remaining_budget']=self.w.store.spendable(self.w.host.run_id)['remaining']
        state['budget']['wall_s']=authority['remaining_budget']['wall_s']-1
        updated=update_working_state(state,archive=pilot.archive(self.w),authority=authority)
        self.assertEqual(updated['budget_accounting'],self.w.store.remaining())
        forged=deepcopy(authority);forged['remaining_budget']['wall_s']+=1
        with self.assertRaisesRegex(ValueError,'CONTEXT_LEDGER_RECONCILIATION_NOT_VERIFIED'):
            update_working_state(state,archive=pilot.archive(self.w),authority=forged)
