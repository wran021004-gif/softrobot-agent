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
    def test_citation_inventory_is_read_only_and_preserves_registered_scopes(self):
        from tools.research.evidence_policy import registered_references,citation_inventory,admit_decision
        from tools.research.contracts import Plan
        from tests.research.s7_study import engineering_plan
        h=historical_host();before=deepcopy(state(h));ledger=h.store.remaining();events=h.store.events(h.run_id)
        rows=citation_inventory(h);known=registered_references(h)
        self.assertEqual({r['reference']['artifact_id'] for r in rows},{r['artifact_id'] for r in known})
        brief=decision_brief(context(h));query=brief['citation_eligibility']['query']
        self.assertEqual(read_evidence(h,query),rows)
        self.assertNotIn(before['family_space_reference'],known)
        checked=[]
        for kind in ('PHYSICAL_OBSERVATION','NUMERICAL_DIAGNOSTIC'):
            row=next(r for r in rows if r['claim_kind']==kind and r['supported_inferences'] and r['candidate'])
            plan=engineering_plan('diagnose','DIAGNOSE',row['candidate'])
            plan['decision']['claimed_inference']=row['supported_inferences'][0]
            plan['supporting_evidence']=[row['reference']]
            admit_decision(h,Plan.model_validate(plan));checked.append(kind)
        self.assertEqual(len(checked),2)
        self.assertEqual(state(h),before);self.assertEqual(h.store.remaining(),ledger);self.assertEqual(h.store.events(h.run_id),events)

    def test_two_actual_s127_4_citation_errors_still_reject_with_repair_feedback(self):
        from unittest.mock import patch
        from tools.platform_host import Host
        from tools.research.config import ROOT
        from tools.research.evidence_policy import admit_decision,registered_references
        from tools.research.contracts import Plan
        from tools.research.agent import received,error_feedback
        from tools.state_io import read
        from tests.research.s126_decision_probe import frozen_s127
        manifest=read(ROOT/'evidence/s127_decision_probe/manifest.json')
        source=Host(manifest['store'],manifest['run_id']);live=Host(ROOT/'runs/s127-4a-decision-20261021','s127-4a-decision-20261021')
        errors=[]
        for result in read(ROOT/'evidence/s127_4_decision/results.json')['cases']:
            if not any('UNREGISTERED_RESEARCH_EVIDENCE' in (c.get('error') or '') for c in result['checks']):continue
            case=next(c for c in manifest['cases'] if c['name']==result['name'] and c['arm']==result['arm'])
            h=frozen_s127(source,case);before=deepcopy(state(h));ledger=h.store.remaining()
            reception=received(live,result['request_id']);body=json.loads(live.store.artifact(reception['body'],raw=True))
            call=next(c for c in body['choices'][0]['message']['tool_calls'] if c['function']['name']=='research_plan')
            value=json.loads(call['function']['arguments']);use=dict(name='research_plan',toolUseId=call['id'],input=value)
            with self.assertRaisesRegex(ValueError,'UNREGISTERED_RESEARCH_EVIDENCE') as raised:admit_decision(h,Plan.model_validate(value))
            with patch('tools.research.agent.record',return_value={'artifact_id':'0'*64}):feedback=error_feedback(h,use,raised.exception,before)
            self.assertTrue(feedback['rejected_references']);self.assertIn('citation_eligibility',feedback['inventory_query']['pointer'])
            self.assertFalse(feedback['scientific_execution_started'])
            self.assertTrue(all(r not in registered_references(h) for r in feedback['rejected_references']))
            self.assertEqual(state(h),before);self.assertEqual(h.store.remaining(),ledger)
            errors.append(feedback)
        self.assertEqual(len(errors),2)

    def test_truncated_probe_response_replays_without_resend_or_native_submission(self):
        import asyncio
        import httpx
        from tools.research.agent import LiveBoundary
        from tests.research.test_s125_contract import cold_host
        h=cold_host();provider=state(h)['pilot']['provider'];sent=[]
        wire=dict(model=provider['model'],thinking=dict(type=provider['thinking']),reasoning_effort=provider['reasoning_effort'],
            max_tokens=provider['max_tokens'],stream=False,messages=[dict(role='user',content='Synthetic truncated fixture')])
        def reply(request):
            sent.append(request)
            return httpx.Response(200,json=dict(choices=[dict(finish_reason='length',message=dict(role='assistant',content='',reasoning_content='fixture'))],
                usage=dict(prompt_tokens=10,completion_tokens=8192,total_tokens=8202)))
        async def exercise():
            first=LiveBoundary(h,httpx.MockTransport(reply));request=lambda:httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire)
            with self.assertRaisesRegex(ValueError,'LENGTH_TRUNCATED'):await first.handle_async_request(request())
            before=h.store.remaining()
            def forbidden(request):raise AssertionError('NO_RESEND')
            recovery=LiveBoundary(h,httpx.MockTransport(forbidden),allow_truncated_response=True)
            response=await recovery.handle_async_request(request())
            self.assertEqual(response.json()['choices'][0]['finish_reason'],'length')
            self.assertEqual(h.store.remaining(),before)
            with self.assertRaisesRegex(ValueError,'LENGTH_TRUNCATED'):recovery.consumed()
            self.assertIn('unconsumed_response',state(h)['pilot'])
            self.assertEqual(len(sent),1)
            await first.aclose();await recovery.aclose()
        asyncio.run(exercise())

    def test_s127_4_frozen_scope_and_real_detail_read_do_not_dispatch(self):
        from unittest.mock import patch
        from tools.platform_host import Host
        from tools.research.config import ROOT
        from tools.state_io import read
        from tests.research.s126_decision_probe import audit_s127, frozen_s127, check_s127
        scope=audit_s127();manifest=read(ROOT/'evidence/s127_decision_probe/manifest.json')
        source=Host(manifest['store'],manifest['run_id']);case=manifest['cases'][-1]
        host=frozen_s127(source,case);wire=source.store.artifact(case['request'])
        packet=json.loads(wire['messages'][0]['content'].split('\nCURRENT_RESEARCH_PACKET\n')[1])
        query={k:v for k,v in packet['research']['evidence_access'].items() if k!='scope'}
        call=dict(function=dict(name='evidence_read',arguments=json.dumps(query)))
        with patch('tools.research.core.dispatch',side_effect=AssertionError('NO_SCIENCE')):
            result=check_s127(host,call)
        self.assertEqual(len(scope['cases']),12)
        self.assertTrue(result['working_set'] and result['local_read'])
        self.assertFalse(result['provided_to_model'])
        self.assertEqual(result['full_execution_admission'],'not_tested')
        self.assertFalse(host.store.transaction.called or host.store.reserve.called)
        query['reference']={'artifact_id':'0'*64,'media_type':'application/json'}
        call['function']['arguments']=json.dumps(query)
        self.assertEqual(check_s127(host,call)['contract_and_reference_checks'],'rejected')

    def test_s127_4_rejects_old_provider_authorization_before_credentials(self):
        import asyncio
        from unittest.mock import patch
        from tools.research.config import ROOT
        from tools.state_io import atomic_json
        from tests.research.s126_decision_probe import live_s127
        path=ROOT/'runs/s127_4_old_authorization_fixture.json'
        atomic_json(path,dict(endpoint='https://api.deepseek.com',probe_request_ceiling=20,user_approval='OLD FIXTURE'))
        with patch('tools.research.provider.load_credential',side_effect=AssertionError('NO_CREDENTIAL_READ')):
            with self.assertRaisesRegex(ValueError,'INDEPENDENT_S127_4A'):
                asyncio.run(live_s127(path))

    def test_derived_delivery_is_audited_without_claiming_raw_artifact_coverage(self):
        from tests.research.test_s125_contract import cold_host
        from tools.research.agent import record
        from tools.research.state import save
        from tools.research.research_context import read_coverage
        h=cold_host();q=dict(reference=state(h)['family_space_reference'],view='working_set',pointer='/eligible_methods')
        body=json.dumps(read_evidence(h,q))
        for i in range(3):
            if i==2:body=json.dumps([dict(synthetic_fixture='changed dynamic delivery; not scientific evidence')])
            key='derived-fixture-'+str(i);use=dict(toolUseId=key,name='evidence_read',input=q)
            record(h,'model_original_tool_feedback',dict(tool_use=use,result=dict(toolUseId=key,status='success',content=[dict(text=body)])))
            wire=save(h,dict(messages=[dict(role='tool',tool_call_id=key,content=body)]))
            metadata=save(h,dict(request=wire));response=save(h,dict(http_status=200))
            with h.store.transaction() as db:
                h.store.event(db,h.run_id,'r3_request','sent',request=key,outputs=[metadata])
                h.store.event(db,h.run_id,'r3_response','received',request=key,outputs=[response])
        rows=read_coverage(h)
        self.assertEqual(len(rows),3)
        self.assertEqual([r['classification'] for r in rows],['new_query','exact_repeat','changed_content'])
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
