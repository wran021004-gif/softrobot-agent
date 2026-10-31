"""Fabricated physical results and Mock Main choices, never actual V1 evidence."""
from copy import deepcopy
import json,unittest
from unittest.mock import patch
from tools.research.state import state,save,update
from tests.research.test_p63g_bounded_evidence import bounded_host,BoundedEvidenceTests
from tests.research.test_recent_round_tools import run_fixture


def selection(candidate,reference):
    return dict(action='select',selected_execution=reference,hypothesis='Synthetic exact result selection fixture.',
        expected_observation='Complete frozen task passes.',weakening_observation='Any original acceptance failure.',
        fixed_conditions='Synthetic fixture only.',stopping_condition='Select only the exact passing result.',
        interpretation='Fabricated interface test, not research evidence.',supporting_evidence=[reference],
        decision=dict(hypothesis_id='synthetic-r3-select',research_intent='SELECT',selected_method='physical_replay',
            selected_candidate=candidate,claimed_inference='observed_task_pass',requested_budget=0))


class ClosureTests(unittest.TestCase):
    def test_exact_certificate_select_automatically_stops_without_stop_action(self):
        h=bounded_host();c,ref=BoundedEvidenceTests().physical(h)
        self.assertEqual(state(h)['spec']['confirmation']['fresh_independent_repetitions'],0)
        with patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_REAL_WORKER')):
            wires=run_fixture(h,[('evidence_read',dict(reference=ref,view='acceptance_certificate')),
                ('research_route',dict(tool='research_plan',action='select')),('research_plan',selection(c,ref))])
        s=state(h);self.assertEqual(s['selected'],ref);self.assertIsNotNone(s['selected_solution'])
        self.assertEqual(h.store.artifact(s['selected_solution'])['evaluation'],ref)
        self.assertEqual(s['research_status'],'stopped')
        self.assertEqual(h.store.artifact(s['final_disposition'])['original_plan']['action'],'select')
        self.assertTrue(all(len(json.dumps(w).encode())<1048576 for w in wires))

    def test_failed_select_rejected_then_mock_main_legally_stops_using_full_index(self):
        h=bounded_host();c,original=BoundedEvidenceTests().physical(h)
        value=deepcopy(h.store.artifact(original));value['acceptance'].update(accepted=False,status='valid_failure')
        value['acceptance']['components']['holding_speed'].update(value=1.,passed=False)
        failed=save(h,value,'SYNTHETIC_R3_FAILED_RESULT')
        update(h,physical_replays=[failed],success_gate=None)
        stop=dict(action='stop',hypothesis='Synthetic finite failure does not establish global infeasibility.',
            expected_observation='No passing independent result in this fixture.',weakening_observation='A valid passing result.',
            fixed_conditions='Synthetic frozen fixture.',stopping_condition='End this fixture after inspecting all fresh results.',
            interpretation='Only this fabricated failed result is covered; no global exclusion.',supporting_evidence=[failed],
            decision=dict(hypothesis_id='synthetic-r3-stop',research_intent='STOP',selected_method='evidence_based_closure',
                selected_candidate=c,claimed_inference='empirical_search',requested_budget=0))
        with patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_REAL_WORKER')):
            run_fixture(h,[('evidence_read',dict(reference=failed,view='acceptance_certificate')),
                ('research_route',dict(tool='research_plan',action='select')),('research_plan',selection(c,failed)),
                ('evidence_read',dict(reference=state(h)['family_space_reference'],view='working_set',pointer='/all_fresh_results')),
                ('research_route',dict(tool='research_plan',action='stop')),('research_plan',stop)],limit=8)
        s=state(h);self.assertIsNone(s.get('selected'));self.assertEqual(s['research_status'],'stopped')
        self.assertEqual(h.store.artifact(s['final_disposition'])['original_plan']['action'],'stop')
        feedback=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id) if e['kind']=='model_original_tool_feedback']
        attempted=[r for r in feedback if r['tool_use']['name']=='research_plan' and r['tool_use']['input']['action']=='select']
        self.assertEqual(len(attempted),1);self.assertEqual(attempted[0]['result']['status'],'error')


if __name__=='__main__':unittest.main()
