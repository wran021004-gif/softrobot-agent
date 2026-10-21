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
    def test_derived_delivery_is_audited_without_claiming_raw_artifact_coverage(self):
        from tests.research.test_s125_contract import cold_host
        from tools.research.agent import record
        from tools.research.state import save
        from tools.research.research_context import read_coverage
        h=cold_host();q=dict(reference=state(h)['family_space_reference'],view='working_set',pointer='/eligible_methods')
        body=json.dumps(read_evidence(h,q))
        for i in range(2):
            key='derived-fixture-'+str(i);use=dict(toolUseId=key,name='evidence_read',input=q)
            record(h,'model_original_tool_feedback',dict(tool_use=use,result=dict(toolUseId=key,status='success',content=[dict(text=body)])))
            wire=save(h,dict(messages=[dict(role='tool',tool_call_id=key,content=body)]))
            metadata=save(h,dict(request=wire));response=save(h,dict(http_status=200))
            with h.store.transaction() as db:
                h.store.event(db,h.run_id,'r3_request','sent',request=key,outputs=[metadata])
                h.store.event(db,h.run_id,'r3_response','received',request=key,outputs=[response])
        rows=read_coverage(h)
        self.assertEqual(len(rows),2);self.assertEqual(rows[-1]['classification'],'exact_repeat')
        self.assertTrue(all(r['retrieval_view'] and r['successfully_provided'] and not r['complete_data'] for r in rows))

    def test_empty_cold_state_has_a_valid_detail_anchor(self):
        from tests.research.test_s125_contract import cold_host
        h=cold_host();before=deepcopy(state(h));c=context(h);query=decision_brief(c)['evidence_access']
        self.assertEqual(query['reference'],before['family_space_reference'])
        self.assertEqual(read_evidence(h,{k:v for k,v in query.items() if k!='scope'})['candidate_index'],[])
        self.assertEqual(state(h),before)

    def test_frozen_summary_and_every_detail_are_read_only(self):
        h=historical_host();before=deepcopy(state(h));ledger=h.store.remaining();events=h.store.events(h.run_id)
        current=context(h);brief=decision_brief(current);ws=current['evidence_working_set']
        self.assertLess(size(brief),36000);self.assertLess(size(brief['evidence_working_set']),15000)
        self.assertEqual(brief['all_fresh_results'],current['all_fresh_results'])
        self.assertEqual(len(brief['all_fresh_results']),9)
        self.assertNotIn('original_acceptance',json.dumps(brief['evidence_working_set']))
        self.assertNotIn('method_remaining',brief)
        self.assertEqual(brief['budget']['provider_budget'],current['budget']['provider_budget'])
        self.assertEqual(brief['budget']['training'],current['training_budget'])
        self.assertNotIn('rl_stages',brief['budget']['method_remaining'])
        query={k:v for k,v in brief['evidence_access'].items() if k!='scope'}
        details=read_evidence(h,query)
        self.assertFalse(details.pop('authoritative_scientific_evidence'))
        self.assertEqual(details.pop('source_state_identity'),digest(before));self.assertEqual(details,ws)
        for original,projected in zip(current['decision_feedback']['actions'],details['eligible_methods']):
            for key in ('references','cold_initializations','warm_sources','response_evidence','remaining_checks'):
                if key not in original:continue
                if key=='remaining_checks':
                    method=original['action']+('/'+original['method'] if original.get('method') else '')
                    self.assertEqual(details['method_requirements'][method][key],original[key])
                else:self.assertEqual(projected[key],original[key])
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
