"""Small offline regressions for existing handoff evidence projection."""
import json
import unittest
from unittest.mock import Mock
from tools.research.session_handoff import feedback_delivery


class SelectedFeedbackTests(unittest.TestCase):
    def project(self, value, view='full'):
        result=dict(status='success',content=[dict(text=json.dumps(value))])
        original=dict(tool_use=dict(toolUseId='fixture-tool',name='evidence_read',
            input=dict(reference={'artifact_id':'fixture'},view=view,pointer='/diagnostic')),result=result)
        host=Mock();host.run_id='fixture'
        host.store.events.return_value=[dict(kind='model_original_tool_feedback',outputs=['fixture-feedback'])]
        host.store.artifact.return_value=original
        delivery=feedback_delivery(host,['fixture-tool'])['items'][0]
        host.store.reserve.assert_not_called();host.store.transaction.assert_not_called()
        return delivery

    def test_large_selected_object_retains_scalars_and_small_metrics(self):
        value=dict(J=.125,initial_J=.25,stop_reason='fixture_iteration_limit',
            best_metrics=dict(error_m=.01),large_array=[dict(values=list(range(500)))]*8,
            task_acceptance='unmeasured')
        row=self.project(value)
        self.assertEqual(row['delivery'],'summary_only')
        facts=row['facts'];shown=facts['selected_value']
        self.assertEqual(shown['J'],value['J'])
        self.assertEqual(shown['stop_reason'],value['stop_reason'])
        self.assertEqual(shown['best_metrics'],value['best_metrics'])
        self.assertIn('large_array',facts['omitted_keys'])
        self.assertLessEqual(len(json.dumps(facts).encode()),3000)

    def test_summary_keeps_preview_semantics_and_small_feedback_stays_exact(self):
        value=dict(value=dict(J=.125,large_array=[dict(values=list(range(500)))]*8),
            reference={'artifact_id':'fixture'},view='deterministic_summary')
        facts=self.project(value,'summary')['facts']
        self.assertEqual(facts['selected_value']['J'],.125)
        self.assertIn('preview semantics',facts['scope'])
        self.assertEqual(self.project(dict(J=.125))['delivery'],'exact_feedback')


if __name__=='__main__':unittest.main()
