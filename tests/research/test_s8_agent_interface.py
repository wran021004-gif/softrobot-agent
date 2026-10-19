"""Rejected request and native schema fixtures, with no provider calls."""
import json
from unittest.mock import Mock, patch
import unittest
from tools.research.agent import error_feedback, plan_schema
from tools.research.contracts import LocalControlSearchSettings


class AgentInterfaceTests(unittest.TestCase):
    def feedback(self,exc,now=None):
        with patch('tools.research.agent.state',return_value=now or {}),patch('tools.research.agent.record',return_value={'artifact_id':'a'*64}):
            return error_feedback(Mock(),{'input':{},'toolUseId':'fixture'},exc,{})

    def test_invalid_window_precise_and_compact(self):
        try:LocalControlSearchSettings(version='local_control_search_v2',knots_s=[.2,.3],correction_window_s=[.25,.35])
        except ValueError as exc:r=self.feedback(exc)
        self.assertEqual(r['error_code'],'ORDERED_V2_CORRECTION_WINDOW_REQUIRED')
        self.assertEqual(r['field'],'control_search.settings.correction_window_s')
        self.assertNotIn('research_context',r);self.assertFalse(r['scientific_execution_started'])
        self.assertLess(len(json.dumps(r)),900)

    def test_candidate_reference_and_execution_status(self):
        r=self.feedback(ValueError('DECISION_CANDIDATE_MISMATCH'))
        self.assertEqual(r['field'],'decision.selected_candidate')
        self.assertEqual(self.feedback(ValueError('failure'),{'physical_replay_launches':1})['status'],'execution_failed')

    def test_pointer_error_has_no_full_history(self):
        self.assertEqual(self.feedback(KeyError('samples'))['error_code'],'INVALID_EVIDENCE_POINTER')

    def test_schema_requires_action_payload(self):
        s=plan_schema(['initialize_control','stop'])
        self.assertEqual(s['allOf'][0]['then']['required'],['control_seed'])
        self.assertNotIn('generation',s['properties'])


if __name__=='__main__':unittest.main()
