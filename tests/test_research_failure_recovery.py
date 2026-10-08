"""Public offline failure/recovery checks; no imported historical test classes."""
from contextlib import ExitStack, redirect_stderr
from copy import deepcopy
from io import BytesIO, StringIO
from pathlib import Path
from threading import Event
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import errno
import json
import socket
import ssl
import shutil
import subprocess
import sys
import time
from uuid import uuid4

from tools.state_io import read, atomic_json
from tools.platform_store import Store, plain, zero, encode
from tools.platform_host import Host
from tools.research_execution import invoke
from tools.model_transports.deepseek import request_completion

ROOT=Path(__file__).resolve().parents[1]
OBSERVATIONS={}
SECRET='FAKE_SECRET_MUST_NOT_PERSIST_9b25'


def native():
    return dict(id='completion-fixture-1',usage=dict(prompt_tokens=11,completion_tokens=7,total_tokens=18),
        choices=[dict(finish_reason='tool_calls',message=dict(role='assistant',content=None,
            tool_calls=[dict(id='native-fixture-1',type='function',function=dict(name='investigation_return',
                arguments=json.dumps(dict(interpretation='Synthetic offline report',unknowns=['No scientific conclusion']))))]))])


class FakeResponse:
    status=200
    headers={'x-request-id':'provider-fixture-17','Authorization':'Bearer '+SECRET}
    def __init__(self,body=None):self.body=json.dumps(native()).encode() if body is None else body
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self):return self.body


