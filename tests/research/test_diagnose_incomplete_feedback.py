"""Read-only failure projections use saved records, never a science worker."""
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch
from tools.research.diagnostic import diagnose


class IncompleteDiagnosisTests(unittest.TestCase):
    def test_native_and_physical_partial_facts_are_returned_without_causal_claim(self):
        def ref(c):return {'artifact_id':c*64,'media_type':'application/json'}
        analysis,replay,raw=ref('a'),ref('b'),ref('c')
        failure={'confirmed_completed_steps':152,'attempted_steps':153,'integration_state':[.152,1.],
            'control_before_call':[2.4,.3,3.75]}
        values={analysis['artifact_id']:{'status':'execution_incomplete','error':'FatalError','reason':'hessian',
                    'numerical_failure':failure,'boundary':{'termination_confirmed':True}},
                replay['artifact_id']:{'status':'execution_incomplete','raw_reference':raw,'boundary':{'termination_confirmed':True}},
                raw['artifact_id']:{'error':'FatalError','reason':'hessian','numerical_failure':failure}}
        store=MagicMock();store.artifact.side_effect=lambda r:values[r['artifact_id']]
        host=SimpleNamespace(store=store)
        s=dict(results=[],analysis_results=[analysis],physical_replays=[replay])
        with patch('tools.research.diagnostic.state',return_value=s),\
             patch('tools.research.diagnostic.save',return_value=ref('d')),\
             patch('tools.research.diagnostic.update') as changed:
            result=diagnose(host,[analysis,replay])
        self.assertEqual([x['source_kind'] for x in result['incomplete_executions']],['native_analysis','physical_replay'])
        self.assertEqual([x['completed_steps'] for x in result['incomplete_executions']],[152,152])
        self.assertEqual([x['failure_time_s'] for x in result['incomplete_executions']],[.152,.152])
        self.assertEqual(result['incomplete_executions'][1]['raw_reference'],raw)
        self.assertTrue(all(not x['acceptance_available'] for x in result['incomplete_executions']))
        self.assertIn('unresolved',result['unique_cause']);self.assertEqual(result['new_scientific_computations'],0)
        changed.assert_called_once();store.reserve.assert_not_called()

    def test_missing_failure_observations_remain_unknown(self):
        ref={'artifact_id':'a'*64,'media_type':'application/json'}
        store=MagicMock();store.artifact.return_value={'status':'execution_incomplete'}
        with patch('tools.research.diagnostic.state',return_value=dict(results=[],analysis_results=[ref],physical_replays=[])),\
             patch('tools.research.diagnostic.save',return_value=ref),patch('tools.research.diagnostic.update'):
            row=diagnose(SimpleNamespace(store=store),[ref])['incomplete_executions'][0]
        self.assertIsNone(row['failure_time_s']);self.assertIsNone(row['completed_steps']);self.assertIsNone(row['error'])
