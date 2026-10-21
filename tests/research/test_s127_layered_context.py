"""Frozen real evidence stays retrievable; no Provider or scientific launch."""
from copy import deepcopy
import json
import unittest
from tools.research.research_context import context, decision_brief
from tools.research.core import read_evidence
from tools.research.state import state
from tools.state_io import digest
from tests.research.test_s127_working_set import historical_host


def size(value):return len(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode())


class LayeredContextTests(unittest.TestCase):
    def test_frozen_summary_and_every_detail_are_read_only(self):
        h=historical_host();before=deepcopy(state(h));ledger=h.store.remaining();events=h.store.events(h.run_id)
        current=context(h);brief=decision_brief(current);ws=current['evidence_working_set']
        self.assertLess(size(brief),36000);self.assertLess(size(brief['evidence_working_set']),15000)
        self.assertEqual(brief['all_fresh_results'],current['all_fresh_results'])
        self.assertEqual(len(brief['all_fresh_results']),9)
        self.assertNotIn('original_acceptance',json.dumps(brief['evidence_working_set']))
        self.assertNotIn('method_remaining',brief)
        self.assertEqual(brief['budget']['provider_budget'],current['budget']['provider_budget'])
        query={k:v for k,v in brief['evidence_access'].items() if k!='scope'}
        details=read_evidence(h,query)
        self.assertFalse(details.pop('authoritative_scientific_evidence'))
        self.assertEqual(details.pop('source_state_identity'),digest(before));self.assertEqual(details,ws)
        for field in ('candidate_index','control_result_links','eligible_methods','read_coverage','source_references'):
            self.assertEqual(read_evidence(h,dict(query,pointer='/'+field)),ws[field])
        for row in brief['evidence_working_set']['control_result_links']:
            if row.get('evaluation_reference'):
                original=h.store.artifact(row['evaluation_reference'])
                if original.get('acceptance'):
                    self.assertEqual(row['task_gap']['accepted'],original['acceptance']['accepted'])
                    self.assertEqual(set(row['constraints']),set(original['acceptance']['components']))
        self.assertEqual(state(h),before);self.assertEqual(h.store.remaining(),ledger)
        self.assertEqual(h.store.events(h.run_id),events)

    def test_distinct_nmpc_states_and_method_statuses(self):
        h=historical_host();c=context(h);brief=decision_brief(c)
        for row in brief['available_research_actions']:
            original=next(v for v in c['decision_feedback']['actions'] if all(v.get(k)==row.get(k) for k in ('action','method','candidate','source')))
            self.assertEqual(row['status'],original['status'])
        nmpc=[r for r in brief['evidence_working_set']['candidate_index'] if r['has_completed_nmpc_execution']]
        self.assertTrue(nmpc)
        for row in nmpc:
            self.assertTrue(row['has_measured_nmpc_reference']);self.assertTrue(row['has_residual_ppo_reference'])
            self.assertEqual(row['has_explicit_control_schedule'],row['control_initialized'])
        self.assertTrue(any(r.get('method')=='direct' for r in brief['available_research_actions']))
        self.assertTrue(any(r.get('method')=='residual' for r in brief['available_research_actions']))


if __name__=='__main__':unittest.main()
