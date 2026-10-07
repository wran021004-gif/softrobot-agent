"""Wire-only offline interface checks, not autonomous model/science evidence."""
from copy import deepcopy
from pathlib import Path
import json
import gzip
import hashlib
import subprocess
import sys
import time
from unittest import TestCase
from unittest.mock import patch

from tests.test_research_mainline3 import Mainline3EngineeringTests
from tests.test_research_investigation_closeout import native, fact
from tools.platform_store import plain, zero, encode
from tools.research_execution import invoke
from tools.state_io import atomic_json

OBSERVATIONS={}
ARTIFACTS={}


def write_bundle(target,value):
    """Keep large immutable fixture snapshots losslessly outside the review JSON.

    These snapshots are not model-visible request evidence or a new runtime
    store. Original facts, provider sends/returns and dispositions stay inline.
    """
    value=deepcopy(value)
    snapshots={key:body for key,body in value['artifacts'].items() if isinstance(body,dict)
        and {'dependencies','input','input_identity','normalization','project_commit'}<=body.keys()}
    if snapshots:
        raw=encode(snapshots).encode('utf8');compressed=gzip.compress(raw,mtime=0)
        target.parent.mkdir(parents=True,exist_ok=True)
        archive=target.with_name('fixture_snapshots.json.gz');archive.write_bytes(compressed)
        value['fixture_snapshot_archive']=dict(path=archive.name,sha256=hashlib.sha256(compressed).hexdigest(),
            artifacts=list(snapshots),format='gzip JSON map of canonical artifact ID to unchanged body')
        value['artifacts']={key:body for key,body in value['artifacts'].items() if key not in snapshots}
    atomic_json(target,value)


