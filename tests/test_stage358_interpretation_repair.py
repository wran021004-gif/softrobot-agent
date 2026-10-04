"""Changed delivery and same-ledger cycle accounting, with paid work blocked."""
from copy import deepcopy
import json
from unittest.mock import patch
from examples import stage358_interpretation_repair as repair
from tests.test_stage356_batch import BatchTests, offline_directory
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.state_io import digest
from tools.platform_store import Store, plain, zero


class RepairTests(BatchTests):
    def test_compact_packet_sources_counts_and_required_payload_content(self):
        parent = repair.parent_host()
        packet = repair.decision_packet()
        before = parent.store.remaining()['used']
        session = Store.session
        def compact(store, *args, **kwargs):
            value = deepcopy(session(store, *args, **kwargs))
            if value['run_id'] == parent.run_id:
                value['state'].update(fact_catalog={}, read_ledger=[], workflow_memory=[])
                value['state'].pop('reference_interface',None)
                value['state']['role_context'].update(decision_packet=packet,
                    decision_packet_reference=dict(artifact_id=digest(packet),media_type='application/json'),
                    instructions=repair.INSTRUCTIONS, working_memory=[])
            return value
        with patch.object(Store,'session',compact):
            payload=payload_for(parent,EvidenceDrivenAdapter())
        checked=repair.check_payload(payload,packet)
        self.assertTrue(checked['passed'])
        self.assertEqual(len(packet['configurations']),5)
        self.assertEqual([(r['initialization_selections'],r['positive_iteration_selections'])
                          for r in packet['diagnostics']],[(30,5),(17,18)])
        c=next(r for r in packet['comparisons'] if r['candidate']=='holding_only' and r['reference']=='retained_baseline')
        self.assertEqual(c['candidate_minus_reference']['mean_complete_update_s'],.12975374571978904)
        self.assertEqual(c['reference_execution_id'],'cf997605885642759ee33920e2c9e2ef')
        self.assertFalse(packet['joint_positive_weight_tested'])
        self.assertEqual(parent.store.remaining()['used'],before)
        self.assertNotIn('reference_view',payload['messages'][1]['content'])

    def test_child_cycle_caps_preserve_parent_phase_and_project_limits(self):
        with offline_directory() as directory:
            parent, _=self.fixture(directory,model_calls=8,max_candidates=4)
            original=repair.parent_host().store.session(repair.parent_host().run_id)['state']['role_context']
            with parent.store.transaction() as db:
                state=parent.store.session(parent.run_id,db)['state']
                state['role_context']=deepcopy(original)
                state['role_context']['phase_budget']=dict(limit=dict(model_calls=2),started_usage=zero())
                parent.store.update_state(db,parent.run_id,state)
                ref=plain(parent.store.put(db,{}))
            project=parent.store.config();phase=parent.store.session(parent.run_id)['state']['role_context']['phase_budget']
            child=repair.create_bounded_child(parent,{},ref)
            self.assertEqual(child.store.remaining(child.run_id)['limit']['model_calls'],2)
            self.assertEqual(child.store.remaining(child.run_id)['limit']['backend_solves'],0)
            for i in range(2):
                row,_=child.store.reserve(child.run_id,'offline-provider-'+str(i),digest(i),'offline-test',
                    {**zero(),'model_calls':1,'wall_s':30.},kind='model_request')
                child.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],
                    caller='offline-test',tool_id='offline.fixture',tool_version='1.0.0',
                    execution_status='completed',charged=zero()),{},.01)
            with self.assertRaisesRegex(ValueError,'BUDGET_EXHAUSTED'):
                child.store.reserve(child.run_id,'third',digest('third'),'offline-test',{**zero(),'model_calls':1})
            self.assertEqual(parent.store.phase_remaining(parent.run_id)['remaining']['model_calls'],0)
            self.assertEqual(parent.store.session(parent.run_id)['state']['role_context']['phase_budget'],phase)
            self.assertEqual(parent.store.config(),project)
            self.assertEqual(parent.store.remaining()['used']['backend_solves'],0)
