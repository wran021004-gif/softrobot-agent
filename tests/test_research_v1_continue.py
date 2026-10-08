"""Focused production-path checks with blocked credentials/network/science."""
from copy import deepcopy
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from tests import test_research_v1_capacity as fixture
from tests.test_research_failure_recovery import FakeResponse
from tools.research_investigations import InvestigationDispatcher
from tools.research_execution import invoke
from tools.platform_store import plain,Store
from tools.state_io import digest,atomic_json,read
from tools.model_transports.deepseek import request_completion

class ContinuationTests(TestCase):
    setUp=fixture.CapacityBindingTests.setUp
    cleanup=fixture.CapacityBindingTests.cleanup

    def grant(self,**updates):
        with self.host.store.transaction() as db:
            state=self.host.store.session(self.host.run_id,db)['state'];g=state['role_context']['investigation_grant'];g.update(updates)
            state['investigation_grant_identity']=digest(g);self.host.store.update_state(db,self.host.run_id,state)

    def test_public_delivery_protection_and_native_history(self):
        self.grant(delivery_allocations={'investigator':dict(budget=plain(self.order.budget),exploration_requests=2,protected_delivery_requests=4)})
        sends=[]
        def transport(adapter,config,wire):
            sends.append(deepcopy(wire))
            if len(sends)<=2:
                answer=fixture.native({});answer['choices'][0]['message'].update(reasoning_content='Required complete reasoning fixture')
                answer['choices'][0]['message']['tool_calls'][0]['id']='read-'+str(len(sends))
                answer['choices'][0]['message']['tool_calls'][0]['function']=dict(name=wire['tools'][1]['function']['name'],arguments=json.dumps(dict(reference=self.ref,pointer='/scalar')))
                return answer
            self.assertEqual([t['function']['name'] for t in wire['tools']],['investigation_return'])
            history=[m for m in wire['messages'] if m.get('role')=='assistant']
            self.assertEqual(len(history),2);self.assertTrue(all(m['reasoning_content']=='Required complete reasoning fixture' for m in history))
            return fixture.native(dict(interpretation='Bounded report with explicit unknowns',facts=[dict(statement='Visible exact scalar',reference=self.ref,pointer='/scalar',value=self.source['scalar'])]))
        # Use v3 native contract; production Host/public submission owns the thread.
        self.dispatch._native_v2=lambda:True
        self.dispatch._selectable=lambda:True
        with patch.object(InvestigationDispatcher,'_native_v2',return_value=True),patch.object(InvestigationDispatcher,'_selectable',return_value=True),patch('tools.platform_models.DeepSeekAdapter._transport',new=transport):
            r=invoke(self.host,'research.investigate',plain(self.order),request_id='submit-report-protection')
            import threading
            for t in threading.enumerate():
                if t.name=='investigation-investigator':t.join(30)
            result=invoke(self.host,'research.investigation_status',dict(investigation_id='investigator'),request_id='collect-report-protection')
        self.assertEqual(r['execution_status'],'completed');self.assertEqual(self.host.store.artifact(result['output'])['status'],'completed')
        self.assertEqual(len(sends),3)
        final=sends[-1]
        pages=[json.loads(m['content']) for m in final['messages'] if m.get('role')=='tool']
        self.assertIn('content',pages[0]);self.assertTrue(pages[1]['repeated_read'])
        self.assertEqual(len(self.host.store.session(self.host.run_id)['state']['investigations']['investigator']['reads']),3)

    def test_original_body_and_usage_survive_parsed_body_persistence_failure(self):
        native=fixture.native(dict(interpretation='Saved original survives secondary write failure'))
        original=json.dumps(native);put=Store.put;failed=[False]
        def failing(store,db,value,*a,**kw):
            if isinstance(value,dict) and value==native and not failed[0]:failed[0]=True;raise OSError('fixture parsed-response persistence failure')
            return put(store,db,value,*a,**kw)
        def transport(adapter,config,wire):return request_completion(config,wire,'isolated-fixture-key')
        from types import SimpleNamespace
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport),patch('tools.model_transports.deepseek.build_opener',return_value=SimpleNamespace(open=lambda *a,**kw:FakeResponse(original.encode()))),patch.object(Store,'put',new=failing):
            result=self.dispatch.dispatch(plain(self.order))
        self.assertEqual(result.status,'completed')  # Local recovery uses saved original; no provider redispatch.
        node=self.host.store.session(self.host.run_id)['state']['investigations']['investigator']
        self.assertEqual(node['usage']['model_calls'],1)
        body=self.host.store.artifact(node['original_body_refs'][0]);self.assertEqual(body['utf8_text'],original)
        self.assertEqual(body['representation'],'complete_original_utf8_text')
        events=self.host.store.events(self.host.run_id)
        usage=[self.host.store.artifact(e['outputs'][0]) for e in events if e['kind']=='investigation_reception' and e['status']=='received']
        self.assertTrue(any(r['provider_usage']==native['usage'] for r in usage))

    def test_safe_malformed_body_is_durable_before_json_decode(self):
        d=self.dispatch;order,row,_=d._reserve(plain(self.order));progress=d._initial_progress()
        cfg={'base_url':'https://api.deepseek.com','timeout_s':1,'_response_observer':lambda metadata,text,omission:d._receive(order,row,progress,metadata,text,omission)}
        from types import SimpleNamespace
        with patch('tools.model_transports.deepseek.build_opener',return_value=SimpleNamespace(open=lambda *a,**kw:FakeResponse(b'{"broken":'))):
            with self.assertRaisesRegex(RuntimeError,'PROCESSING_FAILED'):request_completion(cfg,{},'isolated-fixture-key')
        node=self.host.store.session(self.host.run_id)['state']['investigations']['investigator']
        self.assertEqual(self.host.store.artifact(node['original_body_refs'][0])['utf8_text'],'{"broken":')

    def test_reasoning_only_and_truncation_do_not_execute_partial_calls(self):
        sends=[]
        def transport(wire):
            sends.append(wire)
            return dict(usage=dict(prompt_tokens=4,completion_tokens=5,total_tokens=9),choices=[dict(finish_reason='length',message=dict(role='assistant',reasoning_content='Thinking only',content=None))])
        result=self.dispatch.dispatch(plain(self.order),transport=transport)
        self.assertEqual(result.status,'failed');self.assertIn('REASONING_ONLY_LENGTH',result.reason);self.assertEqual(len(sends),1)
        node=self.host.store.session(self.host.run_id)['state']['investigations']['investigator']
        self.assertFalse(node['progress']['valid_report']);self.assertEqual(len(node['provider_response_refs']),1)

    def test_conditional_probe_is_paid_only_after_blocking_truncation(self):
        self.grant(protocol_correction_limit=6,protocol_correction_role_limits=dict(principal=3,other=3),protocol_correction_per_node=3,protocol_correction_per_decision=2,
            conditional_length_recovery=dict(configurations=[dict(name='default',reasoning_effort='high',max_tokens=32768,supported=True),
                dict(name='probe1',reasoning_effort='low',max_tokens=32768,supported=True),dict(name='probe2',reasoning_effort='high',max_tokens=65536,supported=True)]))
        sends=[]
        def transport(wire):
            sends.append(deepcopy(wire))
            if len(sends)==1:
                answer=fixture.native({},finish='length');answer['choices'][0]['message']['reasoning_content']='Preserved truncated-turn reasoning';return answer
            self.assertEqual(wire['reasoning_effort'],'low');self.assertEqual(wire['max_tokens'],32768)
            self.assertEqual(wire['messages'][-2]['reasoning_content'],'Preserved truncated-turn reasoning')
            return fixture.native(dict(interpretation='Complete focused report'))
        result=self.dispatch.dispatch(plain(self.order),transport=transport)
        self.assertEqual(result.status,'completed');self.assertEqual(len(sends),2)
        state=self.host.store.session(self.host.run_id)['state'];self.assertEqual(state['recovery_probes_used'],1)
        self.assertEqual(state['investigation_protocol_corrections_used'],1)

    def test_public_import_new_b_synthesis_disposition_and_automatic_c_gate(self):
        from tools import research_v1_continue as activity
        from tools import research_v1_continue_gate as gate
        out=self.folder/'continuation-fixture-evidence'
        with patch.object(activity,'OUT',out),patch.object(gate,'OUT',out),patch('tools.platform_store.ROOT',self.folder):
            activity.start();atomic_json(out/'offline_gate.json',dict(passed=True,scope='Fixture bootstrap only; no real grant'))
            activity.freeze();host,m,p=activity.host_for('coordinated',create=True)
            sends=[];counts={}
            original=read(activity.OLD/'coordinated_bundle.json');rawref=original['state']['investigations']['coordinator-plan']['order']['evidence'][0]
            source=original['artifacts'][rawref['artifact_id']]
            def transport(adapter,config,wire):
                sends.append(deepcopy(wire));packet=json.loads(wire['messages'][1]['content']);key=packet['investigation_id'];counts[key]=counts.get(key,0)+1
                if packet['role']=='investigator':
                    pointer='/terminal_error_m' if key.startswith('reach') else '/mean_complete_update_s'
                    if counts[key]==1:
                        answer=fixture.native({});answer['choices'][0]['message']['reasoning_content']='Preserve required provider history'
                        answer['choices'][0]['message']['tool_calls'][0]['function']=dict(name='evidence_read',arguments=json.dumps(dict(reference=rawref,pointer=pointer)))
                        return answer
                    return fixture.native(dict(facts=[dict(statement='Exact recorded fixture value',reference=rawref,pointer=pointer,value=source[pointer[1:]])],interpretation='Offline evidence-only fixture; no scientific material acceptance'))
                if packet['role']=='coordinator':
                    r=packet['reads'][0]
                    return fixture.native(dict(facts=[dict(statement='First report interpretation',reference=r['reference'],pointer='/interpretation',value=r['page']['content']['interpretation'])],interpretation='Actual fixture synthesis of both inspected reports; scientific semantics unassessed'))
                cat=packet['fact_catalog'];entry=next(e for e in cat['content']['entries'] if e['origin']=='principal_additional' and e['pointer']=='/execution_id')
                return fixture.native(dict(interpretation='Fixture formal dispositions only',dispositions=[dict(**t,catalog=cat['reference'],catalog_version='1.0.0',disposition='defer',evidence_used=[dict(handle=entry['handle'])],reason='Offline fixture leaves semantics unassessed') for t in packet['disposition_targets']]))
            with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport),patch('examples.gvs_nmpc_route_experiment.load_credential',side_effect=AssertionError('OFFLINE_CREDENTIAL_BARRIER')):
                try:result=activity.stage_b(host,m,p,transport=True)
                except Exception:
                    failures={k:host.store.artifact(n['failure_record']) if n.get('failure_record') else n.get('reason') for k,n in host.store.session(host.run_id)['state']['investigations'].items() if n['status']!='completed'}
                    self.fail(json.dumps(dict(failures=failures,principal_packet=json.loads(sends[-1]['messages'][1]['content']) if sends else None),ensure_ascii=False))
            atomic_json(out/'material_audit.json',dict(report=result['report'],material_correctness='pass',scope='Fixture structure only; no live/material empirical claim'))
            with patch.object(activity,'execute_c',return_value='automatic fixed C invoked') as c:
                self.assertEqual(activity.close_b(),'automatic fixed C invoked');c.assert_called_once()
            self.assertTrue(read(out/'coordinated_gate.json')['passed'])
            self.assertEqual(len(sends),6)
            state=host.store.session(host.run_id)['state'];self.assertEqual(len(state['historical_investigations']),1)
            self.assertEqual(state['historical_investigations']['coordinator-plan']['own_inference_allowance'],0)
            self.assertEqual({k:n['order']['budget']['model_calls'] for k,n in state['investigations'].items()},
                {'reach-holding-interpretation':12,'timing-integrity-limits':12,'coordinator-summary':6,'principal-coordinated-v2':10})
            self.assertFalse(any(e['kind']=='investigation_provider_attempt' and e.get('request_id')=='investigation-coordinator-plan' for e in host.store.events(host.run_id)))
