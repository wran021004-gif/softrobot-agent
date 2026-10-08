"""One narrowly selected public direct fixture; no scientific test imports."""
from contextlib import ExitStack
import gc
import json
from pathlib import Path
import shutil
from unittest import TestCase,main
from unittest.mock import patch
from uuid import uuid4
from tools import research_direct_validation as direct
from tools.state_io import read,atomic_json

OBSERVATIONS={}

class DirectValidationPreflightTests(TestCase):
    def test_frozen_plan_public_loop_and_closed_read_gate(self):
        folder=direct.ROOT/'runs'/('direct-fixture-'+uuid4().hex);folder.mkdir()
        stores=[]
        try:
            with ExitStack() as stack:
                stack.enter_context(patch('tools.platform_store.ROOT',folder))
                for name in ('tools.platform_models.DeepSeekAdapter._transport',
                    'examples.gvs_nmpc_route_experiment.load_credential','urllib.request.OpenerDirector.open',
                    'extensions.tendon_family.backends.MujocoBackend.solve','extensions.optimization.ipopt.IpoptSolver.solve',
                    'scipy.optimize.minimize','scipy.optimize.least_squares','scipy.integrate.solve_ivp'):
                    stack.enter_context(patch(name,side_effect=AssertionError('OFFLINE_PROHIBITED')))
                out=folder/'evidence';direct.prepare(out)
                manifest=read(out/'validation_manifest.json');stores.append(direct.ROOT/manifest['phases']['direct']['output'])
                sends=[]
                failures=[]
                from tools.research_investigations import InvestigationDispatcher
                handler=InvestigationDispatcher._handle_failure
                def capture(dispatcher,order,row,progress,exc,started):
                    from tools.model_transports.deepseek import sanitize_provider_text
                    failures.append(dict(node=order.investigation_id,stage=progress['stage'],
                        exception_type=type(exc).__name__,fixture_only_message=sanitize_provider_text(str(exc),'',512)))
                    return handler(dispatcher,order,row,progress,exc,started)
                def send(adapter,config,payload):
                    self.assertEqual(payload['tool_choice'],'auto');self.assertEqual(payload['thinking'],{'type':'enabled'})
                    self.assertEqual(payload['reasoning_effort'],'high');self.assertEqual(payload['max_tokens'],3000)
                    sends.append(payload)
                    packet=json.loads(payload['messages'][1]['content']);key=packet['investigation_id']
                    tools=[m for m in payload['messages'] if m['role']=='tool']
                    if packet['role']=='principal':
                        args=dict(interpretation='Offline insufficient-evidence disposition fixture only',
                            dispositions=[dict(investigation_id=t['investigation_id'],report=t['report'],
                                disposition='defer',reason='Offline fixture; semantic adoption is not tested.') for t in packet['disposition_targets']])
                        name='investigation_return'
                    elif not tools:
                        pointer='/sampled_settling' if key=='reach-question' else '/mean_complete_update_s'
                        args=dict(arguments=dict(reference=packet['reads'][0]['reference'],pointer=pointer),
                            reason='Fixture model-selected extra read',tool_version='1.0.0')
                        name=payload['tools'][1]['function']['name']
                    else:
                        page=json.loads(tools[-1]['content']);pointer=page['pointer']
                        value=page['content'];pointer+='/passed' if key=='reach-question' else ''
                        if key=='reach-question':value=value['passed']
                        args=dict(facts=[dict(statement='Fixture recorded value only',reference=page['source'],pointer=pointer,value=value)],
                            interpretation='Offline interface script, not research reasoning')
                        name='investigation_return'
                    return dict(usage=dict(prompt_tokens=12,completion_tokens=8,total_tokens=20),choices=[dict(finish_reason='tool_calls',
                        message=dict(role='assistant',content=None,tool_calls=[dict(id='fixture-'+key,type='function',
                            function=dict(name=name,arguments=json.dumps(args)))]))])
                with patch('tools.platform_models.DeepSeekAdapter._transport',new=send), \
                        patch.object(InvestigationDispatcher,'_handle_failure',new=capture):direct.execute(out,live=False)
                OBSERVATIONS['public_direct']=dict(gate=read(out/'direct_gate.json'),result=read(out/'direct_result.json'),
                    lifecycle=read(out/'application_lifecycle.json'),fixture_failures=failures,
                    bundle=read(out/'direct_bundle.json'),real_provider_calls=0)
                self.assertEqual(len(sends),5)
                result=read(out/'direct_result.json');self.assertEqual(result['status'],'formal_dispositions_recorded')
                gate=read(out/'direct_gate.json');self.assertEqual(len(gate['qualifying_followup_reads']),2)
                self.assertEqual(gate['gates']['actual_provider_interaction'],'unverified')
                self.assertEqual(gate['acceptance_coverage'],'unverified; no accepted report')
                bundle=read(out/'direct_bundle.json');principal=bundle['state']['investigations']['principal-synthesis']
                self.assertLessEqual(principal['usage']['tool_calls']+len(bundle['state']['principal_investigation_reads']),8)
                self.assertTrue(read(out/'application_lifecycle.json')['thread_completed_before_close'])
                self.assertTrue(read(out/'historical_after.json')['unchanged'])
                with self.assertRaisesRegex(ValueError,'NO_REPEATED_LAUNCH'):direct.execute(out,live=False)
                OBSERVATIONS['public_direct']=dict(gate=gate,result=result,lifecycle=read(out/'application_lifecycle.json'),
                    node_usage={k:n['usage'] for k,n in bundle['state']['investigations'].items()},real_provider_calls=0)
        finally:
            gc.collect()
            for path in [*stores,folder]:
                assert path.resolve().is_relative_to((direct.ROOT/'runs').resolve())
                shutil.rmtree(path)

if __name__=='__main__':
    import unittest
    from tests.test_research_validation_gate import SavedGateTests
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(DirectValidationPreflightTests),
        unittest.defaultTestLoader.loadTestsFromTestCase(SavedGateTests)])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    out=direct.ROOT/'evidence/research_direct_validation_20261008_offline';out.mkdir(exist_ok=True)
    atomic_json(out/f'attempt_{len(list(out.glob("attempt_*.json")))+1:02d}.json',dict(tests=result.testsRun,
        failures=[dict(test=t.id(),trace=trace) for t,trace in result.failures],errors=[dict(test=t.id(),trace=trace) for t,trace in result.errors],
        observations=OBSERVATIONS,boundary='Existing direct scenario/Host/public native/Store/ledger; deterministic external adapter only',
        real_provider_calls=0,credential_loads=0,science=0))
    raise SystemExit(0 if result.wasSuccessful() else 1)