class InvestigationFailureRecoveryTests(TestCase):
    def setUp(self):
        self.blocks=ExitStack();self.addCleanup(self.blocks.close)
        for target in ('tools.platform_models.DeepSeekAdapter._transport',
                       'urllib.request.OpenerDirector.open',
                       'examples.gvs_nmpc_route_experiment.load_credential',
                       'extensions.optimization.ipopt.IpoptSolver.solve',
                       'scipy.optimize.least_squares','scipy.optimize.minimize',
                       'scipy.integrate.solve_ivp','extensions.tendon_family.backends.MujocoBackend.solve'):
            self.blocks.enter_context(patch(target,side_effect=AssertionError('PROHIBITED_OFFLINE_BOUNDARY')))
        self.folder=ROOT/'runs'/('failure-recovery-fixture-'+uuid4().hex)
        self.folder.mkdir()
        self.addCleanup(self.clean)
        self.blocks.enter_context(patch('tools.platform_store.ROOT',self.folder))
        self.new_host()

    def new_host(self,suffix='default'):
        cfg=read(ROOT/'evidence/research_mainline3_validation_20261008/frozen_configuration.json')
        cfg['run_id']='failure-offline'
        cfg['policy']['route']=None
        tools=['research.investigate','research.investigation_status','research.investigation_read','research.investigation_disposition']
        cfg['policy'].update(allowed_tools=tools,tool_bindings={t:'1.0.0' for t in tools},
            budget={**zero(),'model_calls':12,'tool_calls':512,'wall_s':1200.},timeout_s=30.,
            operation_allowances={t:dict(reserve_s=5.,timeout_s=30.) for t in tools})
        self.store=Store(self.folder/('store-'+suffix))
        self.store.create(dict(project_id='offline-'+uuid4().hex,grant_id='offline-'+uuid4().hex,
            authorization_source='Isolated deterministic offline failure fixture; no credentials/network/science',
            budget=cfg['policy']['budget']))
        self.host=Host(self.store.root,cfg['run_id']);self.host.create(cfg);self.host.resume()
        with self.store.transaction() as db:
            self.ref=plain(self.store.put(db,dict(result_type='offline_fixture',observed=3)))
            state=self.store.session(self.host.run_id,db)['state']
            state['role_context']=dict(investigation_grant=dict(max_count=6,max_concurrency=2,
                allowed_tools=['evidence.read'],evidence=[self.ref],deadline_unix=time.time()+600,
                per_node_budget={**zero(),'model_calls':2,'tool_calls':2,'wall_s':60.},
                total_budget={**zero(),'model_calls':12,'tool_calls':12,'wall_s':360.}))
            self.store.update_state(db,self.host.run_id,state)

    def clean(self):
        import gc
        gc.collect()  # sqlite context managers end transactions; collect closed readers on Windows.
        if not self.folder.resolve().is_relative_to((ROOT/'runs').resolve()):raise ValueError('OUTSIDE_FIXTURE')
        shutil.rmtree(self.folder)

    def order(self,key):
        return dict(investigation_id=key,question='Inspect an isolated saved observation; no science',
            evidence=[self.ref],queries=[],allowed_tools=['evidence.read'],
            budget={**zero(),'model_calls':2,'tool_calls':2,'wall_s':60.},timeout_s=30.,
            stop_conditions=['One bounded report; no retry'])

    def public(self,tool,args,key):
        receipt=invoke(self.host,tool,args,request_id=key)
        self.assertEqual(receipt['execution_status'],'completed',receipt.get('error'))
        return self.store.artifact(receipt['output'])

    def wait_owner(self,key):
        from tools.workbench import owner
        for _ in range(200):
            try:
                with owner(self.host.folder,'.investigation-'+key+'.lock'):return
            except OSError:time.sleep(.01)
        self.fail('Thread did not release fixture owner lock')

    def run_order(self,key,transport):
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=transport):
            self.public('research.investigate',self.order(key),'submit-'+key)
            self.wait_owner(key)
        return self.public('research.investigation_status',dict(investigation_id=key),'collect-'+key)

    def capture(self,label):
        state=self.store.session(self.host.run_id)['state']
        events=self.store.events(self.host.run_id)
        selected=[e for e in events if e['kind'].startswith('investigation_') or e['kind']=='recovery']
        refs=[r for e in selected for r in e['outputs']]
        artifacts={r['artifact_id']:self.store.artifact(r) for r in refs}
        with self.store.connect(True) as db:
            alltext='\n'.join(bytes(r['body']).decode() for r in db.execute('SELECT body FROM artifacts'))
            self.assertNotIn(SECRET,alltext)
            calls=[]
            for item in db.execute('SELECT request_id,status,reserved,charged,receipt FROM calls ORDER BY rowid'):
                row=dict(item)
                for k in ('reserved','charged','receipt'):
                    if row[k] is not None:row[k]=json.loads(row[k])
                calls.append(row)
        OBSERVATIONS[label]=dict(nodes=state.get('investigations'),events=selected,artifacts=artifacts,
            ledger=self.store.remaining(),calls=calls,substitute='DeepSeekAdapter._transport or named fault point only; no real request',
            fake_secret_absent=True)

    def transport(self,result=None,error=None):
        def send(adapter,config,payload):
            if error:raise error
            return deepcopy(result if result is not None else native())
        return send

    def test_connection_http_and_timeout_preserve_existing_transport_details(self):
        for key,error in [('connection',URLError(ConnectionRefusedError(errno.ECONNREFUSED,'Authorization: Bearer '+SECRET))),
                          ('dns',URLError(socket.gaierror(-2,'password='+SECRET))),
                          ('tls',URLError(ssl.SSLError('access_token='+SECRET))),
                          ('http',HTTPError('https://api.deepseek.com/chat/completions',429,'rejected',
                              {'x-request-id':'provider-rejected-29','Authorization':'Bearer '+SECRET},BytesIO(('password='+SECRET).encode()))),
                          ('timeout',URLError(TimeoutError('access_token='+SECRET)))]:
            self.new_host(key)  # Each unconfirmed node retains its own concurrency slot and escrow.
            def send(adapter,config,payload,error=error):
                class Opener:
                    def open(self,*args,**kwargs):raise error
                with patch('tools.model_transports.deepseek.build_opener',return_value=Opener()):
                    return request_completion(config,payload,'fixture-auth-only')
            result=self.run_order(key,send)
            failure=self.store.artifact(result['failure_record'])
            self.assertEqual(failure['details']['category'],key if key!='http' else 'http')
            self.assertEqual(failure['exception_type'],'RuntimeError')
            self.assertEqual(failure['details']['exception_type'],'HTTPError' if key=='http' else 'URLError')
            if key=='http':
                self.assertTrue(failure['progress']['response_received'])
                self.assertEqual(failure['details']['http_status'],429)
                self.assertEqual(failure['details']['provider_request_id'],'provider-rejected-29')
                self.assertEqual(result['status'],'failed')
            else:
                self.assertIsNone(failure['progress']['response_received'])
                self.assertEqual(result['status'],'unconfirmed')
                self.assertEqual(self.store.lookup(self.host.run_id,'investigation-'+key)['status'],'unknown')
            self.capture(key)

    def test_received_response_parse_failure_is_distinct(self):
        malformed=dict(choices=[dict(message=dict(tool_calls=[]))])
        result=self.run_order('native-parse',self.transport(malformed))
        failure=self.store.artifact(result['failure_record'])
        self.assertEqual(result['status'],'failed')
        self.assertEqual(failure['progress']['stage'],'response_parse')
        self.assertTrue(failure['progress']['response_received'])
        self.assertTrue(failure['progress']['response_saved'])
        self.assertFalse(failure['progress']['valid_report'])
        self.capture('native_parse')
        def send(adapter,config,payload):
            class Opener:
                def open(self,*args,**kwargs):return FakeResponse(b'{malformed response')
            with patch('tools.model_transports.deepseek.build_opener',return_value=Opener()):
                return request_completion(config,payload,'fixture-auth-only')
        result=self.run_order('wire-parse',send)
        failure=self.store.artifact(result['failure_record'])
        self.assertTrue(failure['progress']['response_received'])
        self.assertFalse(failure['progress']['response_saved'])
        self.assertEqual(failure['details']['transport_stage'],'response_parse')
        self.assertEqual(failure['details']['exception_type'],'JSONDecodeError')
        self.capture('wire_parse')

    def test_headers_then_disconnect_keeps_unknown_completion_and_usage(self):
        def send(adapter,config,payload):
            class Response(FakeResponse):
                def read(self):raise ConnectionResetError(errno.ECONNRESET,'Authorization: Bearer '+SECRET)
            class Opener:
                def open(self,*args,**kwargs):return Response()
            with patch('tools.model_transports.deepseek.build_opener',return_value=Opener()):
                return request_completion(config,payload,'fixture-auth-only')
        result=self.run_order('headers-disconnect',send)
        failure=self.store.artifact(result['failure_record'])
        self.assertEqual(result['status'],'unconfirmed')
        self.assertTrue(result['progress']['response_received'])
        self.assertIsNone(result['progress']['response_body_received'])
        self.assertEqual(failure['details']['http_status'],200)
        self.assertEqual(failure['details']['category'],'connection')
        self.assertEqual(failure['details']['provider_request_id'],'provider-fixture-17')
        self.capture('headers_disconnect')
        response=native();response['usage']={}
        result=self.run_order('usage-unknown',self.transport(response))
        self.assertEqual(result['status'],'completed')
        self.assertFalse(result['progress']['actual_usage_known'])
        self.capture('usage_unknown')

    def test_local_preparation_and_missing_saved_report_do_not_hide_failure(self):
        with patch('tools.context_assembly.check_outgoing_request',side_effect=ValueError('api_key='+SECRET)):
            result=self.run_order('preparation',self.transport())
        self.assertEqual(result['status'],'failed')
        self.assertFalse(result['progress']['transport_attempted'])
        self.assertFalse(result['progress']['response_received'])
        self.assertEqual(self.store.artifact(result['failure_record'])['progress']['stage'],'request_preparation')
        self.capture('preparation')
        fail=Event();original=Store.complete
        def incomplete_settlement(store,row,*args,**kwargs):
            if row['caller']=='investigation-dispatcher' and not fail.is_set():
                fail.set();raise OSError('storage unavailable')
            return original(store,row,*args,**kwargs)
        with patch.object(Store,'complete',new=incomplete_settlement),patch('tools.platform_models.DeepSeekAdapter._transport',new=self.transport()):
            self.public('research.investigate',self.order('saved-report'),'submit-saved-report');self.wait_owner('saved-report')
        prior=next(e['outputs'][0] for e in self.store.events(self.host.run_id) if e['kind']=='investigation_response' and e['status']=='validated')
        artifact=Store.artifact
        def unavailable(store,ref,*args,**kwargs):
            if plain(ref)==prior:raise OSError('password='+SECRET)
            return artifact(store,ref,*args,**kwargs)
        before=json.loads(self.store.lookup(self.host.run_id,'investigation-saved-report')['charged'])
        with patch.object(Store,'artifact',new=unavailable):
            result=self.public('research.investigation_status',dict(investigation_id='saved-report'),'collect-unavailable')
        self.assertEqual(result['status'],'unconfirmed')
        self.assertEqual(json.loads(self.store.lookup(self.host.run_id,'investigation-saved-report')['charged']),before)
        self.assertEqual(self.public('research.investigation_status',dict(investigation_id='saved-report'),'collect-restored')['status'],'completed')
        self.capture('saved_report_unavailable')

    def test_response_report_save_and_settlement_faults_do_not_redispatch(self):
        original_put=Store.put;original_complete=Store.complete
        for key,stage in [('response-save','response_evidence_save'),('report-save','report_evidence_save'),('settle','settlement')]:
            failed=Event();count=[]
            def put(store,db,value,media='application/json'):
                if not failed.is_set() and isinstance(value,dict) and (
                    (key=='response-save' and 'choices' in value) or (key=='report-save' and {'report','elapsed_s'}<=value.keys())):
                    failed.set();raise OSError('password='+SECRET)
                return original_put(store,db,value,media)
            def complete(store,row,*args,**kwargs):
                if key=='settle' and row['caller']=='investigation-dispatcher' and not failed.is_set():
                    failed.set();raise OSError('password='+SECRET)
                return original_complete(store,row,*args,**kwargs)
            def send(adapter,config,payload):count.append(1);return native()
            with patch.object(Store,'put',new=put),patch.object(Store,'complete',new=complete),patch('tools.platform_models.DeepSeekAdapter._transport',new=send):
                self.public('research.investigate',self.order(key),'submit-'+key)
                self.wait_owner(key)
            node=self.store.session(self.host.run_id)['state']['investigations'][key]
            failure=self.store.artifact(node['failure_record'])
            self.assertEqual(failure['progress']['stage'],stage)
            self.assertTrue(failure['progress']['response_received'])
            self.assertEqual(failure['progress']['response_saved'],key!='response-save')
            self.assertEqual(failure['progress']['valid_report'],key!='response-save')
            result=self.public('research.investigation_status',dict(investigation_id=key),'collect-'+key)
            self.assertEqual(result['status'],'unconfirmed' if key=='response-save' else 'completed')
            self.assertEqual(len(count),1)
            if key!='response-save':
                self.assertTrue(result['progress']['settlement_completed'])
                self.assertEqual(json.loads(self.store.lookup(self.host.run_id,'investigation-'+key)['charged'])['model_calls'],1)
            self.capture(key)

    def test_failure_record_write_failure_has_bounded_stderr_fallback(self):
        original=Store.put;stderr=StringIO()
        def put(store,db,value,media='application/json'):
            if isinstance(value,dict) and value.get('version')=='investigation_failure@1.0.0':
                raise OSError('access_token='+SECRET)
            return original(store,db,value,media)
        error=ConnectionResetError('Authorization: Bearer '+SECRET)
        with redirect_stderr(stderr),patch.object(Store,'put',new=put):
            result=self.run_order('diagnostic-save',self.transport(error=error))
        self.assertEqual(result['status'],'unconfirmed')
        self.assertIsNone(result['failure_record'])
        fallback=json.loads(stderr.getvalue().splitlines()[0])
        self.assertTrue(fallback['persistence_failed'])
        self.assertEqual(fallback['exception_type'],'ConnectionResetError')
        self.assertNotIn(SECRET,stderr.getvalue())
        self.capture('diagnostic_save');OBSERVATIONS['diagnostic_save']['stderr']=fallback

    def test_processing_failure_then_settlement_failure_keeps_both_causes(self):
        original=Store.complete;fail=Event()
        def complete(store,row,*args,**kwargs):
            if row['caller']=='investigation-dispatcher' and not fail.is_set():
                fail.set();raise OSError('api_key='+SECRET)
            return original(store,row,*args,**kwargs)
        malformed=dict(choices=[dict(message=dict(tool_calls=[]))])
        with patch.object(Store,'complete',new=complete),patch('tools.platform_models.DeepSeekAdapter._transport',new=self.transport(malformed)):
            self.public('research.investigate',self.order('two-failures'),'submit-two-failures');self.wait_owner('two-failures')
        node=self.store.session(self.host.run_id)['state']['investigations']['two-failures']
        second=self.store.artifact(node['failure_record'])
        self.assertEqual(second['progress']['stage'],'settlement')
        first=self.store.artifact(second['progress']['related_failure_record'])
        self.assertEqual(first['progress']['stage'],'response_parse')
        self.assertEqual(self.store.lookup(self.host.run_id,'investigation-two-failures')['status'],'unknown')
        result=self.public('research.investigation_status',dict(investigation_id='two-failures'),'collect-two-failures')
        self.assertEqual(result['status'],'failed')
        self.assertTrue(result['progress']['settlement_completed'])
        self.assertEqual(json.loads(self.store.lookup(self.host.run_id,'investigation-two-failures')['charged'])['model_calls'],1)
        self.capture('processing_then_settlement')

    def test_malicious_metadata_allowlist_and_response_secret_guard(self):
        error=RuntimeError('raw-private-'+SECRET)
        error.provider_response=dict(status_code=403,body=SECRET,headers={'Authorization':SECRET},
            failure_details=dict(category='http',exception_type='HTTPError',reason_type='HTTPError',
                reason_message='api_key='+SECRET,password=SECRET,environment={'HOME':SECRET}))
        error.transport_state=dict(response_received=True,transport_attempted=True,provider_request_id='safe-provider-31',password=SECRET)
        result=self.run_order('metadata',self.transport(error=error))
        failure=self.store.artifact(result['failure_record'])
        self.assertNotIn(SECRET,encode(failure));self.assertNotIn('body',failure['details'])
        self.assertEqual(failure['details']['provider_request_id'],'safe-provider-31')
        self.capture('allowlist')
        response=native();response['api_key']=SECRET
        result=self.run_order('body-secret',self.transport(response))
        self.assertEqual(result['status'],'unconfirmed')
        self.assertTrue(result['progress']['response_received'])
        self.assertFalse(result['progress']['response_saved'])
        self.capture('body_secret')
        response=native()
        arguments=json.loads(response['choices'][0]['message']['tool_calls'][0]['function']['arguments'])
        arguments['api_key']=SECRET
        response['choices'][0]['message']['tool_calls'][0]['function']['arguments']=json.dumps(arguments)
        result=self.run_order('native-secret',self.transport(response))
        self.assertEqual(result['status'],'unconfirmed')
        self.assertFalse(result['progress']['response_saved'])
        self.capture('native_secret')

    def test_live_owner_is_running_and_launch_failure_is_local(self):
        entered=Event();release=Event()
        def pending(adapter,config,payload):
            entered.set()
            if not release.wait(10):raise AssertionError('Fixture release missing')
            return native()
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=pending):
            self.public('research.investigate',self.order('live'),'submit-live')
            try:
                self.assertTrue(entered.wait(10))
                result=self.child('collect','live')
                self.assertEqual(result['status'],'running')
                self.assertIsNone(self.store.lookup(self.host.run_id,'investigation-live')['receipt'])
            finally:release.set();self.wait_owner('live')
        self.capture('live_owner')
        with patch('tools.research_investigations.Thread.start',side_effect=RuntimeError('api_key='+SECRET)):
            result=self.public('research.investigate',self.order('launch'),'submit-launch')
        self.assertEqual(result['status'],'failed')
        self.assertFalse(result['progress']['transport_attempted'])
        failure=self.store.artifact(result['failure_record'])
        self.assertEqual(failure['progress']['stage'],'investigation_launch')
        self.capture('launch_failure')

    def child(self,action,key):
        result=subprocess.run([sys.executable,'-m','tests.test_research_failure_recovery','--child',
            action,str(self.store.root),str(self.folder),key],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout.splitlines()[-1])

    def test_process_interruption_fresh_process_and_stopped_authority(self):
        # The child exits only after a real public submission starts its provider substitute.
        self.assertEqual(self.child('interrupt','interrupted')['status'],'thread_active_at_process_exit')
        before=self.store.remaining()['used']
        result=self.child('collect','interrupted')
        self.assertEqual(result['status'],'unconfirmed')
        self.assertIsNone(result['progress']['response_received'])
        row=self.store.lookup(self.host.run_id,'investigation-interrupted')
        self.assertEqual(row['status'],'unknown');self.assertEqual(json.loads(row['charged']),json.loads(row['reserved']))
        self.assertEqual(self.store.remaining()['used']['model_calls'],before['model_calls'])
        with self.store.transaction() as db:
            state=self.store.session(self.host.run_id,db)['state']
            self.store.update_state(db,self.host.run_id,state,status='stopped')
        after=self.store.remaining()['used']
        blocked=self.child('collect','interrupted')
        self.assertEqual(blocked['status'],'denied_stopped')
        self.assertEqual(self.store.session(self.host.run_id)['status'],'stopped')
        self.assertEqual(self.store.remaining()['used'],after)
        self.capture('fresh_process_stopped')

    def test_sealed_result_priority_and_scope_expiry(self):
        original=Store.complete;failure=Event()
        def after_seal(store,row,*args,**kwargs):
            result=original(store,row,*args,**kwargs)
            if row['caller']=='investigation-dispatcher' and not failure.is_set():
                failure.set();raise OSError('password='+SECRET)
            return result
        with patch.object(Store,'complete',new=after_seal):
            result=self.run_order('sealed',self.transport())
        self.assertEqual(result['status'],'completed')
        self.assertTrue(result['progress']['settlement_completed'])
        self.assertEqual(self.child('collect','sealed')['status'],'completed')
        with self.store.transaction() as db:
            state=self.store.session(self.host.run_id,db)['state']
            state['role_context']['investigation_grant']['deadline_unix']=time.time()-1
            from tools.state_io import digest
            state['investigation_grant_identity']=digest(state['role_context']['investigation_grant'])
            self.store.update_state(db,self.host.run_id,state)
        result=invoke(self.host,'research.investigation_status',dict(investigation_id='sealed'),request_id='expired-read')
        self.assertEqual(result['execution_status'],'failed')
        self.assertIn('DEADLINE_EXPIRED',result['error'])
        self.capture('sealed_and_expired')