class WireOnlyTransport:
    """No Host, Store, source ref, expected value or fixture argument is accepted.

    Calls are deterministic protocol scripts. All references and returned facts
    are derived afresh from the current payload and lawful tool responses.
    Captured requests are output evidence, never an input to the script.
    """
    def __init__(self):self.sent=[]

    def __call__(self,config,payload):
        self.sent.append(deepcopy(payload))
        packet=json.loads(payload['messages'][1]['content'])
        pages=[json.loads(m['content']) for m in payload['messages'] if m['role']=='tool']
        directory=packet['evidence_directory']
        entries=list(directory['inline_entries'])
        for page in pages:
            if page.get('source')==directory['reference'] and page.get('kind')=='content':
                content=page['content'];entries.extend(content if isinstance(content,list) else [content])
        def read(query):
            return native(payload['tools'][1]['function']['name'],dict(arguments=query,
                reason='Read a bounded page from the actual request scope',tool_version='1.0.0'))
        def finish(**values):
            return native('investigation_return',dict(interpretation='Deterministic offline interface script; semantic reasoning unassessed',**values))
        if packet['role']=='coordinator':
            source=next(e['reference'] for e in entries if e['material']=='free_reach')
            children=[]
            for name,pointer in [('reach','/terminal_error_m'),('timing','/deadline_misses')]:
                children.append(dict(investigation_id=packet['investigation_id']+'-'+name,
                    parent_id=packet['investigation_id'],role='investigator',question='Inspect '+pointer,
                    evidence=[source],queries=[],allowed_tools=packet['allowed_tools'],
                    budget=packet['delegation_budget_limit'],timeout_s=packet['timeout_s'],
                    stop_conditions=packet['stopping'],output_bytes=packet['output_bytes']))
            if packet['question']=='Coordinate widening':children[0]['evidence'].append(directory['reference'])
            return finish(children=children,unknowns=['Body not prefetched; children must inspect sources'])
        if packet['role']=='principal':
            targets=packet['disposition_targets']
            reads=[*packet['reads'],*packet['principal_inspection_records']]
            decisions=[]
            for target in targets:
                report=next(r['page']['content'] for r in reads if r['reference']==target['report'] and r['pointer']=='/facts')
                scope=next(r for r in reads if r['pointer']=='/result_type' and r['reference']==report[0]['reference'])
                decisions.append(dict(**target,disposition='accept',reason='Retain inspected saved observation within declared scope',
                    adopted_claims=[dict(statement='Saved observation applies to its original execution',supporting_facts=report,
                        scope=[fact(scope['reference'],scope['pointer'],scope['page']['content'])],
                        support_explanation='Source and scope fields are inspected; causal explanation remains unassessed')],
                    remaining_unknowns=['Real model behavior and diagnostic benefit untested']))
            return finish(dispositions=decisions)
        if packet['question']=='Find unshown material':
            target=next((e for e in entries if e.get('identity_and_version',{}).get('result_type')=='late_counterevidence'),None)
            if target is None:
                catalog_pages=[p for p in pages if p.get('source')==directory['reference']]
                query=deepcopy(directory['query'])
                if catalog_pages:query['offset']=catalog_pages[-1]['next_offset']
                if query['offset'] is None:return finish(completion='incomplete',unknowns=['Requested material not found in complete directory'])
                return read(query)
            pointer='/observed';source=target['reference']
        elif packet['question']=='Probe unknown reference':
            if pages:return finish(unknowns=[pages[-1]['error']],completion='incomplete')
            # A deliberately malformed/unrecognized reference derived from the
            # visible directory identity, not a hidden fixture source.
            source=deepcopy(entries[0]['reference']);source['artifact_id']=('1' if source['artifact_id'][0]=='0' else '0')+source['artifact_id'][1:]
            return read(dict(reference=source,pointer=''))
        elif packet['question']=='Probe unavailable reference':
            source=next(e['reference'] for e in entries if e['availability']=='unavailable')
            if pages:return finish(unknowns=[pages[-1]['error']],completion='incomplete')
            return read(dict(reference=source,pointer=''))
        else:
            source=entries[0]['reference']
            pointer=packet['question'].removeprefix('Inspect ')
            if not pointer.startswith('/'):
                pointer='/deadline_misses' if 'complete-update' in packet['question'] else '/terminal_error_m'
        actual=[p for p in pages if p.get('source')==source and p.get('pointer')==pointer]
        if not actual:return read(dict(reference=source,pointer=pointer,byte_limit=4096))
        return finish(facts=[fact(source,pointer,actual[-1]['content'])],unknowns=['No new causal evidence'],proposed_next_checks=['Separate authorization required for real validation'])


