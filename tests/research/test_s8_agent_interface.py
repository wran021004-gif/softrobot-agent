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

    def test_pointer_rejection_includes_actual_children(self):
        host=Mock();host.store.artifact.return_value={'best':{},'candidates':[]}
        with patch('tools.research.agent.state',return_value={}),patch('tools.research.agent.record',return_value={}):
            r=error_feedback(host,{'input':{'reference':{'artifact_id':'a'*64},'pointer':'/proposals'}},KeyError('proposals'),{})
        self.assertIn('best, candidates',r['expected'])

    def test_search_facts_precede_large_preview(self):
        from tools.research.research_context import compact_evidence
        v={'best':{'reference':'fixture','source':'source','task_gap':{'accepted':False,'normalized_gap':1.}},
            'candidates':[{'reference':str(i),'outputs':{'large':'x'*20000},'task_gap':{}} for i in range(30)],
            'stop_reason':'iteration_limit','search_dimension':1,'finite_difference_evaluations':10}
        r=compact_evidence(v,{'artifact_id':'a'*64})
        prefix=json.dumps(r)[:1800]
        self.assertIn('available_keys',prefix);self.assertIn('normalized_gap',prefix)
        self.assertIn('/best',prefix);self.assertLess(len(json.dumps(r)),5000)

    def test_mathematical_summary_has_actual_static_input_pointer(self):
        from tools.research.analysis import compact_result
        value=dict(status='computed',operation='equilibrium',construction={'computed_tensions_n':[.1,.2]},
            binding={'tendon_order':['a','b']},scoped_claim={'fixture_large':'x'*20000})
        with patch('tools.research.evidence_policy.summarize_evidence',return_value={}):
            r=compact_result(value,{'artifact_id':'a'*64})
        self.assertEqual(r['static_input_observation']['tensions_n'],[.1,.2])
        self.assertEqual(r['static_input_observation']['task_acceptance'],'unmeasured')
        self.assertEqual(r['static_input_observation']['pointer'],'/construction/computed_tensions_n')
        self.assertNotIn('numerical_evidence',r['stored_result_keys'])
        self.assertIn('static_input_observation',json.dumps(r)[:1800])


if __name__=='__main__':unittest.main()