def child_main(action,root,anchor,key):
    import os
    import tools.platform_store as store_module
    store_module.ROOT=Path(anchor)
    host=Host(Path(root),'failure-offline')
    with patch('tools.platform_models.DeepSeekAdapter._transport',side_effect=AssertionError('NO_REDISPATCH')):
        if action=='collect':
            receipt=invoke(host,'research.investigation_status',dict(investigation_id=key),request_id='fresh-process-'+uuid4().hex)
            result=host.store.artifact(receipt['output']) if receipt.get('output') else dict(status='denied_stopped',error=receipt.get('error'))
            print(encode(result));return
        entered=Event()
        def pending(adapter,config,payload):
            entered.set();Event().wait(20);raise AssertionError('Child should already have exited')
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=pending):
            source=host.store.session(host.run_id)['state']['role_context']['investigation_grant']['evidence'][0]
            order=dict(investigation_id=key,question='Interrupted offline fixture',evidence=[source],queries=[],
                budget={**zero(),'model_calls':2,'tool_calls':2,'wall_s':60.},timeout_s=30.,stop_conditions=['No replay'])
            receipt=invoke(host,'research.investigate',order,request_id='submit-child')
            if receipt['execution_status']!='completed' or not entered.wait(10):raise AssertionError('Submission not active')
            print(encode(dict(status='thread_active_at_process_exit')),flush=True)
            os._exit(0)  # Simulated abrupt owner-process death; no provider response.


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--child':child_main(*sys.argv[2:])
    else:
        import argparse
        parser=argparse.ArgumentParser()
        parser.add_argument('--case',required=True,choices=['InvestigationFailureRecoveryTests'])
        parser.add_argument('--method',action='append')
        args=parser.parse_args()
        import unittest
        suite=unittest.TestSuite(InvestigationFailureRecoveryTests(name) for name in args.method) if args.method else unittest.defaultTestLoader.loadTestsFromTestCase(InvestigationFailureRecoveryTests)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        target=ROOT/'evidence/research_failure_recovery_20261008'
        target.mkdir(parents=True,exist_ok=True)
        existing=list(target.glob('offline_attempt_*.json'))
        atomic_json(target/f'offline_attempt_{len(existing)+1:02d}.json',dict(
            tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
            command='python -m tests.test_research_failure_recovery '+ ' '.join(sys.argv[1:]),
            failure_cases=[name.id() for name,_ in result.failures],error_cases=[name.id() for name,_ in result.errors],
            observations=OBSERVATIONS,real_provider_requests=0,credential_loads=0,scientific_executions=0,
            boundary='Production Host/dispatcher/native parsing/Store/ledger. External transport and explicit persistence fault points substituted. Separate child process performs public interrupted submission and recovery.'))
        sys.exit(0 if result.wasSuccessful() else 1)
