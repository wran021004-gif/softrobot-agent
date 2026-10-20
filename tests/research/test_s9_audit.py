"""Accounting regression against the real sealed S9 archive; no executions."""
import json,tarfile
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest
from tools.research.config import ROOT
from tests.research.s9_audit import accounting


class AuditTests(unittest.TestCase):
    def test_original_provider_tool_and_decision_records(self):
        with tarfile.open(ROOT/'evidence/s9_variant/study/immutable_artifacts.tar.gz') as archive:
            values={m.name.split('/')[-1][:-5]:json.load(archive.extractfile(m))
                for m in archive.getmembers() if m.name.endswith('.json')}
        snapshot=next(v for v in values.values() if isinstance(v,dict) and 'events' in v and 'calls' in v)
        store=Mock();store.artifact.side_effect=lambda ref:values[ref['artifact_id']]
        store.events.return_value=snapshot['events'];store.remaining.return_value=snapshot['ledger']
        host=SimpleNamespace(run_id='s9-variant-live-20261020',store=store)
        with patch('tests.research.s9_audit.state',return_value=snapshot['session']['state']):
            result=accounting(host)
        self.assertEqual(result['provider_requests'],10)
        self.assertEqual(result['total_tokens'],407379)
        self.assertEqual(result['tool_calls'],15);self.assertEqual(result['tool_errors'],2)
        self.assertEqual(result['evidence_reads'],11)
        self.assertEqual(result['new_physical_evaluations'],13)
        self.assertEqual(result['unique_response_probes'],12);self.assertEqual(result['cache_reuses'],1)
        self.assertEqual([r['action'] for r in result['decisions']],['control_search','select','select'])
        self.assertTrue(result['task_passed']);self.assertEqual(result['best_task_gap'],0.)
        self.assertEqual(result['missing_usage_requests'],[])


if __name__=='__main__':unittest.main()
