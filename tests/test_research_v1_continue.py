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
from tools.context_assembly import expand_investigation_context

class ContinuationTests(TestCase):
    setUp=fixture.CapacityBindingTests.setUp
    cleanup=fixture.CapacityBindingTests.cleanup

    def test_selected_investigator_projection_and_actual_sent_restoration(self):
        sends=[]
        def transport(wire):
            sends.append(deepcopy(wire));packet=expand_investigation_context(json.loads(wire['messages'][1]['content']));cat=packet['source_fact_catalog']
            entry=next(e for e in cat['entries'] if e['pointer']=='/nested')
            return fixture.native(dict(facts=[dict(statement='Fixture exact nested scalar',catalog=cat['reference'],catalog_version='1.0.0',handle=entry['handle'],projection='/scalar')],
                counterevidence=[dict(statement='Fixture failed Boolean',catalog=cat['reference'],catalog_version='1.0.0',handle=next(e['handle'] for e in cat['entries'] if e['pointer']=='/flag'))],interpretation='Offline fixture only'))
        with patch.object(InvestigationDispatcher,'_selected_reports',return_value=True),patch.object(InvestigationDispatcher,'_selectable',return_value=True),patch.object(InvestigationDispatcher,'_native_v2',return_value=True):
            result=self.dispatch.dispatch(plain(self.order),transport=transport)
            self.assertEqual(result.status,'completed',result.reason)
            report=self.host.store.artifact(result.result)
            self.assertEqual(report['facts'][0]['pointer'],'/nested/scalar')
            self.assertEqual(report['facts'][0]['value'],self.source['nested']['scalar'])
            self.assertIs(report['counterevidence'][0]['value'],False)
            node=self.host.store.session(self.host.run_id)['state']['investigations']['investigator']
            retained=deepcopy(node)
            self.dispatch.prepare(self.order,executing=True,reuse_saved_reads=True)
            self.dispatch._bind_resume_catalog(self.order,sends[0],retained)
            self.assertEqual(self.host.store.session(self.host.run_id)['state']['investigations']['investigator']['source_fact_catalog'],retained['source_fact_catalog'])
            self.assertEqual(len(sends),1)
            events=[e for e in self.host.store.events(self.host.run_id) if e['kind']=='investigator_selection_expansion']
            link=self.host.store.artifact(events[0]['outputs'][0])
            self.assertNotEqual(link['original_selection_reference'],link['deterministic_expansion_reference'])
            # A legitimate implementation migration may change only run origin.
            original=self.host.store.artifact(retained['source_fact_catalog']);migrated=deepcopy(original)
            migrated['activity_run_id']='authorized-original-run'
            with self.host.store.transaction() as db:sent=plain(self.host.store.put(db,migrated))
            payload=deepcopy(sends[0]);packet=json.loads(payload['messages'][1]['content']);packet['source_fact_catalog']['reference']=sent
            payload['messages'][1]['content']=json.dumps(packet)
            prior=dict(retained,source_fact_catalog=sent,source_catalog_origin_run_id='authorized-original-run')
            self.dispatch._bind_resume_catalog(self.order,payload,prior)
            self.assertEqual(self.host.store.session(self.host.run_id)['state']['investigations']['investigator']['source_fact_catalog'],sent)
            changed=deepcopy(original);changed['entries'][0]['value']='changed'
            with self.host.store.transaction() as db:bad=plain(self.host.store.put(db,changed))
            self.dispatch._state('investigator',source_fact_catalog=bad)
            with self.assertRaisesRegex(ValueError,'CONTENT_OR_BINDING_CHANGED'):self.dispatch._bind_resume_catalog(self.order,payload,prior)
            self.dispatch._state('investigator',source_fact_catalog=retained['source_fact_catalog'],status='failed')
            replay=self.dispatch._decode(fixture.native(link['model_selection']),node_id='investigator')
            self.assertEqual(replay.facts[0].value,self.source['nested']['scalar'])
            self.assertEqual(self.host.store.session(self.host.run_id)['state']['investigations']['investigator']['usage']['model_calls'],1)

    def test_available_failed_archived_recomputation_is_not_unavailable(self):
        from tools.research_metric_view import archived_recomputation_presentation
        view=dict(reach=dict(independent_recomputation='available',recomputed_result=False),holding=dict(
            position=dict(independent_recomputation='available',recomputed_result=True),speed=dict(independent_recomputation='unavailable',recomputed_result=None)))
        rows=archived_recomputation_presentation(view,self.ref)['observations']
        self.assertEqual([(r['availability'],r['assessment']) for r in rows],[('available','fail'),('available','pass'),('unavailable','cannot_assess')])
        self.assertIs(rows[0]['archived_result'],False)

    def test_saved_principal_overflow_fits_without_changing_native_history(self):
        from tools.context_assembly import compact_investigation_request,measure_input,check_outgoing_request
        from tools.platform_models import effective_config
        cfg=effective_config(self.host)
        source=fixture.ROOT/'evidence/research_mainline3_v1_complete_20261009'
        for name in ('principal_capacity_failed_wire.json','principal_capacity_repaired_wire.json'):
            wire=read(source/name);before=deepcopy(wire);fixed=compact_investigation_request(wire)
            check_outgoing_request(fixed,cfg,'research_decision')
            self.assertEqual(wire,before)
            self.assertEqual(fixed['messages'][2:],wire['messages'][2:])
            def semantic_schema(v):
                if isinstance(v,dict):return {k:semantic_schema(x) for k,x in v.items() if k not in ('title','description')}
                if isinstance(v,list):return [semantic_schema(x) for x in v]
                return v
            self.assertEqual(semantic_schema(fixed['tools']),semantic_schema(wire['tools']))
            self.assertEqual(fixed['max_tokens'],32768)
            self.assertLess(measure_input(fixed,cfg,'research_decision')['utf8_bytes'],measure_input(wire,cfg,'research_decision')['utf8_bytes'])

    def grant(self,**updates):
        with self.host.store.transaction() as db:
            state=self.host.store.session(self.host.run_id,db)['state'];g=state['role_context']['investigation_grant'];g.update(updates)
            state['investigation_grant_identity']=digest(g);self.host.store.update_state(db,self.host.run_id,state)

    def target_grant(self,role='investigator'):
        from tools.research_v1_continue import correction_policy
        policy=correction_policy();policy['targets']={'investigator':dict(report='report:investigator',
            dispositions={'reach':'disposition:reach','timing':'disposition:timing'} if role=='principal' else {})}
        alloc=dict(budget=plain(self.order.budget),timeout_s=self.order.timeout_s,
            exploration_requests=0,protected_delivery_requests=1)
        self.order=self.order.model_copy(update=dict(role=role))
        # Deliberately conflicting historical counters prove the opt-in executor
        # uses the new rule, rather than merely advertising it in the manifest.
        self.grant(correction_policy=policy,delivery_allocations={'investigator':alloc},
            total_budget={**plain(self.order.budget),'model_calls':40,'tool_calls':60,'wall_s':10200.},
            protocol_correction_limit=0,protocol_correction_role_limits={'principal':0,'other':0},
            protocol_correction_per_node=0,protocol_correction_per_decision=0)
        with self.host.store.transaction() as db:
            state=self.host.store.session(self.host.run_id,db)['state']
            state.update(investigation_protocol_corrections_used=99,investigation_corrections_by_role={'principal':99,'other':99})
            self.host.store.update_state(db,self.host.run_id,state)

    def target_counts(self):
        grant=self.host.store.session(self.host.run_id)['state']['role_context']['investigation_grant']
        return self.dispatch._target_accounting(grant)

    def test_current_target_policy_four_corrections_through_public_executor(self):
        self.target_grant();sends=[]
        def transport(adapter,config,wire):
            sends.append(deepcopy(wire))
            value=len(sends) if len(sends)<=4 else self.source['scalar']
            return fixture.native(dict(interpretation='Offline correction example',facts=[dict(statement='Exact scalar',reference=self.ref,pointer='/scalar',value=value)]))
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport):
            submitted=invoke(self.host,'research.investigate',plain(self.order),request_id='four-corrections')
            import threading
            for t in threading.enumerate():
                if t.name=='investigation-investigator':t.join(30)
            collected=invoke(self.host,'research.investigation_status',dict(investigation_id='investigator'),request_id='collect-four')
        self.assertEqual(submitted['execution_status'],'completed')
        self.assertEqual(self.host.store.artifact(collected['output'])['status'],'completed')
        self.assertEqual(len(sends),5)
        self.assertEqual(self.target_counts()['targets']['report:investigator']['used'],4)
        node=self.host.store.session(self.host.run_id)['state']['investigations']['investigator']
        self.assertEqual(node['requests_by_purpose'],dict(ordinary=1,model_correction=4,engineering_recovery=0))
        feedback=[json.loads(w['messages'][-1]['content'])['correction_authorization'] for w in sends[1:]]
        self.assertEqual([f['extension'] for f in feedback],[False,False,True,True])
        self.assertEqual([f['ordinals']['report:investigator'] for f in feedback],[1,2,3,4])
        self.assertTrue(all(f['latest_output'] and f['remaining_task_requests']>0 and f['remaining_stage_requests']>0 for f in feedback))

    def test_target_cap_survives_report_versions_session_restore_and_redispatch(self):
        self.target_grant();sends=[]
        def transport(wire):
            sends.append(wire)
            return fixture.native(dict(interpretation='Report version '+str(len(sends)),facts=[dict(statement='Invalid scalar',reference=self.ref,pointer='/scalar',value=len(sends))]))
        result=self.dispatch.dispatch(plain(self.order),transport=transport)
        self.assertEqual(result.status,'failed');self.assertEqual(len(sends),5)
        state=deepcopy(self.host.store.session(self.host.run_id)['state']);cfg=deepcopy(self.host.store.session(self.host.run_id)['snapshot']['input'])
        cfg['run_id']='target-restored'
        from tools.platform_host import Host
        restored=Host(self.folder,cfg['run_id']);restored.create(cfg);restored.resume()
        state['investigations']['investigator'].update(usage={k:0 for k in plain(self.order.budget)},started_unix=10**12,
            protocol_corrections_used=0,consecutive_model_corrections=0)
        with restored.store.transaction() as db:
            # Another saved report/version cannot create a new correction target.
            ref=plain(restored.store.put(db,fixture.native(dict(interpretation='Another report version',facts=[]))))
            state['investigations']['investigator']['provider_response_refs'].append(ref)
            restored.store.update_state(db,restored.run_id,state)
        d=InvestigationDispatcher(restored);exc=ValueError('RETURN_SOURCE_VALUE_MISMATCH')
        exc.issue=dict(path='/facts/0/value',original_value=self.source['scalar'],supplied_value=7)
        self.assertIsNone(d._protocol_feedback(self.order,exc))
        self.assertEqual(self.target_counts()['targets']['report:investigator']['used'],4)
        stopped=next(e for e in reversed(restored.store.events(restored.run_id)) if e['kind']=='investigation_target_correction')
        self.assertEqual(restored.store.artifact(stopped['outputs'][0])['latest_output'],self.target_counts()['tasks']['investigator']['latest_output'])
        with self.assertRaisesRegex(ValueError,'FROZEN_TASK_OR_TIMEOUT_MISMATCH'):
            d.dispatch(plain(self.order.model_copy(update=dict(investigation_id='replacement'))),transport=lambda wire:self.fail('No provider redispatch'))

    def test_unchanged_failure_and_cosmetic_versions_stop_without_extension(self):
        self.target_grant();sends=[]
        def transport(wire):
            sends.append(wire)
            return fixture.native(dict(interpretation='Cosmetic version '+str(len(sends)),facts=[dict(statement='Same invalid scalar',reference=self.ref,pointer='/scalar',value=1)]))
        result=self.dispatch.dispatch(plain(self.order),transport=transport)
        self.assertEqual(result.status,'failed');self.assertEqual(len(sends),2)
        self.assertEqual(self.target_counts()['targets']['report:investigator']['used'],1)
        events=self.host.store.events(self.host.run_id)
        stop=next(e for e in events if e['kind']=='investigation_target_correction' and e['status']=='stopped')
        self.assertEqual(self.host.store.artifact(stop['outputs'][0])['reason'],'unchanged_failure_and_feedback')

    def test_target_policy_request_and_deadline_stops_and_zero_cost_local_feedback(self):
        self.target_grant();order,row,_=self.dispatch._reserve(plain(self.order))
        with self.host.store.transaction() as db:
            state=self.host.store.session(self.host.run_id,db)['state']
            raw=fixture.native(dict(interpretation='Saved defect',facts=[]))
            state['investigations']['investigator']['provider_response_refs']=[plain(self.host.store.put(db,raw))]
            self.host.store.update_state(db,self.host.run_id,state)
        exc=ValueError('RETURN_SOURCE_VALUE_MISMATCH');exc.issue=dict(path='/facts/0/value',supplied_value=1,original_value=self.source['scalar'])
        feedback=self.dispatch._protocol_feedback(order,exc)
        self.assertIsNotNone(feedback)
        self.assertEqual(self.target_counts()['targets']['report:investigator']['used'],0)
        # Pending local feedback and failed request assembly spend no requests.
        self.assertEqual(self.dispatch._protocol_feedback(order,exc),feedback)
        self.assertEqual(self.target_counts()['tasks']['investigator']['usage']['model_calls'],0)
        with self.host.store.transaction() as db:
            grant=self.host.store.session(self.host.run_id,db)['state']['role_context']['investigation_grant']
            value=self.dispatch._target_accounting(grant,db);value['tasks']['investigator'].pop('pending_correction')
            value['tasks']['investigator']['usage']['model_calls']=order.budget.model_calls
            self.dispatch._save_target_accounting(db,value)
        self.assertIsNone(self.dispatch._protocol_feedback(order,exc))
        with self.assertRaisesRegex(ValueError,'MODEL_CALLS_BUDGET_EXHAUSTED'):
            self.dispatch._provider_start(order,row,{},dict(passed=True),0)
        with self.host.store.transaction() as db:
            value=self.dispatch._target_accounting(grant,db)
            value['tasks']['investigator']['usage']['model_calls']=0
            value['tasks']['other-task']=dict(usage={**plain(self.order.budget),'model_calls':40})
            self.dispatch._save_target_accounting(db,value)
        self.assertIsNone(self.dispatch._protocol_feedback(order,exc))
        with self.assertRaisesRegex(ValueError,'COMMON_MODEL_BUDGET_EXHAUSTED'):
            self.dispatch._provider_start(order,row,{},dict(passed=True),0)
        with self.host.store.transaction() as db:
            value=self.dispatch._target_accounting(grant,db)
            value['tasks'].pop('other-task')
            value['tasks']['investigator']['usage']['model_calls']=0;value['tasks']['investigator']['started_unix']=0
            self.dispatch._save_target_accounting(db,value)
        self.assertIsNone(self.dispatch._protocol_feedback(order,exc))
        with self.assertRaisesRegex(ValueError,'ELAPSED_LIMIT'):
            self.dispatch._provider_start(order,row,{},dict(passed=True),0)

    def test_current_policy_engineering_recovery_does_not_charge_corrections(self):
        self.target_grant()
        def broken(wire):
            exc=RuntimeError('DEEPSEEK_HTTP_400')
            exc.transport_state=dict(transport_attempted=True,response_received=True,response_body_received=True,http_status=400,stage='transport')
            exc.provider_response=dict(status_code=400)
            raise exc
        self.assertEqual(self.dispatch.dispatch(plain(self.order),transport=broken).status,'failed')
        from tools.platform_host import Host
        d=InvestigationDispatcher(Host(self.folder,self.host.run_id))
        result=d.engineering_recovery('investigator','Confirmed transport defect repaired locally',transport=lambda wire:fixture.native(dict(interpretation='Offline recovered report')))
        self.assertEqual(result.status,'completed')
        counts=self.target_counts()
        self.assertEqual(counts['targets'],{})
        self.assertEqual(counts['tasks']['investigator']['requests_by_purpose'],dict(ordinary=1,model_correction=0,engineering_recovery=1))

    def test_disposition_targets_ignore_report_version_and_charge_independently(self):
        self.target_grant(role='principal');order,row,_=self.dispatch._reserve(plain(self.order))
        def saved(version,target):
            with self.host.store.transaction() as db:
                state=self.host.store.session(self.host.run_id,db)['state']
                raw=fixture.native(dict(interpretation='Version '+str(version),dispositions=[dict(investigation_id=target,report={'artifact_id':str(version)*64,'media_type':'application/json'})]))
                node=state['investigations']['investigator'];node.setdefault('provider_response_refs',[]).append(plain(self.host.store.put(db,raw)))
                self.host.store.update_state(db,self.host.run_id,state)
        for i in range(1,5):
            saved(i,'reach');exc=ValueError('DISPOSITION_FACT_BINDING')
            exc.issue=dict(path='/dispositions/0/adopted_claims/0/scope',selection=[i],reason='Missing selected source scope',legal=dict(requirement='Select exact scope'),failure_key='report:'+str(i)*64)
            self.assertIsNotNone(self.dispatch._protocol_feedback(order,exc))
            self.dispatch._provider_start(order,row,{},dict(passed=True),i)
        saved(5,'reach');exc.issue['selection']=[5]
        self.assertIsNone(self.dispatch._protocol_feedback(order,exc))
        saved(6,'timing');exc.issue['selection']=[6]
        self.assertIsNotNone(self.dispatch._protocol_feedback(order,exc))
        self.dispatch._provider_start(order,row,{},dict(passed=True),5)
        counts=self.target_counts()['targets']
        self.assertEqual(counts['disposition:reach']['used'],4);self.assertEqual(counts['disposition:timing']['used'],1)

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

    def test_multi_call_rejection_answers_every_native_id_with_reasoning(self):
        sends=[]
        def transport(wire):
            sends.append(deepcopy(wire))
            if len(sends)==1:
                answer=fixture.native({});message=answer['choices'][0]['message'];message['reasoning_content']='Preserve original multi-call reasoning'
                call=message['tool_calls'][0];call['function']=dict(name='evidence_read',arguments=json.dumps(dict(reference=self.ref,pointer='/scalar')))
                extra=deepcopy(call);extra['id']='second-native-id';message['tool_calls'].append(extra);return answer
            last_assistant=next(i for i in reversed(range(len(wire['messages']))) if wire['messages'][i]['role']=='assistant')
            self.assertEqual(wire['messages'][last_assistant]['reasoning_content'],'Preserve original multi-call reasoning')
            self.assertEqual({m['tool_call_id'] for m in wire['messages'][last_assistant+1:] if m['role']=='tool'}, {'call','second-native-id'})
            return fixture.native(dict(interpretation='Complete focused offline report'))
        with patch.object(InvestigationDispatcher,'_native_v2',return_value=True),patch.object(InvestigationDispatcher,'_selectable',return_value=True):
            result=self.dispatch.dispatch(plain(self.order),transport=transport)
        self.assertEqual(result.status,'completed');self.assertEqual(len(sends),2)

    def test_response_content_saved_parsed_processed_and_exportable(self):
        from types import SimpleNamespace
        text='Inspect {"evaluator":"evaluate.reach@1.0.0"}; bearer/token/api_key are quoted research labels.'
        body=fixture.native(dict(interpretation=text,unknowns=['Authentication examples are data: user:password@example.com']))
        body['choices'][0]['message']['reasoning_content']='Quoted JSON: {"api_key":"fixture-label"}'
        original=json.dumps(body)
        def transport(adapter,config,wire):return request_completion(config,wire,'isolated-fixture-key')
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport),patch('tools.model_transports.deepseek.build_opener',return_value=SimpleNamespace(open=lambda *a,**kw:FakeResponse(original.encode()))):
            submit=invoke(self.host,'research.investigate',plain(self.order),request_id='submit-content')
            import threading
            for t in threading.enumerate():
                if t.name=='investigation-investigator':t.join(30)
            checked=invoke(self.host,'research.investigation_status',dict(investigation_id='investigator'),request_id='collect-content')
        self.assertEqual(submit['execution_status'],'completed')
        result=self.host.store.artifact(checked['output']);self.assertEqual(result['status'],'completed')
        node=self.host.store.session(self.host.run_id)['state']['investigations']['investigator']
        self.assertEqual(self.host.store.artifact(node['original_body_refs'][0])['utf8_text'],original)
        self.assertEqual(self.host.store.artifact(node['result'])['interpretation'],text)
        self.assertEqual(node['requests_by_purpose'],dict(ordinary=1,model_correction=0,engineering_recovery=0))

    def test_purpose_categories_report_rejection_history_and_restoration(self):
        from tools.research_v1_continue import allocation
        alloc=allocation(3,2,1,4);alloc['budget']=plain(self.order.budget)
        self.grant(delivery_allocations={'investigator':alloc},protocol_correction_limit=8,protocol_correction_per_decision=2)
        sends=[]
        def transport(adapter,config,wire):
            sends.append(deepcopy(wire));answer=fixture.native({});message=answer['choices'][0]['message']
            if len(sends) in (1,3):
                message['reasoning_content']='Every rejected ID must be answered'
                first=message['tool_calls'][0];first['function']=dict(name='evidence_read',arguments=json.dumps(dict(reference=self.ref,pointer='/scalar')))
                second=deepcopy(first);second['id']='second-'+str(len(sends));message['tool_calls'].append(second)
                return answer
            assistant=next(m for m in reversed(wire['messages']) if m.get('role')=='assistant')
            replies={m.get('tool_call_id') for m in wire['messages'] if m.get('role')=='tool'}
            self.assertTrue({c['id'] for c in assistant['tool_calls']}<=replies)
            self.assertEqual(assistant['reasoning_content'],'Every rejected ID must be answered')
            if len(sends)==2:
                message['tool_calls'][0]['function']=dict(name='evidence_read',arguments=json.dumps(dict(reference=self.ref,pointer='/scalar')))
                return answer
            self.assertEqual([t['function']['name'] for t in wire['tools']],['investigation_return'])
            return fixture.native(dict(interpretation='Formal supported result after report-phase rejection'))
        with patch.object(InvestigationDispatcher,'_native_v2',return_value=True),patch.object(InvestigationDispatcher,'_selectable',return_value=True),patch('tools.platform_models.DeepSeekAdapter._transport',new=transport):
            r=invoke(self.host,'research.investigate',plain(self.order),request_id='category-submit')
            import threading
            for t in threading.enumerate():
                if t.name=='investigation-investigator':t.join(30)
            from tools.platform_host import Host
            restored=Host(self.folder,self.host.run_id)
            result=invoke(restored,'research.investigation_status',dict(investigation_id='investigator'),request_id='category-restore')
        self.assertEqual(self.host.store.artifact(result['output'])['status'],'completed')
        node=restored.store.session(restored.run_id)['state']['investigations']['investigator']
        self.assertEqual(node['requests_by_purpose'],dict(ordinary=2,model_correction=2,engineering_recovery=0))
        self.assertEqual(node['usage']['model_calls'],4)
        self.assertEqual([r['purpose'] for r in node['provider_requests']],['ordinary','model_correction','ordinary','model_correction'])
        self.assertEqual(node['submission_phase'],'report_delivery')

    def test_engineering_recovery_separate_from_correction_after_restoration(self):
        from tools.research_v1_continue import allocation
        alloc=allocation(3,2,1,4);alloc['budget']=plain(self.order.budget)
        self.grant(delivery_allocations={'investigator':alloc})
        def broken(wire):
            exc=RuntimeError('DEEPSEEK_HTTP_400')
            exc.transport_state=dict(transport_attempted=True,response_received=True,response_body_received=True,http_status=400,stage='transport')
            exc.provider_response=dict(status_code=400)
            raise exc
        result=self.dispatch.dispatch(plain(self.order),transport=broken);self.assertEqual(result.status,'failed')
        from tools.platform_host import Host
        restored=InvestigationDispatcher(Host(self.folder,self.host.run_id))
        result=restored.engineering_recovery('investigator','Confirmed fixture transport failure repaired',transport=lambda wire:fixture.native(dict(interpretation='New formal report after engineering recovery')))
        self.assertEqual(result.status,'completed')
        node=restored.store.session(restored.run_id)['state']['investigations']['investigator']
        self.assertEqual(node['requests_by_purpose'],dict(ordinary=1,model_correction=0,engineering_recovery=1))
        self.assertEqual(node['usage']['model_calls'],2)
        self.assertEqual(node['provider_requests'][0]['outcome'],'failed')

    def test_public_import_new_b_synthesis_disposition_and_automatic_c_gate(self):
        from tools import research_v1_continue as activity
        from tools import research_v1_continue_gate as gate
        out=self.folder/'continuation-fixture-evidence'
        with patch.object(activity,'OUT',out),patch.object(gate,'OUT',out),patch('tools.platform_store.ROOT',self.folder):
            import time
            activity.start(started_unix=time.time()-2000);atomic_json(out/'offline_gate.json',dict(passed=True,scope='Fixture bootstrap only; no real grant'))
            activity.freeze();host,m,p=activity.host_for('coordinated',create=True)
            authorization=read(out/'authorization.json')
            self.assertTrue(gate.correction_consistency(authorization,p,orders=p['authorized_children'])['passed'])
            conflicting=deepcopy(p);conflicting['allocations']['principal-coordinated-v2']['budget']['model_calls']=12
            self.assertFalse(gate.correction_consistency(authorization,conflicting)['passed'])
            sends=[];counts={}
            original=read(activity.OLD/'coordinated_bundle.json');rawref=original['state']['investigations']['coordinator-plan']['order']['evidence'][0]
            source=original['artifacts'][rawref['artifact_id']]
            def transport(adapter,config,wire):
                sends.append(deepcopy(wire));packet=expand_investigation_context(json.loads(wire['messages'][1]['content']));key=packet['investigation_id'];counts[key]=counts.get(key,0)+1
                if packet['role']=='investigator':
                    pointer='/terminal_error_m' if key.startswith('reach') else '/mean_complete_update_s'
                    if counts[key]==1:
                        answer=fixture.native({});answer['choices'][0]['message']['reasoning_content']='Preserve required provider history'
                        answer['choices'][0]['message']['tool_calls'][0]['function']=dict(name='evidence_read',arguments=json.dumps(dict(reference=rawref,pointer=pointer)))
                        return answer
                    cat=packet['source_fact_catalog'];entry=next(e for e in cat['entries'] if e['reference']==rawref and e['pointer']==pointer)
                    return fixture.native(dict(facts=[dict(statement='Exact recorded fixture value',catalog=cat['reference'],catalog_version='1.0.0',handle=entry['handle'])],interpretation='Offline evidence-only fixture; no scientific material acceptance'))
                if packet['role']=='coordinator':
                    cat=packet['source_fact_catalog'];selected=[]
                    for r in packet['reads'][:2]:
                        entry=next(e for e in cat['entries'] if e['reference']==r['reference'] and e['pointer']=='/interpretation')
                        selected.append(dict(statement='Inspected fixture report interpretation',catalog=cat['reference'],catalog_version='1.0.0',handle=entry['handle']))
                    return fixture.native(dict(facts=selected,interpretation='Actual fixture synthesis of both inspected reports; scientific semantics unassessed'))
                cat=packet['fact_catalog'];entry=next(e for e in cat['content']['entries'] if e['origin']=='principal_additional' and e['pointer']=='/execution_id')
                if counts[key]==1:
                    return fixture.native(dict(interpretation='Offline intentionally missing formal targets',dispositions=[]))
                return fixture.native(dict(interpretation='Fixture formal dispositions only',dispositions=[dict(**t,catalog=cat['reference'],catalog_version='1.0.0',disposition='defer',evidence_used=[dict(handle=entry['handle'])],reason='Offline fixture leaves semantics unassessed') for t in packet['disposition_targets']]))
            with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport),patch('examples.gvs_nmpc_route_experiment.load_credential',side_effect=AssertionError('OFFLINE_CREDENTIAL_BARRIER')):
                try:result=activity.stage_b(host,m,p,transport=True)
                except Exception as exc:
                    failures={k:host.store.artifact(n['failure_record']) if n.get('failure_record') else n.get('reason') for k,n in host.store.session(host.run_id)['state']['investigations'].items() if n['status']!='completed'}
                    self.fail(str(exc)+' '+json.dumps(dict(failures=failures),ensure_ascii=False))
            atomic_json(out/'material_audit.json',dict(report=result['report'],material_correctness='pass',scope='Fixture structure only; no live/material empirical claim'))
            with patch.object(activity,'execute_c',return_value='automatic fixed C invoked') as c:
                self.assertEqual(activity.close_b(),'automatic fixed C invoked');c.assert_called_once()
            self.assertTrue(read(out/'coordinated_gate.json')['passed'])
            self.assertEqual(len(sends),5)
            self.assertNotIn('timing-integrity-limits',counts)
            state=host.store.session(host.run_id)['state'];self.assertEqual(len(state['historical_investigations']),2)
            self.assertGreater(m['preparation_wall_s'],2000)
            self.assertEqual(p['sequential_reservations']['preparation_s'],m['preparation_wall_s'])
            self.assertEqual(host.store.lookup(host.run_id,'offline-preparation')['status'],'completed')
            self.assertEqual(state['investigations']['principal-coordinated-v2']['reserved_wall_s'],2400.)
            self.assertEqual(state['investigations']['principal-coordinated-v2']['requests_by_purpose'],dict(ordinary=1,model_correction=1,engineering_recovery=0))
            self.assertTrue(all(w['model']=='deepseek-flash' and w['max_tokens']==32768 for w in sends))
            self.assertTrue(gate.correction_consistency(authorization,p,grant=state['role_context']['investigation_grant'],
                orders=[n['order'] for n in state['investigations'].values()])['passed'])
            self.assertEqual(state['historical_investigations']['coordinator-plan']['own_inference_allowance'],0)
            self.assertEqual({k:n['order']['budget']['model_calls'] for k,n in state['investigations'].items()},
                {'reach-holding-interpretation':12,'coordinator-summary':6,'principal-coordinated-v2':18})
            self.assertFalse(any(e['kind']=='investigation_provider_attempt' and e.get('request_id')=='investigation-coordinator-plan' for e in host.store.events(host.run_id)))
            atomic_json(out/'fixture_repair_verification.json',dict(passed=True,scope='Offline migration fixture only'))
            before=deepcopy(state['investigations'])
            migrated=activity.bind_repair(dict(defect_id='offline-migration-fixture',failure='Fixture-only version binding',
                affected_paths=['tools/research_v1_continue.py'],verification='fixture_repair_verification.json',started_unix=time.time()))
            after=migrated.store.session(migrated.run_id)['state']['investigations']
            for key,node in before.items():
                self.assertEqual(after[key]['usage'],node['usage'])
                self.assertEqual(after[key]['started_unix'],node['started_unix'])
                self.assertEqual(after[key]['execution_deadline_unix'],node['execution_deadline_unix'])
            self.assertEqual(len(sends),5)
