"""Targeted single-entry offline checks; no imported scientific test classes."""
from contextlib import ExitStack
import gc
import json
from pathlib import Path
import shutil
import time
from io import BytesIO
from urllib.error import HTTPError
from unittest import TestCase, main
from unittest.mock import patch
from uuid import uuid4

from tools import research_single_validation as single
from tools.platform_store import plain
from tools.state_io import read, atomic_json

OBSERVATIONS={}


class SinglePublicValidationTests(TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.folder=single.ROOT/'runs'/('single-fixture-'+uuid4().hex)
        self.folder.mkdir();self.addCleanup(self.clean)
        self.stack.enter_context(patch('tools.platform_store.ROOT',self.folder))
        for target in ('tools.platform_models.DeepSeekAdapter._transport',
                'examples.gvs_nmpc_route_experiment.load_credential','urllib.request.OpenerDirector.open',
                'extensions.tendon_family.backends.MujocoBackend.solve',
                'extensions.optimization.ipopt.IpoptSolver.solve','scipy.optimize.minimize',
                'scipy.optimize.least_squares','scipy.integrate.solve_ivp'):
            self.stack.enter_context(patch(target,side_effect=AssertionError('OFFLINE_PROHIBITED')))
        self.out=self.folder/'evidence'
        single.prepare(self.out)
        self.manifest=read(self.out/'validation_manifest.json')
        self.host=single.Host(single.ROOT/self.manifest['store'],self.manifest['activity_id'])
        self.addCleanup(self.clean_store)

    def clean(self):
        gc.collect()
        assert self.folder.resolve().is_relative_to((single.ROOT/'runs').resolve())
        shutil.rmtree(self.folder)

    def clean_store(self):
        thread=single.owned_thread()
        if thread is not None:thread.join(30.)
        gc.collect()
        assert self.host.store.root.is_relative_to(single.ROOT/'runs')
        shutil.rmtree(self.host.store.root)

    def run_native(self,read_more=False,delay=0,mode='native',http_body=None):
        count=[];assembled=[]
        from tools.context_assembly import check_outgoing_request
        from tools.model_transports.deepseek import request_completion
        def check(payload,config,purpose,**kwargs):
            assembled.append(json.loads(json.dumps(payload)))
            return check_outgoing_request(payload,config,purpose,**kwargs)
        def send(adapter,config,payload):
            count.append(json.loads(json.dumps(payload)))
            self.assertEqual(payload['tool_choice'],'auto')
            self.assertEqual(payload['model'],'deepseek-flash')
            self.assertEqual(payload['thinking'],{'type':config['thinking']})
            self.assertEqual(payload.get('reasoning_effort'),config.get('reasoning_effort'))
            if http_body is not None:
                def reject(request,**kwargs):
                    self.assertEqual(json.loads(request.data),payload)
                    raise HTTPError(request.full_url,400,'BadRequest',{'x-request-id':'fixture-provider-id'},BytesIO(http_body))
                with patch('urllib.request.OpenerDirector.open',side_effect=reject):
                    return request_completion(config,payload,'fixture-key-no-credential-loader')
            time.sleep(delay)
            context=json.loads(payload['messages'][1]['content'])
            page=read(self.out/'preparation_gate.json')['visible_reads'][0]
            if read_more:
                name=payload['tools'][1]['function']['name']
                arguments=dict(arguments=dict(reference=page['reference'],pointer='/sampled_settling/passed'),
                    reason='Offline unauthorized follow-up request',tool_version='1.0.0')
            else:
                name='investigation_return'
                arguments=dict(facts=[dict(statement='Recorded settling failed',reference=page['reference'],
                    pointer='/sampled_settling/passed',value=False)],interpretation='Saved sampled record only')
            if mode=='text':
                return dict(choices=[dict(finish_reason='stop',message=dict(role='assistant',
                    content=json.dumps(arguments)))])
            if mode=='invalid':arguments=dict(facts='invalid arguments')
            return dict(usage=dict(prompt_tokens=12,completion_tokens=8,total_tokens=20),
                choices=[dict(finish_reason='tool_calls',message=dict(role='assistant',content=None,
                    tool_calls=[dict(id='offline-call',type='function',function=dict(name=name,arguments=json.dumps(arguments)))]))])
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=send), \
                patch('tools.context_assembly.check_outgoing_request',side_effect=check):
            single.execute(self.out,live=False,schedule=(5,10,15,20,25,30,35),cutoff=40.)
        self.assertEqual(len(count),1)
        self.assertEqual(self.host.store.session(self.host.run_id)['status'],'stopped')
        gate=read(self.out/'gate.json');self.assertTrue(gate['limits_passed'])
        self.assertEqual(gate['recorded_attempts'],1);self.assertEqual(gate['successful_prefetch_count'],1)
        self.assertEqual(gate['followup_read_count'],0)
        self.assertTrue(gate['compatible_actual_requests'])
        self.assertTrue(all(p['tool_choice']=='auto' and p['thinking']==count[0]['thinking'] for p in assembled))
        if read_more:self.assertGreaterEqual(len(assembled),2)
        self.assertLessEqual(gate['public_operation_count'],8)
        self.assertLessEqual(self.host.store.remaining()['used']['tool_calls'],9)
        self.assertTrue(read(self.out/'historical_after.json')['unchanged'])
        OBSERVATIONS[self._testMethodName]=dict(gate=gate,lifecycle=read(self.out/'application_lifecycle.json'),
            ledger=self.host.store.remaining(),node=read(self.out/'bundle.json')['state']['investigations'],
            assembled_request_settings=[{k:p.get(k) for k in ('model','tool_choice','thinking','reasoning_effort','max_tokens')}
                for p in assembled],real_provider_requests=0,credential_loads=0,science=0)
        with self.assertRaisesRegex(ValueError,'NO_REPEATED_LAUNCH'):single.execute(self.out,live=False)
        return read(self.out/'delivery_report.json')

    def test_single_report_seals_and_stops(self):
        report=self.run_native()
        self.assertEqual(report['结果'],'completed')
        self.assertTrue(report['本次门禁']['single_report_passed'])
        self.assertTrue(report['已知状态']['settlement_completed'])

    def test_additional_read_is_rejected_without_second_provider_request(self):
        report=self.run_native(read_more=True)
        self.assertEqual(report['结果'],'incomplete')
        self.assertEqual(report['本次门禁']['rejected_followup_count'],1)
        self.assertFalse(report['本次门禁']['single_report_passed'])

    def test_owning_application_waits_for_thread(self):
        report=self.run_native(delay=.08)
        self.assertEqual(report['结果'],'completed')
        self.assertTrue(read(self.out/'application_lifecycle.json')['thread_completed_before_close'])

    def failure(self):
        bundle=read(self.out/'bundle.json')
        node=bundle['state']['investigations']['single-saved-fact']
        self.assertEqual(node['status'],'failed')
        self.assertFalse(read(self.out/'gate.json')['single_report_passed'])
        return bundle['artifacts'][node['failure_record']['artifact_id']]

    def test_plain_json_text_is_not_native_report(self):
        self.run_native(mode='text')
        failure=self.failure()
        self.assertEqual(failure['details']['protocol_error'],'INVESTIGATION_NO_NATIVE_TOOL_CALL')
        self.assertEqual(failure['progress']['stage'],'response_parse')
        self.assertTrue(failure['progress']['response_saved'])
        self.assertFalse(failure['progress']['valid_report'])

    def test_invalid_native_arguments_fail_without_retry(self):
        self.run_native(mode='invalid')
        failure=self.failure()
        self.assertTrue(failure['progress']['response_saved'])
        self.assertFalse(failure['progress']['valid_report'])

    def test_http_allowlisted_error_survives_public_failure(self):
        fields=dict(code='invalid_request',type='invalid_request_error',param='tool_choice',
            message='Unsupported tool choice in thinking mode.')
        self.run_native(http_body=json.dumps(dict(error=fields)).encode())
        failure=self.failure()
        self.assertEqual(failure['details']['server_error']['fields'],fields)
        self.assertEqual(failure['details']['http_status'],400)
        self.assertEqual(failure['details']['provider_request_id'],'fixture-provider-id')
        self.assertTrue(failure['progress']['response_body_received'])
        self.assertFalse(failure['progress']['response_saved'])

    def test_http_nested_secret_is_omitted_from_public_evidence(self):
        marker='FIXTURE_SECRET_NESTED_NEVER_PERSIST'
        self.run_native(http_body=json.dumps(dict(error=dict(code='bad',
            message=dict(api_key=marker)))).encode())
        failure=self.failure()
        self.assertEqual(failure['details']['server_error']['omission_reasons'],['sensitive'])
        self.assertNotIn(marker,(self.out/'bundle.json').read_text(encoding='utf-8'))
        for path in self.host.store.root.glob('platform.sqlite*'):
            self.assertNotIn(marker,path.read_bytes().decode('latin1'))

    def test_error_body_bounds_echo_and_malformed_omissions(self):
        from tools.model_transports.deepseek import safe_server_error,ERROR_BODY_LIMIT
        cases=[(b'x'*(ERROR_BODY_LIMIT+1),'too_large'),(b'not json','invalid_json'),
            (b'\xff','invalid_encoding'),('\ud800','invalid_encoding'),
            (dict(error=dict(message='x'*513)),'message_over_limit'),
            (dict(error=dict(message='echo {request}')),'request_echo'),
            (dict(error=dict(message='Authorization: Bearer fixture-secret')),'sensitive'),
            (dict(error=dict(message='Echoed particular private question')),'request_echo'),
            (dict(error=dict(message='safe',headers={'Cookie':'fixture-secret'})),'unexpected_fields')]
        for body,reason in cases:
            with self.subTest(reason=reason):
                result=safe_server_error(body,payload=dict(messages=[dict(content='particular private question')]))
                self.assertIn(reason,result['omission_reasons'])
                self.assertFalse(result['raw_body_saved'])
                self.assertIsNone(result['fields']['message'])
        OBSERVATIONS[self._testMethodName]=dict(omission_cases=len(cases),real_provider_requests=0)


if __name__=='__main__':
    import unittest
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(SinglePublicValidationTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    target=single.ROOT/'evidence/research_request_compatibility_20261008_offline'
    target.mkdir(exist_ok=True)
    previous=list(target.glob('attempt_*.json'))
    atomic_json(target/f'attempt_{len(previous)+1:02d}.json',dict(tests=result.testsRun,
        failures=[dict(test=t.id(),trace=trace) for t,trace in result.failures],
        errors=[dict(test=t.id(),trace=trace) for t,trace in result.errors],observations=OBSERVATIONS,
        boundary='Production Host/public dispatcher/native parser/Store/ledger; external transport only substituted',
        real_provider_requests=0,credential_loads=0,scientific_operations=0))
    raise SystemExit(0 if result.wasSuccessful() else 1)
