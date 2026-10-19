"""Engineering fixtures only; no real engine or provider starts."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest
import subprocess
from pathlib import Path
from uuid import uuid4
from tools.research import tool_readiness as tr


class ReadinessTests(unittest.TestCase):
    def session(self):
        s=Mock(startup_stage='ready',timings={});s.__enter__=Mock(return_value=s);s.__exit__=Mock(return_value=False)
        s.engine.sqrt.return_value=2.;s.environment={'fixture':True}
        return s

    def test_success_gateway_calculation_shutdown(self):
        s=self.session()
        with patch('extensions.tendon_family.sorosim_session.dependency_identity',return_value={'fixture':True}),patch.dict('os.environ',SOROSIM_ROOT='fixture'):
            result=tr.probe(lambda:s)
        self.assertEqual(result['status'],'ready');self.assertIn('shutdown',result['steps'])
        s.__exit__.assert_called_once();self.assertFalse(result['scientific_evidence'])

    def test_unicode_startup_preserved_not_infeasibility(self):
        s=self.session();s.startup_stage='engine_start'
        s.__enter__.side_effect=UnicodeDecodeError('utf8',b'\xbe',0,1,'fixture')
        with patch('extensions.tendon_family.sorosim_session.dependency_identity',return_value={}),patch.dict('os.environ',SOROSIM_ROOT='fixture'):
            r=tr.probe(lambda:s)
        self.assertEqual(r['status'],'engine_start_failed');self.assertEqual(r['error'],'UnicodeDecodeError')
        self.assertEqual(r['encoding_failure']['raw_hex'],'be');self.assertIn('UnicodeDecodeError',r['traceback'])

    def test_gateway_distinguished(self):
        s=self.session();s.startup_stage='gateway';s.__enter__.side_effect=RuntimeError('fixture gateway')
        with patch('extensions.tendon_family.sorosim_session.dependency_identity',return_value={}),patch.dict('os.environ',SOROSIM_ROOT='fixture'):
            self.assertEqual(tr.probe(lambda:s)['status'],'gateway_failed')

    def test_missing_dependency_no_start(self):
        factory=Mock()
        with patch('extensions.tendon_family.sorosim_session.dependency_identity',side_effect=ValueError('pin mismatch')),patch.dict('os.environ',SOROSIM_ROOT='fixture'):
            self.assertEqual(tr.probe(factory)['status'],'dependency_unavailable')
        factory.assert_not_called()

    def test_unavailable_admission_before_science(self):
        s={'spec':{'tool_readiness':{'sorosim_matlab':{'status':'timeout'}},'configuration':{'policy':{'controller':{'extension_id':'controller.sorosim_matlab_nmpc'}}}}}
        with patch.object(tr,'state',return_value=s):
            with self.assertRaisesRegex(ValueError,'ENGINEERING_TOOL_UNAVAILABLE'):tr.require(Mock(),'analysis')
            tr.require(Mock(),'physical_replay')

    def test_runtime_failure_latches_original_reference(self):
        host=Mock();s={'spec':{}}
        with patch.object(tr,'state',return_value=s),patch.object(tr,'update') as update:
            tr.observe_failure(host,{'error':'UnicodeDecodeError'},{'artifact_id':'a'*64,'media_type':'application/json'})
            self.assertFalse(update.call_args.kwargs['tool_failures']['sorosim_matlab']['scientific_infeasibility'])

    def test_timeout_owned_by_engineering_store_no_scientific_charge(self):
        host=Mock();host.run_id='fixture';host.actor='fixture'
        host.store.root=Path('runs/s8-test-'+uuid4().hex);host.store.root.mkdir()
        host.store.reserve.return_value=({'execution_id':'fixture'},True)
        exc=subprocess.TimeoutExpired('fixture',1);exc.termination_confirmed=True
        s={'spec':{'mode':'engineering_numerical','runtime':{'research_python':'fixture'}}}
        with patch.object(tr,'state',return_value=s),patch.object(tr,'save',return_value={}),patch('tools.service_execution._run_contained',side_effect=exc):
            r=tr.check(host,timeout_s=1)
        self.assertEqual(r['status'],'timeout');self.assertTrue(r['boundary']['termination_confirmed'])
        reserved=host.store.reserve.call_args.args[4]
        self.assertEqual(reserved['model_calls'],0);self.assertEqual(reserved['backend_solves'],0)
        self.assertEqual(reserved['tool_calls'],1)


if __name__=='__main__':unittest.main()
