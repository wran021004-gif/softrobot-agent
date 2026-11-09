"""Actual saved Candidate/Plan/Result projection, plus existing-report reuse."""
import json
from types import SimpleNamespace
import unittest

from tools.platform_store import Store
from tools.research.research_context import trace_entry,bounded_action_trace
from tests.research.test_diagnostic_feedback_repair import STORE,REF


def result75_row(host):
    raw=host.store.artifact(REF,paths=('candidate','plan_reference'))
    plan=host.store.artifact(raw['plan_reference'])['original_plan']
    return dict(step=75,action='research_analysis',method='mechanism_structure_v1',candidate=raw['candidate'],
        source=dict(reference=raw['plan_reference'],pointer='/original_plan'),result_references=[REF],
        execution_status='completed',execution_kind='scientific_result_recorded',outcome=dict(status='computed'),
        agent_hypothesis=plan,receipt_output=None)


@unittest.skipUnless((STORE/'platform.sqlite').exists(),'Private original saved evidence is not installed')
class CompactMilestoneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.host=SimpleNamespace(store=Store(STORE),run_id='passive-base-only-full-autonomous-study-20261108-02')
        cls.row=result75_row(cls.host)
        with cls.host.store.read_snapshot():cls.entry=trace_entry(cls.row,cls.host)

    def test_real_lineage_numbers_costs_and_sources(self):
        facts=self.entry['observed_facts']
        self.assertIsNotNone(facts['parent_candidate'])
        self.assertGreater(facts['parameter_change_count'],0)
        self.assertTrue(all('delta' in r and 'unit' in r for r in facts['parameter_changes']))
        result=facts['results'][0]
        self.assertEqual(result['reference'],REF)
        self.assertEqual(result['task_diagnosis']['diagnostic_status'],'complete')
        self.assertIsNotNone(result['cost']);self.assertIsNotNone(result['qualification'])
        self.assertEqual(result['task_gap']['valid_complete'],False)

    def test_hypothesis_interpretation_facts_and_context_are_separate(self):
        self.assertIn('may preserve',self.entry['main_hypothesis']['hypothesis'])
        self.assertNotIn('hypothesis',self.entry['observed_facts'])
        self.assertTrue(self.entry['reporter_interpretation']['reference'])
        wire=json.dumps(self.entry)
        self.assertNotIn('qualification_samples',wire);self.assertNotIn('"integration_state":',wire)
        self.assertNotIn('"state_vector":',wire)
        self.assertLess(len(wire),18000)
        # Recent limit and the two older important failures keep their owners.
        rows=[{**self.row,'step':i,'execution_status':'rejected' if i<3 else 'completed'} for i in range(8)]
        trace=bounded_action_trace(dict(total=8,recent=rows),4)
        self.assertEqual(len(trace['recent']),4);self.assertEqual(len(trace['unresolved']),2)


class ReporterReuseTests(unittest.TestCase):
    def test_same_question_and_evidence_reuse_existing_artifact(self):
        from tests.research.test_passive_capabilities import passive_host
        from tests.research.test_post_reporter_planning import representable_candidate,PROFILE
        from tools.research.reporter import investigate,entries,_wire
        with passive_host(PROFILE) as host:
            candidate=representable_candidate(host)
            query=dict(question='OFFLINE contract fixture: what is actually established by this saved candidate?',
                references=[candidate],reads=[dict(reference=candidate,view='full',pointer='/parameters')])
            first=investigate(host,query);count=len(entries(host))
            second=investigate(host,query)
            self.assertTrue(second['reused']);self.assertEqual(second['report_reference'],first['report_reference'])
            self.assertEqual(len(entries(host)),count)
            changed=investigate(host,{**query,'question':'OFFLINE fixture: what remains unknown about dynamic qualification?'})
            self.assertNotEqual(changed['report_reference'],first['report_reference'])
            wire=_wire(host,changed['report_reference'],host.store.artifact(changed['report_reference']))
            delta=json.loads(wire['messages'][-1]['content'])['evidence_delta']
            self.assertEqual(delta['previous_report'],first['report_reference'])
            self.assertEqual(delta['new_result_references'],[])


if __name__=='__main__':unittest.main()
