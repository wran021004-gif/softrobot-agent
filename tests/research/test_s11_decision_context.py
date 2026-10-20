"""Real sealed S10 regressions and explicitly synthetic budget boundaries; offline."""
from copy import deepcopy
from functools import lru_cache
import json
import unittest
from unittest.mock import patch
from tools.research import core
from tools.research.agent import DeepSeekModel, error_feedback
from tools.research.research_context import context, decision_brief, tool_feedback
from tools.research.evidence_policy import admit_decision, registered_references
from tools.research.budget import decision_budget, protected
from tools.research.contracts import Plan
from tools.research.state import state
from tools.state_io import digest, read
from tools.research.config import ROOT
from tests.research.s8_audit import archive_host, decision_projection, size


@lru_cache(maxsize=1)
def sealed():return archive_host('evidence/s10_mirror/study')


class DecisionContextTests(unittest.TestCase):
    def setUp(self):
        self.host,self.values=sealed()
        self.original=deepcopy(next(v['session']['state'] for v in self.values.values() if isinstance(v,dict) and 'events' in v and 'calls' in v))
        self.host.store.session.return_value={'state':deepcopy(self.original)}
        self.host.store.events.return_value=next(v['events'] for v in self.values.values() if isinstance(v,dict) and 'events' in v and 'calls' in v)

    def test_all_29_saved_requests_and_facts(self):
        result=decision_projection(self.host)
        self.assertEqual(len(result['requests']),29)
        self.assertEqual((len(result['reads']),len(result['errors'])),(48,6))
        self.assertEqual(result['provider_total_tokens'],1754349)
        rows=result['packet_comparisons']
        self.assertTrue(all(all(r['retained_facts'].values()) for r in rows))
        self.assertLess(sum(r['new_bytes'] for r in rows),.8*sum(r['old_bytes'] for r in rows))

    def test_current_brief_registered_handoffs_and_math_scope(self):
        current=context(self.host);before=deepcopy(self.values)
        brief=decision_brief(current)
        self.assertFalse(brief['task_accepted'])
        self.assertAlmostEqual(brief['best_valid']['task_gap']['normalized_gap'],2.419092492282298)
        self.assertIn('holding_speed',brief['best_valid']['violated_constraints'])
        self.assertEqual(len(brief['all_fresh_results']),21)
        self.assertNotIn('observations',brief);self.assertNotIn('decision_feedback',brief)
        self.assertEqual(brief['latest_scientific_feedback']['operation'],'equilibrium')
        self.assertIn('unmeasured',json.dumps(brief['latest_scientific_feedback']))
        self.assertEqual(self.values,before)
        self.assertEqual(state(self.host),self.original)
        self.assertLess(size(brief),size(current))
        for row in brief['available_research_actions']:
            self.assertNotEqual(row['status'],'eligible')
            for ref in row.get('supporting_evidence',[]):self.assertIn(ref,registered_references(self.host))

    def test_exact_handoff_admitted_wrapper_and_wrong_candidate_rejected(self):
        s=state(self.host);s['research_status']='prepared'
        chain=read(ROOT/'evidence/s10_mirror/feedback_decision_chain.json')['decisions']
        proposal=deepcopy(next(r['original_request'] for r in chain if r.get('hypothesis_id')=='H_LARGER_RADIUS_62DD'))
        with self.assertRaisesRegex(ValueError,'UNREGISTERED'):admit_decision(self.host,Plan.model_validate(proposal))
        with patch('tools.research.budget.protected',return_value=False):
            rows=context(self.host)['decision_feedback']['actions']
        row=next(r for r in rows if r['action']=='control_search')
        proposal['supporting_evidence']=row['supporting_evidence']
        proposal['control_search']['candidate']=row['candidate'];proposal['control_search']['source']=row['source']
        proposal['decision']['selected_candidate']=row['candidate']
        self.assertTrue(admit_decision(self.host,Plan.model_validate(proposal)))
        proposal['decision']['selected_candidate']={'artifact_id':'f'*64,'media_type':'application/json'}
        with self.assertRaisesRegex(ValueError,'DECISION_CANDIDATE_MISMATCH'):admit_decision(self.host,Plan.model_validate(proposal))

    def test_feedback_has_real_reference_no_dynamic_state_or_callbacks(self):
        s=state(self.host);ref=s['control_search_results'][0]
        value={'result':{'reference':ref}}
        wrapper={'artifact_id':'f'*64,'media_type':'application/json'}
        with patch('tools.research.research_context.save',return_value=wrapper):view=tool_feedback(self.host,value)
        self.assertEqual(view['scientific_reference'],ref)
        self.assertEqual(view['wrapper_reference'],wrapper)
        self.assertNotIn(wrapper,registered_references(self.host))
        self.assertNotIn('decision_feedback',view);self.assertNotIn('all_fresh_results',view)
        self.assertNotIn('candidates',view['new_facts']['value'])
        self.assertTrue(view['new_facts']['summary']['best']['reference'])
        self.assertLess(size(view),6000)

    def test_saved_invalid_reads_stay_rejected_and_have_real_child_hints(self):
        audit=decision_projection(self.host);s=state(self.host);s['research_status']='prepared'
        for err in audit['errors']:
            use=err['tool_use']
            if use['name']!='evidence_read':continue
            with self.subTest(query=use['input']),patch('tools.research.core.protected',return_value=False):
                with self.assertRaises((ValueError,KeyError,IndexError,TypeError)) as caught:core.read_evidence(self.host,use['input'])
                with patch('tools.research.agent.record',return_value={'artifact_id':'f'*64}):
                    correction=error_feedback(self.host,use,caught.exception,s)
                self.assertFalse(correction['scientific_execution_started'])
                self.assertTrue(correction['expected'])
        # Correct raw pointer, fields and range retrieve actual stored values.
        ref=s['physical_replays'][-1];value=self.host.store.artifact(ref);raw=value['raw_reference']
        with patch('tools.research.core.update'),patch('tools.research.core.protected',return_value=False):
            fields=core.read_evidence(self.host,dict(reference=ref,view='fields',fields=['acceptance','raw_reference']))
            rows=core.read_evidence(self.host,dict(reference=raw,pointer='/samples',view='range',start=30,count=6))
        self.assertEqual(fields['acceptance'],value['acceptance']);self.assertEqual(len(rows['items']),6)

    def test_next_request_boundary_and_success_keep_original_protection(self):
        s=state(self.host);s['research_status']='prepared';s['pilot']['live_model_requests']=0
        for remaining in (8,5,4,3):
            ledger=deepcopy(self.host.store.remaining.return_value);ledger['remaining']['model_calls']=remaining
            with self.subTest(remaining=remaining),patch.object(self.host.store,'remaining',return_value=ledger):
                view=decision_budget(self.host)
                self.assertEqual(view['provider_budget']['next_request_exploration_remaining'],max(0,remaining-5))
                self.assertEqual(view['closeout']['next_request_will_protect'],remaining<=5)
                self.assertEqual(protected(self.host),remaining<=4)
        s['success_gate']={'evidence':s['physical_replays'][-1]}
        self.assertTrue(decision_budget(self.host)['closeout']['active'])

    def test_stop_coverage_and_display_paths_remain_strict(self):
        chain=read(ROOT/'evidence/s10_mirror/feedback_decision_chain.json')['decisions']
        stop=deepcopy(chain[-1]['original_request'])
        self.assertTrue(admit_decision(self.host,Plan.model_validate(stop)))
        stop['supporting_evidence']=stop['supporting_evidence'][:-1]
        with patch.object(self.host.store,'lookup',return_value=None),patch('tools.research.core.guard'),patch('tools.research.experience.disposition_bindings',return_value={}):
            with self.assertRaisesRegex(ValueError,'STOP_MUST_CITE_ALL_NEW_EXPERIMENT_RESULTS'):
                core.dispatch(self.host,stop,'offline-stop-rejected')
        ref=state(self.host)['analysis_results'][-1]
        with patch('tools.research.core.protected',return_value=False):
            for pointer,view in (('/value/construction','full'),('/static_input_observation','full'),('','range')):
                with self.subTest(pointer=pointer),self.assertRaises((ValueError,KeyError)):
                    core.read_evidence(self.host,dict(reference=ref,pointer=pointer,view=view))

    def test_reasoning_tool_ids_and_originals_unchanged(self):
        messages=[dict(role='assistant',content=[dict(reasoningContent=dict(reasoningText=dict(text='fixture reasoning'))),
            dict(toolUse=dict(toolUseId='fixture',name='evidence_read',input={}))]),
            dict(role='user',content=[dict(toolResult=dict(toolUseId='fixture',status='success',content=[dict(text='fixture')]))])]
        original=deepcopy(messages);wire=DeepSeekModel.format_request_messages(messages,'fixture system')
        self.assertEqual(wire[1]['reasoning_content'],'fixture reasoning')
        self.assertEqual(wire[1]['tool_calls'][0]['id'],wire[2]['tool_call_id']);self.assertEqual(messages,original)


if __name__=='__main__':unittest.main()
