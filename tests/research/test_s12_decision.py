"""S12 real sealed failure regressions; no new scientific calculations."""
import unittest
from unittest.mock import patch
from tools.research.research_context import tool_feedback,context,decision_brief
from tools.research.agent import plan_schema
from tools.research.state import state
from tests.research.s12_decision_probe import snapshot


class S12DecisionTests(unittest.TestCase):
    def test_wrapper_result_paths(self):
        h,p,values,event=snapshot(319)
        for result in ({'candidate':p['candidates'][0],'source':state(h)['control_initializations'][-1]['source']},
                       {'accepted_stop':True,'claims':{'fixture':True}}):
            wrapper={'artifact_id':'f'*64,'media_type':'application/json'}
            with patch('tools.research.research_context.save',return_value=wrapper):
                feedback=tool_feedback(h,{'result':result,'plan':{}})
            self.assertIsNone(feedback['scientific_reference'])
            self.assertEqual(feedback['new_facts']['pointer'],'/result')

    def test_next_request_actions_use_existing_closeout(self):
        h,p,values,event=snapshot(450)
        current=context(h)
        self.assertEqual(current['actions'],['stop','select'])
        self.assertNotIn('mechanics',plan_schema(current['actions'])['properties']['action']['enum'])
        self.assertEqual(h.store.remaining()['remaining']['model_calls'],5)

    def test_fresh_failure_is_compact_measured_diagnostic(self):
        h,p,values,event=snapshot(319)
        brief=decision_brief(context(h));feedback=brief['latest_scientific_feedback']
        diagnostic=feedback['physical_diagnostic']
        self.assertFalse(diagnostic['task_passed'])
        self.assertLessEqual(len(diagnostic['critical_samples']),4)
        self.assertTrue(diagnostic['critical_samples'])
        for row in diagnostic['critical_samples']:
            raw=h.store.artifact(row['raw_reference'])
            sample=raw['samples'][int(row['read_pointer'].rsplit('/',1)[-1])]
            self.assertEqual(row['observed']['tip_m'],sample['tip_m'])
        self.assertIn('not a proven failure cause',' '.join(diagnostic['limitations']))

    def test_no_future_artifacts_or_scientific_writes(self):
        first,p,values,event=snapshot(34)
        last,q,later,_=snapshot(450)
        self.assertNotIn(state(last)['physical_replays'][0]['artifact_id'],values)
        self.assertFalse(state(first)['physical_replays'])
        with self.assertRaises(AssertionError):first.store.reserve()


if __name__=='__main__':unittest.main()