class EvidenceDiscoveryTests(TestCase):
    setUp=Mainline3EngineeringTests.setUp
    isolated_host=Mainline3EngineeringTests.isolated_host
    order=Mainline3EngineeringTests.order

    def host(self):
        host,ref=self.isolated_host(80,session_budget={**zero(),'model_calls':80,'tool_calls':512,'wall_s':1500.})
        with host.store.transaction() as db:
            state=host.store.session(host.run_id,db)['state'];grant=state['role_context']['investigation_grant']
            grant.update(include_completed_reports=True,deadline_unix=time.time()+3600,
                per_node_budget={**zero(),'model_calls':24,'tool_calls':24,'wall_s':60.},
                total_budget={**zero(),'model_calls':80,'tool_calls':120,'wall_s':300.})
            host.store.update_state(db,host.run_id,state)
        return host,ref

    def public(self,host,tool,args,key):
        receipt=invoke(host,tool,args,request_id=key)
        self.assertEqual(receipt['execution_status'],'completed',receipt.get('error'))
        return receipt,host.store.artifact(receipt['output'])

    def collect(self,host,key):
        for i in range(100):
            _,result=self.public(host,'research.investigation_status',dict(investigation_id=key),'status-'+key+'-'+str(i))
            if result['status'] not in ('pending','running'):return result
            time.sleep(.01)
        self.fail('Bounded status collection exhausted')

    def run_order(self,host,order,transport):
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport):
            self.public(host,'research.investigate',order,'submit-'+order['investigation_id'])
            return self.collect(host,order['investigation_id'])

    def capture(self,label,host,transport=None,**details):
        state=host.store.session(host.run_id)['state']
        refs=list(state['role_context']['investigation_grant']['evidence'])
        for node in state.get('investigations',{}).values():refs.extend(node[k] for k in ('result','directory','disposition_record') if node.get(k))
        for event in host.store.events(host.run_id):refs.extend(event['outputs'])
        for ref in refs:
            try:ARTIFACTS[ref['artifact_id']]=host.store.artifact(ref)
            except ValueError:pass
        OBSERVATIONS[label]=dict(nodes=state.get('investigations',{}),
            principal_reads=state.get('principal_investigation_reads',[]),ledger=host.store.remaining(),
            actual_requests=transport.sent if transport else [],**details)

    def test_wire_only_direct_and_coordinated_delivery(self):
        from tools.research_mainline3 import live_interface_scenario,interface_proposal
        for mode in ('direct','coordinated'):
            proposal=interface_proposal(mode)
            host,_=self.isolated_host(proposal['project_budget']['model_calls'],session_budget=proposal['project_budget'],operation_allowances=proposal['operation_allowances'])
            transport=WireOnlyTransport()
            with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport):result=live_interface_scenario(host,mode)
            self.assertEqual(result['status'],'formal_dispositions_recorded',result)
            self.assertEqual(len(result['dispositions']),2)
            if mode=='coordinated':
                packet=json.loads(transport.sent[0]['messages'][1]['content'])
                self.assertEqual(packet['reads'],[])
                self.assertEqual(packet['evidence_directory']['inline_entries'][0]['material'],'free_reach')
                self.assertTrue(all(not n['order']['queries'] for n in host.store.session(host.run_id)['state']['investigations'].values() if n['order']['parent_id']))
            for ref in result['dispositions']:
                record=host.store.artifact(ref);self.assertTrue(record['inspection_links'])
                self.assertIn('unassessed',record['semantic_correctness'])
            self.capture('wire_'+mode,host,transport,result=result)

    def test_growth_pages_unshown_counterevidence(self):
        host,ref=self.host()
        with host.store.transaction() as db:
            refs=[plain(host.store.put(db,dict(result_type='catalog_fixture',run_id='fixture-'+str(i),observed=i))) for i in range(15)]
            refs.append(plain(host.store.put(db,dict(result_type='late_counterevidence',run_id='offline-synthetic',observed=False))))
            state=host.store.session(host.run_id,db)['state'];state['role_context']['investigation_grant']['evidence']=refs
            host.store.update_state(db,host.run_id,state)
        order=self.order('growth',ref);order.update(question='Find unshown material',evidence=refs,queries=[],budget={**zero(),'model_calls':24,'tool_calls':24,'wall_s':60.})
        transport=WireOnlyTransport();result=self.run_order(host,order,transport)
        self.assertEqual(result['status'],'completed',result)
        self.assertNotIn(refs[-1]['artifact_id'],json.dumps(transport.sent[0]))
        report=host.store.artifact(result['result']);self.assertEqual(report['facts'][0]['reference'],refs[-1])
        self.assertIs(report['facts'][0]['value'],False)
        self.assertGreater(len(transport.sent),2)
        self.capture('growth',host,transport,result=result)

    def test_unknown_unavailable_and_child_widening(self):
        host,ref=self.host()
        missing=dict(artifact_id='f'*64,media_type='application/json')
        with host.store.transaction() as db:
            outside=plain(host.store.put(db,dict(result_type='authorized_other_scope',observed='offline fixture')))
            state=host.store.session(host.run_id,db)['state'];state['role_context']['investigation_grant']['evidence'].extend([missing,outside])
            host.store.update_state(db,host.run_id,state)
        for key,question,evidence,reason in [('unknown','Probe unknown reference',[ref],'QUERY_SOURCE_OUT_OF_SCOPE')]:
            order=self.order(key,ref);order.update(question=question,evidence=evidence,queries=[],budget={**zero(),'model_calls':2,'tool_calls':2,'wall_s':60.})
            transport=WireOnlyTransport();result=self.run_order(host,order,transport)
            self.assertEqual(result['status'],'incomplete',result)
            self.assertIn(reason,host.store.artifact(result['result'])['unknowns'][0])
            self.capture(key,host,transport,result=result)
        unavailable_order=self.order('missing',missing);unavailable_order['queries']=[]
        unavailable=invoke(host,'research.investigate',unavailable_order,request_id='missing-public')
        self.assertEqual(unavailable['execution_status'],'rejected')
        self.assertIn('EVIDENCE_MISSING_OR_CHANGED',unavailable['error'])
        self.capture('unavailable',host,rejection=unavailable,provider_attempts=0)
        coordinator=self.order('narrow',ref,role='coordinator');coordinator.update(queries=[],budget={**zero(),'model_calls':2,'tool_calls':2,'wall_s':60.})
        transport=WireOnlyTransport();result=self.run_order(host,coordinator,transport)
        child=host.store.artifact(result['result'])['children'][0];child['evidence'].append(outside)
        denied=invoke(host,'research.investigate',child,request_id='widen-child')
        self.assertNotEqual(denied['execution_status'],'completed');self.assertIn('CHILD_NOT_REQUESTED',denied['error'])
        illegal=deepcopy(coordinator);illegal.update(investigation_id='illegal-return',question='Coordinate widening')
        widened=self.run_order(host,illegal,transport)
        self.assertEqual(widened['status'],'failed',widened)
        self.assertIn('CHILD_EVIDENCE_SCOPE_EXCEEDED',widened['reason'])
        self.capture('widening',host,transport,rejection=denied,return_rejection=widened)

    def test_complete_request_overflow_and_unread_adoption(self):
        host,ref=self.host();order=self.order('checks',ref)
        order.update(queries=[],question='Inspect /terminal_error_m',budget={**zero(),'model_calls':2,'tool_calls':2,'wall_s':60.})
        transport=WireOnlyTransport();result=self.run_order(host,order,transport)
        self.assertEqual(result['status'],'completed',result)
        from tools.context_assembly import check_outgoing_request
        from tools.platform_models import effective_config
        payload=deepcopy(transport.sent[-1]);payload['messages'].append(dict(role='tool',tool_call_id='overflow',content=encode(dict(counterevidence='X'*170000))))
        with self.assertRaisesRegex(ValueError,'CONTEXT_SEND_BOUNDARY_OVERFLOW') as error:check_outgoing_request(payload,effective_config(host),'research_decision')
        returned=host.store.artifact(result['result'])['facts']
        decision=dict(investigation_id='checks',report=result['result'],disposition='accept',reason='Attempt unread adoption',adopted_claims=[dict(statement='Saved observation',supporting_facts=returned,scope=returned,support_explanation='Interface fixture')])
        denied=invoke(host,'research.investigation_disposition',decision,request_id='unread-accept')
        self.assertIn('PRINCIPAL_MUST_INSPECT',denied['error'])
        # Overflow on the actual second send includes prior assistant reasoning,
        # its native call and returned page, schemas, metadata and output reserve.
        overflow_order=deepcopy(order);overflow_order['investigation_id']='overflow'
        overflowing=WireOnlyTransport()
        def inflated(adapter,config,payload):
            raw=overflowing(config,payload)
            raw['choices'][0]['message']['reasoning_content']='X'*170000
            return raw
        failed=self.run_order(host,overflow_order,inflated)
        self.assertEqual(failed['status'],'failed');self.assertIn('CONTEXT_SEND_BOUNDARY_OVERFLOW',failed['reason'])
        self.assertEqual(len(overflowing.sent),1)
        self.assertEqual(host.store.session(host.run_id)['state']['investigations']['overflow']['usage']['model_calls'],1)
        self.capture('overflow_and_adoption',host,transport,overflow=str(error.exception),unread_accept=denied,actual_overflow=failed)

    def test_fresh_process_recovery_authority_budget_and_stop(self):
        host,ref=self.host();order=self.order('restore',ref)
        order.update(queries=[],question='Inspect /terminal_error_m',budget={**zero(),'model_calls':2,'tool_calls':2,'wall_s':60.})
        transport=WireOnlyTransport();result=self.run_order(host,order,transport)
        self.assertEqual(result['status'],'completed',result)
        state=host.store.session(host.run_id)['state'];directory=state['investigations']['restore']['directory']
        # Only durable process context is passed. This process has no provider
        # substitute, cannot redispatch, and uses public status and read entries.
        script='''import json,sys,time
from pathlib import Path
from unittest.mock import patch
from tools.platform_host import Host
from tools.research_execution import invoke
from tools.platform_store import plain
context=json.loads(sys.argv[1])
with patch('tools.platform_store.ROOT',Path(context['authority_root'])), patch('tools.platform_models.DeepSeekAdapter._transport',side_effect=AssertionError('NO_REDISPATCH')):
 host=Host(context['store'],context['run'])
 before=host.store.remaining()
 state=host.store.session(host.run_id)['state'];node=state['investigations']['restore']
 status=invoke(host,'research.investigation_status',{'investigation_id':'restore'},request_id='process-status-'+context['phase'])
 ref=node['directory']
 read=invoke(host,'research.investigation_read',{'reference':ref,'pointer':'/entries','limit':1},request_id='process-read-'+context['phase'])
 print(json.dumps(dict(status=status,read=read,page=host.store.artifact(read['output']) if read.get('output') else None,before=before,after=host.store.remaining(),session_status=host.store.session(host.run_id)['status'])))
'''
        context=dict(store=str(host.store.root),authority_root=str(host.store.root.parent),run=host.run_id)
        def child(phase):
            completed=subprocess.run([sys.executable,'-c',script,json.dumps(dict(context,phase=phase))],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=60)
            self.assertEqual(completed.returncode,0,completed.stderr);return json.loads(completed.stdout)
        active=child('active');self.assertEqual(active['status']['execution_status'],'completed')
        self.assertEqual(active['page']['content'][0]['reference'],ref)
        self.assertEqual(active['before']['used']['model_calls'],active['after']['used']['model_calls'])
        # Advance the clock in the new process only; the frozen grant is retained.
        expired_script=script.replace("host=Host(context['store'],context['run'])","host=Host(context['store'],context['run'])\n time.time=lambda: context['as_of']")
        completed=subprocess.run([sys.executable,'-c',expired_script,json.dumps(dict(context,phase='expired',as_of=time.time()+7200))],capture_output=True,text=True,timeout=60)
        self.assertEqual(completed.returncode,0,completed.stderr);expired=json.loads(completed.stdout)
        self.assertIn('DEADLINE_EXPIRED',expired['read']['error']);self.assertIn('DEADLINE_EXPIRED',expired['status']['error'])
        with host.store.transaction() as db:
            state=host.store.session(host.run_id,db)['state'];state['stop_reason']='OFFLINE_FIXTURE_STOP'
            host.store.update_state(db,host.run_id,state,'stopped')
        stopped=child('stopped');self.assertEqual(stopped['session_status'],'stopped')
        self.assertNotEqual(stopped['read']['execution_status'],'completed')
        self.assertEqual(host.store.artifact(directory)['entries'][0]['reference'],ref)
        self.capture('fresh_process',host,transport,active=active,expired=expired,stopped=stopped)


if __name__=='__main__':
    import unittest
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(EvidenceDiscoveryTests))
    write_bundle(Path(__file__).resolve().parents[1]/'evidence/research_evidence_discovery_20261008/offline_verification.json',
        dict(date='2026-10-08',boundary='WireOnlyTransport takes only actual outgoing payload and lawful tool responses; deterministic interface scripts, no real model autonomy',
            command='python -m tests.test_research_evidence_discovery',checks_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
            real_provider_requests=0,scientific_executions=0,observations=OBSERVATIONS,artifacts=ARTIFACTS))
    raise SystemExit(not result.wasSuccessful())
