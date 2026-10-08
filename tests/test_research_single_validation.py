"""Targeted single-entry offline checks; no imported scientific test classes."""
from contextlib import ExitStack
import gc
import json
from pathlib import Path
import shutil
import time
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

    def run_native(self,read_more=False,delay=0):
        count=[]
        def send(adapter,config,payload):
            count.append(1)
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
            return dict(usage=dict(prompt_tokens=12,completion_tokens=8,total_tokens=20),
                choices=[dict(finish_reason='tool_calls',message=dict(role='assistant',content=None,
                    tool_calls=[dict(id='offline-call',type='function',function=dict(name=name,arguments=json.dumps(arguments)))]))])
        with patch('tools.platform_models.DeepSeekAdapter._transport',new=send):
            single.execute(self.out,live=False,schedule=(5,10,15,20,25,30,35),cutoff=40.)
        self.assertEqual(len(count),1)
        self.assertEqual(self.host.store.session(self.host.run_id)['status'],'stopped')
        gate=read(self.out/'gate.json');self.assertTrue(gate['limits_passed'])
        self.assertEqual(gate['recorded_attempts'],1);self.assertEqual(gate['successful_prefetch_count'],1)
        self.assertEqual(gate['followup_read_count'],0)
        self.assertLessEqual(gate['public_operation_count'],8)
        self.assertLessEqual(self.host.store.remaining()['used']['tool_calls'],9)
        self.assertTrue(read(self.out/'historical_after.json')['unchanged'])
        OBSERVATIONS[self._testMethodName]=dict(gate=gate,lifecycle=read(self.out/'application_lifecycle.json'),
            ledger=self.host.store.remaining(),node=read(self.out/'bundle.json')['state']['investigations'],
            real_provider_requests=0,credential_loads=0,science=0)
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


if __name__=='__main__':
    import unittest
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(SinglePublicValidationTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    target=single.ROOT/'evidence/research_single_validation_20261008_offline'
    target.mkdir(exist_ok=True)
    previous=list(target.glob('attempt_*.json'))
    atomic_json(target/f'attempt_{len(previous)+1:02d}.json',dict(tests=result.testsRun,
        failures=[dict(test=t.id(),trace=trace) for t,trace in result.failures],
        errors=[dict(test=t.id(),trace=trace) for t,trace in result.errors],observations=OBSERVATIONS,
        boundary='Production Host/public dispatcher/native parser/Store/ledger; external transport only substituted',
        real_provider_requests=0,credential_loads=0,scientific_operations=0))
    raise SystemExit(0 if result.wasSuccessful() else 1)
