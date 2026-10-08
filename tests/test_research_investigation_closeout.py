"""Public-path software checks. Only external provider transport is substituted."""
from copy import deepcopy
from threading import Event,Lock
from unittest import TestCase
from unittest.mock import patch
import json
import time

from tests.test_research_mainline3 import Mainline3EngineeringTests
from tools.platform_store import plain,zero
from tools.research_execution import invoke
from tools.state_io import atomic_json

OBSERVATIONS={}
ARTIFACTS={}


def native(name,args):
    return dict(choices=[dict(finish_reason='tool_calls',message=dict(role='assistant',content=None,
        tool_calls=[dict(id='call-1',type='function',function=dict(name=name,arguments=json.dumps(args)))]))])


def fact(ref,pointer,value):
    return dict(statement='Exact saved '+pointer,reference=ref,pointer=pointer,value=value)


class InvestigationCloseoutTests(TestCase):
    setUp=Mainline3EngineeringTests.setUp
    isolated_host=Mainline3EngineeringTests.isolated_host
    order=Mainline3EngineeringTests.order
    report=Mainline3EngineeringTests.report

    def host(self,model_ceiling=15):
        host,ref=self.isolated_host(model_ceiling,session_budget={**zero(),'model_calls':15,'tool_calls':512,'wall_s':1500.})
        with host.store.transaction() as db:
            state=host.store.session(host.run_id,db)['state'];grant=state['role_context']['investigation_grant']
            grant.update(max_count=5,per_node_budget={**zero(),'model_calls':3,'tool_calls':8,'wall_s':60.},
                total_budget={**zero(),'model_calls':model_ceiling,'tool_calls':40,'wall_s':300.})
            host.store.update_state(db,host.run_id,state)
        # Preserve the existing sealed fixture session; create higher-budget
        # fixtures through its constructor, never edit a historical snapshot.
        return host,ref

    def public(self,host,tool,args,key):
        receipt=invoke(host,tool,args,request_id=key)
        self.assertEqual(receipt['execution_status'],'completed',receipt.get('error'))
        return receipt,host.store.artifact(receipt['output'])

    def collect(self,host,key):
        deadline=time.monotonic()+15
        for i in range(80):
            receipt,result=self.public(host,'research.investigation_status',dict(investigation_id=key),'status-'+key+'-'+str(i))
            if result['status'] not in ('pending','running'):return receipt,result
            if time.monotonic()>deadline:self.fail('Bounded collection timeout')
            time.sleep(.01)
        self.fail('Bounded collection requests exhausted')

    def capture(self,label,host,receipts=(),**details):
        state=host.store.session(host.run_id)['state']
        nodes=deepcopy(state.get('investigations',{}))
        references=[*state['role_context']['investigation_grant']['evidence'],*[r['output'] for r in receipts if r.get('output')]]
        for node in nodes.values():
            references.extend(node[k] for k in ('result','disposition_record') if node.get(k))
            node.pop('principal_disposition',None)  # Canonical record retained once by reference below.
        for reference in references:ARTIFACTS[reference['artifact_id']]=host.store.artifact(reference)
        if details.get('result'):details['result']={k:v for k,v in details['result'].items() if k!='receipts'}
        OBSERVATIONS[label]=dict(receipts=list(receipts),nodes=nodes,
            principal_reads=state.get('principal_investigation_reads',[]),ledger=host.store.remaining(),**details)

    def test_additional_query_and_request_bounds(self):
        host,ref=self.host();order=self.order('interactive',ref)
        order['budget'].update(model_calls=2,tool_calls=2)
        calls=[]
        def transport(adapter,config,payload):
            calls.append(deepcopy(payload))
            if len(calls)==1:
                read=payload['tools'][1]['function']['name']
                response=native(read,dict(arguments=dict(reference=ref,pointer='/deadline_misses'),reason='Read additional original timing evidence',tool_version='1.0.0'))
                response['choices'][0]['message']['reasoning_content']='Synthetic reasoning field retained in the complete request.'
                return response
            last=json.loads(payload['messages'][-1]['content'])
            self.assertEqual(last['content'],35)
            self.assertEqual(payload['messages'][-2]['reasoning_content'],'Synthetic reasoning field retained in the complete request.')
            return native('investigation_return',dict(facts=[fact(ref,'/deadline_misses',35)],
                counterevidence=[fact(ref,'/terminal_error_m',.06672099201814737)],unknowns=['No causal result'],interpretation='Saved timing fact'))
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport):
            submitted,result=self.public(host,'research.investigate',order,'submit-interactive')
            self.assertEqual(result['status'],'pending')
            receipt,result=self.collect(host,'interactive')
        self.assertEqual(result['status'],'completed',result.get('reason'))
        self.assertEqual(len(calls),2)
        self.assertGreater(len(json.dumps(calls[1])),len(json.dumps(calls[0])))
        state=host.store.session(host.run_id)['state'];node=state['investigations']['interactive']
        self.assertEqual([r['pointer'] for r in node['reads']],['/terminal_error_m','/deadline_misses'])
        self.assertNotIn('principal_investigation_reads',state)
        self.assertEqual(host.store.remaining()['used']['model_calls'],2)
        self.assertEqual(node['usage']['tool_calls'],2)
        self.capture('additional_query',host,[submitted,receipt],request_message_counts=[len(p['messages']) for p in calls])

    def test_scope_budget_and_complete_outgoing_overflow(self):
        host,ref=self.host();order=self.order('bounded',ref)
        with host.store.transaction() as db:outside=plain(host.store.put(db,dict(secret_scope='Not granted synthetic fixture')))
        calls=[]
        def transport(adapter,config,payload):
            calls.append(payload)
            return native(payload['tools'][1]['function']['name'],dict(arguments=dict(reference=outside,pointer=''),reason='Attempt outside scope',tool_version='1.0.0'))
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport):
            submitted,_=self.public(host,'research.investigate',order,'submit-bounded')
            receipt,result=self.collect(host,'bounded')
        self.assertEqual(result['status'],'incomplete',result.get('reason'))
        self.assertEqual(len(calls),1)
        self.assertEqual(host.store.remaining()['used']['model_calls'],1)
        events=host.store.events(host.run_id)
        rejection=next(e for e in events if e['kind']=='investigator_read' and e['status']=='rejected')
        # Prefetch consumed the only operation; denied query cannot mint quota.
        self.assertIn('BUDGET_EXHAUSTED',host.store.artifact(rejection['outputs'][0])['result']['error'])
        order2=self.order('outside',ref);order2['budget'].update(model_calls=2,tool_calls=2)
        def outside_transport(adapter,config,payload):
            if payload['messages'][-1]['role']=='tool':
                self.assertIn('QUERY_SOURCE_OUT_OF_SCOPE',payload['messages'][-1]['content'])
                return native('investigation_return',dict(interpretation='Insufficient evidence',unknowns=['Out-of-scope source unavailable']))
            return native(payload['tools'][1]['function']['name'],dict(arguments=dict(reference=outside),reason='Out-of-scope fixture read',tool_version='1.0.0'))
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=outside_transport):
            self.public(host,'research.investigate',order2,'submit-outside');_,second=self.collect(host,'outside')
        self.assertEqual(second['status'],'completed',second.get('reason'))
        # A huge accumulated native exchange must fail before another attempt.
        order3=self.order('overflow',ref);order3['budget'].update(model_calls=2,tool_calls=2)
        attempts=[]
        def overflow(adapter,config,payload):
            attempts.append(payload)
            response=native(payload['tools'][1]['function']['name'],dict(arguments=dict(reference=ref,pointer='/deadline_misses'),reason='Additional evidence',tool_version='1.0.0'))
            response['choices'][0]['message']['content']='x'*200000
            return response
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=overflow):
            self.public(host,'research.investigate',order3,'submit-overflow');_,third=self.collect(host,'overflow')
        self.assertEqual(third['status'],'failed')
        self.assertIn('CONTEXT_SEND_BOUNDARY_OVERFLOW',third['reason'])
        self.assertEqual(len(attempts),1)
        self.capture('scope_budget_request_bounds',host,[submitted,receipt],scope_result=second,overflow_result=third)

    def test_public_parallel_reservations_and_recovery(self):
        host,ref=self.host();entered=[Event(),Event()];release=Event();mutex=Lock();attempts=[]
        def transport(adapter,config,payload):
            with mutex:index=len(attempts);attempts.append(payload)
            entered[index].set()
            if not release.wait(10):raise AssertionError('Parallel release was not signalled')
            return native('investigation_return',plain(self.report(ref)))
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport):
            first,_=self.public(host,'research.investigate',self.order('parallel-a',ref),'submit-a')
            second,_=self.public(host,'research.investigate',self.order('parallel-b',ref),'submit-b')
            try:
                self.assertTrue(entered[0].wait(10));self.assertTrue(entered[1].wait(10))
                from tools.platform_host import Host
                reopened=Host(host.store.root,host.run_id)
                _,active=self.public(reopened,'research.investigation_status',dict(investigation_id='parallel-a'),'active-status')
                self.assertEqual(active['status'],'running')
                used=host.store.remaining()['used']
                self.assertEqual(used['model_calls'],2)
                denied=invoke(host,'research.investigate',self.order('parallel-c',ref),request_id='submit-c')
                self.assertEqual(denied['execution_status'],'failed')
                self.assertIn('CONCURRENCY_EXCEEDED',denied['error'])
                self.assertEqual(len(attempts),2)
            finally:release.set()
            ra,a=self.collect(host,'parallel-a');rb,b=self.collect(host,'parallel-b')
            self.assertEqual(a['status'],'completed',a.get('reason'));self.assertEqual(b['status'],'completed',b.get('reason'))
            replay,result=self.public(reopened,'research.investigate',self.order('parallel-a',ref),'recollect-a')
            self.assertEqual(result['status'],'completed');self.assertEqual(len(attempts),2)
        self.capture('public_concurrency_recovery',host,[first,second,ra,rb,replay],reserved_while_active=used,concurrency_rejection=denied,both_entered_before_release=True)
        # The concurrency grant allows two, but the shared model balance allows
        # only one. Verify rejection occurs before entering transport again.
        narrow,nref=self.host(model_ceiling=1);nentered=Event();nrelease=Event();nattempts=[]
        def bounded(adapter,config,payload):
            nattempts.append(payload);nentered.set()
            if not nrelease.wait(10):raise AssertionError('Shared-budget release missing')
            return native('investigation_return',plain(self.report(nref)))
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=bounded):
            self.public(narrow,'research.investigate',self.order('balance-a',nref),'balance-a')
            try:
                self.assertTrue(nentered.wait(10))
                denied=invoke(narrow,'research.investigate',self.order('balance-b',nref),request_id='balance-b')
                self.assertIn('TOTAL_GRANT_EXCEEDED',denied['error']);self.assertEqual(len(nattempts),1)
            finally:nrelease.set()
            _,a=self.collect(narrow,'balance-a');self.assertEqual(a['status'],'completed')
        self.capture('shared_balance',narrow,shared_rejection=denied,synthetic_transport_attempts=1)

    def test_unconfirmed_and_saved_response_recovery(self):
        host,ref=self.host();attempts=[]
        def uncertain(adapter,config,payload):attempts.append(payload);raise TimeoutError('Synthetic uncertain provider attempt')
        order=self.order('uncertain',ref)
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=uncertain):
            submission,_=self.public(host,'research.investigate',order,'submit-uncertain');receipt,result=self.collect(host,'uncertain')
            self.assertEqual(result['status'],'unconfirmed')
            _,again=self.public(host,'research.investigate',order,'collect-uncertain-again')
            self.assertEqual(again['status'],'unconfirmed');self.assertEqual(len(attempts),1)
        row=host.store.lookup(host.run_id,'investigation-uncertain')
        self.assertIsNone(row['receipt']);self.assertEqual(row['reserved'],row['charged'])
        # Crash-window fixture uses real reserve/prepare/save/recover, no transport.
        from tools.research_investigations import InvestigationDispatcher
        dispatcher=InvestigationDispatcher(host);saved_order,saved_row,_=dispatcher._reserve(self.order('saved',ref))
        _,_,reads,_=dispatcher.prepare(saved_order)
        with host.store.transaction() as db:
            state=host.store.session(host.run_id,db)['state'];state['investigations']['saved'].update(reads=reads,usage={**zero(),'model_calls':1,'tool_calls':1})
            host.store.update_state(db,host.run_id,state)
            response=host.store.put(db,dict(report=plain(self.report(ref)),elapsed_s=.01))
            host.store.event(db,host.run_id,'investigation_response','validated',request=saved_row['request_id'],execution=saved_row['execution_id'],outputs=[response])
        recovered,saved=self.public(host,'research.investigation_status',dict(investigation_id='saved'),'recover-saved')
        self.assertEqual(saved['status'],'completed',saved.get('reason'))
        self.capture('unconfirmed_saved_recovery',host,[submission,receipt,recovered],real_external_attempts=0,synthetic_transport_attempts=len(attempts))

    def test_principal_claim_links_values_identities_scope_and_defer(self):
        host,ref=self.host()
        def transport(adapter,config,payload):return native('investigation_return',plain(self.report(ref)))
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport):
            self.public(host,'research.investigate',self.order('decision',ref),'submit-decision');_,result=self.collect(host,'decision')
        supporting=fact(ref,'/terminal_error_m',.06672099201814737)
        scope=fact(ref,'/result_type','free_reach')
        decision=dict(investigation_id='decision',report=result['result'],disposition='accept',reason='Retain saved failure result',
            adopted_claims=[dict(statement='Saved terminal error exceeds the declared tolerance',supporting_facts=[supporting],scope=[scope],
                support_explanation='The inspected terminal error supports reporting failure for this saved free-reach execution.')])
        empty=invoke(host,'research.investigation_disposition',dict(investigation_id='decision',disposition='accept',reason='Unsupported'),request_id='empty-accept')
        self.assertIn('ACCEPT_REQUIRES',empty['error'])
        unread=invoke(host,'research.investigation_disposition',decision,request_id='unread-accept')
        self.assertIn('PRINCIPAL_MUST_INSPECT',unread['error'])
        inspected=[]
        for index,p in enumerate(('/terminal_error_m','/result_type')):
            receipt,_=self.public(host,'research.investigation_read',dict(reference=ref,pointer=p),'inspect-'+str(index));inspected.append(receipt)
        wrong=deepcopy(decision);wrong['adopted_claims'][0]['supporting_facts'][0]['value']=0
        self.assertIn('VALUE_MISMATCH',invoke(host,'research.investigation_disposition',wrong,request_id='wrong-value')['error'])
        wrong=deepcopy(decision);wrong['adopted_claims'][0]['supporting_facts'][0]['source_identity']={'execution_id':'different-execution'}
        self.assertIn('IDENTITY_MISMATCH',invoke(host,'research.investigation_disposition',wrong,request_id='wrong-identity')['error'])
        wrong=deepcopy(decision);wrong['adopted_claims'][0]['scope'][0]['value']='tracking'
        self.assertIn('VALUE_MISMATCH',invoke(host,'research.investigation_disposition',wrong,request_id='wrong-scope')['error'])
        wrong=deepcopy(decision);wrong['report']=ref
        self.assertIn('REPORT_BINDING_MISMATCH',invoke(host,'research.investigation_disposition',wrong,request_id='wrong-report')['error'])
        wrong=deepcopy(decision);wrong['adopted_claims'][0]['supporting_facts']=[scope]
        self.assertIn('DISPOSITION_FACT_BINDING',invoke(host,'research.investigation_disposition',wrong,request_id='unrelated-citation')['error'])
        receipt,accepted=self.public(host,'research.investigation_disposition',decision,'supported-accept')
        record=host.store.artifact(accepted['disposition_record'])
        self.assertEqual(len(record['inspection_links']),2);self.assertTrue(record['semantic_claims_unassessed'])
        deferred,defer=self.public(host,'research.investigation_disposition',dict(investigation_id='decision',report=result['result'],disposition='defer',reason='Insufficient evidence for a causal conclusion',remaining_unknowns=['Dominant cause unassessed']),'defer')
        deferred_record=host.store.artifact(defer['disposition_record'])
        self.assertFalse(deferred_record['independently_inspected'])
        from tools.platform_host import Host
        investigator=Host(host.store.root,host.run_id,actor='investigator:test')
        denied=invoke(investigator,'research.investigation_disposition',decision,request_id='role-denied')
        self.assertIn('PRINCIPAL_ONLY',denied['error'])
        self.capture('principal_disposition',host,[*inspected,receipt,deferred],unsupported_accept=empty,unread_accept=unread,role_denied=denied)

    def test_integrated_direct_and_coordinated_public_scenarios(self):
        from tools.research_mainline3 import live_interface_scenario,interface_proposal
        # The runner's full proposed budgets include public collection and reads.
        for mode in ('direct','coordinated'):
            proposal=interface_proposal(mode)
            host,ref=self.isolated_host(model_ceiling=12,session_budget=proposal['project_budget'],operation_allowances=proposal['operation_allowances'])
            # Fixture constructor below allocates sufficient immutable budgets.
            # No saved activity/grant or dependency seal is rewritten.
            def transport(adapter,config,payload):
                packet=json.loads(payload['messages'][1]['content'])
                text=json.dumps(packet)
                if 'Request exactly two distinct subordinate' in text:
                    from tools.research_investigations import InvestigationOrder
                    children=[]
                    for key,p in [('child-reach','/terminal_error_m'),('child-timing','/deadline_misses')]:
                        child=self.order(key,ref,parent_id='temporary-coordinator')
                        child['evidence']=[ref];child['question']='Inspect distinct '+key
                        child['queries']=[dict(reference=ref,pointer=p)]
                        child['budget']={**zero(),'model_calls':3,'tool_calls':8,'wall_s':180.};child['timeout_s']=180.
                        children.append(plain(InvestigationOrder.model_validate(child)))
                    return native('investigation_return',dict(interpretation='Two bounded independent questions',children=children))
                state=host.store.session(host.run_id)['state']
                source=state['role_context']['investigation_grant']['evidence'][0]
                if 'Return exactly one explicit structured disposition' in text:
                    children=[n for n in state['investigations'].values() if n['order']['role']=='investigator']
                    decisions=[]
                    for node in children:
                        report=host.store.artifact(node['result'])
                        decisions.append(dict(investigation_id=node['order']['investigation_id'],report=node['result'],disposition='accept',reason='Adopt saved factual observation within its scope',
                            adopted_claims=[dict(statement='Retain saved observation for this execution',supporting_facts=report['facts'],scope=[fact(source,'/result_type','free_reach')],support_explanation='Inspected original facts support retaining the bounded report; causal reasoning remains unassessed.')],remaining_unknowns=['No live validation']))
                    return native('investigation_return',dict(interpretation='Explicit structured principal decisions',dispositions=decisions))
                p='/deadline_misses' if 'complete-update' in text or 'child-timing' in text else '/terminal_error_m'
                value=35 if p=='/deadline_misses' else .06672099201814737
                return native('investigation_return',dict(facts=[fact(source,p,value)],interpretation='Bounded saved observation',unknowns=['No causal proof']))
            with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport):
                result=live_interface_scenario(host,mode)
            self.assertEqual(result['status'],'formal_dispositions_recorded',json.dumps(result))
            self.assertEqual(len(result['dispositions']),2)
            self.capture('integrated_'+mode,host,result['receipts'],result=result)

    def test_paginated_original_pointer_binding(self):
        host,ref=self.host()
        with host.store.transaction() as db:
            source=plain(host.store.put(db,dict(samples=[20,20,30])))
            state=host.store.session(host.run_id,db)['state'];state['role_context']['investigation_grant']['evidence'].append(source)
            host.store.update_state(db,host.run_id,state)
        for key,p,status in [('offset-valid','/samples/1','completed'),('offset-unseen','/samples/0','failed')]:
            order=self.order(key,source)
            order['queries']=[dict(reference=source,pointer='/samples',offset=1,limit=1)]
            def transport(adapter,config,payload):
                return native('investigation_return',dict(facts=[fact(source,p,20)],interpretation='Original offset page binding'))
            with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport):
                self.public(host,'research.investigate',order,'submit-'+key);_,result=self.collect(host,key)
            self.assertEqual(result['status'],status,result.get('reason'))
            if status=='failed':self.assertIn('NOT_IN_INSPECTED_PAGE',result['reason'])
        self.capture('pagination',host)


if __name__=='__main__':
    import unittest
    from pathlib import Path
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(InvestigationCloseoutTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    target=Path(__file__).resolve().parents[1]/'evidence/research_mainline3_closeout_20261008/offline_verification.json'
    atomic_json(target,dict(transport='Injected deterministic DeepSeekAdapter._transport; native function tool calls; production Host, scoped reader, decoder, request bounds, ledger and disposition validator',
        date='2026-10-08',command='python -m tests.test_research_investigation_closeout (softagent, Python 3.11.16)',
        checks=list(unittest.defaultTestLoader.getTestCaseNames(InvestigationCloseoutTests)),
        real_provider_requests=0,scientific_executions=0,checks_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),observations=OBSERVATIONS,artifacts=ARTIFACTS))
    raise SystemExit(not result.wasSuccessful())
