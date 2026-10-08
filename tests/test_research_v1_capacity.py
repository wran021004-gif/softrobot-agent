"""Targeted report/capacity regressions; no scientific test imports or solves."""
from copy import deepcopy
import json
import gc
from pathlib import Path
import shutil
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from tools.platform_store import Store,plain,zero
from tools.platform_host import Host
from tools.research_investigations import InvestigationDispatcher,InvestigationOrder,InvestigationReturn,SourceFact
from tools.research_v1_delivery import model_configuration
from tools.research_mainline3 import configuration,interface_proposal
from tools.context_assembly import check_outgoing_request
from tools.state_io import digest,read

ROOT=Path(__file__).resolve().parents[1]

def native(args,finish='tool_calls'):
    return dict(usage=dict(prompt_tokens=20,completion_tokens=30,total_tokens=50),choices=[dict(finish_reason=finish,
        message=dict(role='assistant',content=None,tool_calls=[dict(id='call',type='function',
            function=dict(name='investigation_return',arguments=json.dumps(args)))]))])

class CapacityBindingTests(TestCase):
    def setUp(self):
        self.folder=ROOT/'runs'/('v1-capacity-fixture-'+uuid4().hex)
        cfg=model_configuration(configuration());cfg['run_id']='capacity-fixture'
        proposal=interface_proposal('coordinated',expanded=True)
        cfg['policy'].update(route=None,budget=proposal['project_budget'],allowed_tools=list(proposal['tool_bindings']),
            tool_bindings=proposal['tool_bindings'],operation_allowances=proposal['operation_allowances'])
        self.addCleanup(self.cleanup)
        store=Store(self.folder);store.create(dict(project_id=self.folder.name,grant_id=self.folder.name,
            authorization_source='Offline fixture only',budget=proposal['project_budget']))
        self.host=Host(self.folder,'capacity-fixture');self.host.create(cfg);self.host.resume()
        self.source=dict(execution_id='historical-execution',result_type='free_reach',scalar=0.002697828858325615,
            nested=dict(scalar=0.0026978288583256148),flag=False)
        with store.transaction() as db:
            self.ref=plain(store.put(db,self.source));state=store.session(self.host.run_id,db)['state']
            grant=dict(max_count=3,max_concurrency=2,allowed_tools=['evidence.read'],evidence=[self.ref],include_completed_reports=True,
                per_node_budget=proposal['node_budget'],total_budget=proposal['total_node_budget'],output_bytes=65536,protocol_correction_limit=2)
            state.update(role_context=dict(role='principal',investigation_grant=grant),investigation_grant_identity=digest(grant))
            store.update_state(db,self.host.run_id,state)
        self.dispatch=InvestigationDispatcher(self.host)
        self.order=InvestigationOrder(investigation_id='investigator',question='Read saved facts',evidence=[self.ref],
            queries=[dict(reference=self.ref,pointer='',limit=100)],budget=proposal['node_budget'],timeout_s=600,output_bytes=65536,stop_conditions=['Bounded fixture only'])

    def cleanup(self):
        assert self.folder.resolve().is_relative_to((ROOT/'runs').resolve())
        gc.collect()
        if self.folder.exists():shutil.rmtree(self.folder)

    def test_exact_scalar_type_identity_and_visibility(self):
        fact=SourceFact(statement='Original value',reference=self.ref,pointer='/scalar',value=self.source['scalar'],source_identity=dict(execution_id='historical-execution'))
        self.dispatch._validate_fact(fact,'RETURN')
        for pointer,value,identity in [('/scalar',self.source,{}),('/scalar',0.0026978288583256148,{}),('/flag',0,{}),('/scalar',self.source['scalar'],dict(execution_id='wrong'))]:
            with self.assertRaises(ValueError):self.dispatch._validate_fact(fact.model_copy(update=dict(pointer=pointer,value=value,source_identity=identity)),'RETURN')
        with self.assertRaisesRegex(ValueError,'INVALID_SINGLE_JSON_POINTER'):
            self.dispatch._validate_fact(fact.model_copy(update=dict(pointer='/scalar, /flag')),'RETURN')
        _,_,reads,_=self.dispatch.prepare(self.order)
        self.assertTrue(self.dispatch._visible(fact,reads[0]))
        self.assertFalse(self.dispatch._visible(fact,dict(reads[0],page=dict(reads[0]['page'],kind='overview'))))

    def test_length_and_plain_text_never_recover_as_success(self):
        # Even syntactically complete JSON with a provider length flag is invalid.
        with self.assertRaisesRegex(ValueError,'TRUNCATED'):self.dispatch._decode(native(dict(interpretation='Complete-looking JSON'),finish='length'))
        from schemas.platform import ModelResponse
        from tools.platform_models import DeepSeekAdapter
        response=native(dict(interpretation='Text wrapper'))
        response['choices'][0]['message']=dict(role='assistant',content=json.dumps(dict(tool_calls=response['choices'][0]['message']['tool_calls'])))
        with self.assertRaises(ValueError):DeepSeekAdapter().decode(ModelResponse(raw=response),0,{'evidence.read':'1.0.0'})

    def test_wire_output_and_accumulated_request_guard(self):
        _,wire,_,measurement=self.dispatch.prepare(self.order)
        self.assertEqual(wire['max_tokens'],32768);self.assertEqual(wire['thinking'],dict(type='enabled'))
        self.assertEqual(wire['reasoning_effort'],'high');self.assertEqual(wire['tool_choice'],'auto')
        self.assertEqual(measurement['response_reserve_tokens'],32768)
        config=self.host.store.session(self.host.run_id)['snapshot']['input']['policy']['model']
        wire['messages'].append(dict(role='tool',content='x'*160000,tool_call_id='oversize'))
        with self.assertRaisesRegex(ValueError,'OVERFLOW'):check_outgoing_request(wire,config,'research_decision')

    def test_paid_invalid_report_correction_keeps_original_budget(self):
        sends=[]
        def transport(wire):
            sends.append(deepcopy(wire))
            value=self.source if len(sends)==1 else self.source['scalar']
            return native(dict(facts=[dict(statement='Exact scalar',reference=self.ref,pointer='/scalar',value=value)],interpretation='Fixture only'))
        result=self.dispatch.dispatch(plain(self.order),transport=transport)
        self.assertEqual(result.status,'completed')
        state=self.host.store.session(self.host.run_id)['state']
        self.assertEqual(state['investigations']['investigator']['usage']['model_calls'],2)
        self.assertEqual(state['investigation_protocol_corrections_used'],1)
        self.assertIn('INVALID_UNEXECUTED_REPORT',sends[1]['messages'][-1]['content'])
        self.assertEqual(self.host.store.remaining()['used']['model_calls'],2)

    def test_large_complete_report_is_available_to_principal(self):
        report=InvestigationReturn(facts=[SourceFact(statement='Exact scalar',reference=self.ref,pointer='/scalar',value=self.source['scalar'])],
            unknowns=['Fixture long archived explanation '+('a'*2400) for _ in range(8)],interpretation='Complete report; archive and request retain the final unknown.')
        self.assertGreater(len(json.dumps(plain(report)).encode()),16384)
        first=self.dispatch.dispatch(plain(self.order),transport=lambda wire:native(plain(report)))
        self.assertEqual(first.status,'completed')
        principal=self.order.model_copy(update=dict(investigation_id='principal',role='principal',evidence=[first.result],
            queries=[]))
        order,row,_=self.dispatch._reserve(plain(principal))
        from schemas.platform_operations import ReadEvidence
        page=self.dispatch._query(order,ReadEvidence(reference=first.result,pointer='',limit=100,byte_limit=65536))
        self.assertIsNone(page['page']['next_offset']);self.assertEqual(page['page']['content'],plain(report))
        _,wire,_,_=self.dispatch.prepare(principal.model_copy(update=dict(queries=[ReadEvidence(reference=first.result,pointer='',limit=100,byte_limit=65536)])),executing=True)
        packet=json.loads(wire['messages'][1]['content'])
        self.assertEqual(packet['reads'][0]['page']['content']['unknowns'][-1],report.unknowns[-1])

    def test_timeout_and_output_grant_cannot_expand(self):
        with self.assertRaisesRegex(ValueError,'OUTPUT_CAPACITY'):
            with self.host.store.transaction() as db:
                state=self.host.store.session(self.host.run_id,db)['state'];grant=state['role_context']['investigation_grant'];grant['output_bytes']=16384
                state['investigation_grant_identity']=digest(grant);self.host.store.update_state(db,self.host.run_id,state)
            self.dispatch.prepare(self.order)

    def _public_stage(self,mode):
        from tools.research_mainline3 import live_interface_scenario,direct_validation_plan
        with self.host.store.transaction() as db:
            ref=plain(self.host.store.put(db,read(ROOT/'runs/stage336_manual_20261001_090616/stage336_audit.json')['execution']['factual_result']))
        plan=direct_validation_plan(ref,expanded=True,mode=mode)
        sends=[]
        def transport(adapter,config,payload):
            sends.append(deepcopy(payload));packet=json.loads(payload['messages'][1]['content'])
            role=packet['role'];key=packet['investigation_id']
            if role=='coordinator':
                children=[dict(investigation_id='child-'+str(i),parent_id=key,role='investigator',question=q,evidence=[ref],
                    budget=packet['delegation_budget_limit'],timeout_s=packet['timeout_s'],output_bytes=packet['output_bytes'],stop_conditions=['Bounded fixture'])
                    for i,q in enumerate(('Saved reach observations','Saved timing observations'))]
                return native(dict(interpretation='Fixture delegation only',children=children))
            if role=='principal':
                self.assertEqual(len(packet['reads']),2)
                self.assertTrue(all(r['page']['next_offset'] is None for r in packet['reads']))
                return native(dict(interpretation='Offline defer fixture',dispositions=[dict(investigation_id=t['investigation_id'],report=t['report'],disposition='defer',reason='Fixture semantics unassessed') for t in packet['disposition_targets']]))
            tools=[m for m in payload['messages'] if m['role']=='tool']
            if not tools:
                arguments=dict(reference=ref,pointer='/sampled_settling')
                # Exercise the actual advertised contract in both legacy and
                # business-field fixtures; never ask production to unwrap v2.
                if 'arguments' in payload['tools'][1]['function']['parameters'].get('properties',{}):
                    arguments=dict(arguments=arguments,reason='Fixture model chooses original observation',tool_version='1.0.0')
                answer=native({});answer['choices'][0]['message']['tool_calls'][0]['function']=dict(name=payload['tools'][1]['function']['name'],
                    arguments=json.dumps(arguments))
                return answer
            page=json.loads(tools[-1]['content'])
            return native(dict(facts=[dict(statement='Original sampled limit result',reference=ref,pointer='/sampled_settling/passed',value=page['content']['passed'])],interpretation='Fixture only'))
        errors=[];handler=InvestigationDispatcher._handle_failure
        def capture(dispatcher,order,row,progress,exc,started,**kwargs):
            errors.append(str(exc));return handler(dispatcher,order,row,progress,exc,started,**kwargs)
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport),patch.object(InvestigationDispatcher,'_handle_failure',new=capture):
            result=live_interface_scenario(self.host,mode,plan=plan)
        failures={k:dict(status=n['status'],progress=n.get('progress'),
            failure=self.host.store.artifact(n['failure_record']) if n.get('failure_record') else None)
            for k,n in self.host.store.session(self.host.run_id)['state']['investigations'].items() if n['status']!='completed'}
        self.assertEqual(result['status'],'formal_dispositions_recorded',dict(errors=errors,failures=failures))
        self.assertTrue(all(p['max_tokens']==32768 for p in sends))
        self.assertEqual(len(sends),6 if mode=='coordinated' else 5)
        self.assertEqual(len(self.host.store.session(self.host.run_id)['state']['principal_investigation_reads']),1)

    def test_expanded_public_direct_stage(self):self._public_stage('direct')

    def test_expanded_public_coordinator_stage(self):self._public_stage('coordinated')
